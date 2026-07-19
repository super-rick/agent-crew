#!/bin/bash
# AgentCrew MCN — Terminal Demo Script
# Generates clean demo output suitable for recording to GIF/asciinema.
# No real API calls — all output is pre-scripted for consistency.
#
# Usage:
#   bash demo/agentcrew-demo.sh              # watch the demo
#   bash demo/agentcrew-demo.sh | tee /tmp/demo.txt   # save output
#   asciinema rec -c "bash demo/agentcrew-demo.sh" demo.cast  # record to asciinema

set -e

# Terminal colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'
PS1="${GREEN}agentcrew${NC}:${CYAN}~/demo${NC}\$ "

print_cmd() { echo -e "${PS1}${BOLD}$1${NC}"; sleep 0.4; }
print_out() { echo -e "$1"; sleep 0.2; }
section() { echo ""; echo -e "  ${YELLOW}${BOLD}$1${NC}"; sleep 0.3; }

clear
echo ""
echo -e "  🤖 ${BOLD}AgentCrew MCN${NC} — Your AI Marketing Team (30s Demo)"
echo "  ============================================================"
sleep 1

# ── Install ──
section "📦 1. Install"
print_cmd "pip install agentcrew-mcn"
print_out "  Collecting agentcrew-mcn"
print_out "  Downloading agentcrew_mcn-0.2.1-py3-none-any.whl"
sleep 0.5
print_out "  Successfully installed agentcrew-mcn-0.2.1"

# ── Init ──
section "⚙️  2. Initialize"
print_cmd "agentcrew-mcn init"
print_out "  ✅ config.yaml created"
print_out "  ✅ .env template created"
print_out "  ✅ data/ directory initialized"
sleep 0.5

# ── Write ──
section "✍️  3. Generate content (Writer Agent)"
print_cmd "agentcrew-mcn write generate -t 'Python async programming' -s technical -p juejin"
print_out "  🔍 RAG: retrieved 3 relevant documents"
print_out "  🤖 Writer Agent: composing..."
sleep 1
print_out "  ┌─────────────────────────────────────────────"
print_out "  │ # Python 异步编程完全指南"
print_out "  │ ## 为什么需要异步编程?"
print_out "  │ 在现代 Web 开发中，I/O 密集型任务占据了大量时间…"
print_out "  │ ## asyncio 核心概念"
print_out "  │ async/await 是 Python 异步编程的基础…"
print_out "  │ \`\`\`python"
print_out "  │ import asyncio"
print_out "  │ async def fetch_data(url): ..."
print_out "  │ \`\`\`"
print_out "  │ ## 实战案例"
print_out "  │ …"
print_out "  │ ## 总结"
print_out "  └─────────────────────────────────────────────"
print_out "  ✅ Generated 2,847 words | Platform: juejin"
sleep 0.5

# ── Review ──
section "🛡️  4. Review content (Reviewer Agent)"
print_cmd "agentcrew-mcn review check --content article.md --platform juejin"
print_out "  🔍 Sensitive words: passed (0 hits)"
print_out "  📋 Platform compliance: passed"
print_out "  ⭐ Quality score: 85/100"
print_out "  ✅ REVIEW PASSED → ready to publish"
sleep 0.5

# ── Publish ──
section "🚀 5. Publish (Publisher Agent)"
print_cmd "agentcrew-mcn publish post --file article.md --platform juejin"
print_out "  📤 Publishing to juejin..."
sleep 0.8
print_out "  ✅ Published: juejin.cn/post/86a7d3c..."
sleep 0.5

# ── Schedule ──
section "⏰ 6. Schedule it!"
print_cmd "agentcrew-mcn schedule start --topic-file topics.txt --platform juejin --interval 6"
print_out "  📅 Scheduler started (interval: 6h, random jitter ±15m)"
print_out "  📝 12 topics queued → next post in ~6 hours"
sleep 0.5

# ── Dashboard ──
section "📊 Bonus: Dashboard"
print_cmd "streamlit run dashboard/app.py &"
print_out "  http://localhost:8501"
sleep 0.5

# ── Outro ──
echo ""
echo -e "  🎉 ${BOLD}AgentCrew MCN${NC} — 3 AI employees, 24/7 content marketing"
echo ""
echo -e "     ${CYAN}pip install agentcrew-mcn${NC}"
echo -e "     ${CYAN}github.com/super-rick/agentcrew-mcn${NC}"
echo ""

sleep 2
echo -n "Demo complete. ⭐ Star us on GitHub!"
