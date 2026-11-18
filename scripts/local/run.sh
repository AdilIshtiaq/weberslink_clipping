#!/usr/bin/env bash
# Starts WeberslinkClip on your computer: API, video worker and website.
# Press Ctrl+C to stop everything.
#
#   bash scripts/local/run.sh          # app at http://localhost:3107
#   bash scripts/local/run.sh --ai     # also start the AI-edit worker
set -euo pipefail
cd "$(dirname "$0")/../.."

[ -f .env ] || { echo "No .env yet. Run:  bash scripts/local/setup.sh"; exit 1; }
if ! (exec 3<>/dev/tcp/127.0.0.1/6379) 2>/dev/null; then
  echo "Redis is not running on port 6379. Start Redis (Memurai on Windows), then run this again."
  exit 1
fi

if [ -x backend/.venv/Scripts/python.exe ]; then PY=backend/.venv/Scripts/python.exe; else PY=backend/.venv/bin/python; fi
mkdir -p data/logs
PIDS=()

start() {
  local name=$1; shift
  ( cd "$1"; shift; exec "$@" ) >"data/logs/$name.log" 2>&1 &
  PIDS+=($!)
  echo "started $name (log: data/logs/$name.log)"
}
stop_all() {
  echo; echo "Stopping..."
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap stop_all INT TERM EXIT

PYABS=$(cd backend && pwd)/${PY#backend/}
start api     backend "$PYABS" -m uvicorn src.main:app --host 127.0.0.1 --port 8000
# The API creates any missing tables when it starts; the workers need them.
echo -n "waiting for the API"
for _ in $(seq 1 90); do
  (exec 3<>/dev/tcp/127.0.0.1/8000) 2>/dev/null && break
  echo -n "."; sleep 1
done
echo
start worker  backend "$PYABS" -m src.workers.run_workers
if [ "${1:-}" = "--ai" ]; then
  start ai-worker backend "$PYABS" -m arq src.workers.ai_worker.AIWorkerSettings
fi
start web     frontend node node_modules/next/dist/bin/next start --port 3107

echo
echo "Open http://localhost:3107  (Ctrl+C to stop)"
wait
