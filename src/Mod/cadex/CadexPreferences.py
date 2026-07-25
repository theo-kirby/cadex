# SPDX-License-Identifier: LGPL-2.1-or-later

"""Native FreeCAD preferences for Cadex.

Preferences intentionally store only non-secret settings. API keys are read
from the process environment, OS keyring, or a user-selected .env file by
CadexAuth.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading

import FreeCAD as App

from CadexAuth import (
    DEFAULT_PROVIDER,
    PROVIDERS,
    delete_keyring_key,
    list_provider_models,
    resolve_auth_credential,
    resolve_auth_state,
    store_keyring_key,
    validate_api_key,
    validate_configured_auth,
)
from CadexDebug import default_capture_directory, resolve_capture_directory

PREFERENCE_GROUP = "User parameter:BaseApp/Preferences/Mod/cadex"
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"
DEFAULT_CHATGPT_MODEL = ""
DEFAULT_CLAUDE_CODE_MODEL = "claude-fable-5"
DEFAULT_MODELS = {
    "openai": DEFAULT_MODEL,
    "anthropic": DEFAULT_ANTHROPIC_MODEL,
    "chatgpt": DEFAULT_CHATGPT_MODEL,
    "claude-code": DEFAULT_CLAUDE_CODE_MODEL,
}
REASONING_EFFORTS = (
    "none",
    "minimal",
    "low",
    "medium",
    "high",
    "xhigh",
    "max",
    "ultra",
)
DEFAULT_REASONING_EFFORT = "low"
DEFAULT_SCRIPTED_TIMEOUT_SECONDS = 300.0
DEFAULT_SCRIPTED_MEMORY_LIMIT_MB = 6144


def normalize_provider(value: str | None) -> str:
    clean = (value or "").strip().lower()
    return clean if clean in PROVIDERS else DEFAULT_PROVIDER


@dataclass(frozen=True)
class CadexSettings:
    experimental_mode: bool = True
    use_online_provider: bool = True
    model: str = DEFAULT_MODEL
    dotenv_path: str = ""
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    provider: str = DEFAULT_PROVIDER
    anthropic_model: str = DEFAULT_ANTHROPIC_MODEL
    chatgpt_model: str = DEFAULT_CHATGPT_MODEL
    claude_code_model: str = DEFAULT_CLAUDE_CODE_MODEL
    web_search_enabled: bool = False
    codex_skills_enabled: bool = False
    openai_base_url: str = ""
    anthropic_base_url: str = ""
    xscript_enabled: bool = True
    scripted_timeout_seconds: float = DEFAULT_SCRIPTED_TIMEOUT_SECONDS
    scripted_memory_limit_mb: int = DEFAULT_SCRIPTED_MEMORY_LIMIT_MB

    @property
    def resolved_dotenv_path(self) -> Path | None:
        if not self.dotenv_path:
            return None
        return Path(self.dotenv_path).expanduser()

    @property
    def active_model(self) -> str:
        """Model for the selected provider."""
        provider = normalize_provider(self.provider)
        if provider == "anthropic":
            return self.anthropic_model.strip() or DEFAULT_ANTHROPIC_MODEL
        if provider == "chatgpt":
            return self.chatgpt_model.strip()
        if provider == "claude-code":
            return self.claude_code_model.strip() or DEFAULT_CLAUDE_CODE_MODEL
        return self.model.strip() or DEFAULT_MODEL

    @property
    def active_base_url(self) -> str | None:
        """Base URL override for the selected provider; None means official endpoint."""
        provider = normalize_provider(self.provider)
        if provider in {"chatgpt", "claude-code"}:
            return None
        if provider == "anthropic":
            override = self.anthropic_base_url.strip()
        else:
            override = self.openai_base_url.strip()
        return override or None

    def base_url_for(self, provider: str) -> str | None:
        """Base URL override for ``provider``; None means official endpoint."""
        clean_provider = normalize_provider(provider)
        if clean_provider in {"chatgpt", "claude-code"}:
            return None
        if clean_provider == "anthropic":
            override = self.anthropic_base_url.strip()
        else:
            override = self.openai_base_url.strip()
        return override or None

    def model_for(self, provider: str) -> str:
        """Configured interactive model for ``provider``."""
        clean_provider = normalize_provider(provider)
        if clean_provider == "anthropic":
            return self.anthropic_model.strip() or DEFAULT_ANTHROPIC_MODEL
        if clean_provider == "chatgpt":
            return self.chatgpt_model.strip()
        if clean_provider == "claude-code":
            return self.claude_code_model.strip() or DEFAULT_CLAUDE_CODE_MODEL
        return self.model.strip() or DEFAULT_MODEL


@dataclass(frozen=True)
class CadexDebugSettings:
    context_debug_enabled: bool = False
    capture_directory: str = ""

    @property
    def resolved_capture_directory(self) -> Path:
        return resolve_capture_directory(self.capture_directory)


def preferences():
    return App.ParamGet(PREFERENCE_GROUP)


def normalize_reasoning_effort(value: str | None) -> str:
    clean = (value or "").strip().lower()
    return clean if clean in REASONING_EFFORTS else DEFAULT_REASONING_EFFORT


def _positive_float(value: object, default: float) -> float:
    try:
        clean = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return clean if clean > 0 else default


def _positive_int(value: object, default: int) -> int:
    try:
        clean = int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return default
    return clean if clean > 0 else default


def load_settings() -> CadexSettings:
    pref = preferences()
    return CadexSettings(
        experimental_mode=pref.GetBool("ExperimentalMode", True),
        use_online_provider=pref.GetBool("UseOnlineProvider", True),
        model=pref.GetString("Model", DEFAULT_MODEL) or DEFAULT_MODEL,
        dotenv_path=pref.GetString("DotenvPath", ""),
        reasoning_effort=normalize_reasoning_effort(
            pref.GetString("ReasoningEffort", DEFAULT_REASONING_EFFORT)
        ),
        provider=normalize_provider(pref.GetString("Provider", DEFAULT_PROVIDER)),
        anthropic_model=pref.GetString("AnthropicModel", DEFAULT_ANTHROPIC_MODEL)
        or DEFAULT_ANTHROPIC_MODEL,
        chatgpt_model=pref.GetString("ChatGPTModel", DEFAULT_CHATGPT_MODEL),
        claude_code_model=pref.GetString("ClaudeCodeModel", DEFAULT_CLAUDE_CODE_MODEL)
        or DEFAULT_CLAUDE_CODE_MODEL,
        web_search_enabled=pref.GetBool("WebSearchEnabled", False),
        codex_skills_enabled=pref.GetBool("CodexSkillsEnabled", False),
        openai_base_url=pref.GetString("OpenAIBaseUrl", ""),
        anthropic_base_url=pref.GetString("AnthropicBaseUrl", ""),
        xscript_enabled=pref.GetBool("XScriptEnabled", True),
        scripted_timeout_seconds=_positive_float(
            pref.GetFloat("ScriptedTimeoutSeconds", DEFAULT_SCRIPTED_TIMEOUT_SECONDS),
            DEFAULT_SCRIPTED_TIMEOUT_SECONDS,
        ),
        scripted_memory_limit_mb=_positive_int(
            pref.GetInt("ScriptedMemoryLimitMB", DEFAULT_SCRIPTED_MEMORY_LIMIT_MB),
            DEFAULT_SCRIPTED_MEMORY_LIMIT_MB,
        ),
    )


def load_debug_settings() -> CadexDebugSettings:
    pref = preferences()
    return CadexDebugSettings(
        context_debug_enabled=pref.GetBool("ContextDebugEnabled", False),
        capture_directory=pref.GetString("ContextDebugDirectory", ""),
    )


def save_settings(settings: CadexSettings) -> None:
    pref = preferences()
    pref.SetBool("ExperimentalMode", bool(settings.experimental_mode))
    pref.SetBool("UseOnlineProvider", bool(settings.use_online_provider))
    pref.SetString("Model", settings.model.strip() or DEFAULT_MODEL)
    pref.SetString("DotenvPath", settings.dotenv_path.strip())
    pref.SetString(
        "ReasoningEffort", normalize_reasoning_effort(settings.reasoning_effort)
    )
    pref.SetString("Provider", normalize_provider(settings.provider))
    pref.SetString(
        "AnthropicModel", settings.anthropic_model.strip() or DEFAULT_ANTHROPIC_MODEL
    )
    pref.SetString("ChatGPTModel", settings.chatgpt_model.strip())
    pref.SetString(
        "ClaudeCodeModel",
        settings.claude_code_model.strip() or DEFAULT_CLAUDE_CODE_MODEL,
    )
    pref.SetBool("WebSearchEnabled", bool(settings.web_search_enabled))
    pref.SetBool("CodexSkillsEnabled", bool(settings.codex_skills_enabled))
    pref.SetString("OpenAIBaseUrl", settings.openai_base_url.strip())
    pref.SetString("AnthropicBaseUrl", settings.anthropic_base_url.strip())
    pref.SetBool("XScriptEnabled", bool(settings.xscript_enabled))
    pref.SetFloat(
        "ScriptedTimeoutSeconds",
        _positive_float(
            settings.scripted_timeout_seconds, DEFAULT_SCRIPTED_TIMEOUT_SECONDS
        ),
    )
    pref.SetInt(
        "ScriptedMemoryLimitMB",
        _positive_int(
            settings.scripted_memory_limit_mb, DEFAULT_SCRIPTED_MEMORY_LIMIT_MB
        ),
    )


def save_debug_settings(settings: CadexDebugSettings) -> None:
    pref = preferences()
    pref.SetBool("ContextDebugEnabled", bool(settings.context_debug_enabled))
    pref.SetString("ContextDebugDirectory", settings.capture_directory.strip())


def reset_settings() -> None:
    pref = preferences()
    pref.RemBool("ExperimentalMode")
    pref.RemBool("ExperimentalModePrompted")
    pref.RemBool("UseOnlineProvider")
    pref.RemString("Model")
    pref.RemString("DotenvPath")
    pref.RemString("ReasoningEffort")
    pref.RemString("Provider")
    pref.RemString("AnthropicModel")
    pref.RemString("ChatGPTModel")
    pref.RemString("ClaudeCodeModel")
    pref.RemBool("WebSearchEnabled")
    pref.RemBool("CodexSkillsEnabled")
    pref.RemString("OpenAIBaseUrl")
    pref.RemString("AnthropicBaseUrl")
    pref.RemBool("XScriptEnabled")
    pref.RemFloat("ScriptedTimeoutSeconds")
    pref.RemInt("ScriptedMemoryLimitMB")
    pref.RemBool("ContextDebugEnabled")
    pref.RemString("ContextDebugDirectory")


def configured_dotenv_path() -> Path | None:
    return load_settings().resolved_dotenv_path


def fetch_models_for_provider(
    provider: str,
    dotenv_path: Path | None = None,
    base_url: str | None = None,
) -> dict:
    """Resolve the configured key for ``provider`` and query its models endpoint.

    Returns the ``list_provider_models`` payload:
    {"ok": bool, "models": [str, ...], "error": str | None}.
    """
    clean_provider = normalize_provider(provider)
    if clean_provider == "chatgpt":
        return list_provider_models(None, provider=clean_provider)
    credential = resolve_auth_credential(
        dotenv_path=dotenv_path, provider=clean_provider
    )
    if credential is None:
        spec = PROVIDERS[clean_provider]
        return {
            "ok": False,
            "models": [],
            "error": f"No {spec.display_name} {spec.credential_label} is configured.",
        }
    return list_provider_models(
        credential.value, provider=clean_provider, base_url=base_url
    )
