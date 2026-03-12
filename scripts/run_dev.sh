#!/usr/bin/env bash

set -euo pipefail

export PG_LOG_LEVEL="${PG_LOG_LEVEL:-DEBUG}"
export PG_LOG_TO_CONSOLE="${PG_LOG_TO_CONSOLE:-true}"
export PG_LOG_TO_FILE="${PG_LOG_TO_FILE:-false}"
export PG_AUTO_CHOOSE_POWERUPS="${PG_AUTO_CHOOSE_POWERUPS:-true}"

if command -v python >/dev/null 2>&1; then
  PYTHONPATH="${PYTHONPATH:-src}" python -m prisoners_gambit
else
  PYTHONPATH="${PYTHONPATH:-src}" python3 -m prisoners_gambit
fi
