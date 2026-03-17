import json
import os
from pathlib import Path

from planner_core.providers import PROVIDER_LABELS, PROVIDER_LINKS


CONFIG_FILE_NAME = "config.json"


def get_config_dir() -> Path:
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "AiPlanner"
        return Path.home() / "AppData" / "Roaming" / "AiPlanner"
    return Path.home() / ".config" / "aiplanner"


def get_config_path() -> Path:
    return get_config_dir() / CONFIG_FILE_NAME


def load_config() -> dict:
    path = get_config_path()
    if not path.exists():
        return default_config()

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_config()

    config = default_config()
    config.update({key: value for key, value in data.items() if key != "providers"})
    providers = data.get("providers", {})
    if isinstance(providers, dict):
        for provider_name in PROVIDER_LABELS:
            provider_data = providers.get(provider_name, {})
            if isinstance(provider_data, dict):
                config["providers"][provider_name]["api_key"] = str(provider_data.get("api_key", "")).strip()
    return config


def save_config(config: dict) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def default_config() -> dict:
    return {
        "default_provider": "",
        "providers": {
            provider_name: {"api_key": ""}
            for provider_name in PROVIDER_LABELS
        },
    }


def set_default_provider(config: dict, provider_name: str) -> None:
    config["default_provider"] = provider_name


def set_api_key(config: dict, provider_name: str, api_key: str) -> None:
    config["providers"].setdefault(provider_name, {})
    config["providers"][provider_name]["api_key"] = api_key.strip()


def get_api_key(config: dict, provider_name: str) -> str:
    provider_data = config.get("providers", {}).get(provider_name, {})
    return str(provider_data.get("api_key", "")).strip()


def get_provider_label(provider_name: str) -> str:
    return PROVIDER_LABELS[provider_name]


def get_provider_link(provider_name: str) -> str:
    return PROVIDER_LINKS[provider_name]
