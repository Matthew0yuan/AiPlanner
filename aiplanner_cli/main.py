import sys

from dotenv import load_dotenv
from rich.console import Console

from aiplanner_cli.activity import ActivityMonitor
from aiplanner_cli.config import load_config
from aiplanner_cli.session import PlannerCLI


def main() -> int:
    load_dotenv()
    console = Console()
    config = load_config()
    activity_monitor = ActivityMonitor()
    app = PlannerCLI(console, config, activity_monitor=activity_monitor)

    try:
        app.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye.[/yellow]")
        return 0
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        return 1
    finally:
        activity_monitor.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
