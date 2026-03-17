import sys

from dotenv import load_dotenv
from rich.console import Console

from aiplanner_cli.config import load_config
from aiplanner_cli.session import PlannerCLI


def main() -> int:
    load_dotenv()
    console = Console()
    config = load_config()
    app = PlannerCLI(console, config)

    try:
        app.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye.[/yellow]")
        return 0
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
