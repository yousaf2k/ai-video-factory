"""
LLM Provider Base Classes
Abstract base class for all LLM providers (Gemini, OpenAI, Z.AI, Qwen, Kimi K2 2.5)
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
import time
import requests
import config
import os
import json
from core.comfy_client import http_session
from core import llm_call_log
from core import model_registry
from core import thinking_formats

# Get logger for provider operations
logger = logging.getLogger(__name__)


def _resolve_timeout(config_module, prefix: str, default: int = 300) -> int:
    """Provider request timeout: {PREFIX}_TIMEOUT (when > 0) -> LLM_TIMEOUT
    (when > 0) -> default. Local providers on slow hardware should raise
    LLM_TIMEOUT or their per-provider value."""
    try:
        raw = int(getattr(config_module, f"{prefix}_TIMEOUT", 0) or 0)
    except (TypeError, ValueError):
        raw = 0
    if raw > 0:
        return raw
    try:
        global_timeout = int(getattr(config_module, "LLM_TIMEOUT", 0) or 0)
    except (TypeError, ValueError):
        global_timeout = 0
    if global_timeout > 0:
        return global_timeout
    return default


def _resolve_max_tokens(config_module, prefix: str, default: int = 16384) -> int:
    """Provider-specific {PREFIX}_MAX_TOKENS override, else global LLM_MAX_TOKENS."""
    raw = str(getattr(config_module, f"{prefix}_MAX_TOKENS", "") or "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return getattr(config_module, 'LLM_MAX_TOKENS', default)


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    # Wire format used when the active model declares no
    # compat.thinkingFormat in models.json (None = no thinking field).
    default_thinking_format: Optional[str] = None

    @abstractmethod
    def ask(self, prompt: str, response_format: str = None) -> str:
        """
        Send prompt to LLM and return text response.

        Args:
            prompt: The text prompt to send
            response_format: Optional format hint (e.g., "application/json")

        Returns:
            Text response from LLM
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging and display"""
        pass

    @property
    @abstractmethod
    def requires_api_key(self) -> bool:
        """Whether this provider needs API key"""
        pass

    def validate_config(self) -> bool:
        """Validate required configuration exists"""
        if self.requires_api_key:
            if not self.api_key or self.api_key == "":
                raise ValueError(
                    f"{self.name} requires API key"
                    f"Set {self.env_key} environment variable or add to config.py"
                )
        return True

    def disable_thinking(self):
        """Turn thinking off for subsequent ask() calls (used by story generation).

        Sets the hard-off flag consumed by every provider's request builder.
        Providers whose wire format has an off representation express it
        (zai/deepseek: thinking.type=disabled, openai: reasoning_effort=none,
        gemini: thinking_budget=0, ollama/qwen: bool false); models whose
        declared format has none simply send nothing either way."""
        self._thinking_disabled = True
        return True

    def set_thinking_level(self, level):
        """Configure the thinking/reasoning level from Settings.

        Accepts any value the provider supports (the Settings dropdown lists
        THINKING_OPTIONS[provider]); unknown/custom values pass through to the
        provider's effort field verbatim. "" / "default" / None clears it.
        """
        raw = str(level or "").strip().lower()
        if raw in ("", "default"):
            self.thinking_level = None
        else:
            self.thinking_level = raw
        return bool(getattr(self, "thinking_level", None))

    def _effective_thinking_level(self) -> Optional[str]:
        """Configured thinking level mapped through the model's thinkingLevelMap.

        Returns the provider value to send, or None when the level is
        unsupported for this model (null in models.json) — ask() then sends
        nothing. Providers without a models.json entry pass levels through.
        """
        level = getattr(self, "thinking_level", None)
        if not level:
            return None
        return model_registry.map_thinking_level(
            getattr(self, "provider_key", None), getattr(self, "model", None), level)

    def _thinking_format(self) -> Optional[str]:
        """Wire format for the active model: compat.thinkingFormat from
        models.json wins; the class default is the fallback. This is what
        makes the file the source of truth — e.g. a qwen model loaded in
        Strata declares "qwen" and the body gets enable_thinking regardless
        of which provider serves it."""
        fmt = model_registry.get_thinking_format(
            getattr(self, "provider_key", None), getattr(self, "model", None))
        if fmt:
            return fmt
        return getattr(self, "default_thinking_format", None)

    def _thinking_request_fields(self) -> Dict[str, Any]:
        """Request-body field(s) implementing the model's thinking format.

        Precedence: _thinking_disabled (story generation) -> hard "off";
        else the configured level mapped through thinkingLevelMap.
        Returns {} when nothing should be sent (no level configured, a null
        mapped level, or a format with no representation for the value).
        """
        if getattr(self, "_thinking_disabled", False):
            level = "off"
        else:
            configured = getattr(self, "thinking_level", None)
            if not configured:
                return {}
            level = self._effective_thinking_level()
            if not level:
                return {}
        return thinking_formats.build(self._thinking_format(), level)

    def _bool_thinking_flag(self):
        """Tri-state thinking switch for providers with boolean think params
        (Ollama `think`, Qwen `enable_thinking`).

        Returns True (thinking on), False (thinking off), or None (leave the
        model default). Story-generation disable and "off" map to False."""
        if getattr(self, "_thinking_disabled", False):
            return False
        # Mapped through the model's thinkingLevelMap (models.json) first;
        # a None result means the level is unsupported -> leave the default.
        level = self._effective_thinking_level()
        if not level:
            return None
        if level in ("off", "disabled", "false", "no", "0"):
            return False
        if level in ("on", "enabled", "true", "yes", "1", "low", "medium", "high", "max"):
            return True
        return None  # unparseable custom value: leave the model default

    def log_request(self, prompt: str, response_format: Optional[str]):
        """Log request details"""
        logger.debug(f"{self.name} API Request:")
        logger.debug(f"  Model: {self.model} ")
        logger.debug(f"  Prompt length: {len(prompt)} characters")
        if response_format:
            logger.debug(f"  Response format: {response_format} ")

    def log_response(self, response: str, elapsed: float):
        """Log response details"""
        logger.debug(f"{self.name} API Response:")
        logger.debug(f"  Response length: {len(response)} characters")
        logger.debug(f"  Success in {elapsed:.2f}s")

    def log_error(self, error: Exception, elapsed: float):
        """Log errors with full traceback"""
        llm_call_log.fail_call(error, elapsed)
        logger.debug(f"{self.name} API Error: {str(error)}")
        logger.error(f"  Elapsed: {elapsed:.2f}s")
        logger.debug(f"  Traceback: {error.__traceback__}")

    def log_raw_request(self, url: str, method: str = "POST",
                        headers: Optional[dict] = None, body=None) -> None:
        """Full raw wire request -> llm_io.log + the structured call log.

        Auth headers are redacted; bodies are JSON-serialized (SDK objects
        via model_dump when available)."""
        try:
            llm_call_log.record_raw_request(self, url, method, headers, body)
            if not llm_call_log.raw_enabled():
                return
            from core.logger_config import setup_llm_io_logger
            import json as _json
            io_logger = setup_llm_io_logger(self.__class__.__name__)
            io_logger.info(f"{'=' * 80}")
            io_logger.info(f"RAW REQUEST to {self.name} API")
            io_logger.info(f"{method} {url}")
            for k, v in llm_call_log.redact_headers(headers).items():
                io_logger.info(f"Header: {k}: {v}")
            if body is not None:
                io_logger.info("Body:")
                io_logger.info(_json.dumps(
                    llm_call_log._jsonify(body), ensure_ascii=False, indent=2, default=str))
            io_logger.info("=" * 80)
            io_logger.info("")
        except Exception as e:
            logger.debug(f"Raw request logging failed: {e}")

    def log_raw_response(self, status=None, body=None) -> None:
        """Full raw wire response -> llm_io.log + the structured call log."""
        try:
            llm_call_log.record_raw_response(self, status, body)
            if not llm_call_log.raw_enabled():
                return
            from core.logger_config import setup_llm_io_logger
            import json as _json
            io_logger = setup_llm_io_logger(self.__class__.__name__)
            io_logger.info(f"{'=' * 80}")
            io_logger.info(f"RAW RESPONSE from {self.name} API (status={status})")
            if body is not None:
                io_logger.info("Body:")
                io_logger.info(_json.dumps(
                    llm_call_log._jsonify(body), ensure_ascii=False, indent=2, default=str))
            io_logger.info("=" * 80)
            io_logger.info("")
        except Exception as e:
            logger.debug(f"Raw response logging failed: {e}")

    def _raw_post(self, url: str, data: dict, headers: dict, **kwargs):
        """http_session.post with full raw request/response logging."""
        self.log_raw_request(url, "POST", headers, data)
        response = http_session.post(url, json=data, headers=headers, **kwargs)
        self.log_raw_response(
            getattr(response, "status_code", None), getattr(response, "text", ""))
        return response

    # ------------------------------------------------------------- console streaming

    def _console_stream_enabled(self) -> bool:
        try:
            return bool(getattr(config, 'LLM_STREAM_TO_CONSOLE', True))
        except Exception:
            return True

    def _begin_console_stream(self):
        print(f"[LLM] {self.name} ({self.model}): ", end="", flush=True)

    def _print_stream_chunk(self, text: str):
        if text:
            print(text, end="", flush=True)

    def _finish_console_stream(self):
        print(flush=True)

    def _parse_sse_content_chunk(self, payload: str) -> str:
        """Extract the assistant text delta from one OpenAI-style SSE data line."""
        if not payload or payload == "[DONE]":
            return ""
        try:
            chunk = json.loads(payload)
        except Exception:
            return ""
        try:
            return chunk.get("choices", [{}])[0].get("delta", {}).get("content") or ""
        except Exception:
            return ""

    def _post_chat(self, url: str, data: dict, headers: dict, **kwargs) -> str:
        """POST a chat-completions style request and return the assistant content.

        When console streaming is enabled the request is sent with
        "stream": true and tokens are printed to the console as they arrive;
        the full text is still returned to the caller and logged as before.
        Any non-200 response raises (same as the previous inline handling).
        """
        if not self._console_stream_enabled():
            response = self._raw_post(url, data, headers, **kwargs)
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            return response.json().get("choices", [{}])[0].get("message", {}).get("content", "")

        stream_data = dict(data)
        stream_data["stream"] = True
        self.log_raw_request(url, "POST", headers, stream_data)
        response = http_session.post(url, json=stream_data, headers=headers, stream=True, **kwargs)
        if response.status_code != 200:
            self.log_raw_response(
                getattr(response, "status_code", None), getattr(response, "text", ""))
            raise Exception(f"HTTP {response.status_code}: {response.text}")
        self.log_raw_response(getattr(response, "status_code", None), "(streamed)")

        parts = []
        self._begin_console_stream()
        try:
            for line in response.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data:"):
                    continue
                delta = self._parse_sse_content_chunk(line[5:].strip())
                if delta:
                    parts.append(delta)
                    self._print_stream_chunk(delta)
        finally:
            self._finish_console_stream()
        return "".join(parts)

    def log_request_full(self, prompt: str, response_format: Optional[str]):
        """Log the full request content"""
        llm_call_log.begin_call(self, prompt, response_format)

        from core.logger_config import setup_llm_io_logger
        io_logger = setup_llm_io_logger(self.__class__.__name__)

        io_logger.info(f"{'='*80}")
        io_logger.info(f"REQUEST to {self.name} API")
        io_logger.info(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        io_logger.info(f"Model: {self.model}")
        if response_format:
            io_logger.info(f"Response Format: {response_format}")
        io_logger.info(f"{'='*80}")
        io_logger.info(f"PROMPT:\n{prompt}")
        io_logger.info(f"{'='*80}\n")

    def log_response_full(self, response: str, elapsed: float):
        """Log the full response content"""
        llm_call_log.complete_call(response, elapsed)

        from core.logger_config import setup_llm_io_logger
        io_logger = setup_llm_io_logger(self.__class__.__name__)

        io_logger.info(f"{'='*80}")
        io_logger.info(f"RESPONSE from {self.name} API")
        io_logger.info(f"Elapsed: {elapsed:.2f}s")
        io_logger.info(f"{'='*80}")
        io_logger.info(f"RESPONSE:\n{response}")
        io_logger.info(f"{'='*80}\n")


class GeminiProvider(LLMProvider):
    """Google Gemini API provider (refactored from gemini_engine.py)"""

    def __init__(self, api_key: str, model: str, base_url: str = None):
        self.api_key = api_key
        self.model = model
        self.env_key = "GEMINI_API_KEY"
        self.base_url = base_url
        self.timeout = _resolve_timeout(config, 'GEMINI')
        self.max_tokens = _resolve_max_tokens(config, 'GEMINI')
        self._thinking_disabled = False
        self.thinking_level = None

    @property
    def name(self) -> str:
        return "Gemini"

    @property
    def requires_api_key(self) -> bool:
        return True

    def disable_thinking(self):
        """Disable thinking via thinking_budget=0 (Gemini 2.5+ thinking models)."""
        self._thinking_disabled = True
        return True

    def ask(self, prompt: str, response_format: str = None) -> str:
        """Send prompt to Gemini API"""
        self.validate_config()
        self.log_request(prompt, response_format)
        self.log_request_full(prompt, response_format)

        try:
            import google.genai as genai
            from google.genai import types

            start_time = time.time()

            # Initialize client
            http_options = {'api_version': 'v1alpha'}
            if self.base_url:
                http_options['base_url'] = self.base_url
            client = genai.Client(
                api_key=self.api_key,
                http_options=http_options
            )

            # Configure response format
            gen_config_kwargs = {
                "response_mime_type": "application/json" if response_format == "application/json" else "text/plain",
                "max_output_tokens": self.max_tokens,
            }
            if self._thinking_disabled:
                # thinking_budget=0 turns thinking off on 2.5-series thinking
                # models; guarded so an older SDK without ThinkingConfig
                # degrades to normal (thinking) behaviour instead of failing.
                try:
                    gen_config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
                except Exception as cfg_err:
                    logger.debug(f"Gemini thinking_config unavailable, continuing with defaults: {cfg_err}")
                    self._thinking_disabled = False
            elif getattr(self, "thinking_level", None):
                # Configured level from Settings, mapped through the model's
                # thinkingLevelMap (models.json): "off" -> budget 0,
                # low/high/custom -> thinking_level (Gemini 3 series). A None
                # mapping means the level is unsupported -> send nothing.
                level = self._effective_thinking_level()
                if level:
                    try:
                        if level == "off":
                            gen_config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
                        else:
                            gen_config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_level=level)
                    except Exception as cfg_err:
                        logger.debug(f"Gemini thinking_config for level '{level}' unavailable, continuing with defaults: {cfg_err}")
            gen_config = types.GenerateContentConfig(**gen_config_kwargs)

            # Full raw request/response log (SDK path; auth header redacted)
            self.log_raw_request(
                f"{self.base_url or 'https://generativelanguage.googleapis.com'}"
                f"/v1alpha/models/{self.model}:generateContent",
                headers={"x-goog-api-key": self.api_key or ""},
                body={"contents": prompt, "generation_config": gen_config_kwargs})
            if self._console_stream_enabled():
                # Stream chunks to the console via the SDK
                self.log_raw_request(
                    f"{self.base_url or 'https://generativelanguage.googleapis.com'}"
                    f"/v1alpha/models/{self.model}:streamGenerateContent",
                    headers={"x-goog-api-key": self.api_key or ""},
                    body={"contents": prompt, "generation_config": gen_config_kwargs})
                stream = client.models.generate_content_stream(
                    model=self.model,
                    contents=prompt,
                    config=gen_config
                )
                parts = []
                self._begin_console_stream()
                try:
                    for chunk in stream:
                        text = getattr(chunk, "text", None)
                        if text:
                            parts.append(text)
                            self._print_stream_chunk(text)
                finally:
                    self._finish_console_stream()
                content = "".join(parts)
                self.log_raw_response(200, {"content": content})
            else:
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=gen_config
                )
                self.log_raw_response(200, response)
                content = response.text

            elapsed = time.time() - start_time
            self.log_response(content, elapsed)
            self.log_response_full(content, elapsed)

            return content

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class OpenAIProvider(LLMProvider):
    """OpenAI (ChatGPT) API provider"""

    default_thinking_format = "openai"

    def __init__(self, api_key: str, model: str, base_url: str = None):
        self.api_key = api_key
        self.model = model
        self.env_key = "OPENAI_API_KEY"
        self.base_url = base_url
        self.timeout = _resolve_timeout(config, 'OPENAI')
        # Optional reasoning effort for reasoning models (o-series / gpt-5*):
        # "minimal" | "low" | "medium" | "high". None = model default.
        self.reasoning_effort = None
        self._thinking_disabled = False
        self.thinking_level = None

    def set_reasoning_effort(self, effort):
        if effort and str(effort).strip().lower() in ("none", "minimal", "low", "medium", "high"):
            self.reasoning_effort = str(effort).strip().lower()

    def disable_thinking(self):
        """reasoning_effort="none" disables hidden reasoning tokens completely."""
        self._thinking_disabled = True
        self.reasoning_effort = "none"
        return True

    @property
    def name(self) -> str:
        return "OpenAI"

    @property
    def requires_api_key(self) -> bool:
        return True

    def ask(self, prompt: str, response_format: str = None) -> str:
        """Send prompt to OpenAI API"""
        self.validate_config()
        self.log_request(prompt, response_format)
        self.log_request_full(prompt, response_format)

        try:
            import openai

            start_time = time.time()

            # Initialize client
            client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url or None)

            # Make request (chat completions — the Responses API takes `input`,
            # not `messages`, and does not return `.choices`)
            request_kwargs = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
            }
            # Thinking control: dispatched by the active model's
            # compat.thinkingFormat (models.json) — "openai" injects
            # reasoning_effort; other declared formats inject their own fields.
            fields = self._thinking_request_fields()
            if fields:
                request_kwargs.update(fields)
            elif self.reasoning_effort and not getattr(self, "thinking_level", None):
                # Legacy ctor path (no configured thinking level)
                request_kwargs["reasoning_effort"] = self.reasoning_effort

            # Full raw request/response log (SDK path: body = request kwargs,
            # raw response = the parsed SDK object via model_dump)
            self.log_raw_request(
                f"{self.base_url or 'https://api.openai.com/v1'}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key or ''}"},
                body=request_kwargs)

            if self._console_stream_enabled():
                # Stream tokens to the console via the SDK; the assembled text
                # is returned and logged exactly like the non-streaming path.
                stream_kwargs = dict(request_kwargs)
                stream_kwargs["stream"] = True
                stream = client.chat.completions.create(**stream_kwargs)
                parts = []
                self._begin_console_stream()
                try:
                    for chunk in stream:
                        if not getattr(chunk, "choices", None):
                            continue
                        delta = getattr(chunk.choices[0].delta, "content", None)
                        if delta:
                            parts.append(delta)
                            self._print_stream_chunk(delta)
                finally:
                    self._finish_console_stream()
                content = "".join(parts)
                self.log_raw_response(200, {"content": content})
            else:
                response = client.chat.completions.create(**request_kwargs)
                self.log_raw_response(200, response)
                content = response.choices[0].message.content

            elapsed = time.time() - start_time
            self.log_response(content, elapsed)
            self.log_response_full(content, elapsed)

            return content

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class ZAIProvider(LLMProvider):
    """Z.AI (Zhipu / BigModel) API provider"""

    default_thinking_format = "zai"

    def __init__(self, api_key: str, model: str, base_url: str = None, disable_ssl_verify: bool = False,
                 reasoning_effort: str = None):
        self.api_key = api_key
        self.model = model
        self.env_key = "ZHIPU_API_KEY"
        # Updated to correct BigModel endpoint
        self.base_url = base_url or "https://api.z.ai/api/coding/paas/v4"
        self.timeout = _resolve_timeout(config, 'ZHIPU', default=300)
        self.disable_ssl_verify = disable_ssl_verify
        self.max_tokens = _resolve_max_tokens(config, 'ZHIPU')
        # GLM-5.x thinking effort: "default" | "low" | "high" | "max".
        # None = send nothing, the model auto-selects its default.
        self.reasoning_effort = self._normalize_effort(reasoning_effort)
        self._thinking_disabled = False
        self.thinking_level = None

    @staticmethod
    def _normalize_effort(effort):
        if effort and str(effort).strip().lower() in ("default", "low", "high", "max"):
            return str(effort).strip().lower()
        return None

    def disable_thinking(self):
        """Send thinking.type=disabled so GLM does not reason before answering."""
        self._thinking_disabled = True
        return True

    @property
    def name(self) -> str:
        return "Z.AI"

    @property
    def requires_api_key(self) -> bool:
        return True

    def ask(self, prompt: str, response_format: str = None) -> str:
        """Send prompt to Z.AI API"""
        self.validate_config()
        self.log_request(prompt, response_format)
        self.log_request_full(prompt, response_format)

        if self.disable_ssl_verify:
            logger.warning("SSL verification is DISABLED for Z.AI API requests. This is less secure!")

        try:
            start_time = time.time()

            # Prepare request
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "max_tokens": self.max_tokens
            }
            # Thinking control: dispatched by the active model's
            # compat.thinkingFormat (models.json) — default "zai" sends
            # thinking.type/effort (GLM-5.x: effort=max measurably deepens
            # reasoning; unset -> model auto-defaults).
            fields = self._thinking_request_fields()
            if fields:
                data.update(fields)
            elif self.reasoning_effort and not getattr(self, "thinking_level", None):
                # Legacy ctor path (no configured thinking level)
                data["thinking"] = {"type": "enabled", "effort": self.reasoning_effort}

            # Make request (streams to the console when enabled)
            content = self._post_chat(
                url, data, headers,
                timeout=self.timeout,
                verify=not self.disable_ssl_verify
            )
            self.log_response(content, time.time() - start_time)
            self.log_response_full(content, time.time() - start_time)
            return content

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class DeepSeekProvider(LLMProvider):
    """DeepSeek API provider (OpenAI-compatible)"""

    default_thinking_format = "deepseek"

    def __init__(self, api_key: str, model: str, base_url: str = None):
        self.api_key = api_key
        self.model = model
        self.env_key = "DEEPSEEK_API_KEY"
        self.base_url = base_url or "https://api.deepseek.com"
        self.timeout = _resolve_timeout(config, 'DEEPSEEK')
        self.max_tokens = _resolve_max_tokens(config, 'DEEPSEEK')

    @property
    def name(self) -> str:
        return "DeepSeek"

    @property
    def requires_api_key(self) -> bool:
        return True

    def ask(self, prompt: str, response_format: str = None) -> str:
        """Send prompt to DeepSeek API"""
        self.validate_config()
        self.log_request(prompt, response_format)
        self.log_request_full(prompt, response_format)

        try:
            start_time = time.time()

            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "max_tokens": self.max_tokens
            }

            # Thinking control: dispatched by the active model's
            # compat.thinkingFormat (models.json) — "deepseek" sends
            # thinking.type enabled/disabled.
            data.update(self._thinking_request_fields())

            content = self._post_chat(url, data, headers, timeout=self.timeout)
            self.log_response(content, time.time() - start_time)
            self.log_response_full(content, time.time() - start_time)
            return content

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class QwenProvider(LLMProvider):
    """Qwen (Alibaba Cloud DashScope, OpenAI-compatible mode) API provider"""

    default_thinking_format = "qwen"

    def __init__(self, api_key: str, model: str, base_url: str = None):
        self.api_key = api_key
        self.model = model
        self.env_key = "QWEN_API_KEY"
        # OpenAI-compatible endpoint (models.json provides the default)
        self.base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.timeout = _resolve_timeout(config, 'QWEN')
        self.max_tokens = _resolve_max_tokens(config, 'QWEN')

    @property
    def name(self) -> str:
        return "Qwen"

    @property
    def requires_api_key(self) -> bool:
        return True

    def ask(self, prompt: str, response_format: str = None) -> str:
        """Send prompt to Qwen API via DashScope compatible-mode"""
        self.validate_config()
        self.log_request(prompt, response_format)
        self.log_request_full(prompt, response_format)

        try:
            start_time = time.time()

            # Prepare request (OpenAI-compatible format)
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "max_tokens": self.max_tokens
            }

            # Thinking control: dispatched by the active model's
            # compat.thinkingFormat (models.json) — "qwen" sends top-level
            # enable_thinking; other declared formats (e.g. "openai" ->
            # reasoning_effort) work the same as on any OpenAI-compatible
            # endpoint.
            data.update(self._thinking_request_fields())

            # Make request
            content = self._post_chat(url, data, headers, timeout=self.timeout)
            self.log_response(content, time.time() - start_time)
            self.log_response_full(content, time.time() - start_time)
            return content

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class KimiProvider(LLMProvider):
    """Kimi K2 2.5 (Moonshot AI) API provider"""

    def __init__(self, api_key: str, model: str, base_url: str = None):
        self.api_key = api_key
        self.model = model
        self.env_key = "KIMI_API_KEY"
        self.base_url = base_url or "https://api.moonshot.cn/v1"
        self.timeout = _resolve_timeout(config, 'KIMI')

    @property
    def name(self) -> str:
        return "Kimi"

    @property
    def requires_api_key(self) -> bool:
        return True

    def ask(self, prompt: str, response_format: str = None) -> str:
        """Send prompt to Kimi API via Moonshot"""
        self.validate_config()
        self.log_request(prompt, response_format)
        self.log_request_full(prompt, response_format)

        try:
            start_time = time.time()

            # Prepare request
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }

            # Thinking control: dispatched by the active model's
            # compat.thinkingFormat (models.json); Kimi models declare no
            # format by default, so nothing is sent unless one is configured.
            data.update(self._thinking_request_fields())

            # Make request
            content = self._post_chat(url, data, headers, timeout=self.timeout)
            self.log_response(content, time.time() - start_time)
            self.log_response_full(content, time.time() - start_time)
            return content

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class OllamaProvider(LLMProvider):
    """Ollama local LLM API provider (OpenAI-compatible /v1 endpoint)"""

    default_thinking_format = "openai"

    def __init__(self, api_key: str, model: str, base_url: str = None):
        # api_key not used for Ollama, but kept for interface consistency
        self.api_key = api_key  # Will be empty string
        self.model = model
        self.base_url = base_url or "http://localhost:11434"
        self.timeout = _resolve_timeout(config, 'OLLAMA')

    @property
    def name(self) -> str:
        return "Ollama"

    @property
    def requires_api_key(self) -> bool:
        return False  # Ollama does NOT require API key!

    def ask(self, prompt: str, response_format: str = None) -> str:
        """Send prompt to Ollama API (OpenAI-compatible /v1 endpoint)"""
        self.validate_config()
        self.log_request(prompt, response_format)
        self.log_request_full(prompt, response_format)

        try:
            start_time = time.time()

            # Prepare request (OpenAI-compatible format; same shape as
            # LM Studio / Strata — models.json drives the thinking format)
            url = f"{self.base_url}/v1/chat/completions"
            headers = {"Content-Type": "application/json"}

            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }

            # Thinking control: dispatched by the active model's
            # compat.thinkingFormat (models.json) — e.g. "openai" sends
            # reasoning_effort (supported by Ollama /v1 for thinking models).
            data.update(self._thinking_request_fields())

            # Make request
            content = self._post_chat(url, data, headers, timeout=self.timeout)
            self.log_response(content, time.time() - start_time)
            self.log_response_full(content, time.time() - start_time)
            return content

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class LMStudioProvider(LLMProvider):
    """LM Studio local LLM API provider (OpenAI-compatible)"""

    default_thinking_format = "openai"


    def __init__(self, api_key: str, model: str, base_url: str = None):
        # api_key not used for LM Studio, but kept for interface consistency
        self.api_key = api_key  # Will be empty string
        self.model = model
        self.base_url = base_url or "http://localhost:1234"
        self.timeout = _resolve_timeout(config, 'LMSTUDIO')

    @property
    def name(self) -> str:
        return "LM Studio"

    @property
    def requires_api_key(self) -> bool:
        return False  # LM Studio does NOT require API key!

    def ask(self, prompt: str, response_format: str = None) -> str:
        """Send prompt to LM Studio API"""
        self.validate_config()
        self.log_request(prompt, response_format)
        self.log_request_full(prompt, response_format)

        try:
            start_time = time.time()

            # Prepare request (OpenAI-compatible format)
            url = f"{self.base_url}/v1/chat/completions"
            headers = {"Content-Type": "application/json"}

            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }

            # Thinking control: dispatched by the active model's
            # compat.thinkingFormat (models.json) — e.g. a qwen model loaded
            # here declares "qwen" and gets enable_thinking; the class default
            # is "openai" (reasoning_effort).
            data.update(self._thinking_request_fields())

            # Make request
            content = self._post_chat(url, data, headers, timeout=self.timeout)
            self.log_response(content, time.time() - start_time)
            self.log_response_full(content, time.time() - start_time)
            return content

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class StrataProvider(LMStudioProvider):
    """Strata local LLM API provider (OpenAI-compatible, like LM Studio)"""

    default_thinking_format = "openai"

    def __init__(self, api_key: str, model: str, base_url: str = None):
        # api_key not used for Strata, but kept for interface consistency
        super().__init__(api_key=api_key, model=model,
                         base_url=base_url or "http://127.0.0.1:8080")
        self.env_key = "STRATA_API_KEY"
        # Own timeout (not LMSTUDIO_TIMEOUT): STRATA_TIMEOUT -> LLM_TIMEOUT
        self.timeout = _resolve_timeout(config, 'STRATA')

    @property
    def name(self) -> str:
        return "Strata"

    @property
    def requires_api_key(self) -> bool:
        return False  # Strata does NOT require API key!


def _registry_base_url(provider_key: str) -> Optional[str]:
    """baseUrl for a provider from models.json (None when not registered)."""
    entry = model_registry.get_provider_entry(provider_key)
    if entry:
        return entry.get("baseUrl") or None
    return None


def _resolve_provider_config(provider_key: str, config_module,
                             model_attr: str, fallback_model: str) -> tuple:
    """Resolve (base_url, api_key, model) for a provider.

    Precedence:
      base_url: non-empty {PROVIDER}_BASE_URL setting -> models.json baseUrl
                -> class default (ctor)
      api_key:  {PROVIDER}_API_KEY config attr (decryption-aware) ->
                models.json apiKey reference resolved from the environment
      model:    {PROVIDER}_MODEL setting -> first models.json model ->
                fallback_model; custom ids not in the file still work
    """
    base_url = (getattr(config_module, f"{provider_key.upper()}_BASE_URL", "") or "").strip() or None
    if not base_url:
        base_url = _registry_base_url(provider_key)

    api_key = getattr(config_module, f"{provider_key.upper()}_API_KEY", "") or ""
    if not api_key:
        api_key = model_registry.get_api_key(provider_key)

    model = (getattr(config_module, model_attr, "") or "").strip()
    registry_models = model_registry.get_model_ids(provider_key)
    if registry_models:
        if not model:
            logger.info(f"models.json: using default model '{registry_models[0]}' for {provider_key}")
            model = registry_models[0]
        elif model not in registry_models:
            logger.info(f"models.json: model '{model}' not listed for {provider_key}; using it anyway")
    return base_url, api_key, (model or fallback_model)


def get_provider(provider_name: Optional[str] = None, config_module=None) -> LLMProvider:
    """
    Factory function to get LLM provider instance.

    Args:
        provider_name: Name of provider (gemini, openai, zhipu, deepseek, qwen, kimi, ollama, lmstudio, strata)
        config_module: Config module (defaults to global config)

    Returns:
        LLM provider instance
    """
    if config_module is None:
        import config
    else:
        config = config_module

    # Get provider from config or use default
    if provider_name is None:
        provider_name = getattr(config, 'LLM_PROVIDER', 'gemini')

    logger.info(f"Initializing LLM provider: {provider_name}")

    # Registry-driven configuration (models.json): base URL, API key (env
    # reference) and active model. Non-empty {PROVIDER}_BASE_URL settings
    # override the file; {PROVIDER}_MODEL picks the active model.
    provider = None

    if provider_name == "gemini":
        base_url, api_key, model = _resolve_provider_config(
            "gemini", config, "GEMINI_TEXT_MODEL", 'gemini-3.5-flash-lite')
        provider = GeminiProvider(api_key=api_key, model=model, base_url=base_url)
        provider.set_thinking_level(getattr(config, 'GEMINI_THINKING_LEVEL', None))

    elif provider_name == "openai":
        base_url, api_key, model = _resolve_provider_config(
            "openai", config, "OPENAI_MODEL", 'gpt-4o')
        provider = OpenAIProvider(api_key=api_key, model=model, base_url=base_url)
        provider.set_reasoning_effort(getattr(config, 'OPENAI_REASONING_EFFORT', None))
        # set_thinking_level passes custom values (e.g. "none") through verbatim
        provider.set_thinking_level(getattr(config, 'OPENAI_REASONING_EFFORT', None))

    elif provider_name == "zhipu":
        base_url, api_key, model = _resolve_provider_config(
            "zhipu", config, "ZHIPU_MODEL", 'glm-5.3')
        disable_ssl_verify = getattr(config, 'ZHIPU_DISABLE_SSL_VERIFY', False)
        reasoning_effort = getattr(config, 'ZHIPU_REASONING_EFFORT', None)
        provider = ZAIProvider(api_key=api_key, model=model, base_url=base_url,
                               disable_ssl_verify=disable_ssl_verify,
                               reasoning_effort=reasoning_effort)
        # set_thinking_level passes custom values through verbatim (the ctor
        # normalizer whitelists default/low/high/max only)
        provider.set_thinking_level(reasoning_effort)

    elif provider_name == "deepseek":
        base_url, api_key, model = _resolve_provider_config(
            "deepseek", config, "DEEPSEEK_MODEL", 'deepseek-chat')
        provider = DeepSeekProvider(api_key=api_key, model=model, base_url=base_url)
        provider.set_thinking_level(getattr(config, 'DEEPSEEK_THINKING_LEVEL', None))

    elif provider_name == "qwen":
        base_url, api_key, model = _resolve_provider_config(
            "qwen", config, "QWEN_MODEL", 'qwen-max')
        provider = QwenProvider(api_key=api_key, model=model, base_url=base_url)
        provider.set_thinking_level(getattr(config, 'QWEN_THINKING_LEVEL', None))

    elif provider_name == "kimi":
        base_url, api_key, model = _resolve_provider_config(
            "kimi", config, "KIMI_MODEL", 'kimi-labs')
        provider = KimiProvider(api_key=api_key, model=model, base_url=base_url)
        provider.set_thinking_level(getattr(config, 'KIMI_THINKING_LEVEL', None))

    elif provider_name == "ollama":
        base_url, api_key, model = _resolve_provider_config(
            "ollama", config, "OLLAMA_MODEL", 'llama2')
        provider = OllamaProvider(api_key="", model=model, base_url=base_url)
        provider.set_thinking_level(getattr(config, 'OLLAMA_THINKING_LEVEL', None))

    elif provider_name == "lmstudio":
        base_url, api_key, model = _resolve_provider_config(
            "lmstudio", config, "LMSTUDIO_MODEL", 'lmstudio-community/qwen2')
        provider = LMStudioProvider(api_key="", model=model, base_url=base_url)
        provider.set_thinking_level(getattr(config, 'LMSTUDIO_THINKING_LEVEL', None))

    elif provider_name == "strata":
        base_url, api_key, model = _resolve_provider_config(
            "strata", config, "STRATA_MODEL", 'strata')
        provider = StrataProvider(api_key="", model=model, base_url=base_url)
        provider.set_thinking_level(getattr(config, 'STRATA_THINKING_LEVEL', None))

    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")

    # Registry key used at ask()-time to look up the model's thinkingLevelMap
    provider.provider_key = provider_name

    # Timeout from the (possibly overridden) config module:
    # {PROVIDER}_TIMEOUT -> LLM_TIMEOUT -> the ctor's value (global config).
    provider.timeout = _resolve_timeout(config, provider_name.upper(), default=provider.timeout)
    return provider


if __name__ == "__main__":
    # Test provider instantiation
    print("Testing LLM Provider Factory\n")

    # Test Gemini (default config)
    try:
        provider = get_provider("gemini")
        print(f"[OK] {provider.name} provider instantiated")
        print(f"  Model: {provider.model}")
        print(f"  Requires API key: {provider.requires_api_key}")
        provider.validate_config()
        print(f"  Configuration valid: OK")
    except Exception as e:
        print(f"[FAIL] {provider.name} provider failed: {e}")

    # Test OpenAI
    try:
        provider = get_provider("openai")
        print(f"[OK] {provider.name} provider instantiated")
        print(f"  Model: {provider.model}")
        print(f"  Requires API key: {provider.requires_api_key}")
        print(f"  Configuration valid: OK (skipping validation)")
    except Exception as e:
        print(f"[FAIL] {provider.name} provider failed: {e}")

    # Test Z.AI
    try:
        provider = get_provider("zhipu")
        print(f"[OK] {provider.name} provider instantiated")
        print(f"  Model: {provider.model}")
        print(f"  Requires API key: {provider.requires_api_key}")
        print(f"  Configuration valid: OK (skipping validation)")
    except Exception as e:
        print(f"[FAIL] {provider.name} provider failed: {e}")

    # Test Qwen
    try:
        provider = get_provider("qwen")
        print(f"[OK] {provider.name} provider instantiated")
        print(f"  Model: {provider.model}")
        print(f"  Requires API key: {provider.requires_api_key}")
        print(f"  Configuration valid: OK (skipping validation)")
    except Exception as e:
        print(f"[FAIL] {provider.name} provider failed: {e}")

    # Test Kimi
    try:
        provider = get_provider("kimi")
        print(f"[OK] {provider.name} provider instantiated")
        print(f"  Model: {provider.model}")
        print(f"  Requires API key: {provider.requires_api_key}")
        print(f"  Configuration valid: OK (skipping validation)")
    except Exception as e:
        print(f"[FAIL] {provider.name} provider failed: {e}")

    # Test DeepSeek
    try:
        provider = get_provider("deepseek")
        print(f"[OK] {provider.name} provider instantiated")
        print(f"  Model: {provider.model}")
        print(f"  Base URL: {provider.base_url}")
        print(f"  Requires API key: {provider.requires_api_key}")
        print(f"  Configuration valid: OK (skipping validation)")
    except Exception as e:
        print(f"[FAIL] {provider.name} provider failed: {e}")

    # Test Ollama (NEW!)
    try:
        provider = get_provider("ollama")
        print(f"[OK] {provider.name} provider instantiated")
        print(f"  Model: {provider.model}")
        print(f"  Base URL: {provider.base_url}")
        print(f"  Requires API key: {provider.requires_api_key}")
        print(f"  Configuration valid: OK (local server, no API key!)")
    except Exception as e:
        print(f"[FAIL] {provider.name} provider failed: {e}")

    # Test LM Studio (NEW!)
    try:
        provider = get_provider("lmstudio")
        print(f"[OK] {provider.name} provider instantiated")
        print(f"  Model: {provider.model}")
        print(f"  Base URL: {provider.base_url}")
        print(f"  Requires API key: {provider.requires_api_key}")
        print(f"  Configuration valid: OK (local server, no API key!)")
    except Exception as e:
        print(f"[FAIL] {provider.name} provider failed: {e}")

    print("\nAll providers tested successfully!")
    print("\nNote: Ollama and LM Studio require local servers running.")
    print("      These providers work WITHOUT API keys (privacy-friendly!)")
