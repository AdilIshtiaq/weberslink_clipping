#!/usr/bin/env bash
# One-time setup for running WeberslinkClip directly on your computer (no Docker).
# Works in Git Bash on Windows, and on macOS and Linux.
#
#   bash scripts/local/setup.sh
#
# Needs these installed first: Node 22, pnpm, uv, ffmpeg, PostgreSQL 15+ and a
# Redis-compatible server on port 6379 (Memurai on Windows, Redis elsewhere).
set -euo pipefail
cd "$(dirname "$0")/../.."

MISSING=0
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1 ($2)"; MISSING=1; }; }
need node   "install Node 22 from https://nodejs.org"
need pnpm   "run: npm install -g pnpm"
need uv     "https://docs.astral.sh/uv/getting-started/installation/"
need ffmpeg "install ffmpeg and add it to PATH"
need ffprobe "comes with ffmpeg"
need psql   "install PostgreSQL 15 or newer and add its bin folder to PATH"
[ "$MISSING" = 0 ] || exit 1

if ! (exec 3<>/dev/tcp/127.0.0.1/6379) 2>/dev/null; then
  echo "Warning: nothing is listening on Redis port 6379. Install and start Memurai (Windows) or Redis."
  echo "         Setup continues; start Redis before running run.sh."
fi

DB_NAME=${DB_NAME:-weberslinkclip}
DB_USER=${DB_USER:-weberslinkclip}
ADMIN_URL=${PG_ADMIN_URL:-postgresql://postgres@localhost:5432/postgres}
NATIVE_ROOT=$(pwd -W 2>/dev/null || pwd)   # Windows-style path under Git Bash

# Read KEY from .env if it is there.
getenv() { [ -f .env ] && grep -E "^$1=" .env | head -1 | cut -d= -f2- || true; }
rand() { openssl rand -hex 24 2>/dev/null || head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n'; }

# ---------- 1. Database ----------
DB_PASSWORD=$(getenv DB_PASSWORD)
DB_PASSWORD=${DB_PASSWORD:-$(rand)}
if [ -z "${PGPASSWORD:-}" ] && [ -t 0 ] && [ -z "${PG_ADMIN_URL:-}" ]; then
  read -r -s -p "PostgreSQL 'postgres' admin password: " PGPASSWORD; echo
  export PGPASSWORD
fi
echo "Creating database '$DB_NAME'..."
psql "$ADMIN_URL" -v ON_ERROR_STOP=1 -qtA <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
    CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASSWORD';
  ELSE
    ALTER ROLE $DB_USER PASSWORD '$DB_PASSWORD';
  END IF;
END \$\$;
SQL
if [ "$(psql "$ADMIN_URL" -qtAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'")" != "1" ]; then
  psql "$ADMIN_URL" -v ON_ERROR_STOP=1 -qc "CREATE DATABASE $DB_NAME OWNER $DB_USER"
fi
DB_ADMIN_URL="${ADMIN_URL%/*}/$DB_NAME"
psql "$DB_ADMIN_URL" -v ON_ERROR_STOP=1 -qc 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'
APP_DB="postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
if [ "$(psql "$APP_DB" -qtAc "SELECT to_regclass('public.users') IS NOT NULL")" != "t" ]; then
  echo "Creating tables..."
  psql "$APP_DB" -v ON_ERROR_STOP=1 -q -f init.sql >/dev/null
else
  echo "Tables already exist, leaving them alone."
fi

# ---------- 2. Settings ----------
if [ -f .env ]; then
  echo ".env already exists, keeping it."
else
  echo "Writing .env..."
  ASSEMBLY_AI_API_KEY=${ASSEMBLY_AI_API_KEY:-}
  GOOGLE_API_KEY=${GOOGLE_API_KEY:-}
  if [ -t 0 ]; then
    [ -n "$ASSEMBLY_AI_API_KEY" ] || read -r -p "AssemblyAI API key (transcription, can add later): " ASSEMBLY_AI_API_KEY
    [ -n "$GOOGLE_API_KEY" ] || read -r -p "Google AI API key (clip selection, can add later): " GOOGLE_API_KEY
  fi
  cat > .env <<ENV
# Local run settings (created by scripts/local/setup.sh). Never commit this file.
DB_PASSWORD=$DB_PASSWORD
DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASSWORD@127.0.0.1:5432/$DB_NAME
# 127.0.0.1, not "localhost": on Windows "localhost" can resolve to IPv6, which Redis does not listen on.
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
TEMP_DIR=$NATIVE_ROOT/data
CORS_ORIGINS=http://localhost:3107

BACKEND_AUTH_SECRET=$(rand)
APP_SETTINGS_ENCRYPTION_KEY=$(rand)
BETTER_AUTH_SECRET=$(rand)
ALLOW_UNSIGNED_BACKEND_AUTH=false

# false = plan limits and the free early bird allowance apply; true = unlimited.
SELF_HOST=false
EARLY_BIRD_ENABLED=true
EARLY_BIRD_MINUTE_LIMIT=300

ASSEMBLY_AI_API_KEY=$ASSEMBLY_AI_API_KEY
LLM=google-gla:gemini-3-flash-preview
GOOGLE_API_KEY=$GOOGLE_API_KEY
ENV
fi

# The frontend reads its own file.
cat > frontend/.env.local <<ENV
DATABASE_URL=postgresql://$DB_USER:$(getenv DB_PASSWORD)@localhost:5432/$DB_NAME
BETTER_AUTH_SECRET=$(getenv BETTER_AUTH_SECRET)
BETTER_AUTH_URL=${APP_URL:-http://localhost:3107}
NEXT_PUBLIC_APP_URL=${APP_URL:-http://localhost:3107}
NEXT_PUBLIC_API_URL=${API_URL:-http://localhost:8000}
BACKEND_INTERNAL_URL=http://localhost:8000
BACKEND_AUTH_SECRET=$(getenv BACKEND_AUTH_SECRET)
APP_SETTINGS_ENCRYPTION_KEY=$(getenv APP_SETTINGS_ENCRYPTION_KEY)
NEXT_PUBLIC_SELF_HOST=$(getenv SELF_HOST)
NEXT_TELEMETRY_DISABLED=1
ENV

mkdir -p data/logs

# ---------- 3. Dependencies and build ----------
echo "Installing backend packages (large the first time, because it includes torch; later runs are fast).."
( cd backend && uv sync )
echo "Installing and building the frontend..."
( cd frontend && pnpm install --frozen-lockfile )
# On Windows, when the project is on a different drive than your user folder (for example D: and C:),
# Next.js's file tracer scans the whole user folder and fails on protected folders. Pointing the
# "home folder" at a small folder inside the project for this one build step avoids it.
if [ -n "${USERPROFILE:-}" ]; then
  mkdir -p frontend/.home
  ( cd frontend && USERPROFILE="$(pwd -W 2>/dev/null || pwd)/.home" HOME="$(pwd)/.home" pnpm exec next build )
else
  ( cd frontend && pnpm exec next build )
fi

echo
echo "Setup finished. Start everything with:  bash scripts/local/run.sh"
