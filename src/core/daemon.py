
import asyncio
import json
import subprocess
from rich.console import Console
from src.core.agent import AISREContext

console = Console()

class AISREDaemon:
    def __init__(self, interval: int = 60, auto_fix: bool = False):
        self.interval = interval
        self.auto_fix = auto_fix
        self.ctx = AISREContext()
        self.running = False

    async def start(self):
        """Starts the monitoring loop"""
        mode_str = "[bold red]🚑 SELF-HEAL MODE ENABLED[/bold red]" if self.auto_fix else "[green]👀 READ-ONLY MODE[/green]"
        console.print(f"[bold green]AI SRE Observer Daemon starting... (Interval: {self.interval}s)[/bold green]")
        console.print(f"Mode: {mode_str}")
        
        # Connect to MCP (Tools)
        await self.ctx.connect_mcp()
        
        self.running = True
        try:
            while self.running:
                await self.monitor_cycle()
                await asyncio.sleep(self.interval)
        except KeyboardInterrupt:
            console.print("[bold yellow]🛑 Stopping Daemon...[/bold yellow]")
        finally:
            await self.ctx.cleanup()

    async def monitor_cycle(self):
        """One iteration of monitoring"""
        console.print("[dim]🔍 Scanning cluster for issues...[/dim]")
        
        unhealthy_pods = self._get_unhealthy_pods()
        
        if not unhealthy_pods:
            console.print("[green]✅ Cluster looks healthy.[/green]")
            return

        console.print(f"[bold red]⚠️  Found {len(unhealthy_pods)} unhealthy pods![/bold red]")
        
        for pod in unhealthy_pods:
            name = pod['metadata']['name']
            ns = pod['metadata']['namespace']
            status = pod['status']['phase']
            reason = pod['status'].get('containerStatuses', [{}])[0].get('state', {}).get('waiting', {}).get('reason', 'Unknown')
            
            console.print(f"👉 Investigating {name} ({ns}) - {status}/{reason}")
            
            # Formulate a query for the Agent
            query = f"Diagnose why the pod '{name}' in namespace '{ns}' is failing. It has status '{status}' and reason '{reason}'. Check logs and events."
            
            if self.auto_fix:
                query += " IMPORTANT: You are running in SELF-HEALING mode. If the issue is a transient crash, you are authorized to delete the pod. If it is a configuration error (like bad env vars, args, or missing secrets), you are AUTHORIZED to PATCH the deployment to fix it. Use your tools to find the deployment and modify it."
            else:
                query += " You are in READ-ONLY mode. Do not change any state. Just diagnose."

            # Delegate to the AI Agent for reasoning
            await self.ctx.run_query(query)

    def _get_unhealthy_pods(self) -> list:
        """
        Polls k8s using kubectl directly for efficiency.
        Returns detailed list of unhealthy pods.
        """
        try:
            # Get all pods in JSON format
            result = subprocess.run(
                ["kubectl", "get", "pods", "-A", "-o", "json"],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            
            failing = []
            for pod in data.get('items', []):
                phase = pod['status'].get('phase')
                
                # Check for CrashLoopBackOff or Error
                container_statuses = pod['status'].get('containerStatuses', [])
                is_crashing = False
                for cs in container_statuses:
                    state = cs.get('state', {})
                    if 'waiting' in state and state['waiting'].get('reason') in ['CrashLoopBackOff', 'ImagePullBackOff', 'ErrImagePull']:
                        is_crashing = True
                    if 'terminated' in state and state['terminated'].get('exitCode') != 0:
                        is_crashing = True

                # Logic: If not Running/Succeeded OR explicitly crashing
                if phase not in ['Running', 'Succeeded'] or is_crashing:
                     # Double check if it's just Pending creation (not an error yet)? 
                     # For now, let's focus on known bad states or simple non-running if older than X?
                     # Let's simple filter for now:
                     if phase == 'Failed' or is_crashing:
                         failing.append(pod)
                     elif phase == 'Pending':
                         # If pending for too long, maybe? keeping it simple for v1.
                         pass
            
            return failing

        except subprocess.CalledProcessError as e:
            console.print(f"[red]❌ Failed to scan cluster: {e}[/red]")
            return []
        except Exception as e:
            console.print(f"[red]❌ Error parsing pod data: {e}[/red]")
            return []
