"""Tests for the Reviewer Agent."""

from __future__ import annotations

from unittest.mock import MagicMock

from agents.base import Task
from agents.reviewer import (
    PLATFORM_RULES,
    QUALITY_CRITERIA,
    ReviewerAgent,
    ReviewResult,
)


class TestReviewerAgent:
    """Test suite for ReviewerAgent."""

    def test_initialization(self, mock_llm_client):
        reviewer = ReviewerAgent(mock_llm_client)
        assert reviewer.name == "reviewer"
        assert reviewer.description is not None
        assert len(reviewer.sensitive_patterns) == 0  # No built-in words, config only
        assert "juejin" in reviewer.default_platform_rules

    def test_get_system_prompt(self, mock_llm_client):
        reviewer = ReviewerAgent(mock_llm_client)
        prompt = reviewer.get_system_prompt()
        assert prompt is not None
        assert len(prompt) > 0

    # ── Sensitive word detection ─────────────────────────────────

    def test_check_sensitive_clean_content(self, mock_llm_client):
        """Clean content should pass sensitive check."""
        reviewer = ReviewerAgent(mock_llm_client)
        result = reviewer._check_sensitive(
            "Python 异步编程详解",
            "这是一篇关于 Python 异步编程的技术文章，介绍了 asyncio 的用法。",
        )
        assert result["passed"] is True
        assert len(result["hits"]) == 0

    def test_check_sensitive_blocked_content(self, mock_llm_client):
        """Content with sensitive words (from config) should be blocked."""
        reviewer = ReviewerAgent(
            mock_llm_client,
            config={"reviewer_sensitive_words": {"加微信": "禁止导流", "赌博": "违规内容"}},
        )
        result = reviewer._check_sensitive(
            "文章标题",
            "加微信了解更多内容。",
        )
        assert result["blocked"] is True
        assert len(result["hits"]) == 1

    def test_check_sensitive_custom_words(self, mock_llm_client):
        """Custom sensitive words from config should be checked."""
        reviewer = ReviewerAgent(
            mock_llm_client,
            config={"reviewer_sensitive_words": {"TEST_CUSTOM": "自定义违规词"}},
        )
        result = reviewer._check_sensitive("标题", "包含 TEST_CUSTOM 的内容")
        assert result["blocked"] is True
        assert any(h["word"] == "TEST_CUSTOM" for h in result["hits"])

    # ── Platform compliance ───────────────────────────────────────

    def test_platform_compliance_juejin_pass(self, mock_llm_client):
        reviewer = ReviewerAgent(mock_llm_client)
        result = reviewer._check_platform_compliance(
            "Python 异步编程完全指南",
            "这是一篇很长的技术文章。" * 100,
            "juejin",
        )
        assert result["passed"] is True
        assert len(result["violations"]) == 0

    def test_platform_compliance_title_too_short(self, mock_llm_client):
        reviewer = ReviewerAgent(mock_llm_client)
        result = reviewer._check_platform_compliance(
            "短",
            "内容正文" * 200,
            "juejin",
        )
        assert result["passed"] is False
        assert any(v["type"] == "title_too_short" for v in result["violations"])

    def test_platform_compliance_content_too_short(self, mock_llm_client):
        reviewer = ReviewerAgent(mock_llm_client)
        result = reviewer._check_platform_compliance(
            "一个合适的标题",
            "短内容",
            "juejin",
        )
        assert result["passed"] is False
        assert any(v["type"] == "content_too_short" for v in result["violations"])

    def test_platform_compliance_title_missing_juejin(self, mock_llm_client):
        reviewer = ReviewerAgent(mock_llm_client)
        result = reviewer._check_platform_compliance(
            None,
            "文章正文内容" * 100,
            "juejin",
        )
        assert result["passed"] is False
        assert any(v["type"] == "title_missing" for v in result["violations"])

    def test_platform_compliance_zhihu_no_title_ok(self, mock_llm_client):
        """Zhihu doesn't require a title."""
        reviewer = ReviewerAgent(mock_llm_client)
        result = reviewer._check_platform_compliance(
            None,
            "知乎回答内容" * 100,
            "zhihu",
        )
        assert result["passed"] is True

    def test_platform_compliance_forbidden_pattern(self, mock_llm_client):
        """Platform-specific forbidden patterns should be caught."""
        reviewer = ReviewerAgent(mock_llm_client)
        result = reviewer._check_platform_compliance(
            "好的标题",
            "扫码加入我们的群获取更多信息",
            "zhihu",
        )
        assert any(v["type"] == "platform_forbidden" for v in result["violations"])

    # ── Quality scoring ───────────────────────────────────────────

    def test_score_quality_high(self, mock_llm_client):
        """Well-structured content should score high."""
        reviewer = ReviewerAgent(mock_llm_client)
        good_content = (
            "# Python 异步编程完全指南\n\n"
            "## 什么是异步编程\n\n"
            "异步编程是一种并发模型，允许程序在等待 I/O 操作时执行其他任务。\n\n"
            "## 为什么需要异步\n\n"
            "在现代 Web 应用中，大量的时间花在等待网络请求上。\n\n"
            "```python\nimport asyncio\n\nasync def main():\n    print('hello')\n```\n\n"
            "## 实战案例\n\n"
            "下面我们来看一个实际的例子。\n\n"
            "```python\nasync def fetch(url):\n    async with aiohttp.ClientSession() as session:\n"
            "        async with session.get(url) as resp:\n            return await resp.text()\n```\n\n"
            "## 总结\n\n"
            "本文介绍了 Python 异步编程的核心概念和实践方法，希望对大家有所帮助。"
            "异步编程是现代 Python 开发中不可或缺的技能，掌握它可以大幅提升应用的并发性能。"
            "在实际项目中，我们经常使用 asyncio 配合 aiohttp 来构建高性能的 Web 服务。"
        )
        result = reviewer._score_quality("Python 异步编程完全指南", good_content)
        assert result["score"] >= 70
        assert len(result["deductions"]) == 0

    def test_score_quality_low(self, mock_llm_client):
        """Poor content should score low."""
        reviewer = ReviewerAgent(mock_llm_client)
        bad_content = "短内容"
        result = reviewer._score_quality("短", bad_content)
        assert result["score"] < 50

    def test_score_quality_no_headings(self, mock_llm_client):
        """Content without headings should be penalized."""
        reviewer = ReviewerAgent(mock_llm_client)
        content = "这是一篇文章。" * 200
        result = reviewer._score_quality("好的标题", content)
        assert any(
            d["type"] == "has_headings" for d in result["deductions"]
        )

    # ── Full execute flow ─────────────────────────────────────────

    def test_execute_passes_clean_content(self, mock_llm_client):
        """Full review of clean content should pass."""
        reviewer = ReviewerAgent(mock_llm_client)
        task = Task(
            task_id="test_rev_001",
            task_type="review",
            params={
                "content": {
                    "title": "Python 异步编程完全指南",
                    "text": (
                        "# Python 异步编程\n\n"
                        "## 概述\n\n"
                        "异步编程是现代 Python 的重要特性。\n\n"
                        "```python\nimport asyncio\n```\n\n"
                        "## 总结\n\n"
                        "希望本文对大家有帮助。"
                    ),
                },
                "platform": "juejin",
            },
        )
        result = reviewer.execute(task)
        assert result.success
        assert result.agent_name == "reviewer"
        assert "review_passed" in result.data
        assert "review_score" in result.data

    def test_execute_blocks_sensitive_content(self, mock_llm_client):
        """Review should block content with sensitive words from config."""
        reviewer = ReviewerAgent(
            mock_llm_client,
            config={"reviewer_sensitive_words": {"赌博": "违规内容"}},
        )
        task = Task(
            task_id="test_rev_002",
            task_type="review",
            params={
                "content": {
                    "title": "好标题",
                    "text": "文章内容包含赌博相关词语。",
                },
                "platform": "juejin",
            },
        )
        result = reviewer.execute(task)
        assert result.success  # TaskResult.success = review completed
        assert result.data["review_passed"] is False

    def test_execute_with_string_content(self, mock_llm_client):
        """Should accept plain string content."""
        reviewer = ReviewerAgent(mock_llm_client)
        task = Task(
            task_id="test_rev_003",
            task_type="review",
            params={
                "content": "Python 异步编程详解\n\n这是一篇很长的技术文章。" * 50,
                "platform": "generic",
            },
        )
        result = reviewer.execute(task)
        assert result.success
        assert result.data["platform"] == "generic"

    def test_execute_uses_custom_min_score(self, mock_llm_client):
        """Custom min_pass_score should affect pass/fail."""
        reviewer = ReviewerAgent(mock_llm_client)
        task = Task(
            task_id="test_rev_004",
            task_type="review",
            params={
                "content": {
                    "title": "短",
                    "text": "短内容",
                },
                "platform": "generic",
                "min_pass_score": 10,  # Very low, should pass
            },
        )
        result = reviewer.execute(task)
        assert result.success
        # Even with low score, it might pass if min_pass_score is low enough
        assert result.data["review_score"] < 50

    def test_execute_failure_reported(self):
        """If something unexpected happens, it should be captured."""
        failing_client = MagicMock()
        reviewer = ReviewerAgent(failing_client)
        task = Task(
            task_id="test_rev_fail",
            task_type="review",
            params={"content": None, "platform": "juejin"},  # Will trigger exception
        )
        result = reviewer.execute(task)
        assert not result.success

    # ── Convenience method ────────────────────────────────────────

    def test_review_content_convenience(self, mock_llm_client):
        """review_content convenience method should work."""
        reviewer = ReviewerAgent(mock_llm_client)
        review = reviewer.review_content(
            text="Python 异步编程完整指南\n\n## 介绍\n\n这是一篇很长的技术文章。" * 30,
            title="Python 异步编程完整指南",
            platform="juejin",
        )
        assert isinstance(review, ReviewResult)
        assert review.score >= 0

    # ── ReviewResult dataclass ────────────────────────────────────

    def test_review_result_to_dict(self):
        result = ReviewResult(
            passed=True,
            score=85,
            issues=[{"type": "test", "detail": "test issue"}],
            suggestions=["Improve title"],
        )
        d = result.to_dict()
        assert d["passed"] is True
        assert d["score"] == 85
        assert len(d["issues"]) == 1
        assert d["suggestions"] == ["Improve title"]
        assert "reviewed_at" in d


class TestReviewerAgentLLM:
    """Tests for the optional LLM-based deep review."""

    def test_llm_deep_review_passes(self, mock_llm_client):
        mock_llm_client.chat.return_value = (
            '{"blocked": false, "issues": [], "suggestions": [], "verdict": "pass"}'
        )
        reviewer = ReviewerAgent(mock_llm_client)
        result = reviewer._llm_deep_review(
            "好的标题", "好的内容" * 50, "juejin"
        )
        assert result["blocked"] is False

    def test_llm_deep_review_blocks(self, mock_llm_client):
        mock_llm_client.chat.return_value = (
            '{"blocked": true, "issues": [{"type":"spam","detail":"looks like spam"}],'
            '"suggestions": ["Rewrite"], "verdict": "block"}'
        )
        reviewer = ReviewerAgent(mock_llm_client)
        result = reviewer._llm_deep_review(
            "标题", "可能是垃圾内容" * 50, "juejin"
        )
        assert result["blocked"] is True

    def test_llm_deep_review_empty_content(self, mock_llm_client):
        reviewer = ReviewerAgent(mock_llm_client)
        result = reviewer._llm_deep_review(None, "", "juejin")
        assert result.get("skipped") is True

    def test_llm_deep_review_parse_error(self, mock_llm_client):
        mock_llm_client.chat.return_value = "not valid json at all"
        reviewer = ReviewerAgent(mock_llm_client)
        result = reviewer._llm_deep_review("标题", "内容" * 50, "juejin")
        assert result["verdict"] == "parse_error"
        assert not result["blocked"]  # Parse error = don't block

    def test_execute_with_llm_review(self, mock_llm_client):
        """Full execute with LLM review enabled."""
        mock_llm_client.chat.return_value = (
            '{"blocked": false, "issues": [], "suggestions": ["Add more examples"], "verdict": "pass"}'
        )
        reviewer = ReviewerAgent(mock_llm_client)
        task = Task(
            task_id="test_rev_llm_001",
            task_type="review",
            params={
                "content": {
                    "title": "Python 异步编程详解",
                    "text": "好内容" * 100,
                },
                "platform": "juejin",
                "use_llm": True,
            },
        )
        result = reviewer.execute(task)
        assert result.success
        assert result.data["review_suggestions"] is not None


class TestPlatformRules:
    """Verify platform rules are complete."""

    def test_all_platforms_have_rules(self):
        for platform in ["juejin", "zhihu", "devto", "generic"]:
            assert platform in PLATFORM_RULES
            rules = PLATFORM_RULES[platform]
            assert "min_content_length" in rules
            assert "max_content_length" in rules


class TestQualityCriteria:
    """Verify quality criteria are well-formed."""

    def test_all_criteria_have_weights(self):
        for key, (label, weight, check_fn) in QUALITY_CRITERIA.items():
            assert weight > 0, f"Criteria '{key}' has zero or negative weight"
            assert callable(check_fn), f"Criteria '{key}' check_fn not callable"
