import time


class ActivityMonitor:
    def __init__(self, idle_seconds: int = 180, enable_listeners: bool = True):
        self.idle_seconds = idle_seconds
        self.available = False
        self._listeners = []
        self._last_activity = time.monotonic()
        self._prompted_for_current_idle = False

        if enable_listeners:
            self._start_listeners()

    def _start_listeners(self) -> None:
        try:
            from pynput import keyboard, mouse
        except ImportError:
            return

        def on_activity(*_args):
            self.record_activity()

        try:
            self._listeners = [
                keyboard.Listener(on_press=on_activity, on_release=on_activity),
                mouse.Listener(on_move=on_activity, on_click=on_activity, on_scroll=on_activity),
            ]
            for listener in self._listeners:
                listener.daemon = True
                listener.start()
            self.available = True
        except Exception:
            self.stop()

    def record_activity(self) -> None:
        self._last_activity = time.monotonic()
        self._prompted_for_current_idle = False

    def should_prompt(self) -> bool:
        if not self.available or self._prompted_for_current_idle:
            return False
        if time.monotonic() - self._last_activity < self.idle_seconds:
            return False
        self._prompted_for_current_idle = True
        return True

    def stop(self) -> None:
        for listener in self._listeners:
            try:
                listener.stop()
            except Exception:
                pass
        self._listeners = []
        self.available = False
