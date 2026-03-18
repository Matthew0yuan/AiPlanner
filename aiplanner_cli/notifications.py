import json
import platform
import shutil
import subprocess


def send_desktop_notification(title: str, message: str) -> bool:
    system = platform.system().lower()
    if system == "windows":
        return _send_windows_notification(title, message)
    if system == "linux":
        return _send_linux_notification(title, message)
    if system == "darwin":
        return _send_macos_notification(title, message)
    return False


def _send_windows_notification(title: str, message: str) -> bool:
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        return False

    title_json = json.dumps(title)
    message_json = json.dumps(message)
    script = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null;"
        "[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] > $null;"
        f"$title = {title_json};"
        f"$message = {message_json};"
        '$xml = New-Object Windows.Data.Xml.Dom.XmlDocument;'
        '$xml.LoadXml("<toast><visual><binding template=\\"ToastGeneric\\"><text>" + $title + "</text><text>" + $message + "</text></binding></visual></toast>");'
        '$toast = [Windows.UI.Notifications.ToastNotification]::new($xml);'
        '[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("AI Planner CLI").Show($toast)'
    )
    return _spawn_command([powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script])


def _send_linux_notification(title: str, message: str) -> bool:
    notify_send = shutil.which("notify-send")
    if not notify_send:
        return False
    return _spawn_command([notify_send, title, message])


def _send_macos_notification(title: str, message: str) -> bool:
    osascript = shutil.which("osascript")
    if not osascript:
        return False
    script = f'display notification {json.dumps(message)} with title {json.dumps(title)}'
    return _spawn_command([osascript, "-e", script])


def _spawn_command(command: list[str]) -> bool:
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return True
