import os
import sys
import json
import asyncio
from typing import List, Dict, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI
import logging
from rich.console import Console

console = Console()

class AISREContext:
    def __init__(self):
        self.history: List[Dict] = []
        self.client = self._init_openai()
        self.mcp_session: Optional[ClientSession] = None
        self.tools: List[Dict] = []
    
    def _init_openai(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            console.print("[red]❌ Error: OPENAI_API_KEY not found in environment.[/red]")
            sys.exit(1)
        return AsyncOpenAI(api_key=api_key)

    async def connect_mcp(self):
        # Connect to the Kubernetes MCP Server
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "kubernetes-mcp-server"],
            env=os.environ.copy()
        )
        
        # Determine the context for the connection
        self.stdio_context = stdio_client(server_params)
        read, write = await self.stdio_context.__aenter__()
        
        self.mcp_session = ClientSession(read, write)
        await self.mcp_session.__aenter__()
        await self.mcp_session.initialize()
        
        # Discover tools
        tools_result = await self.mcp_session.list_tools()
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.inputSchema
                }
            } for t in tools_result.tools
        ]
        console.print(f"[green]✅ Connected to K8s MCP! Found {len(self.tools)} tools.[/green]")

    async def cleanup(self):
        if self.mcp_session:
            await self.mcp_session.__aexit__(None, None, None)
        if hasattr(self, 'stdio_context'):
            await self.stdio_context.__aexit__(None, None, None)

    async def run_query(self, user_query: str):
        """Runs the main agent loop for a query"""
        self.history.append({"role": "user", "content": user_query})
        
        console.print(f"[cyan]🤖 Assessing: {user_query}[/cyan]")
        
        response = await self.client.chat.completions.create(
            model=os.getenv("MODEL_NAME", "gpt-4o"),
            messages=[
                {"role": "system", "content": "You are a Senior Site Reliability Engineer (SRE). Your job is to diagnose, fix, and manage Kubernetes clusters. You have access to powerful tools via MCP. Use them proactively. Always confirm destructive actions (delete, scale down to 0) before executing unless explicitly authorized. Be concise and technical."},
                *self.history
            ],
            tools=self.tools,
            tool_choice="auto"
        )
        
        msg = response.choices[0].message
        
        if msg.tool_calls:
            self.history.append(msg)
            
            for tool_call in msg.tool_calls:
                console.print(f"[yellow]🛠️  Executing: {tool_call.function.name}[/yellow]")
                
                tool_args = json.loads(tool_call.function.arguments)
                try:
                    result = await self.mcp_session.call_tool(tool_call.function.name, tool_args)
                    output = str(result.content)
                    console.print(f"[dim]   Result size: {len(output)} chars[/dim]")
                except Exception as e:
                    output = f"Error: {str(e)}"
                    console.print(f"[red]❌ Tool Failure: {str(e)}[/red]")

                self.history.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": output
                })
            
            # Recursive call to process tool results
            final_res = await self.client.chat.completions.create(
                model=os.getenv("MODEL_NAME", "gpt-4o"),
                messages=[
                    {"role": "system", "content": "You are a Senior Site Reliability Engineer (SRE)."},
                    *self.history
                ]
            )
            final_msg = final_res.choices[0].message.content
            self.history.append({"role": "assistant", "content": final_msg})
            console.print(f"\n[bold white]{final_msg}[/bold white]\n")
            return final_msg
        else:
            self.history.append(msg)
            console.print(f"\n[bold white]{msg.content}[/bold white]\n")
            return msg.content
