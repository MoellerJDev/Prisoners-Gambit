#!/usr/bin/env bash

set -euo pipefail

export PG_LOG_LEVEL="${PG_LOG_LEVEL:-DEBUG}"
export PG_LOG_TO_CONSOLE="${PG_LOG_TO_CONSOLE:-true}"
export PG_LOG_TO_FILE="${PG_LOG_TO_FILE:-false}"
export PG_AUTO_CHOOSE_POWERUPS="${PG_AUTO_CHOOSE_POWERUPS:-true}"

python -m prisoners_gambit