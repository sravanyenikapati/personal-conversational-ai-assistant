"""
Personal AI Assistant — Entry Point.

Usage:
    python main.py              # Launch desktop UI (default)
    python main.py --cli        # Run in terminal (text-only, no UI)
    python main.py --api        # Start FastAPI backend server (Phase 2)
    python main.py --debug      # Launch UI with DEBUG logging
"""

from __future__ import annotations

import argparse
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="ai-assistant",
        description="Personal Conversational AI Assistant",
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run in terminal mode (no GUI, text only)",
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Start the FastAPI backend server (Phase 2)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG logging",
    )
    return parser.parse_args()


def run_desktop(debug: bool = False) -> None:
    """Launch the Tkinter desktop UI."""
    from assistant.config import get_settings
    from assistant.logger import configure_root_logger

    settings = get_settings()
    log_level = "DEBUG" if debug else settings.log_level
    configure_root_logger(log_level)

    from assistant.ui.desktop import ChatApp
    app = ChatApp()
    app.mainloop()


def run_cli() -> None:
    """Simple terminal REPL — useful for quick testing without the GUI."""
    from assistant.config import get_settings
    from assistant.core.brain import Brain
    from assistant.logger import configure_root_logger
    from rich.console import Console
    from rich.prompt import Prompt

    configure_root_logger("WARNING")  # keep CLI clean
    console = Console()
    brain = Brain()
    settings = get_settings()

    console.print(
        f"\n[bold blue]🤖 {settings.app_name}[/bold blue] — CLI mode\n"
        "[dim]Type your message and press Enter. Type 'quit' or 'exit' to stop.[/dim]\n"
    )

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break

        if user_input.lower() in ("clear", "reset"):
            brain.reset()
            console.print("[dim]Conversation cleared.[/dim]\n")
            continue

        reply = brain.chat(user_input)
        console.print(f"\n[bold green]Assistant[/bold green]: {reply}\n")


def run_api() -> None:
    """Start the FastAPI backend server."""
    try:
        import uvicorn
    except ImportError:
        print("uvicorn not installed. Run: pip install uvicorn[standard]")
        sys.exit(1)

    uvicorn.run(
        "assistant.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


def main() -> None:
    args = parse_args()

    if args.api:
        run_api()
    elif args.cli:
        run_cli()
    else:
        run_desktop(debug=args.debug)


if __name__ == "__main__":
    main()
