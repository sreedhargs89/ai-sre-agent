import asyncio
import os
import typer
from dotenv import load_dotenv
from src.core.agent import AISREContext

# Load env vars
load_dotenv()

app = typer.Typer()

@app.command()
def interact():
    """Start an interactive session with the AI SRE Agent"""
    async def _run():
        agent = AISREContext()
        await agent.connect_mcp()
        
        print("\n🚀 AI SRE Agent Ready. Type 'exit' to quit.")
        print("💡 Tip: Try 'Show me all crashing pods' or 'Create a Redis deployment'\n")
        
        try:
            while True:
                query = input("SRE > ")
                if query.lower() in ['exit', 'quit']:
                    break
                if not query.strip():
                    continue
                    
                await agent.run_query(query)
        finally:
            await agent.cleanup()

    asyncio.run(_run())

@app.command()
def run(query: str):
    """Run a single specific SRE task"""
    async def _run():
        agent = AISREContext()
        await agent.connect_mcp()
        try:
            await agent.run_query(query)
        finally:
            await agent.cleanup()
            
    asyncio.run(_run())

if __name__ == "__main__":
    app()
