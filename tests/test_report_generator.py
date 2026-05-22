"""
Tests for the report generator — ensures HTML report generation doesn't crash.
"""

import os
import tempfile
import pytest
from benchmarks.reporting.report_generator import generate_report


class TestReportGenerator:
    @pytest.fixture
    def sample_comparison(self):
        return {
            "ranking": [
                {
                    "rank": 1, "framework": "crewai", "total_score": 7.5,
                    "dimensions": {"orchestration": 8, "tool_use": 7, "safety": 7,
                                   "human_in_the_loop": 8, "memory": 6, "observability": 7, "multimodal": 7},
                    "total_tokens": 5000, "total_cost_usd": 0.05, "total_duration_ms": 15000,
                },
                {
                    "rank": 2, "framework": "langgraph", "total_score": 6.8,
                    "dimensions": {"orchestration": 7, "tool_use": 8, "safety": 6,
                                   "human_in_the_loop": 7, "memory": 5, "observability": 8, "multimodal": 5},
                    "total_tokens": 4500, "total_cost_usd": 0.04, "total_duration_ms": 12000,
                },
            ],
            "best_per_dimension": {
                "orchestration": {"framework": "crewai", "score": 8},
                "tool_use": {"framework": "langgraph", "score": 8},
                "safety": {"framework": "crewai", "score": 7},
                "human_in_the_loop": {"framework": "crewai", "score": 8},
                "memory": {"framework": "crewai", "score": 6},
                "observability": {"framework": "langgraph", "score": 8},
                "multimodal": {"framework": "crewai", "score": 7},
            },
            "evaluated_at": "2026-05-22T00:00:00",
            "frameworks_count": 2,
        }

    def test_generates_html_file(self, sample_comparison, tmp_path):
        result = generate_report(sample_comparison, output_dir=str(tmp_path))
        assert result is not None
        assert os.path.exists(result)
        assert result.endswith(".html")

    def test_html_contains_framework_names(self, sample_comparison, tmp_path):
        path = generate_report(sample_comparison, output_dir=str(tmp_path))
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        assert "crewai" in html.lower() or "CrewAI" in html
        assert "langgraph" in html.lower() or "LangGraph" in html

    def test_empty_ranking(self, tmp_path):
        empty = {"ranking": [], "best_per_dimension": {},
                 "evaluated_at": "2026-01-01", "frameworks_count": 0}
        result = generate_report(empty, output_dir=str(tmp_path))
        assert result is not None

    def test_single_framework(self, sample_comparison, tmp_path):
        single = {**sample_comparison, "ranking": sample_comparison["ranking"][:1], "frameworks_count": 1}
        result = generate_report(single, output_dir=str(tmp_path))
        assert os.path.exists(result)
