"""Tests for LLM invocation helper with fallback retry."""

from unittest.mock import MagicMock, patch

from futureproof.agents.helpers.llm_invoker import invoke_llm

# Patch targets at the source module (lazy imports inside invoke_llm)
_PATCH_GET_FALLBACK = "futureproof.llm.fallback.get_fallback_manager"
_PATCH_GET_MODEL = "futureproof.llm.fallback.get_model_with_fallback"


def _make_response(content: str):
    """Build a mock LLM response."""
    resp = MagicMock()
    resp.content = content
    return resp


def _make_config(model: str):
    """Build a mock ModelConfig."""
    cfg = MagicMock()
    cfg.description = model
    cfg.model = model
    return cfg


class TestInvokeLLMFallback:
    """Tests for invoke_llm retry and fallback behavior."""

    @patch(_PATCH_GET_FALLBACK)
    @patch(_PATCH_GET_MODEL)
    def test_success_on_first_try(self, mock_get_model, mock_get_manager):
        model = MagicMock()
        model.invoke.return_value = _make_response("analysis result")
        mock_get_model.return_value = (model, _make_config("gpt-4.1"))

        result = invoke_llm("prompt", "analysis")

        assert result == {"analysis": "analysis result"}
        assert model.invoke.call_count == 1

    @patch(_PATCH_GET_FALLBACK)
    @patch(_PATCH_GET_MODEL)
    def test_fallback_on_rate_limit(self, mock_get_model, mock_get_manager):
        model1 = MagicMock()
        model1.invoke.side_effect = Exception("429 rate limit exceeded")
        model2 = MagicMock()
        model2.invoke.return_value = _make_response("fallback result")

        config1 = _make_config("gpt-4.1")
        config2 = _make_config("gpt-4o")
        mock_get_model.side_effect = [(model1, config1), (model2, config2)]

        manager = MagicMock()
        manager.handle_error.return_value = True  # Recoverable error
        mock_get_manager.return_value = manager

        result = invoke_llm("prompt", "analysis", "Analysis")

        assert result == {"analysis": "fallback result"}
        assert manager.handle_error.call_count == 1
        assert model2.invoke.call_count == 1

    @patch(_PATCH_GET_FALLBACK)
    @patch(_PATCH_GET_MODEL)
    def test_no_fallback_on_non_recoverable_error(self, mock_get_model, mock_get_manager):
        model = MagicMock()
        model.invoke.side_effect = ValueError("invalid prompt")
        mock_get_model.return_value = (model, _make_config("gpt-4.1"))

        manager = MagicMock()
        manager.handle_error.return_value = False  # Non-recoverable
        mock_get_manager.return_value = manager

        result = invoke_llm("prompt", "analysis", "Analysis")

        assert "error" in result
        assert "invalid prompt" in result["error"]
        assert model.invoke.call_count == 1

    @patch(_PATCH_GET_FALLBACK)
    @patch(_PATCH_GET_MODEL)
    def test_all_models_fail(self, mock_get_model, mock_get_manager):
        models = []
        configs = []
        for name in ["gpt-4.1", "gpt-4o", "gpt-4.1-mini", "gpt-4o-mini"]:
            m = MagicMock()
            m.invoke.side_effect = Exception(f"429 rate limit for {name}")
            models.append(m)
            configs.append(_make_config(name))

        mock_get_model.side_effect = list(zip(models, configs))

        manager = MagicMock()
        # First 3 calls return True (fallback available), last returns False
        manager.handle_error.side_effect = [True, True, True, False]
        mock_get_manager.return_value = manager

        result = invoke_llm("prompt", "analysis", "Analysis")

        assert "error" in result
        assert "gpt-4o-mini" in result["error"]
        assert manager.handle_error.call_count == 4

    @patch(_PATCH_GET_FALLBACK)
    @patch(_PATCH_GET_MODEL)
    def test_fallback_after_two_failures(self, mock_get_model, mock_get_manager):
        model1 = MagicMock()
        model1.invoke.side_effect = Exception("429 rate limit")
        model2 = MagicMock()
        model2.invoke.side_effect = Exception("404 not found")
        model3 = MagicMock()
        model3.invoke.return_value = _make_response("third time's the charm")

        mock_get_model.side_effect = [
            (model1, _make_config("gpt-4.1")),
            (model2, _make_config("gpt-4o")),
            (model3, _make_config("gpt-4.1-mini")),
        ]

        manager = MagicMock()
        manager.handle_error.side_effect = [True, True]
        mock_get_manager.return_value = manager

        result = invoke_llm("prompt", "advice", "Advice")

        assert result == {"advice": "third time's the charm"}
        assert manager.handle_error.call_count == 2
