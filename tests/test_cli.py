import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from rich.console import Console

from aiplanner_cli import config as cli_config
from aiplanner_cli.activity import ActivityMonitor
from aiplanner_cli.notifications import send_desktop_notification
from aiplanner_cli.session import PlannerCLI, default_work_hours
from planner_core.planner import PlannerService
from planner_core.validation import validate_time_blocks


class ConfigTests(unittest.TestCase):
    def test_config_round_trip(self):
        path = Path("tests") / ".tmp-config.json"
        try:
            with patch("aiplanner_cli.config.get_config_path", return_value=path):
                config = cli_config.default_config()
                cli_config.set_default_provider(config, "gemini")
                cli_config.set_api_key(config, "gemini", "secret-key")
                cli_config.save_config(config)

                loaded = cli_config.load_config()
        finally:
            if path.exists():
                path.unlink()

        self.assertEqual(loaded["default_provider"], "gemini")
        self.assertEqual(cli_config.get_api_key(loaded, "gemini"), "secret-key")


class ValidationTests(unittest.TestCase):
    def test_validate_time_blocks_rejects_overlap(self):
        with self.assertRaises(ValueError):
            validate_time_blocks(
                [
                    {"task_title": "A", "start": "09:00", "end": "10:00", "mode": "deep"},
                    {"task_title": "B", "start": "09:30", "end": "10:30", "mode": "light"},
                ],
                "9-18",
            )

    def test_validate_time_blocks_rejects_before_current_time(self):
        with self.assertRaises(ValueError):
            validate_time_blocks(
                [{"task_title": "A", "start": "12:00", "end": "12:30", "mode": "deep"}],
                "9-18",
                current_time="12:15",
            )


class CliBehaviorTests(unittest.TestCase):
    def test_send_desktop_notification_uses_linux_notify_send(self):
        with patch("aiplanner_cli.notifications.platform.system", return_value="Linux"):
            with patch("aiplanner_cli.notifications.shutil.which", return_value="/usr/bin/notify-send"):
                with patch("aiplanner_cli.notifications.subprocess.Popen") as mock_popen:
                    self.assertTrue(send_desktop_notification("AI Planner", "Still there?"))

        mock_popen.assert_called_once()

    def test_activity_monitor_prompts_once_per_idle_period(self):
        monitor = ActivityMonitor(idle_seconds=180, enable_listeners=False)
        monitor.available = True
        monitor._last_activity -= 181

        self.assertTrue(monitor.should_prompt())
        self.assertFalse(monitor.should_prompt())

        monitor.record_activity()
        monitor._last_activity -= 181
        self.assertTrue(monitor.should_prompt())

    def test_generic_coding_goal_becomes_single_coding_task(self):
        provider = Mock()
        planner = PlannerService(provider)

        tasks = planner.decompose("complete coding", "14-16")

        provider.generate_text.assert_not_called()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["title"], "Coding")
        self.assertEqual(tasks[0]["estimate_minutes"], 120)

    def test_default_work_hours_falls_back_late_night(self):
        fake_now = Mock()
        fake_now.hour = 23

        with patch("aiplanner_cli.session.datetime") as mock_datetime:
            mock_datetime.now.return_value = fake_now
            self.assertEqual(default_work_hours(), "9-17")

    def test_delay_preserves_past_blocks(self):
        console = Console(record=True)
        app = PlannerCLI(console, cli_config.default_config(), activity_monitor=ActivityMonitor(enable_listeners=False))
        app.work_hours = "9-18"
        app.blocks = [
            {"task_title": "Done task", "start": "09:00", "end": "09:30", "mode": "deep", "status": "done"},
            {"task_title": "Current task", "start": "09:30", "end": "10:00", "mode": "deep", "status": "pending"},
            {"task_title": "Break", "start": "10:00", "end": "10:10", "mode": "break", "status": "pending"},
            {"task_title": "Next task", "start": "10:10", "end": "11:00", "mode": "light", "status": "pending"},
        ]
        app.planner = Mock()
        app.planner.reschedule.return_value = [
            {"task_title": "Rescheduled task", "start": "10:15", "end": "11:00", "mode": "deep"},
        ]

        with patch("aiplanner_cli.session.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "10:15"
            app.delay_from_block(1)

        self.assertEqual(app.blocks[0]["task_title"], "Done task")
        self.assertEqual(app.blocks[0]["status"], "done")
        self.assertEqual(app.blocks[1]["task_title"], "Rescheduled task")
        self.assertEqual(app.blocks[1]["status"], "pending")

    def test_prompt_work_hours_allows_returning_to_menu(self):
        console = Console(record=True)
        app = PlannerCLI(console, cli_config.default_config(), activity_monitor=ActivityMonitor(enable_listeners=False))

        with patch("aiplanner_cli.session.Prompt.ask", return_value="menu"):
            self.assertIsNone(app.prompt_work_hours())

    def test_configure_provider_can_return_to_main_menu(self):
        console = Console(record=True)
        app = PlannerCLI(console, cli_config.default_config(), activity_monitor=ActivityMonitor(enable_listeners=False))

        with patch.object(app, "prompt_provider_selection", return_value="openai"):
            with patch.object(app, "prompt_provider_setup_action", return_value="menu"):
                self.assertIsNone(app.configure_provider(force_select=True))

    def test_start_new_plan_returns_to_menu_when_provider_request_fails(self):
        console = Console(record=True)
        app = PlannerCLI(console, cli_config.default_config(), activity_monitor=ActivityMonitor(enable_listeners=False))
        app.provider_name = "openai"
        app.planner = Mock()
        app.planner.decompose.side_effect = RuntimeError("OpenAI request failed: bad key")

        with patch.object(app, "prompt_work_hours", return_value="9-18"):
            with patch.object(app, "prompt_goal", return_value="finish homework"):
                with patch.object(app, "prompt_request_error_action", return_value="menu"):
                    result = app.start_new_plan()

        self.assertTrue(result.return_to_menu)
        self.assertFalse(result.plan_ready)


if __name__ == "__main__":
    unittest.main()
