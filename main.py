import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(
        description="my_neo-agent: AI Coding Agent with Web UI Dashboard and CLI shell",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--web", action="store_true", help="Launch FastAPI Web UI Dashboard server")
    group.add_argument("--cli", action="store_true", help="Launch interactive Rich Terminal CLI mode")
    group.add_argument("--desktop", action="store_true", help="Launch transparent Desktop Floating Mascot Companion app")
    
    parser.add_argument("--port", type=int, default=8000, help="Port for Web UI Dashboard server (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host binding for Web server (default: 127.0.0.1)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for Uvicorn dev mode")

    args = parser.parse_args()

    if args.web:
        print(f"🚀 Launching my_neo-agent Web Dashboard on http://{args.host}:{args.port}")
        import uvicorn
        uvicorn.run("server:app", host=args.host, port=args.port, reload=args.reload)

    elif args.cli:
        print("💻 Starting my_neo-agent Terminal CLI...")
        from cli import main_cli
        main_cli()

    elif args.desktop:
        print("👾 Starting my_neo-agent Desktop Floating Mascot Overlay...")
        from desktop_mascot import launch_desktop_mascot
        launch_desktop_mascot()


if __name__ == "__main__":
    main()
