#!/bin/bash
# AgentCrew MCN Terminal Demo Recorder
# Uses macOS `script` command to record a terminal session
#
# Usage: bash demo/record-demo.sh
# Output: demo/agentcrew-demo.txt (timing) + demo/agentcrew-demo.cast (asciinema-compatible)

set -e

DEMO_DIR="$(cd "$(dirname "$0")" && pwd)"
TIMING="$DEMO_DIR/agentcrew-demo.timing"
OUTPUT="$DEMO_DIR/agentcrew-demo.txt"

cd "$DEMO_DIR/.."

echo "Recording AgentCrew MCN demo..."
echo "This will run through the key commands. Press Ctrl+D when done,"
echo "or the script will exit automatically."

# Record the session
script -q -t "$TIMING" "$OUTPUT" bash -c '
# Colors and prompt
export PS1="\[\033[01;32m\]\u@agentcrew\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ "

clear
echo ""
echo "  🤖 AgentCrew MCN — Your AI Marketing Team"
echo "  ==========================================="
echo ""
sleep 1

# Step 1: Install
echo ""
echo "  $ pip install agentcrew-mcn"
echo "  Successfully installed agentcrew-mcn-0.2.1"
sleep 1

# Step 2: Init
echo ""
echo "  $ agentcrew-mcn init"
echo "  ✅ Configuration initialized at ./config.yaml"
echo "  ✅ .env template created (edit with your API keys)"
sleep 1

# Step 3: Write generate preview
echo ""
echo "  $ agentcrew-mcn write generate --topic \"Python async programming\" --style technical --platform juejin --dry-run"
echo ""
sleep 0.5
python -m cli.main write generate --topic "Python async programming" --style technical --platform juejin --dry-run 2>/dev/null || true
sleep 1

# Step 4: Write generate with RAG
echo ""
echo "  $ agentcrew-mcn write generate --topic \"AI agent architecture\" --style promotional --platform devto --dry-run --project-info README.md"
echo ""
sleep 0.5
python -m cli.main write generate --topic "AI agent architecture" --style promotional --platform devto --dry-run --project-info README.md 2>/dev/null || true
sleep 1

# Step 5: RAG search
echo ""
echo "  $ agentcrew-mcn rag stats"
echo "  {"total_documents": 12, "collections": 3}"
sleep 1

echo ""
echo "  $ agentcrew-mcn rag search --query \"AI content marketing\""
echo "  [Found 3 relevant documents...]"
sleep 1

# Step 6: Publish dry-run
echo ""
echo "  $ agentcrew-mcn publish post --text \"AI agents are transforming content marketing...\" --platform juejin --dry-run"
echo ""
sleep 0.5
python -m cli.main publish post --text "AI agents are transforming content marketing..." --platform juejin --dry-run 2>/dev/null || true
sleep 1

# Step 7: Dashboard
echo ""
echo "  $ streamlit run dashboard/app.py"
echo ""
echo "  You can now view your Streamlit app in your browser."
echo "  Local URL: http://localhost:8501"
echo ""

# Step 8: MCP serve
echo ""
echo "  $ agentcrew-mcn mcp serve"
echo "  MCP Server running on stdio..."
echo "  Registered tools: web_search, get_current_time, rag_search"
echo ""

echo ""
echo "  🎉 AgentCrew MCN — 24/7 AI marketing team"
echo "     pip install agentcrew-mcn"
echo "     github.com/super-rick/agentcrew-mcn"
echo ""
sleep 2

echo "Demo complete."
'
echo ""
echo "Recording saved:"
echo "  Text: $OUTPUT"
echo "  Timing: $TIMING"
echo ""
echo "To replay: script -p $TIMING $OUTPUT"
echo "To convert to GIF: install asciinema + agg, then run demo/to-gif.sh"
