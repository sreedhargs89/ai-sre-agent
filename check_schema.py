from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
import os
import json

async def check_tool(tool_name):
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "kubernetes-mcp-server"],
        env=os.environ.copy()
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            for tool in tools.tools:
                if tool.name == tool_name:
                    print(json.dumps(tool.inputSchema, indent=2))
                    return

if __name__ == "__main__":
    asyncio.run(check_tool("resources_create_or_update"))
