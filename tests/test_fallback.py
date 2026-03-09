"""Tests for multi-provider FallbackLLMManager."""

from unittest.mock import MagicMock, patch

from fu7ur3pr00f.llm.fallback import (
    FallbackLLMManager,
    ModelConfig,
    _build_provider_kwargs,
    build_default_chain,
)


class TestBuildDefaultChain:
    """Test dynamic fallback chain construction."""

    @patch("fu7ur3pr00f.llm.fallback.settings")
    def test_openai_chain(self, mock_settings) -> None:
        mock_settings.active_provider = "openai"
        chain = build_default_chain()
        assert len(chain) > 0
        assert all(c.provider == "openai" for c in chain)

    @patch("fu7ur3pr00f.llm.fallback.settings")
    def test_anthropic_chain(self, mock_settings) -> None:
        mock_settings.active_provider = "anthropic"
        chain = build_default_chain()
        assert len(chain) > 0
        assert all(c.provider == "anthropic" for c in chain)

    @patch("fu7ur3pr00f.llm.fallback.settings")
    def test_unknown_provider_returns_empty(self, mock_settings) -> None:
        mock_settings.active_provider = "unknown"
        assert build_default_chain() == []

    @patch("fu7ur3pr00f.llm.fallback.settings")
    def test_empty_provider_returns_empty(self, mock_settings) -> None:
        mock_settings.active_provider = ""
        assert build_default_chain() == []


class TestBuildProviderKwargs:
    """Test provider-specific kwargs for init_chat_model."""

    @patch("fu7ur3pr00f.llm.fallback.settings")
    def test_azure_kwargs(self, mock_settings) -> None:
        mock_settings.azure_openai_endpoint = "https://test.openai.azure.com/"
        mock_settings.azure_openai_api_version = "2024-12-01-preview"
        mock_settings.azure_openai_api_key = "az-key"
        config = ModelConfig("azure", "gpt-4.1", "Azure GPT-4.1")
        kwargs = _build_provider_kwargs(config)
        assert kwargs["azure_deployment"] == "gpt-4.1"
        assert kwargs["azure_endpoint"] == "https://test.openai.azure.com/"
        assert kwargs["api_key"] == "az-key"

    @patch("fu7ur3pr00f.llm.fallback.settings")
    def test_openai_kwargs(self, mock_settings) -> None:
        mock_settings.openai_api_key = "sk-test"
        config = ModelConfig("openai", "gpt-4.1", "OpenAI GPT-4.1")
        kwargs = _build_provider_kwargs(config)
        assert kwargs["api_key"] == "sk-test"
        assert "base_url" not in kwargs

    @patch("fu7ur3pr00f.llm.fallback.settings")
    def test_futureproof_proxy_kwargs(self, mock_settings) -> None:
        mock_settings.futureproof_proxy_key = "fp-key"
        mock_settings.futureproof_proxy_url = "https://llm.futureproof.dev"
        config = ModelConfig("futureproof", "gpt-4.1", "FP GPT-4.1")
        kwargs = _build_provider_kwargs(config)
        assert kwargs["api_key"] == "fp-key"
        assert kwargs["base_url"] == "https://llm.futureproof.dev"

    @patch("fu7ur3pr00f.llm.fallback.settings")
    def test_anthropic_kwargs(self, mock_settings) -> None:
        mock_settings.anthropic_api_key = "sk-ant-test"
        config = ModelConfig("anthropic", "claude-sonnet-4-20250514", "Claude")
        kwargs = _build_provider_kwargs(config)
        assert kwargs["api_key"] == "sk-ant-test"

    @patch("fu7ur3pr00f.llm.fallback.settings")
    def test_google_kwargs(self, mock_settings) -> None:
        mock_settings.google_api_key = "AIza-test"
        config = ModelConfig("google", "gemini-2.5-flash", "Gemini")
        kwargs = _build_provider_kwargs(config)
        assert kwargs["google_api_key"] == "AIza-test"

    @patch("fu7ur3pr00f.llm.fallback.settings")
    def test_ollama_kwargs(self, mock_settings) -> None:
        mock_settings.ollama_base_url = "http://localhost:11434"
        config = ModelConfig("ollama", "qwen3", "Ollama Qwen3")
        kwargs = _build_provider_kwargs(config)
        assert kwargs["base_url"] == "http://localhost:11434"


class TestFallbackManager:
    """Test FallbackLLMManager behavior."""

    def test_mark_failed_skips_model(self) -> None:
        chain = [
            ModelConfig("openai", "gpt-4.1", "GPT-4.1"),
            ModelConfig("openai", "gpt-4o", "GPT-4o"),
        ]
        manager = FallbackLLMManager(fallback_chain=chain)
        manager.mark_failed(chain[0])
        available = manager.get_available_models()
        assert len(available) == 1
        assert available[0].model == "gpt-4o"

    def test_all_failed_resets(self) -> None:
        chain = [ModelConfig("openai", "gpt-4.1", "GPT-4.1")]
        manager = FallbackLLMManager(fallback_chain=chain)
        manager.mark_failed(chain[0])
        # get_model should reset failures when all models are failed
        with patch.object(manager, "_create_model") as mock_create:
            mock_create.return_value = MagicMock()
            model, config = manager.get_model()
            assert config.model == "gpt-4.1"

    def test_handle_error_rate_limit(self) -> None:
        chain = [
            ModelConfig("openai", "gpt-4.1", "GPT-4.1"),
            ModelConfig("openai", "gpt-4o", "GPT-4o"),
        ]
        manager = FallbackLLMManager(fallback_chain=chain)
        manager._current_model = chain[0]
        should_retry = manager.handle_error(Exception("429 rate limit"))
        assert should_retry is True
        assert len(manager.get_available_models()) == 1

    def test_handle_error_non_recoverable(self) -> None:
        chain = [ModelConfig("openai", "gpt-4.1", "GPT-4.1")]
        manager = FallbackLLMManager(fallback_chain=chain)
        manager._current_model = chain[0]
        should_retry = manager.handle_error(ValueError("bad prompt"))
        assert should_retry is False

    def test_is_fallback_error_patterns(self) -> None:
        manager = FallbackLLMManager(fallback_chain=[])
        assert manager._is_fallback_error(Exception("429 too many requests"))
        assert manager._is_fallback_error(Exception("rate_limit exceeded"))
        assert manager._is_fallback_error(Exception("model not found"))
        assert manager._is_fallback_error(Exception("404 does not exist"))
        assert not manager._is_fallback_error(ValueError("bad input"))

    def test_is_fallback_error_status_code(self) -> None:
        manager = FallbackLLMManager(fallback_chain=[])
        err = Exception("opaque error message")
        err.status_code = 429  # type: ignore[attr-defined]
        assert manager._is_fallback_error(err)

    def test_get_status(self) -> None:
        chain = [
            ModelConfig("openai", "gpt-4.1", "GPT-4.1"),
            ModelConfig("openai", "gpt-4o", "GPT-4o"),
        ]
        manager = FallbackLLMManager(fallback_chain=chain)
        status = manager.get_status()
        assert status["total_models"] == 2
        assert len(status["available_models"]) == 2
        assert status["current_model"] is None
