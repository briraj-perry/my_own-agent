import sys
import os
import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.table import Table
from rich.syntax import Syntax
from rich.live import Live
from rich.align import Align
from rich.text import Text

from agent.orchestrator import MasterOrchestrator
from indexer import CodebaseIndexer

console = Console()

MASCOT_ASCII = """
   [bold #9d4edd]┌─────────────────────────┐[/bold #9d4edd]
   [bold #9d4edd]│[/bold #9d4edd]   ┌───────────────┐   [bold #9d4edd]│[/bold #9d4edd]
   [bold #9d4edd]│[/bold #9d4edd]   │  [bold #00f5d4]> _[/bold #00f5d4]         │   [bold #9d4edd]│[/bold #9d4edd]   [bold #f72585]NEO-AGENT Terminal CLI[/bold #f72585]
   [bold #9d4edd]│[/bold #9d4edd]   └───────────────┘   [bold #9d4edd]│[/bold #9d4edd]   [dim #4cc9f0]Powered by LangGraph & Ollama[/dim #4cc9f0]
   [bold #9d4edd]│[/bold #9d4edd]       [bold #f72585]> -[/bold #f72585]           [bold #9d4edd]│[/bold #9d4edd]
   [bold #9d4edd]└──────┬─────────┬────────┘[/bold #9d4edd]
          [bold #9d4edd]│         │[/bold #9d4edd]
"""

class NeoCLI:
    def __init__(self):
        self.agent = MasterOrchestrator()
        self.indexer = CodebaseIndexer(root_dir=os.path.dirname(__file__))

    def print_banner(self):
        console.clear()
        console.print(MASCOT_ASCII)
        console.print(Panel(
            "[bold #00f5d4]Welcome to my_neo-agent CLI[/bold #00f5d4]\n"
            "Commands: [bold #f72585]/model[/bold #f72585] - select model | [bold #f72585]/reindex[/bold #f72585] - scan codebase | [bold #f72585]/files[/bold #f72585] - view tree | [bold #f72585]/exit[/bold #f72585] - quit",
            border_style="purple",
            title="[bold #9d4edd]my_neo-agent v1.0[/bold #9d4edd]"
        ))

    async def run_chat_loop(self):
        self.print_banner()
        self.indexer.scan_files()
        
        while True:
            try:
                user_input = Prompt.ask("\n[bold #f72585]neo-agent[/bold #f72585] [bold #00f5d4]>[/bold #00f5d4]").strip()
                if not user_input:
                    continue

                if user_input.lower() in ["/exit", "exit", "quit", "/quit"]:
                    console.print("[yellow]Goodbye from my_neo-agent![/yellow]")
                    break

                if user_input.lower() == "/reindex":
                    res = self.indexer.reindex()
                    console.print(f"[bold #00f5d4]✓ {res['message']}[/bold #00f5d4]")
                    continue

                if user_input.lower() == "/files":
                    tree = self.indexer.get_file_tree()
                    table = Table(title="Workspace Codebase Tree", border_style="purple")
                    table.add_column("Type", style="dim")
                    table.add_column("Path", style="cyan")
                    table.add_column("Lines", justify="right", style="green")
                    
                    for item in self.indexer.indexed_files:
                        table.add_row(item["ext"], item["path"], str(item["lines"]))
                    console.print(table)
                    continue

                if user_input.lower() == "/model":
                    console.print("\n[bold #9d4edd]Available Models:[/bold #9d4edd]")
                    for idx, m in enumerate(self.agent.AVAILABLE_MODELS, 1):
                        is_active = " [bold #00f5d4](Active)[/bold #00f5d4]" if m["id"] == self.agent.active_model else ""
                        console.print(f" {idx}. [bold]{m['name']}[/bold] ({m['id']}){is_active}")
                    
                    choice = Prompt.ask("Select model number", default="1")
                    try:
                        chosen_idx = int(choice) - 1
                        if 0 <= chosen_idx < len(self.agent.AVAILABLE_MODELS):
                            new_m = self.agent.AVAILABLE_MODELS[chosen_idx]["id"]
                            self.agent.set_model(new_m)
                            console.print(f"[bold #00f5d4]✓ Active model set to: {new_m}[/bold #00f5d4]")
                        else:
                            console.print("[red]Invalid selection.[/red]")
                    except ValueError:
                        console.print("[red]Invalid input.[/red]")
                    continue

                # Process Agent execution stream
                await self.process_query(user_input)

            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Session terminated.[/yellow]")
                break

    async def process_query(self, query: str):
        full_text = ""
        console.print(f"\n[dim #4cc9f0]🤖 Neo Agent Processing ({self.agent.active_model})...[/dim #4cc9f0]\n")

        async for event in self.agent.stream_response(query):
            evt_type = event.get("type")

            if evt_type == "state":
                status = event.get("status")
                mascot_st = event.get("mascot_state")
                console.print(f"[dim purple]└─ State [{mascot_st}]: {status}[/dim purple]")

            elif evt_type == "token":
                token = event.get("content", "")
                full_text += token
                sys.stdout.write(token)
                sys.stdout.flush()

            elif evt_type == "routing":
                target = event.get("target_agent", "neo").upper()
                reason = event.get("reasoning", "")
                console.print(f"[bold cyan]🎯 Routed to [{target} AGENT]: {reason}[/bold cyan]")

            elif evt_type == "artifact":
                art = event.get("artifact", {})
                console.print(f"\n[bold green]📦 Artifact: {art.get('title')} ({art.get('file_path')})[/bold green]")

            elif evt_type == "permission_request":
                console.print("\n")
                console.print(Panel(
                    f"[bold red]⚠️ PERMISSION REQUEST REQUIRED[/bold red]\n\n"
                    f"[bold white]Title:[/bold white] {event.get('title')}\n"
                    f"[bold white]Action:[/bold white] {event.get('action')}\n"
                    f"[bold yellow]Command:[/bold yellow] [italic]{event.get('command')}[/italic]\n"
                    f"[bold red]Risk Level:[/bold red] {event.get('risk_level')}",
                    border_style="red",
                    title="[bold yellow]NEO SECURITY PROMPT[/bold yellow]"
                ))
                
                approved = Confirm.ask("Do you authorize this operation?", default=False)
                self.agent.resolve_permission(event.get("id"), approved)
                if not approved:
                    console.print("[red]✖ Operation rejected by user.[/red]")

            elif evt_type == "framework_selection_required":
                console.print("\n")
                console.print(Panel(
                    "[bold cyan]⚡ CHOOSE APP FRAMEWORK[/bold cyan]\n\n"
                    "Do you want to build this using Next.js or normal HTML?\n"
                    "• [bold green]Yes[/bold green]: Next.js (Claw Agent)\n"
                    "• [bold yellow]No[/bold yellow]: Normal HTML (Neo Agent)",
                    border_style="cyan",
                    title="[bold yellow]FRAMEWORK SELECTION PROMPT[/bold yellow]"
                ))
                use_nextjs = Confirm.ask("Do you want to build this using Next.js?", default=True)
                choice = "nextjs" if use_nextjs else "html"
                self.agent.resolve_framework_selection(event.get("id"), choice)


            elif evt_type == "execution_log":
                console.print(Panel(
                    Syntax(event.get("output", ""), "bash", theme="monokai"),
                    title="[bold cyan]Live Execution Output[/bold cyan]",
                    border_style="cyan"
                ))

        console.print("\n")

def main_cli():
    cli_app = NeoCLI()
    asyncio.run(cli_app.run_chat_loop())

if __name__ == "__main__":
    main_cli()
