import os
import shlex
import sys
import time
import webbrowser
from dataclasses import dataclass
from datetime import datetime

from rich.console import Console
from rich.live import Live
from rich.prompt import Confirm, Prompt
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


@dataclass
class SessionResult:
    should_quit: bool = False
    reopen_config: bool = False
    restart_planning: bool = False


class PlannerCLI:
    def __init__(self, console: Console, config: dict):
        self.console = console
        self.config = config
        self.provider_name = ""
        self.planner: PlannerService | None = None
        self.blocks: list[dict] = []
        self.work_hours = ""
        self.goal = ""

    def run(self) -> None:
        while True:
            self.ensure_provider_ready()
            self.start_new_plan()
            result = self.command_loop()

            if result.should_quit:
                return
            if result.reopen_config:
                self.configure_provider(force_select=True)
                continue
            if result.restart_planning:
                continue

    def ensure_provider_ready(self) -> None:
        provider_name = self.config.get("default_provider", "").strip().lower()
        if provider_name not in PROVIDER_LABELS:
            provider_name = self.configure_provider(force_select=True)
        else:
            api_key = get_api_key(self.config, provider_name)
            if not api_key:
                provider_name = self.configure_provider(force_select=False, preferred_provider=provider_name)

        api_key = get_api_key(self.config, provider_name)
        self.provider_name = provider_name
        self.planner = PlannerService(create_provider(provider_name, api_key))

    def configure_provider(self, force_select: bool, preferred_provider: str | None = None) -> str:
        provider_name = preferred_provider or self.config.get("default_provider", "").strip().lower()
        if force_select or provider_name not in PROVIDER_LABELS:
            provider_name = self.prompt_provider_selection()

        while True:
            set_default_provider(self.config, provider_name)
            existing_key = get_api_key(self.config, provider_name)
            label = get_provider_label(provider_name)
            self.console.print(f"\n[bold]{label}[/bold] is the active provider.")

            if existing_key:
                if Confirm.ask("Use the saved API key?", default=True):
                    save_config(self.config)
                    return provider_name

            api_key = Prompt.ask("Enter your API key", password=True, default=existing_key or "")
            if api_key.strip():
                set_api_key(self.config, provider_name, api_key.strip())
                save_config(self.config)
                return provider_name

            action = self.prompt_missing_key_action(provider_name)
            if action == "selected":
                webbrowser.open_new_tab(PROVIDER_LINKS[provider_name])
            elif action == "all":
                for name in ("openai", "claude", "gemini"):
                    webbrowser.open_new_tab(PROVIDER_LINKS[name])
            elif action == "switch":
                provider_name = self.prompt_provider_selection()
            else:
                self.console.print("[yellow]An API key is required to continue.[/yellow]")

    def prompt_provider_selection(self) -> str:
        table = Table(title="Choose a Provider")
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Provider", style="bold")
        for index, provider_name in enumerate(("openai", "claude", "gemini"), start=1):
            table.add_row(str(index), get_provider_label(provider_name))
        self.console.print(table)

        mapping = {"1": "openai", "2": "claude", "3": "gemini"}
        while True:
            choice = Prompt.ask("Provider", default="1")
            if choice in mapping:
                return mapping[choice]
            self.console.print("[red]Choose 1, 2, or 3.[/red]")

    def prompt_missing_key_action(self, provider_name: str) -> str:
        label = get_provider_label(provider_name)
        self.console.print(f"[yellow]No {label} API key provided.[/yellow]")
        self.console.print("1. Open the selected provider page")
        self.console.print("2. Open all provider pages")
        self.console.print("3. Switch provider")
        self.console.print("4. Try entering the key again")
        while True:
            choice = Prompt.ask("Action", default="4")
            mapping = {"1": "selected", "2": "all", "3": "switch", "4": "retry"}
            if choice in mapping:
                return mapping[choice]
            self.console.print("[red]Choose 1, 2, 3, or 4.[/red]")

    def start_new_plan(self) -> None:
        self.console.rule("[bold cyan]AI Planner CLI[/bold cyan]")
        self.work_hours = self.prompt_work_hours()
        self.goal = Prompt.ask("What do you need to do today?").strip()
        while not self.goal:
            self.console.print("[red]Goal cannot be empty.[/red]")
            self.goal = Prompt.ask("What do you need to do today?").strip()

        self.console.print("\n[dim]Decomposing goal...[/dim]")
        tasks = self.planner.decompose(self.goal, self.work_hours)
        self.render_tasks(tasks)

        self.console.print("\n[dim]Scheduling your day...[/dim]")
        blocks = self.planner.schedule(tasks, self.work_hours)
        self.blocks = [{**block, "status": "pending"} for block in blocks]
        self.render_blocks()

    def prompt_work_hours(self) -> str:
        default_hours = default_work_hours()
        while True:
            work_hours = Prompt.ask("Work hours (H-H)", default=default_hours).strip()
            try:
                parse_work_hours(work_hours)
            except ValueError as exc:
                self.console.print(f"[red]{exc}[/red]")
                continue
            return work_hours

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

        for display_index, (block_index, block) in enumerate(self.get_visible_blocks(), start=1):
            status = block["status"]
            table.add_row(
                str(display_index),
                f'{block["start"]} - {block["end"]}',
                block["task_title"],
                block["mode"],
                status,
            )

        if not self.get_visible_blocks():
            self.console.print("[yellow]No work blocks available.[/yellow]")
            return

        self.console.print(table)
        self.console.print("[dim]Commands: start <n>, done <n>, skip <n>, delay <n>, show, new, config, quit[/dim]")

    def command_loop(self) -> SessionResult:
        while True:
            command_line = Prompt.ask("\nCommand").strip()
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
                self.handle_block_command(command, display_index)
                continue

            self.console.print("[red]Unknown command.[/red]")

    def handle_block_command(self, command: str, display_index: int) -> None:
        resolved = self.resolve_display_index(display_index)
        if resolved is None:
            self.console.print("[red]That block number does not exist.[/red]")
            return

        block_index, block = resolved
        if block["status"] != "pending":
            self.console.print("[yellow]That block is already completed or skipped.[/yellow]")
            return

        if command == "done":
            block["status"] = "done"
            self.render_blocks()
            return
        if command == "skip":
            block["status"] = "skip"
            self.render_blocks()
            return
        if command == "delay":
            self.delay_from_block(block_index)
            self.render_blocks()
            return
        if command == "start":
            self.run_timer(block_index)
            self.render_blocks()

    def delay_from_block(self, block_index: int) -> None:
        current_time = datetime.now().strftime("%H:%M")
        remaining_tasks = [
            {"task_title": block["task_title"], "mode": block["mode"]}
            for block in self.blocks[block_index:]
            if block["status"] == "pending" and block["mode"] != "break"
        ]
        if not remaining_tasks:
            self.console.print("[yellow]No pending work blocks remain to reschedule.[/yellow]")
            return

        self.console.print("[dim]Rescheduling the rest of your day...[/dim]")
        rescheduled = self.planner.reschedule(remaining_tasks, current_time, self.work_hours)
        preserved = self.blocks[:block_index]
        self.blocks = preserved + [{**block, "status": "pending"} for block in rescheduled]

    def run_timer(self, block_index: int) -> None:
        block = self.blocks[block_index]
        self.console.print(f"[bold]Starting focus timer for:[/bold] {block['task_title']}")
        completed = self.countdown(FOCUS_SECONDS, f"Focus: {block['task_title']}", "magenta")
        if not completed:
            return

        self.console.print("[green]Focus session complete. Starting break...[/green]")
        completed = self.countdown(BREAK_SECONDS, "Break", "green")
        if not completed:
            return

        while True:
            choice = Prompt.ask("Break done. Choose next step", choices=["more", "done"], default="done")
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
