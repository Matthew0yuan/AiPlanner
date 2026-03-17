import os
from dataclasses import dataclass
from typing import Protocol


PROVIDER_LABELS = {
    "openai": "OpenAI",
    "claude": "Claude",
    "gemini": "Gemini",
}

PROVIDER_LINKS = {
    "openai": "https://platform.openai.com/api-keys",
    "claude": "https://console.anthropic.com/settings/keys",
    "gemini": "https://aistudio.google.com/app/apikey",
}


class TextProvider(Protocol):
    provider_name: str

    def generate_text(self, system_prompt: str, user_message: str, temperature: float) -> str:
        ...


@dataclass
class GeminiProvider:
    api_key: str
    model: str = "gemini-3.1-flash-lite-preview"
    provider_name: str = "gemini"

    def generate_text(self, system_prompt: str, user_message: str, temperature: float) -> str:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError("google-genai is not installed") from exc

        client = genai.Client(api_key=self.api_key)
        try:
            response = client.models.generate_content(
                model=self.model,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=temperature,
                ),
            )
        except Exception as exc:
            raise RuntimeError("Gemini request failed") from exc

        raw = (response.text or "").strip()
        if not raw:
            raise ValueError("Agent returned an empty response")
        return raw


@dataclass
class OpenAIProvider:
    api_key: str
    model: str = "gpt-4.1-mini"
    provider_name: str = "openai"

    def generate_text(self, system_prompt: str, user_message: str, temperature: float) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai is not installed") from exc

        client = OpenAI(api_key=self.api_key)
        try:
            response = client.responses.create(
                model=self.model,
                temperature=temperature,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
        except Exception as exc:
            raise RuntimeError("OpenAI request failed") from exc

        raw = (getattr(response, "output_text", "") or "").strip()
        if not raw:
            raise ValueError("Agent returned an empty response")
        return raw


@dataclass
class ClaudeProvider:
    api_key: str
    model: str = "claude-3-5-sonnet-latest"
    provider_name: str = "claude"

    def generate_text(self, system_prompt: str, user_message: str, temperature: float) -> str:
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise RuntimeError("anthropic is not installed") from exc

        client = Anthropic(api_key=self.api_key)
        try:
            response = client.messages.create(
                model=self.model,
                temperature=temperature,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as exc:
            raise RuntimeError("Claude request failed") from exc

        parts = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        raw = "".join(parts).strip()
        if not raw:
            raise ValueError("Agent returned an empty response")
        return raw


def create_provider(provider_name: str, api_key: str) -> TextProvider:
    if provider_name == "gemini":
        return GeminiProvider(api_key=api_key)
    if provider_name == "openai":
        return OpenAIProvider(api_key=api_key)
    if provider_name == "claude":
        return ClaudeProvider(api_key=api_key)
    raise ValueError(f"Unsupported provider: {provider_name}")


def create_provider_from_env() -> TextProvider:
    provider_name = os.environ.get("AI_PLANNER_PROVIDER", "gemini").strip().lower()
    env_map = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
    }
    if provider_name not in env_map:
        raise RuntimeError(f"Unsupported AI_PLANNER_PROVIDER: {provider_name}")

    api_key = os.environ.get(env_map[provider_name], "").strip()
    if not api_key:
        raise RuntimeError(f"{env_map[provider_name]} is not configured")

    return create_provider(provider_name, api_key)
