#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  printf 'Run sh setup.sh first.\n' >&2
  exit 1
fi
exec .venv/bin/python -B -m flask --app app run --host 127.0.0.1 --port "${ARENA_PORT:-4190}"
