#!/usr/bin/env bash
# 2_run_pipeline.sh — One-command pipeline runner
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."

echo "══════════════════════════════════════════════"
echo "  CCM Research Publications Pipeline"
echo "══════════════════════════════════════════════"

# Install dependencies
echo ""
echo "📦  Installing dependencies..."
pip install -q -r "$ROOT/requirements.txt"

# Run classification pipeline
echo ""
echo "🚀  Running fetch + classify pipeline..."
python "$SCRIPT_DIR/1_fetch_and_classify.py"

echo ""
echo "✅  Done! Open dashboard/index.html in your browser."
echo "    Or push to GitHub and enable GitHub Pages."
