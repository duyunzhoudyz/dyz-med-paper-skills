#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "========================================================"
echo "  DYZ MedPaper — Medical Paper Skills Installer (macOS)"
echo "========================================================"
echo

PY=""
for cand in python3 python; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1; then
      PY="$cand"
      break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "[ERROR] Python 3.10+ not found. Please install from https://www.python.org/downloads/"
  exit 2
fi

echo "Select target AI agent host:"
echo "  [1] Claude Code    (~/.claude/skills)"
echo "  [2] Codex          (~/.agents/skills)"
echo "  [3] Cursor         (~/.cursor/skills)"
echo "  [4] GitHub Copilot (~/.copilot/skills)"
echo "  [5] Gemini CLI     (~/.gemini/skills)"
echo "  [6] Claude Code + Codex (recommended)"
read -r -p "Enter [1-6] (default 6): " CHOICE
CHOICE="${CHOICE:-6}"

echo
echo "Select skill pack (smaller stage packs help avoid host description-budget truncation):"
echo "  [1] all      (all 32 skills)"
echo "  [2] start    (5 skills: ideate, init, diagnose, orchestrator, passport)"
echo "  [3] evidence (7 skills: mechanism, data-adequacy, registration, cnki, key-lit, screening, evidence-audit)"
echo "  [4] analysis (5 skills: analyze, interpret, sensitivity, figures-tables, flowchart)"
echo "  [5] writing  (7 skills: writing-plan, IMRaD sections, write)"
echo "  [6] delivery (8 skills: translate, deai, guideline, review, revision, journal-finder, export, submit)"
read -r -p "Enter [1-6] (default 1): " PCHOICE
case "${PCHOICE:-1}" in
  2) PACK="start" ;;
  3) PACK="evidence" ;;
  4) PACK="analysis" ;;
  5) PACK="writing" ;;
  6) PACK="delivery" ;;
  *) PACK="all" ;;
esac

install_one() {
  local target="$1"
  "$PY" scripts/install_codex.py --pack "$PACK" --target "$target"
  "$PY" scripts/install_codex.py --pack "$PACK" --target "$target" --check
}

case "$CHOICE" in
  1) install_one "$HOME/.claude/skills" ;;
  2) install_one "$HOME/.agents/skills" ;;
  3) install_one "$HOME/.cursor/skills" ;;
  4) install_one "$HOME/.copilot/skills" ;;
  5) install_one "$HOME/.gemini/skills" ;;
  *)
    install_one "$HOME/.claude/skills"
    install_one "$HOME/.agents/skills"
    ;;
esac

echo
echo "Installation & verification passed (pack=$PACK). Restart your agent host to load skills."
