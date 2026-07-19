"""Tests for cross-platform content adaptation (v0.4)."""

from __future__ import annotations

from agents.writer import WriterAgent


class TestCrossPlatformGeneration:
    """Test WriterAgent.cross_platform_generate."""

    def test_cross_platform_generates_for_all_defaults(self, mock_llm_client):
        """Should generate content for juejin, zhihu, devto by default."""
        writer = WriterAgent(mock_llm_client)
        results = writer.cross_platform_generate("Python async programming", enable_rag=False)

        assert set(results.keys()) == {"juejin", "zhihu", "devto"}
        for platform, content in results.items():
            assert content is not None
            assert "测试生成" in content

    def test_cross_platform_custom_platforms(self, mock_llm_client):
        """Should respect custom platform list."""
        writer = WriterAgent(mock_llm_client)
        results = writer.cross_platform_generate("Topic", platforms=["juejin"], enable_rag=False)
        assert list(results.keys()) == ["juejin"]

    def test_cross_platform_empty_platforms(self, mock_llm_client):
        """Empty platform list should return empty dict."""
        writer = WriterAgent(mock_llm_client)
        results = writer.cross_platform_generate("Topic", platforms=[], enable_rag=False)
        assert results == {}

    def test_cross_platform_each_version_differs(self, mock_llm_client):
        """Each platform should get different content (LLM call params differ)."""
        writer = WriterAgent(mock_llm_client)
        # Track what the LLM is called with
        call_args = []

        original_chat = mock_llm_client.chat

        def tracking_chat(messages):
            user_content = messages[1]["content"] if len(messages) > 1 else ""
            call_args.append(user_content)
            return original_chat(messages)

        mock_llm_client.chat = tracking_chat

        writer.cross_platform_generate("Python", enable_rag=False)

        # Should have 3 calls with different platform instructions
        assert len(call_args) == 3
        assert any("掘金" in a for a in call_args)
        assert any("知乎" in a for a in call_args)
        assert any("Dev.to" in a for a in call_args)


class TestPlatformStyleProfiles:
    """Test platform-specific style profiles."""

    def test_juejin_profile_includes_code(self, mock_llm_client):
        """Juejin prompt should require code examples."""
        writer = WriterAgent(mock_llm_client)
        prompt = writer._build_writing_prompt(
            topic="Python",
            style="technical",
            platform="juejin",
            skill_context={},
            rag_context="",
            project_info="",
            word_count="auto",
        )
        assert "代码示例" in prompt
        assert "掘金" in prompt

    def test_zhihu_profile_includes_storytelling(self, mock_llm_client):
        """Zhihu prompt should require opinion + storytelling."""
        writer = WriterAgent(mock_llm_client)
        prompt = writer._build_writing_prompt(
            topic="Python",
            style="technical",
            platform="zhihu",
            skill_context={},
            rag_context="",
            project_info="",
            word_count="auto",
        )
        assert "故事化" in prompt or "观点" in prompt

    def test_devto_profile_includes_english(self, mock_llm_client):
        """Dev.to prompt should require English."""
        writer = WriterAgent(mock_llm_client)
        prompt = writer._build_writing_prompt(
            topic="Python",
            style="technical",
            platform="devto",
            skill_context={},
            rag_context="",
            project_info="",
            word_count="auto",
        )
        assert "ENGLISH" in prompt or "English" in prompt

    def test_juejin_has_code_requirement(self, mock_llm_client):
        """Juejin prompt specifically requires code examples."""
        writer = WriterAgent(mock_llm_client)
        prompt = writer._build_writing_prompt(
            topic="Test",
            style="technical",
            platform="juejin",
            skill_context={},
            rag_context="",
            project_info="",
            word_count="auto",
        )
        assert "代码示例" in prompt

    def test_devto_has_tag_requirement(self, mock_llm_client):
        """Dev.to prompt should suggest tags."""
        writer = WriterAgent(mock_llm_client)
        prompt = writer._build_writing_prompt(
            topic="Test",
            style="technical",
            platform="devto",
            skill_context={},
            rag_context="",
            project_info="",
            word_count="auto",
        )
        assert "tags" in prompt.lower() or "tag" in prompt.lower()

    def test_platform_styles_are_distinct(self, mock_llm_client):
        """Juejin, zhihu, and devto prompts should all be different."""
        writer = WriterAgent(mock_llm_client)
        prompts = {}
        for platform in ["juejin", "zhihu", "devto"]:
            prompts[platform] = writer._build_writing_prompt(
                topic="Python",
                style="technical",
                platform=platform,
                skill_context={},
                rag_context="",
                project_info="",
                word_count="auto",
            )

        # All prompts should differ
        assert prompts["juejin"] != prompts["zhihu"]
        assert prompts["juejin"] != prompts["devto"]
        assert prompts["zhihu"] != prompts["devto"]
