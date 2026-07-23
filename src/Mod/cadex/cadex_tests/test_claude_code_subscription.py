# SPDX-License-Identifier: LGPL-2.1-or-later

"""Focused contracts for the Claude Code subscription provider."""

from __future__ import annotations

import json
from pathlib import Path
import time

import pytest

import CadexAuth as auth
import CadexPreferences as preferences
import CadexProvider as provider
import CadexSession as session

OAUTH_TOKEN = "sk-ant-oat01-example-token"
API_KEY = "sk-ant-api03-example-key"


def _write_credentials(
    config_dir: Path,
    token: str = OAUTH_TOKEN,
    expires_in_seconds: float = 3600.0,
    subscription_type: str = "max",
) -> Path:
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / auth.CLAUDE_CODE_CREDENTIALS_FILENAME
    path.write_text(
        json.dumps(
            {
                "claudeAiOauth": {
                    "accessToken": token,
                    "refreshToken": "sk-ant-ort01-example",
                    "expiresAt": int((time.time() + expires_in_seconds) * 1000),
                    "subscriptionType": subscription_type,
                }
            }
        )
    )
    return path


class TestProviderSpec:
    def test_registered_with_subscription_auth_kind(self):
        spec = auth.provider_spec("claude-code")
        assert spec.display_name == "Claude Code subscription"
        assert spec.auth_kind == "claude_code_subscription"
        assert spec.env_var == "CLAUDE_CODE_OAUTH_TOKEN"
        assert not spec.uses_api_key
        assert spec.uses_http_credential
        assert spec.is_anthropic_api
        assert spec.credential_label == "sign-in"

    def test_auth_headers_use_bearer_and_oauth_beta(self):
        headers = auth.provider_spec("claude-code").auth_headers(OAUTH_TOKEN)
        assert headers["Authorization"] == f"Bearer {OAUTH_TOKEN}"
        assert headers["anthropic-version"] == auth.ANTHROPIC_API_VERSION
        assert headers["anthropic-beta"] == auth.ANTHROPIC_OAUTH_BETA
        assert "x-api-key" not in headers

    def test_anthropic_headers_unchanged(self):
        headers = auth.provider_spec("anthropic").auth_headers(API_KEY)
        assert headers == {
            "x-api-key": API_KEY,
            "anthropic-version": auth.ANTHROPIC_API_VERSION,
        }

    def test_models_url_follows_anthropic_convention(self):
        spec = auth.provider_spec("claude-code")
        assert spec.models_url_for() == "https://api.anthropic.com/v1/models"
        assert spec.models_url_for("https://proxy.local") == (
            "https://proxy.local/v1/models"
        )


class TestCredentialResolution:
    @pytest.fixture(autouse=True)
    def _no_host_keychain(self, monkeypatch):
        """Keep tests hermetic: never consult the real macOS keychain."""
        monkeypatch.setattr(auth, "_read_claude_code_keychain", lambda: None)

    def test_credentials_file_resolves_token(self, tmp_path: Path):
        path = _write_credentials(tmp_path)
        env = {"CLAUDE_CONFIG_DIR": str(tmp_path)}
        credential = auth.resolve_auth_credential(env=env, provider="claude-code")
        assert credential is not None
        assert credential.value == OAUTH_TOKEN
        assert credential.source == str(path)

    def test_env_var_overrides_credentials_file(self, tmp_path: Path):
        _write_credentials(tmp_path, token="sk-ant-oat01-from-file")
        env = {
            "CLAUDE_CONFIG_DIR": str(tmp_path),
            "CLAUDE_CODE_OAUTH_TOKEN": OAUTH_TOKEN,
        }
        credential = auth.resolve_auth_credential(env=env, provider="claude-code")
        assert credential is not None
        assert credential.value == OAUTH_TOKEN
        assert credential.source == "environment"

    def test_expired_token_is_not_offered(self, tmp_path: Path):
        _write_credentials(tmp_path, expires_in_seconds=-120.0)
        env = {"CLAUDE_CONFIG_DIR": str(tmp_path)}
        assert auth.resolve_auth_credential(env=env, provider="claude-code") is None
        state = auth.resolve_auth_state(env=env, provider="claude-code")
        assert state.status is auth.AuthStatus.INVALID
        assert "expired" in state.message

    def test_missing_sign_in_reports_login_hint(self, tmp_path: Path):
        env = {"CLAUDE_CONFIG_DIR": str(tmp_path)}
        state = auth.resolve_auth_state(env=env, provider="claude-code")
        assert state.status is auth.AuthStatus.NOT_CONFIGURED
        assert "Claude Code" in state.message
        assert str(tmp_path) in state.message

    def test_signed_in_state_reports_plan(self, tmp_path: Path):
        _write_credentials(tmp_path, subscription_type="max")
        env = {"CLAUDE_CONFIG_DIR": str(tmp_path)}
        state = auth.resolve_auth_state(env=env, provider="claude-code")
        assert state.status is auth.AuthStatus.CONFIGURED_UNVERIFIED
        assert "max" in state.message
        assert state.redacted_key != OAUTH_TOKEN

    def test_malformed_credentials_file_is_ignored(self, tmp_path: Path):
        tmp_path.mkdir(parents=True, exist_ok=True)
        (tmp_path / auth.CLAUDE_CODE_CREDENTIALS_FILENAME).write_text("not json")
        env = {"CLAUDE_CONFIG_DIR": str(tmp_path)}
        assert auth.read_claude_code_credentials(env=env) is None
        assert auth.resolve_auth_credential(env=env, provider="claude-code") is None

    def test_token_detection(self):
        assert auth.is_claude_code_oauth_token(OAUTH_TOKEN)
        assert not auth.is_claude_code_oauth_token(API_KEY)
        assert not auth.is_claude_code_oauth_token("")
        assert not auth.is_claude_code_oauth_token(None)

    def test_no_pasted_secrets_for_claude_code(self):
        result = auth.store_keyring_key(OAUTH_TOKEN, provider="claude-code")
        assert result["stored"] is False
        assert "Claude Code" in str(result["error"])


def _keychain_payload(
    token: str = OAUTH_TOKEN, expires_in_seconds: float = 3600.0
) -> str:
    return json.dumps(
        {
            "claudeAiOauth": {
                "accessToken": token,
                "expiresAt": int((time.time() + expires_in_seconds) * 1000),
                "subscriptionType": "max",
            }
        }
    )


class TestKeychainFallback:
    def test_keychain_resolves_when_file_is_missing(self, tmp_path: Path):
        env = {"CLAUDE_CONFIG_DIR": str(tmp_path)}
        credentials = auth.read_claude_code_credentials(
            env=env, keychain_reader=_keychain_payload
        )
        assert credentials is not None
        assert credentials["access_token"] == OAUTH_TOKEN
        assert auth.CLAUDE_CODE_KEYCHAIN_SERVICE in credentials["source"]

    def test_credentials_file_wins_over_keychain(self, tmp_path: Path):
        _write_credentials(tmp_path, token="sk-ant-oat01-from-file")
        env = {"CLAUDE_CONFIG_DIR": str(tmp_path)}
        credentials = auth.read_claude_code_credentials(
            env=env,
            keychain_reader=lambda: _keychain_payload("sk-ant-oat01-from-keychain"),
        )
        assert credentials is not None
        assert credentials["access_token"] == "sk-ant-oat01-from-file"

    def test_expired_keychain_token_reports_expired(self, tmp_path: Path, monkeypatch):
        env = {"CLAUDE_CONFIG_DIR": str(tmp_path)}
        monkeypatch.setattr(
            auth,
            "_read_claude_code_keychain",
            lambda: _keychain_payload(expires_in_seconds=-120.0),
        )
        assert auth.resolve_auth_credential(env=env, provider="claude-code") is None
        state = auth.resolve_auth_state(env=env, provider="claude-code")
        assert state.status is auth.AuthStatus.INVALID
        assert "expired" in state.message

    def test_unreadable_keychain_means_not_configured(self, tmp_path: Path, monkeypatch):
        env = {"CLAUDE_CONFIG_DIR": str(tmp_path)}
        monkeypatch.setattr(auth, "_read_claude_code_keychain", lambda: None)
        state = auth.resolve_auth_state(env=env, provider="claude-code")
        assert state.status is auth.AuthStatus.NOT_CONFIGURED


class TestSystemShaping:
    def test_oauth_token_prepends_claude_code_identity(self):
        shaped = provider.anthropic_system_for_credential(
            OAUTH_TOKEN, [{"type": "text", "text": "CAD instructions."}]
        )
        assert shaped[0] == {
            "type": "text",
            "text": provider.CLAUDE_CODE_SYSTEM_IDENTITY,
        }
        assert shaped[1]["text"] == "CAD instructions."

    def test_string_system_becomes_blocks_behind_identity(self):
        shaped = provider.anthropic_system_for_credential(OAUTH_TOKEN, "Compile.")
        assert [block["text"] for block in shaped] == [
            provider.CLAUDE_CODE_SYSTEM_IDENTITY,
            "Compile.",
        ]

    def test_api_key_system_passes_through_unchanged(self):
        blocks = [{"type": "text", "text": "CAD instructions."}]
        assert provider.anthropic_system_for_credential(API_KEY, blocks) is blocks
        assert provider.anthropic_system_for_credential(None, "Compile.") == "Compile."


class TestAnthropicClientAuthKwargs:
    def test_oauth_token_becomes_bearer_auth(self):
        kwargs = provider.anthropic_client_auth_kwargs(OAUTH_TOKEN)
        assert kwargs == {
            "auth_token": OAUTH_TOKEN,
            "default_headers": {"anthropic-beta": auth.ANTHROPIC_OAUTH_BETA},
        }

    def test_api_key_stays_api_key(self):
        assert provider.anthropic_client_auth_kwargs(API_KEY) == {"api_key": API_KEY}

    def test_missing_credential_defers_to_sdk_resolution(self):
        assert provider.anthropic_client_auth_kwargs(None) == {}
        assert provider.anthropic_client_auth_kwargs("") == {}


class TestPreferences:
    def test_default_model_is_fable(self):
        assert preferences.DEFAULT_CLAUDE_CODE_MODEL == "claude-fable-5"
        assert preferences.DEFAULT_MODELS["claude-code"] == "claude-fable-5"

    def test_active_model_defaults_to_fable(self):
        settings = preferences.CadexSettings(provider="claude-code")
        assert settings.active_model == "claude-fable-5"
        assert settings.model_for("claude-code") == "claude-fable-5"

    def test_blank_model_falls_back_to_fable(self):
        settings = preferences.CadexSettings(
            provider="claude-code", claude_code_model="   "
        )
        assert settings.active_model == "claude-fable-5"

    def test_subscription_ignores_base_url_overrides(self):
        settings = preferences.CadexSettings(
            provider="claude-code",
            anthropic_base_url="https://proxy.local",
            openai_base_url="https://other.local/v1",
        )
        assert settings.active_base_url is None
        assert settings.base_url_for("claude-code") is None

    def test_normalize_provider_accepts_claude_code(self):
        assert preferences.normalize_provider("claude-code") == "claude-code"
        assert preferences.normalize_provider("Claude-Code") == "claude-code"


class _FakeService:
    """Just enough of CadexService for choose_provider."""

    def __init__(self, can_call: bool = True):
        self._can_call = can_call

    def provider_name(self) -> str:
        return "claude-code"

    def auth_state(self):
        status = (
            auth.AuthStatus.CONFIGURED_UNVERIFIED
            if self._can_call
            else auth.AuthStatus.NOT_CONFIGURED
        )
        return auth.AuthState(status)

    def provider_model(self) -> str:
        return "claude-fable-5"

    def provider_api_key(self) -> str | None:
        return OAUTH_TOKEN

    def provider_reasoning_effort(self) -> str:
        return "high"

    def provider_base_url(self) -> str | None:
        return None

    def web_search_enabled(self) -> bool:
        return False

    def codex_skills_enabled(self) -> bool:
        return False


class TestChooseProvider:
    def test_claude_code_rides_the_anthropic_adapter(self):
        chosen = session.choose_provider(_FakeService())
        assert isinstance(chosen, session.AnthropicProvider)
        assert chosen.model == "claude-fable-5"
        assert chosen.api_key == OAUTH_TOKEN
        assert chosen.base_url is None

    def test_unconfigured_token_falls_back_offline(self):
        chosen = session.choose_provider(_FakeService(can_call=False))
        assert isinstance(chosen, session.OfflineProvider)
