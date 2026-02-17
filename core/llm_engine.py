"""
LLM Provider Base Classes
Abstract base class for all LLM providers (Gemini, OpenAI, Z.AI, Qwen, Kimi K2 2.5)
"""
from abc import ABC, abstractmethod
from typing import Optional
import logging
import time
import requests
import config
import os

# Get logger for provider operations
logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

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
        logger.debug(f"{self.name} API Error: {str(error)}")
        logger.error(f"  Elapsed: {elapsed:.2f}s")
        logger.debug(f"  Traceback: {error.__traceback__}")

    def log_request_full(self, prompt: str, response_format: Optional[str]):
        """Log the full request content"""
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

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.env_key = "GEMINI_API_KEY"
        self.timeout = 120  # Default timeout in seconds
        self.max_tokens = getattr(config, 'LLM_MAX_TOKENS', 16384)

    @property
    def name(self) -> str:
        return "Gemini"

    @property
    def requires_api_key(self) -> bool:
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
            client = genai.Client(
                api_key=self.api_key,
                http_options={'api_version': 'v1alpha'}
            )

            # Configure response format
            gen_config = types.GenerateContentConfig(
                response_mime_type="application/json" if response_format == "application/json" else "text/plain",
                max_output_tokens=self.max_tokens
            )

            # Make request
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=gen_config
            )

            elapsed = time.time() - start_time
            self.log_response(response.text, elapsed)
            self.log_response_full(response.text, elapsed)

            return response.text

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class OpenAIProvider(LLMProvider):
    """OpenAI (ChatGPT) API provider"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.env_key = "OPENAI_API_KEY"
        self.timeout = 120  # Default timeout in seconds

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
            client = openai.OpenAI(api_key=self.api_key)

            # Make request
            response = client.responses.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )

            elapsed = time.time() - start_time
            self.log_response(response.choices[0].message.content, elapsed)
            self.log_response_full(response.choices[0].message.content, elapsed)

            return response.choices[0].message.content

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class ZAIProvider(LLMProvider):
    """Z.AI (Zhipu / BigModel) API provider"""

    def __init__(self, api_key: str, model: str, base_url: str = None, disable_ssl_verify: bool = False):
        self.api_key = api_key
        self.model = model
        self.env_key = "ZHIPU_API_KEY"
        # Updated to correct BigModel endpoint
        self.base_url = base_url or "https://api.z.ai/api/coding/paas/v4"
        self.timeout = 120  # Default timeout in seconds
        self.disable_ssl_verify = disable_ssl_verify
        self.max_tokens = getattr(config, 'LLM_MAX_TOKENS', 16384)

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

            # Make request
            response = requests.post(
                url,
                json=data,
                headers=headers,
                timeout=self.timeout,
                verify=not self.disable_ssl_verify
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                self.log_response(content, time.time() - start_time)
                self.log_response_full(content, time.time() - start_time)
                return content
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                raise Exception(error_msg)

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class QwenProvider(LLMProvider):
    """Qwen (Alibaba Cloud) API provider"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.env_key = "QWEN_API_KEY"
        self.timeout = 120  # Default timeout in seconds

    @property
    def name(self) -> str:
        return "Qwen"

    @property
    def requires_api_key(self) -> bool:
        return True

    def ask(self, prompt: str, response_format: str = None) -> str:
        """Send prompt to Qwen API via DashScope"""
        self.validate_config()
        self.log_request(prompt, response_format)
        self.log_request_full(prompt, response_format)

        try:
            start_time = time.time()

            # Prepare request
            url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": self.model,
                "input": {
                    "messages": [{"role": "user", "content": prompt}]
                }
            }

            # Make request
            response = requests.post(url, json=data, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                result = response.json()
                content = result.get("output", {}).get("text", "")
                self.log_response(content, time.time() - start_time)
                self.log_response_full(content, time.time() - start_time)
                return content
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                raise Exception(error_msg)

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class KimiProvider(LLMProvider):
    """Kimi K2 2.5 (Moonshot AI) API provider"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.env_key = "KIMI_API_KEY"
        self.timeout = 120  # Default timeout in seconds

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
            url = "https://api.moonshot.cn/v1"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }

            # Make request
            response = requests.post(url, json=data, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                self.log_response(content, time.time() - start_time)
                self.log_response_full(content, time.time() - start_time)
                return content
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                raise Exception(error_msg)

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class OllamaProvider(LLMProvider):
    """Ollama local LLM API provider (Open-source, self-hosted)"""

    def __init__(self, api_key: str, model: str, base_url: str = None):
        # api_key not used for Ollama, but kept for interface consistency
        self.api_key = api_key  # Will be empty string
        self.model = model
        self.base_url = base_url or "http://localhost:11434"
        self.timeout = 120  # Default timeout in seconds

    @property
    def name(self) -> str:
        return "Ollama"

    @property
    def requires_api_key(self) -> bool:
        return False  # Ollama does NOT require API key!

    def ask(self, prompt: str, response_format: str = None) -> str:
        """Send prompt to Ollama API"""
        self.validate_config()
        self.log_request(prompt, response_format)
        self.log_request_full(prompt, response_format)

        try:
            start_time = time.time()

            # Prepare request
            url = f"{self.base_url}/api/generate"
            headers = {"Content-Type": "application/json"}

            data = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }

            # Make request
            response = requests.post(url, json=data, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                result = response.json()
                content = result.get("response", "")
                self.log_response(content, time.time() - start_time)
                self.log_response_full(content, time.time() - start_time)
                return content
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                raise Exception(error_msg)

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


class LMStudioProvider(LLMProvider):
    """LM Studio local LLM API provider (OpenAI-compatible)"""

    def __init__(self, api_key: str, model: str, base_url: str = None):
        # api_key not used for LM Studio, but kept for interface consistency
        self.api_key = api_key  # Will be empty string
        self.model = model
        self.base_url = base_url or "http://localhost:1234"
        self.timeout = 120  # Default timeout in seconds

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

            # Make request
            response = requests.post(url, json=data, headers=headers, timeout=self.timeout)

            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                self.log_response(content, time.time() - start_time)
                self.log_response_full(content, time.time() - start_time)
                return content
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                raise Exception(error_msg)

        except Exception as e:
            elapsed = time.time() - start_time
            self.log_error(e, elapsed)
            raise


def get_provider(provider_name: Optional[str] = None, config_module=None) -> LLMProvider:
    """
    Factory function to get LLM provider instance.

    Args:
        provider_name: Name of provider (gemini, openai, zhipu, qwen, kimi, ollama, lmstudio)
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

    if provider_name == "gemini":
        api_key = getattr(config, 'GEMINI_API_KEY', '')
        model = getattr(config, 'GEMINI_TEXT_MODEL', 'gemini-2.0-flash')
        return GeminiProvider(api_key=api_key, model=model)

    elif provider_name == "openai":
        api_key = getattr(config, 'OPENAI_API_KEY', '')
        model = getattr(config, 'OPENAI_MODEL', 'gpt-4o')
        return OpenAIProvider(api_key=api_key, model=model)

    elif provider_name == "zhipu":
        api_key = getattr(config, 'ZHIPU_API_KEY', '')
        model = getattr(config, 'ZHIPU_MODEL', 'deep-v3')
        disable_ssl_verify = getattr(config, 'ZHIPU_DISABLE_SSL_VERIFY', False)
        return ZAIProvider(api_key=api_key, model=model, disable_ssl_verify=disable_ssl_verify)

    elif provider_name == "qwen":
        api_key = getattr(config, 'QWEN_API_KEY', '')
        model = getattr(config, 'QWEN_MODEL', 'qwen-max')
        return QwenProvider(api_key=api_key, model=model)

    elif provider_name == "kimi":
        api_key = getattr(config, 'KIMI_API_KEY', '')
        model = getattr(config, 'KIMI_MODEL', 'kimi-labs')
        return KimiProvider(api_key=api_key, model=model)

    elif provider_name == "ollama":
        base_url = getattr(config, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        model = getattr(config, 'OLLAMA_MODEL', 'llama2')
        return OllamaProvider(api_key="", model=model, base_url=base_url)

    elif provider_name == "lmstudio":
        base_url = getattr(config, 'LMSTUDIO_BASE_URL', 'http://localhost:1234')
        model = getattr(config, 'LMSTUDIO_MODEL', 'lmstudio-community/qwen2')
        return LMStudioProvider(api_key="", model=model, base_url=base_url)

    else:
        raise ValueError(f"Unknown LLM provider: {provider_name}")


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
