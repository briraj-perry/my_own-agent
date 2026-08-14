"""Interactive Terminal CLI interface for my_neo-agent with Folder Navigation, Multi-Agent Telemetry & Model Selection."""

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

from agent import NeoAgentCore
from indexer import CodebaseIndexer
from tools import file_tools

console = Console()

MASCOT_ASCII = """
   [bold #9d4edd]┌─────────────────────────┐[/bold #9d4edd]
   [bold #9d4edd]│[/bold #9d4edd]   ┌───────────────┐   [bold #9d4edd]│[/bold #9d4edd]
   [bold #9d4edd]│[/bold #9d4edd]   │  [bold #00f5d4]> _[/bold #00f5d4]         │   [bold #9d4edd]│[/bold #9d4edd]   [bold #f72585]NEO-AGENT Terminal CLI Studio[/bold #f72585]
   [bold #9d4edd]│[/bold #9d4edd]   └───────────────┘   [bold #9d4edd]│[/bold #9d4edd]   [dim #4cc9f0]Autonomous Multi-Agent & Code Architecture[/dim #4cc9f0]
   [bold #9d4edd]│[/bold #9d4edd]       [bold #f72585]> -[/bold #f72585]           [bold #9d4edd]│[/bold #9d4edd]
   [bold #9d4edd]└──────┬─────────┬────────┘[/bold #9d4edd]
          [bold #9d4edd]│         │[/bold #9d4edd]
"""


class NeoCLI:
    def __init__(self):
        self.agent = NeoAgentCore()
        self.indexer = CodebaseIndexer(root_dir=file_tools.get_workspace_root())

    def get_current_folder(self) -> str:
        return file_tools.get_workspace_root()

    def print_banner(self):
        console.clear()
        console.print(MASCOT_ASCII)
        curr_folder = self.get_current_folder()
        model_name = self.agent.active_model
        console.print(Panel(
            f"[bold #00f5d4]Welcome to my_neo-agent CLI Studio[/bold #00f5d4]\n"
            f"📁 [bold white]Active Folder:[/bold white] [bold cyan]{curr_folder}[/bold cyan]\n"
            f"⚡ [bold white]Active Model:[/bold white]  [bold magenta]{model_name}[/bold magenta]\n\n"
            f"Commands:\n"
            f"  • [bold #f72585]/folder <path>[/bold #f72585] or [bold #f72585]/cd <path>[/bold #f72585] — Open & switch to any folder on your computer\n"
            f"  • [bold #f72585]/eagle[/bold #f72585]                — 🦅 Eagle Agent: Deep full-folder audit, auto-repair & review\n"
            f"  • [bold #f72585]/files[/bold #f72585]                — View all files in active folder\n"
            f"  • [bold #f72585]/fix[/bold #f72585] or [bold #f72585]/autofix[/bold #f72585]        — Auto-scan & repair errors across all files\n"
            f"  • [bold #f72585]/model[/bold #f72585]                — Change active Ollama model\n"
            f"  • [bold #f72585]/reindex[/bold #f72585]              — Refresh codebase AST symbol index\n"
            f"  • [bold #f72585]/clear[/bold #f72585]                — Clear terminal screen\n"
            f"  • [bold #f72585]/exit[/bold #f72585]                 — Exit CLI",
            border_style="purple",
            title="[bold #9d4edd]my_neo-agent v3.0[/bold #9d4edd]"
        ))

    def switch_folder(self, target_path: str):
        """Switches the active workspace folder to ANY system directory on disk."""
        target_path = target_path.strip().strip('"\'')
        if not target_path or target_path == ".":
            target_path = os.getcwd()

        res = file_tools.set_workspace_root(target_path)
        if res.get("status") == "success":
            self.agent.active_working_folder = file_tools.get_workspace_root()
            self.indexer.root_dir = file_tools.get_workspace_root()
            self.indexer.reindex()
            code_files = file_tools.get_folder_code_files(file_tools.get_workspace_root())
            py_count = sum(1 for cf in code_files if cf.get("is_python"))
            
            console.print(Panel(
                f"📁 [bold green]Active Folder Successfully Changed![/bold green]\n\n"
                f"Path: [bold cyan]{file_tools.get_workspace_root()}[/bold cyan]\n"
                f"Files Indexed: [bold white]{len(code_files)} total ({py_count} Python files)[/bold white]",
                border_style="green",
                title="[bold green]WORKSPACE SWITCHED[/bold green]"
            ))
        else:
            console.print(f"[bold red]✖ {res.get('message', 'Failed to open directory.')}[/bold red]")

    async def run_chat_loop(self):
        self.print_banner()
        self.indexer.scan_files()
        
        while True:
            try:
                curr_disp = os.path.basename(self.get_current_folder()) or self.get_current_folder()
                user_input = Prompt.ask(f"\n[bold #f72585]neo-agent[/bold #f72585] [dim]({curr_disp})[/dim] [bold #00f5d4]>[/bold #00f5d4]").strip()
                if not user_input:
                    continue

                # Exit command
                if user_input.lower() in ["/exit", "exit", "quit", "/quit"]:
                    console.print("[yellow]Goodbye from my_neo-agent![/yellow]")
                    break

                # Clear screen
                if user_input.lower() in ["/clear", "cls", "clear"]:
                    self.print_banner()
                    continue

                # Folder / CD command
                if user_input.lower().startswith(("/folder", "/cd", "cd ")):
                    parts = user_input.split(maxsplit=1)
                    if len(parts) > 1:
                        target = parts[1]
                    else:
                        target = Prompt.ask("Enter folder path on your computer (e.g. C:/projects/my-app)", default=self.get_current_folder())
                    self.switch_folder(target)
                    continue

                # Re-index command
                if user_input.lower() == "/reindex":
                    res = self.indexer.reindex()
                    console.print(f"[bold #00f5d4]✓ {res['message']}[/bold #00f5d4]")
                    continue

                # Files list command
                if user_input.lower() in ["/files", "/ls", "ls", "dir"]:
                    curr_root = file_tools.get_workspace_root()
                    code_files = file_tools.get_folder_code_files(curr_root)
                    table = Table(title=f"Files in '{curr_root}' ({len(code_files)} items)", border_style="purple")
                    table.add_column("Type", style="dim", width=8)
                    table.add_column("Relative Path", style="cyan")
                    table.add_column("Full System Path", style="dim")
                    
                    for item in code_files[:40]:
                        icon = "🐍 Python" if item.get("is_python") else f"📄 {item['ext']}"
                        table.add_row(icon, item["rel_path"], item["full_path"])
                    console.print(table)
                    if len(code_files) > 40:
                        console.print(f"[dim]... and {len(code_files) - 40} more files[/dim]")
                    continue

                # Auto-Fix command
                if user_input.lower() in ["/fix", "/autofix"]:
                    curr_root = file_tools.get_workspace_root()
                    console.print(f"\n[bold cyan]🔍 Scanning & Diagnosing all files in '{curr_root}'...[/bold cyan]")
                    res = await self.agent.analyze_and_autofix_folder(curr_root)
                    if res.get("status") in ["fixed", "success"]:
                        console.print(Panel(
                            f"[bold green]🎉 {res.get('message')}[/bold green]\n\n"
                            f"Target File: [bold cyan]{res.get('target_file')}[/bold cyan]\n"
                            f"Path: {res.get('full_path')}\n\n"
                            f"[dim]Diagnostic Details:[/dim]\n{res.get('analysis', '')[:600]}",
                            border_style="green",
                            title="[bold green]AUTO-FIX COMPLETE[/bold green]"
                        ))
                    elif res.get("status") == "clean":
                        console.print(f"[bold green]✅ {res.get('message')}[/bold green]")
                    else:
                        console.print(f"[bold yellow]⚠️ Notice: {res.get('message')}[/bold yellow]")
                    continue

                # Eagle Agent full-folder audit & review command
                if user_input.lower() in ["/eagle", "eagle"]:
                    curr_root = file_tools.get_workspace_root()
                    console.print(f"\n[bold magenta]🦅 Eagle Agent: Starting deep whole-folder audit on '{curr_root}'...[/bold magenta]")
                    res = await self.agent.analyze_and_review_with_eagle(curr_root)
                    if res.get("status") in ["fixed", "success"]:
                        fixed_files = res.get("fixed_files", [])
                        fixed_str = ", ".join(f"[bold cyan]{f['file']}[/bold cyan]" for f in fixed_files) if fixed_files else "None (Codebase verified clean!)"
                        console.print(Panel(
                            f"[bold green]🎉 {res.get('message')}[/bold green]\n\n"
                            f"Files Repaired: {fixed_str}\n\n"
                            f"[bold yellow]Application Quality Review:[/bold yellow]\n\n{res.get('analysis', '')}",
                            border_style="magenta",
                            title="[bold magenta]🦅 EAGLE AGENT AUDIT & REVIEW[/bold magenta]"
                        ))
                    elif res.get("status") == "clean":
                        console.print(f"[bold green]✅ {res.get('message')}[/bold green]")
                    else:
                        console.print(f"[bold red]✖ {res.get('message')}[/bold red]")
                    continue

                # Model selection command
                if user_input.lower() == "/model":
                    available_models = self.agent.get_available_models()
                    console.print("\n[bold #9d4edd]Available Models:[/bold #9d4edd]")
                    for idx, m in enumerate(available_models, 1):
                        is_active = " [bold #00f5d4](Active)[/bold #00f5d4]" if m["id"] == self.agent.active_model else ""
                        console.print(f" {idx}. [bold]{m['name']}[/bold] ({m['id']}){is_active}")
                    
                    choice = Prompt.ask("Select model number or ID", default="1")
                    try:
                        if choice.isdigit():
                            chosen_idx = int(choice) - 1
                            if 0 <= chosen_idx < len(available_models):
                                new_m = available_models[chosen_idx]["id"]
                                self.agent.set_model(new_m)
                                console.print(f"[bold #00f5d4]✓ Active model set to: {new_m}[/bold #00f5d4]")
                            else:
                                console.print("[red]Invalid selection.[/red]")
                        else:
                            self.agent.set_model(choice)
                            console.print(f"[bold #00f5d4]✓ Active model set to: {choice}[/bold #00f5d4]")
                    except Exception as ex:
                        console.print(f"[red]Error selecting model: {ex}[/red]")
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

            elif evt_type == "plan_generated":
                plan = event.get("plan", {})
                steps = plan.get("steps", [])
                table = Table(title=f"🧠 Execution Plan: {plan.get('title', 'Task Plan')}", border_style="purple")
                table.add_column("Step", style="dim", width=8)
                table.add_column("Title & Goal", style="cyan")
                table.add_column("Target", style="yellow")
                table.add_column("Role", style="green")
                for s in steps:
                    table.add_row(s.get("step_id", ""), s.get("title", ""), s.get("target_file") or "—", s.get("assigned_role", "Engineer"))
                console.print(table)

            elif evt_type == "token":
                token = event.get("content", "")
                full_text += token
                sys.stdout.write(token)
                sys.stdout.flush()

            elif evt_type == "folder_selection_required":
                console.print("\n")
                available = event.get("available_folders", [])
                def_folder = event.get("default_folder", file_tools.get_workspace_root())
                console.print(Panel(
                    f"[bold cyan]📁 TARGET FOLDER SELECTION REQUIRED[/bold cyan]\n\n"
                    f"{event.get('description', 'Where do you want to save/work on files?')}\n"
                    f"Available folders:\n" + "\n".join(f"  • [green]{f}[/green]" for f in available[:5]) +
                    f"\n\n[dim]Default: {def_folder}[/dim]",
                    border_style="cyan",
                    title="[bold yellow]FOLDER SELECTION[/bold yellow]"
                ))
                chosen = Prompt.ask("Enter target folder path", default=def_folder)
                self.agent.resolve_folder_selection(event.get("id"), chosen)

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
                
                approved = Confirm.ask("Do you authorize this operation?", default=True)
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
