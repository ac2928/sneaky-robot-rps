#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
printf '\nReady. Run: sh run.sh\nCheck: .venv/bin/python -B -m pytest -q -p no:cacheprovider\n'
