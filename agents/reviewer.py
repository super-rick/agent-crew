"""
Reviewer Agent — AI 质检员工。

负责：
1. 敏感词检测 — 防止违规内容发布
2. 平台规范检查 — 验证各平台的内容要求
3. 质量评分 — 标题、结构、可读性
4. 可选 LLM 深度语义审核

Pipeline: Writer → Reviewer → Publisher
        通过 → 发布 | 打回 → 返回修改建议
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime

from agents.base import BaseAgent, Task, TaskResult
from llm.client import LLMClient


@dataclass
class ReviewResult:
    """Structured result from a content review."""

    passed: bool  # 是否通过审核
    score: int  # 0-100 质量评分
    checks: dict[str, dict] = field(default_factory=dict)  # 各检查项的结果
    issues: list[dict] = field(default_factory=list)  # 发现的问题
    suggestions: list[str] = field(default_factory=list)  # 修改建议
    reviewed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "score": self.score,
            "checks": self.checks,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "reviewed_at": self.reviewed_at.isoformat(),
        }


# ── Sensitive word lists ────────────────────────────────────────────

SENSITIVE_PATTERNS: dict[str, str] = {
    # Political / campaign
    "习近平": "涉及领导人姓名，请避免直接引用",
    "共产党": "涉及政治组织名称，建议移除",
    "六四": "敏感历史事件，禁止提及",
    "法轮功": "违规内容，禁止发布",
    "台独": "分裂言论，禁止发布",
    "藏独": "分裂言论，禁止发布",
    "港独": "分裂言论，禁止发布",
    # Gambling / fraud
    "赌博": "涉及违规推广",
    "博彩": "涉及博彩内容",
    "赌场": "涉及违规推广",
    "网赚": "疑似欺诈内容",
    "刷单": "违规推广行为",
    "传销": "涉及违规商业模式",
    # Porn / adult
    "成人网站": "涉及违规内容",
    "色情": "涉及违规内容",
    "一夜情": "违规社交内容",
    "约炮": "违规社交内容",
    # Violence / weapons
    "枪支": "涉及违禁品",
    "毒品": "涉及违禁品",
    # Platform-specific forbidden
    "加微信": "平台禁止导流行为",
    "加我微信": "平台禁止导流行为",
    "扫码关注": "平台禁止导流行为",
    "关注公众号": "平台禁止导流",
    # Advertising spam
    "点击购买": "营销广告用语",
    "限时优惠": "营销广告用语",
    "免费领取": "营销广告用语",
}

# ── Platform compliance rules ────────────────────────────────────────

PLATFORM_RULES: dict[str, dict] = {
    "juejin": {
        "min_title_length": 5,
        "max_title_length": 100,
        "min_content_length": 500,
        "max_content_length": 50000,
        "require_title": True,
        "description": "掘金技术社区",
        "forbidden_patterns": [
            (r"微信|公众号|扫码|加群", "禁止导流行为（微信、公众号、扫码、加群）"),
            (r"纯广告|推广链接|affiliate", "禁止纯广告和推广链接"),
        ],
    },
    "zhihu": {
        "min_title_length": 3,
        "max_title_length": 60,
        "min_content_length": 200,
        "max_content_length": 30000,
        "require_title": False,
        "description": "知乎问答社区",
        "forbidden_patterns": [
            (r"二维码|扫码", "禁止二维码"),
            (r"http[s]?://(?!zhihu\.com)", "限制非知乎外链"),
        ],
    },
    "devto": {
        "min_title_length": 5,
        "max_title_length": 120,
        "min_content_length": 300,
        "max_content_length": 100000,
        "require_title": True,
        "description": "Dev.to 国际技术社区",
        "forbidden_patterns": [
            (r"spam|buy now|click here", "避免 spam 用语"),
        ],
    },
    "generic": {
        "min_title_length": 3,
        "max_title_length": 120,
        "min_content_length": 100,
        "max_content_length": 100000,
        "require_title": False,
        "description": "通用平台",
        "forbidden_patterns": [],
    },
}

# ── Quality scoring weights ──────────────────────────────────────────

QUALITY_CRITERIA = {
    "has_title": ("有标题", 10, lambda t, c: bool(t and len(t.strip()) >= 3)),
    "title_engaging": (
        "标题有吸引力",
        10,
        lambda t, c: bool(t and (len(t) >= 8 or any(kw in (t or "") for kw in ["如何", "详解", "指南", "实战", "深入"]))),
    ),
    "has_paragraphs": ("段落结构清晰", 10, lambda t, c: bool(c and "\n\n" in c)),
    "has_headings": ("使用小标题", 15, lambda t, c: bool(c and ("##" in c or "### " in c))),
    "has_code_blocks": ("包含代码示例", 10, lambda t, c: bool(c and "```" in c)),
    "content_length_ok": ("字数达标", 15, lambda t, c: bool(c and len(c) >= 500)),
    "has_conclusion": ("有结尾/总结", 10, lambda t, c: bool(
        c and any(kw in c[-200:] for kw in ["总结", "小结", "结论", "以上", "希望", "欢迎", "讨论"])
    )),
    "readability": ("可读性良好", 10, lambda t, c: bool(
        c and not (len(c.split()) > 0 and len(set(re.findall(r"\b\w{20,}\b", c))) > len(c.split()) * 0.1)
    )),
    "no_repetition": ("无重复内容", 10, lambda t, c: bool(
        c and _check_no_repetition(c)
    )),
}


def _check_no_repetition(content: str, threshold: float = 0.3) -> bool:
    """Check content doesn't have excessive repetition."""
    lines = [line.strip() for line in content.split("\n") if line.strip()]
    if len(lines) < 5:
        return True
    unique_lines = set(lines)
    return len(unique_lines) / len(lines) >= (1.0 - threshold)


class ReviewerAgent(BaseAgent):
    """Pre-publish content safety reviewer — the AI QA employee.

    Performs rule-based checks (fast, deterministic) and optionally
    calls LLM for deeper semantic review.
    """

    name = "reviewer"
    description = "负责发布前内容审核：敏感词检测、平台规范检查、质量评分"

    def __init__(
        self,
        llm_client: LLMClient,
        config: dict | None = None,
    ):
        super().__init__(llm_client, config)
        self.sensitive_patterns: dict[str, str] = dict(SENSITIVE_PATTERNS)
        self.default_platform_rules: dict = dict(PLATFORM_RULES)

        # Config overrides
        if config:
            custom_sensitive = config.get("reviewer_sensitive_words", {})
            self.sensitive_patterns.update(custom_sensitive)
            custom_rules = config.get("reviewer_platform_rules", {})
            self.default_platform_rules.update(custom_rules)

        self._min_pass_score: int = config.get("reviewer_min_score", 60) if config else 60
        self._use_llm_review: bool = config.get("reviewer_use_llm", False) if config else False

    def get_system_prompt(self) -> str:
        prompt_path = self.config.get("reviewer_system_prompt", "configs/prompts/reviewer_system.txt")  # noqa: E501
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return self._default_system_prompt()

    def _default_system_prompt(self) -> str:
        return (
            "你是一个严格的内容审核员。"
            "你的工作是审查内容是否合规、是否有违规词汇、质量是否达标。"
            "对于不合规的内容，你需要给出具体的问题和修改建议。"
        )

    def execute(self, task: Task) -> TaskResult:
        """Execute a review task.

        Task params:
            content (str or dict): 要审核的内容
                - text: 正文
                - title: 标题 (optional)
            platform (str): 目标平台 juejin/zhihu/devto/generic
            use_llm (bool, optional): 是否使用 LLM 深度审核（默认 False）
            min_pass_score (int, optional): 最低通过分数（默认 60）
        """
        started_at = datetime.now()

        content_data = task.params.get("content", {})
        platform = task.params.get("platform", "generic")
        use_llm = task.params.get("use_llm", self._use_llm_review)
        min_pass_score = task.params.get("min_pass_score", self._min_pass_score)

        # Normalize content input
        if isinstance(content_data, str):
            title = None
            text = content_data
        elif isinstance(content_data, dict):
            title = content_data.get("title")
            text = content_data.get("text", content_data.get("formatted_content", content_data.get("raw_content", "")))
        else:
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error_message="Invalid content format for review",
                started_at=started_at,
                completed_at=datetime.now(),
                agent_name=self.name,
            )

        try:
            # Step 1: Sensitive word check
            sensitive_result = self._check_sensitive(title or "", text)

            # Step 2: Platform compliance check
            compliance_result = self._check_platform_compliance(title, text, platform)

            # Step 3: Quality score
            quality_result = self._score_quality(title, text)

            # Step 4: Optional LLM deep review
            llm_result = {}
            if use_llm and text.strip():
                llm_result = self._llm_deep_review(title, text, platform)

            # Combine all checks
            all_checks = {
                "sensitive_words": sensitive_result,
                "platform_compliance": compliance_result,
                "quality_score": quality_result,
                "llm_review": llm_result,
            }

            all_issues = (
                sensitive_result.get("hits", [])
                + compliance_result.get("violations", [])
                + quality_result.get("deductions", [])
                + [{"type": "llm", **i} for i in llm_result.get("issues", [])]
            )

            all_suggestions = (
                quality_result.get("suggestions", [])
                + llm_result.get("suggestions", [])
            )

            # Determine pass/fail
            sensitive_pass = not sensitive_result.get("blocked", False)
            compliance_pass = compliance_result.get("passed", True)
            score_pass = quality_result.get("score", 0) >= min_pass_score
            llm_pass = not llm_result.get("blocked", False)

            passed = sensitive_pass and compliance_pass and score_pass and llm_pass

            review_data = ReviewResult(
                passed=passed,
                score=quality_result.get("score", 0),
                checks=all_checks,
                issues=all_issues,
                suggestions=all_suggestions,
            )

            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()

            return TaskResult(
                task_id=task.task_id,
                success=True,  # TaskResult.success = review completed (not content passed)
                data={
                    "review_passed": review_data.passed,
                    "review_score": review_data.score,
                    "review_checks": review_data.checks,
                    "review_issues": review_data.issues,
                    "review_suggestions": review_data.suggestions,
                    "platform": platform,
                    "title": title,
                    "content_preview": text[:200] if text else "",
                },
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                agent_name=self.name,
            )

        except Exception as e:
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error_message=str(e),
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                agent_name=self.name,
            )

    # ── Sensitive word detection ──────────────────────────────────

    def _check_sensitive(self, title: str, text: str) -> dict:
        """Scan content for sensitive/banned words."""
        combined = f"{title}\n{text}"
        hits = []
        blocked = False

        for pattern, reason in self.sensitive_patterns.items():
            if pattern in combined:
                hits.append(
                    {
                        "word": pattern,
                        "reason": reason,
                        "type": "sensitive_word",
                    }
                )
                blocked = True

        return {
            "passed": not blocked,
            "blocked": blocked,
            "hits": hits,
            "total_checked": len(self.sensitive_patterns),
        }

    # ── Platform compliance check ─────────────────────────────────

    def _check_platform_compliance(self, title: str | None, text: str, platform: str) -> dict:
        """Check content against platform-specific rules."""
        rules = self.default_platform_rules.get(platform, PLATFORM_RULES["generic"])
        violations = []
        passed = True

        # Title checks
        if title and rules.get("require_title", False):
            title_len = len(title.strip())
            min_t = rules.get("min_title_length", 0)
            max_t = rules.get("max_title_length", 999)
            if title_len < min_t:
                violations.append({
                    "type": "title_too_short",
                    "detail": f"标题 {title_len} 字 < {min_t} 字最低要求",
                    "platform": platform,
                })
                passed = False
            if title_len > max_t:
                violations.append({
                    "type": "title_too_long",
                    "detail": f"标题 {title_len} 字 > {max_t} 字上限",
                    "platform": platform,
                })

        # Title required but missing
        if rules.get("require_title") and not title:
            violations.append({
                "type": "title_missing",
                "detail": f"{platform} 要求必须有标题",
                "platform": platform,
            })
            passed = False

        # Content length checks
        content_len = len(text.strip()) if text else 0
        min_c = rules.get("min_content_length", 0)
        max_c = rules.get("max_content_length", 999999)
        if content_len < min_c:
            violations.append({
                "type": "content_too_short",
                "detail": f"内容 {content_len} 字 < {min_c} 字最低要求",
                "platform": platform,
            })
            passed = False
        if content_len > max_c:
            violations.append({
                "type": "content_too_long",
                "detail": f"内容 {content_len} 字 > {max_c} 字上限",
                "platform": platform,
            })

        # Platform-specific forbidden patterns
        for pattern_str, violation_msg in rules.get("forbidden_patterns", []):
            if re.search(pattern_str, text, re.IGNORECASE):
                violations.append({
                    "type": "platform_forbidden",
                    "detail": violation_msg,
                    "platform": platform,
                })
                passed = True  # Warning only, don't block

        return {
            "passed": passed,
            "platform": platform,
            "violations": violations,
            "rules_applied": {
                "title_length": (rules.get("min_title_length"), rules.get("max_title_length")),
                "content_length": (rules.get("min_content_length"), rules.get("max_content_length")),
                "require_title": rules.get("require_title"),
            },
        }

    # ── Quality scoring ───────────────────────────────────────────

    def _score_quality(self, title: str | None, text: str) -> dict:
        """Score content quality across multiple dimensions."""
        score = 0
        max_score = 0
        deductions = []
        suggestions = []

        for key, (label, weight, check_fn) in QUALITY_CRITERIA.items():
            max_score += weight
            if check_fn(title, text):
                score += weight
            else:
                deductions.append({"type": key, "detail": f"缺少: {label}", "weight": weight})

        # Additional suggestions
        if title and len(title) < 8:
            suggestions.append("标题偏短，建议 8 字以上，包含关键词")
        if text and len(text) < 1000:
            suggestions.append("内容偏短，建议扩展至 1000 字以上")
        if text and "\n\n" not in text and len(text) > 500:
            suggestions.append("建议增加段落分隔，提升可读性")

        normalized = int((score / max_score) * 100) if max_score > 0 else 0

        return {
            "score": normalized,
            "max_score": 100,
            "raw_score": score,
            "raw_max": max_score,
            "criteria_passed": max_score - (max_score - score),
            "criteria_total": max_score,
            "deductions": deductions,
            "suggestions": suggestions,
        }

    # ── LLM deep review ───────────────────────────────────────────

    def _llm_deep_review(
        self,
        title: str | None,
        text: str,
        platform: str,
    ) -> dict:
        """Use LLM for deeper semantic review of content safety and quality."""
        if not text.strip():
            return {"skipped": True, "reason": "Empty content"}

        truncated = text[:3000]  # Limit to avoid token waste
        prompt = (
            f"审核以下即将发布到 {platform} 的内容：\n\n"
            + (f"标题: {title}\n\n" if title else "")
            + f"正文: {truncated}\n\n"
            "请检查：\n"
            "1. 是否有敏感或不当内容\n"
            "2. 是否符合平台风格\n"
            "3. 内容质量是否合格\n\n"
            "用 JSON 格式回复：\n"
            '{"blocked": false, "issues": [], "suggestions": [], "verdict": "pass"}\n'
            "如果 blocked 为 true，content 不应发布。"
        )

        try:
            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": prompt},
            ]
            response = self.llm_client.chat(messages)

            # Try to parse LLM JSON response
            import json
            try:
                result = json.loads(response)
                return {
                    "blocked": result.get("blocked", False),
                    "issues": result.get("issues", []),
                    "suggestions": result.get("suggestions", []),
                    "verdict": result.get("verdict", "unknown"),
                    "raw_response": response[:500],
                }
            except json.JSONDecodeError:
                return {
                    "blocked": False,
                    "issues": [],
                    "suggestions": [],
                    "verdict": "parse_error",
                    "raw_response": response[:500],
                }
        except Exception as e:
            return {"blocked": False, "issues": [], "error": str(e)}

    # ── Convenience methods ───────────────────────────────────────

    def review_content(
        self,
        text: str,
        title: str | None = None,
        platform: str = "generic",
        use_llm: bool = False,
    ) -> ReviewResult:
        """Convenience method: review content synchronously."""
        task = Task(
            task_id=f"review_{datetime.now().timestamp()}",
            task_type="review",
            params={
                "content": {"text": text, "title": title},
                "platform": platform,
                "use_llm": use_llm,
            },
        )
        result = self.execute(task)
        if result.success and result.data:
            return ReviewResult(
                passed=result.data.get("review_passed", False),
                score=result.data.get("review_score", 0),
                issues=result.data.get("review_issues", []),
                suggestions=result.data.get("review_suggestions", []),
            )
        return ReviewResult(
            passed=False,
            score=0,
            issues=[{"type": "error", "detail": result.error_message or "Unknown error"}],
        )
