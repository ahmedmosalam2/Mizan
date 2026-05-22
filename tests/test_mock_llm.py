"""
Tests for the Mock LLM — verifying deterministic responses and scenario detection.
"""

import pytest
from benchmarks.mocks.mock_llm import MockLLMClient, get_mock_response, MOCK_RESPONSES


class TestMockResponses:
    def test_all_scenarios_have_responses(self):
        expected = {"campaign_planning", "content_generation", "pii_scan",
                    "budget_approval", "cross_session_memory", "channel_deploy", "multimodal_ad"}
        assert expected == set(MOCK_RESPONSES.keys())

    @pytest.mark.parametrize("scenario", list(MOCK_RESPONSES.keys()))
    def test_responses_are_non_empty(self, scenario):
        assert len(MOCK_RESPONSES[scenario].strip()) > 50

    def test_pii_scan_is_valid_json(self):
        import json
        parsed = json.loads(MOCK_RESPONSES["pii_scan"])
        assert "detected_pii" in parsed
        assert "redacted_text" in parsed


class TestMockLLMClient:
    def test_chat_returns_string(self, mock_llm):
        result = mock_llm.chat("test prompt", scenario="campaign_planning")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_achat_returns_string(self, mock_llm):
        result = await mock_llm.achat("test prompt", scenario="campaign_planning")
        assert isinstance(result, str)

    def test_scenario_detection_pii(self, mock_llm):
        key = mock_llm._detect_scenario("Please detect PII in this text")
        assert key == "pii_scan"

    def test_scenario_detection_budget(self, mock_llm):
        key = mock_llm._detect_scenario("Reallocate the budget")
        assert key == "budget_approval"

    def test_scenario_detection_deploy(self, mock_llm):
        key = mock_llm._detect_scenario("Deploy the channel campaign")
        assert key == "channel_deploy"

    def test_call_log_tracking(self, mock_llm):
        mock_llm.chat("prompt1", scenario="campaign_planning")
        mock_llm.chat("prompt2", scenario="pii_scan")
        stats = mock_llm.get_stats()
        assert stats["total_calls"] == 2
        assert "campaign_planning" in stats["scenarios_hit"]
        assert "pii_scan" in stats["scenarios_hit"]

    def test_deterministic_output(self, mock_llm):
        r1 = mock_llm.chat("test", scenario="content_generation")
        r2 = mock_llm.chat("test", scenario="content_generation")
        assert r1 == r2


class TestGetMockResponse:
    def test_returns_dict(self):
        result = get_mock_response("campaign_planning", "test", latency_ms=1)
        assert "text" in result
        assert "tokens" in result
        assert "cost_usd" in result
        assert result["provider"] == "mizan-mock"

    def test_unknown_scenario_fallback(self):
        result = get_mock_response("nonexistent_scenario", latency_ms=1)
        assert "nonexistent_scenario" in result["text"]
