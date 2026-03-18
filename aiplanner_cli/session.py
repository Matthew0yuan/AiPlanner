import shlex
import time
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, TypeVar

from aiplanner_cli.activity import ActivityMonitor
from aiplanner_cli.notifications import send_desktop_notification
from rich.console import Console
from rich.live import Live
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from aiplanner_cli.config import (
    get_api_key,
    get_provider_label,
    save_config,
    set_api_key,
    set_default_provider,
)
from planner_core.planner import PlannerService
from planner_core.providers import PROVIDER_LABELS, PROVIDER_LINKS, create_provider
from planner_core.validation import parse_work_hours


FOCUS_SECONDS = 25 * 60
BREAK_SECONDS = 5 * 60
T = TypeVar("T")


@dataclass
class SessionResult:
    should_quit: bool = False
    reopen_config: bool = False
    restart_planning: bool = False
    return_to_menu: bool = False
    plan_ready: bool = False


class PlannerCLI:
    def __init__(self, console: Console, config: dict, activity_monitor: ActivityMonitor | None = None):
        self.console = console
        self.config = config
        self.activity_monitor = activity_monitor or ActivityMonitor()
        self.provider_name = ""
        self.planner: PlannerService | None = None
        self.blocks: list[dict] = []
        self.work_hours = ""
        self.goal = ""
        self.monitoring_notice_shown = False

    def run(self) -> None:
        while True:
            action = self.prompt_main_menu()
            if action == "quit":
                return
            if action == "config":
                self.configure_provider(force_select=not self.has_configured_provider())
                continue

            while True:
                if not self.ensure_provider_ready():
                    break

                result = self.start_new_plan()
                if result.should_quit:
                    return
                if result.reopen_config:
                    self.configure_provider(force_select=False, preferred_provider=self.provider_name)
                    break
                if result.return_to_menu:
                    break
                if not result.plan_ready:
                    break

                result = self.command_loop()
                if result.should_quit:
                    return
                if result.reopen_config:
                    self.configure_provider(force_select=False, preferred_provider=self.provider_name)
                    break
                if result.restart_planning:
                    continue
                break

    def prompt_main_menu(self) -> str:
        self.console.rule("[bold cyan]AI Planner CLI[/bold cyan]")
        self.render_provider_status()
        self.console.print("1. Start planning")
        self.console.print("2. Configure provider")
        self.console.print("3. Quit")

        mapping = {"1": "plan", "2": "config", "3": "quit"}
        while True:
            choice = Prompt.ask("Menu", default="1").strip().lower()
            self.activity_monitor.record_activity()
            if choice in mapping:
                return mapping[choice]
            if choice in {"plan", "start"}:
                return "plan"
            if choice in {"config", "settings"}:
                return "config"
            if choice in {"quit", "exit"}:
                return "quit"
            self.console.print("[red]Choose 1, 2, or 3.[/red]")

    def render_provider_status(self) -> None:
        provider_name = self.config.get("default_provider", "").strip().lower()
        if provider_name in PROVIDER_LABELS:
            label = get_provider_label(provider_name)
            has_key = bool(get_api_key(self.config, provider_name))
            key_status = "saved key" if has_key else "no key saved"
            self.console.print(f"[bold]Provider:[/bold] {label} ({key_status})")
            return
        self.console.print("[bold]Provider:[/bold] not configured")

    def has_configured_provider(self) -> bool:
        provider_name = self.config.get("default_provider", "").strip().lower()
        return provider_name in PROVIDER_LABELS and bool(get_api_key(self.config, provider_name))

    def ensure_provider_ready(self) -> bool:
        provider_name = self.config.get("default_provider", "").strip().lower()
        if provider_name not in PROVIDER_LABELS:
            provider_name = self.configure_provider(force_select=True) or ""
        elif not get_api_key(self.config, provider_name):
            provider_name = self.configure_provider(force_select=False, preferred_provider=provider_name) or ""

        if provider_name not in PROVIDER_LABELS:
            return False

        api_key = get_api_key(self.config, provider_name)
        if not api_key:
            return False

        self.provider_name = provider_name
        self.planner = PlannerService(create_provider(provider_name, api_key))
        return True

    def configure_provider(self, force_select: bool, preferred_provider: str | None = None) -> str | None:
        provider_name = preferred_provider or self.config.get("default_provider", "").strip().lower()
        if force_select or provider_name not in PROVIDER_LABELS:
            provider_name = self.prompt_provider_selection(allow_back=True)
            if provider_name is None:
                return None

        while True:
            label = get_provider_label(provider_name)
            existing_key = get_api_key(self.config, provider_name)
            self.console.print(f"\n[bold]{label}[/bold] configuration")

            action = self.prompt_provider_setup_action(provider_name, has_saved_key=bool(existing_key))
            if action == "use_saved":
                set_default_provider(self.config, provider_name)
                save_config(self.config)
                return provider_name
            if action == "enter_key":
                api_key = Prompt.ask("Enter your API key", password=True).strip()
                self.activity_monitor.record_activity()
                if api_key.lower() == "menu":
                    return None
                if not api_key:
                    self.console.print("[yellow]No API key entered.[/yellow]")
                    continue
                set_default_provider(self.config, provider_name)
                set_api_key(self.config, provider_name, api_key)
                save_config(self.config)
                return provider_name
            if action == "selected":
                webbrowser.open_new_tab(PROVIDER_LINKS[provider_name])
                continue
            if action == "all":
                for name in ("openai", "claude", "gemini"):
                    webbrowser.open_new_tab(PROVIDER_LINKS[name])
                continue
            if action == "switch":
                provider_name = self.prompt_provider_selection(allow_back=True)
                if provider_name is None:
                    return None
                continue
            if action == "menu":
                return None

    def prompt_provider_selection(self, allow_back: bool) -> str | None:
        table = Table(title="Choose a Provider")
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Provider", style="bold")
        for index, provider_name in enumerate(("openai", "claude", "gemini"), start=1):
            table.add_row(str(index), get_provider_label(provider_name))
        if allow_back:
            table.add_row("4", "Back to main menu")
        self.console.print(table)

        mapping = {"1": "openai", "2": "claude", "3": "gemini"}
        while True:
            default_choice = "1" if not allow_back else "4"
            choice = Prompt.ask("Provider", default=default_choice).strip().lower()
            self.activity_monitor.record_activity()
            if choice in mapping:
                return mapping[choice]
            if allow_back and choice in {"4", "back", "menu"}:
                return None
            self.console.print("[red]Choose a valid option from the list.[/red]")

    def prompt_provider_setup_action(self, provider_name: str, has_saved_key: bool) -> str:
        label = get_provider_label(provider_name)
        if has_saved_key:
            self.console.print(f"[green]{label} has a saved API key.[/green]")
            self.console.print("1. Use the saved API key")
            self.console.print("2. Enter or update the API key")
            self.console.print("3. Open the selected provider page")
            self.console.print("4. Open all provider pages")
            self.console.print("5. Switch provider")
            self.console.print("6. Back to main menu")
            mapping = {
                "1": "use_saved",
                "2": "enter_key",
                "3": "selected",
                "4": "all",
                "5": "switch",
                "6": "menu",
            }
            default_choice = "1"
        else:
            self.console.print(f"[yellow]No {label} API key provided.[/yellow]")
            self.console.print("1. Enter the API key")
            self.console.print("2. Open the selected provider page")
            self.console.print("3. Open all provider pages")
            self.console.print("4. Switch provider")
            self.console.print("5. Back to main menu")
            mapping = {
                "1": "enter_key",
                "2": "selected",
                "3": "all",
                "4": "switch",
                "5": "menu",
            }
            default_choice = "1"

        while True:
            choice = Prompt.ask("Action", default=default_choice).strip().lower()
            self.activity_monitor.record_activity()
            if choice in mapping:
                return mapping[choice]
            if choice in {"back", "menu"}:
                return "menu"
            self.console.print("[red]Choose a valid option from the list.[/red]")

    def start_new_plan(self) -> SessionResult:
        self.console.rule("[bold cyan]New Plan[/bold cyan]")

        work_hours = self.prompt_work_hours()
        if work_hours is None:
            return SessionResult(return_to_menu=True)
        self.work_hours = work_hours

        goal = self.prompt_goal()
        if goal is None:
            return SessionResult(return_to_menu=True)
        self.goal = goal

        tasks, result = self.run_planner_step(
            "Decomposing goal",
            lambda: self.planner.decompose(self.goal, self.work_hours),
        )
        if result:
            return result
        self.render_tasks(tasks)

        blocks, result = self.run_planner_step(
            "Scheduling your day",
            lambda: self.planner.schedule(tasks, self.work_hours),
        )
        if result:
            return result

        self.blocks = [{**block, "status": "pending"} for block in blocks]
        self.render_blocks()
        return SessionResult(plan_ready=True)

    def prompt_work_hours(self) -> str | None:
        default_hours = default_work_hours()
        while True:
            work_hours = Prompt.ask("Work hours (H-H or 'menu')", default=default_hours).strip()
            self.activity_monitor.record_activity()
            if work_hours.lower() == "menu":
                return None
            try:
                parse_work_hours(work_hours)
            except ValueError as exc:
                self.console.print(f"[red]{exc}[/red]")
                continue
            return work_hours

    def prompt_goal(self) -> str | None:
        while True:
            goal = Prompt.ask("What do you need to do today? ('menu' to go back)").strip()
            self.activity_monitor.record_activity()
            if goal.lower() == "menu":
                return None
            if goal:
                return goal
            self.console.print("[red]Goal cannot be empty.[/red]")

    def run_planner_step(
        self,
        label: str,
        operation: Callable[[], T],
    ) -> tuple[T | None, SessionResult | None]:
        while True:
            self.console.print(f"\n[dim]{label}...[/dim]")
            try:
                return operation(), None
            except Exception as exc:
                action = self.prompt_request_error_action(exc)
                if action == "retry":
                    continue
                if action == "config":
                    provider_name = self.configure_provider(force_select=False, preferred_provider=self.provider_name)
                    if provider_name is None:
                        return None, SessionResult(return_to_menu=True)
                    self.provider_name = provider_name
                    self.planner = PlannerService(create_provider(provider_name, get_api_key(self.config, provider_name)))
                    continue
                if action == "switch":
                    provider_name = self.configure_provider(force_select=True)
                    if provider_name is None:
                        return None, SessionResult(return_to_menu=True)
                    self.provider_name = provider_name
                    self.planner = PlannerService(create_provider(provider_name, get_api_key(self.config, provider_name)))
                    continue
                if action == "menu":
                    return None, SessionResult(return_to_menu=True)
                return None, SessionResult(should_quit=True)

    def prompt_request_error_action(self, error: Exception) -> str:
        self.console.print(f"[red]Error:[/red] {error}")
        self.console.print("1. Retry the request")
        self.console.print("2. Reconfigure the current provider")
        self.console.print("3. Switch provider")
        self.console.print("4. Back to main menu")
        self.console.print("5. Quit")
        mapping = {
            "1": "retry",
            "2": "config",
            "3": "switch",
            "4": "menu",
            "5": "quit",
        }
        while True:
            choice = Prompt.ask("Action", default="2").strip().lower()
            self.activity_monitor.record_activity()
            if choice in mapping:
                return mapping[choice]
            if choice in {"back", "menu"}:
                return "menu"
            if choice in {"quit", "exit"}:
                return "quit"
            self.console.print("[red]Choose a valid option from the list.[/red]")

    def render_tasks(self, tasks: list[dict]) -> None:
        table = Table(title="Task Breakdown")
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Task", style="bold")
        table.add_column("Estimate")
        table.add_column("Energy")
        for index, task in enumerate(tasks, start=1):
            table.add_row(str(index), task["title"], f'{task["estimate_minutes"]} min', task["energy"])
        self.console.print(table)

    def render_blocks(self) -> None:
        table = Table(title=f"Today's Plan ({self.work_hours})")
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Time")
        table.add_column("Task", style="bold")
        table.add_column("Mode")
        table.add_column("Status")

        visible_blocks = self.get_visible_blocks()
        for display_index, (block_index, block) in enumerate(visible_blocks, start=1):
            status = block["status"]
            table.add_row(
                str(display_index),
                f'{block["start"]} - {block["end"]}',
                block["task_title"],
                block["mode"],
                status,
            )

        if not visible_blocks:
            self.console.print("[yellow]No work blocks available.[/yellow]")
            return

        self.console.print(table)
        self.console.print("[dim]Commands: start <n>, done <n>, skip <n>, delay <n>, show, new, config, menu, quit[/dim]")

    def command_loop(self) -> SessionResult:
        while True:
            command_line = Prompt.ask("\nCommand").strip()
            self.activity_monitor.record_activity()
            if not command_line:
                continue

            parts = shlex.split(command_line)
            command = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else None

            if command == "show":
                self.render_blocks()
                continue
            if command == "new":
                return SessionResult(restart_planning=True)
            if command == "config":
                return SessionResult(reopen_config=True)
            if command == "menu":
                return SessionResult(return_to_menu=True)
            if command == "quit":
                return SessionResult(should_quit=True)
            if command in {"done", "skip", "delay", "start"}:
                if not arg:
                    self.console.print(f"[red]{command} requires a block number.[/red]")
                    continue
                try:
                    display_index = int(arg)
                except ValueError:
                    self.console.print("[red]Block number must be an integer.[/red]")
                    continue
                result = self.handle_block_command(command, display_index)
                if result and (result.should_quit or result.reopen_config or result.restart_planning or result.return_to_menu):
                    return result
                continue

            self.console.print("[red]Unknown command.[/red]")

    def handle_block_command(self, command: str, display_index: int) -> SessionResult | None:
        resolved = self.resolve_display_index(display_index)
        if resolved is None:
            self.console.print("[red]That block number does not exist.[/red]")
            return None

        block_index, block = resolved
        if block["status"] != "pending":
            self.console.print("[yellow]That block is already completed or skipped.[/yellow]")
            return None

        if command == "done":
            block["status"] = "done"
            self.render_blocks()
            return None
        if command == "skip":
            block["status"] = "skip"
            self.render_blocks()
            return None
        if command == "delay":
            result = self.delay_from_block(block_index)
            if result is None:
                self.render_blocks()
            return result
        if command == "start":
            self.run_timer(block_index)
            self.render_blocks()
        return None

    def delay_from_block(self, block_index: int) -> SessionResult | None:
        current_time = datetime.now().strftime("%H:%M")
        remaining_tasks = [
            {"task_title": block["task_title"], "mode": block["mode"]}
            for block in self.blocks[block_index:]
            if block["status"] == "pending" and block["mode"] != "break"
        ]
        if not remaining_tasks:
            self.console.print("[yellow]No pending work blocks remain to reschedule.[/yellow]")
            return None

        rescheduled, result = self.run_planner_step(
            "Rescheduling the rest of your day",
            lambda: self.planner.reschedule(remaining_tasks, current_time, self.work_hours),
        )
        if result:
            return result

        preserved = self.blocks[:block_index]
        self.blocks = preserved + [{**block, "status": "pending"} for block in rescheduled]
        return None

    def run_timer(self, block_index: int) -> None:
        block = self.blocks[block_index]
        self.console.print(f"[bold]Starting focus timer for:[/bold] {block['task_title']}")
        if not self.activity_monitor.available and not self.monitoring_notice_shown:
            self.console.print("[dim]Idle monitoring is unavailable until the optional input hook is installed.[/dim]")
            self.monitoring_notice_shown = True
        self.activity_monitor.record_activity()
        completed = self.countdown(FOCUS_SECONDS, f"Focus: {block['task_title']}", "magenta")
        if not completed:
            return

        self.console.print("[green]Focus session complete. Starting break...[/green]")
        completed = self.countdown(BREAK_SECONDS, "Break", "green")
        if not completed:
            return

        while True:
            choice = Prompt.ask("Break done. Choose next step", choices=["more", "done"], default="done")
            self.activity_monitor.record_activity()
            if choice == "done":
                block["status"] = "done"
                return
            if choice == "more":
                completed = self.countdown(FOCUS_SECONDS, f"Focus: {block['task_title']}", "magenta")
                if not completed:
                    return

    def countdown(self, total_seconds: int, label: str, color: str) -> bool:
        end_time = time.monotonic() + total_seconds
        try:
            with Live(self.format_timer_text(total_seconds, label, color), refresh_per_second=4, console=self.console) as live:
                while True:
                    if self.activity_monitor.should_prompt():
                        live.stop()
                        send_desktop_notification(
                            "AI Planner",
                            "No keyboard or mouse activity for 3 minutes. Are you still there?",
                        )
                        still_there = Prompt.ask(
                            "No keyboard or mouse activity for 3 minutes. Are you still there?",
                            choices=["yes", "no"],
                            default="yes",
                        )
                        self.activity_monitor.record_activity()
                        if still_there == "no":
                            self.console.print("[yellow]Timer paused. Start the block again when you are back.[/yellow]")
                            return False
                        live.start()
                    remaining = max(0, int(end_time - time.monotonic()))
                    live.update(self.format_timer_text(remaining, label, color))
                    if remaining <= 0:
                        break
                    time.sleep(1)
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Timer cancelled.[/yellow]")
            return False
        return True

    @staticmethod
    def format_timer_text(seconds: int, label: str, color: str) -> Text:
        minutes, secs = divmod(seconds, 60)
        return Text(f"{label}  {minutes:02d}:{secs:02d}", style=color)

    def get_visible_blocks(self) -> list[tuple[int, dict]]:
        return [
            (index, block)
            for index, block in enumerate(self.blocks)
            if block["mode"] != "break"
        ]

    def resolve_display_index(self, display_index: int) -> tuple[int, dict] | None:
        visible_blocks = self.get_visible_blocks()
        if display_index < 1 or display_index > len(visible_blocks):
            return None
        return visible_blocks[display_index - 1]


def default_work_hours() -> str:
    current_hour = datetime.now().hour
    if current_hour >= 23:
        return "9-17"
    end_hour = min(current_hour + 8, 23)
    if end_hour <= current_hour:
        return "9-17"
    return f"{current_hour}-{end_hour}"
