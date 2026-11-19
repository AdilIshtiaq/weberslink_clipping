# Run WeberslinkClip on your computer (no Docker)

This runs four small programs directly on your machine: the website, the API, the video worker and (optionally) the AI-edit worker. It also needs a database (PostgreSQL) and Redis, which you install once.

The scripts were tested end to end on Linux. On Windows, use **Git Bash** (it comes with Git for Windows). Windows is expected to work the same way but has not been tested here, so tell me if a step fails.

## 1. Install the tools once

On Windows, open a terminal and run (check each name with `winget search` if one is not found):

```bash
winget install OpenJS.NodeJS.LTS
winget install astral-sh.uv
winget install Gyan.FFmpeg
winget install PostgreSQL.PostgreSQL.16
winget install Memurai.MemuraiDeveloper
npm install -g pnpm
```

- **PostgreSQL** asks you to choose a password for the `postgres` user. Remember it.
- **Memurai** is a free Redis-compatible service for Windows. It starts automatically on port 6379.
- On macOS or Linux, install Node 22, pnpm, uv, ffmpeg, PostgreSQL 15+ and Redis with your package manager.
- Close and reopen the terminal afterwards so the new commands are found. Make sure PostgreSQL's `bin` folder is on your PATH (for example `C:\Program Files\PostgreSQL\16\bin`).

You also need two keys: an [AssemblyAI](https://www.assemblyai.com/) key (transcription) and a [Google AI](https://aistudio.google.com/) key (clip selection). You can add them later in `.env`.

## 2. Set up (once)

In Git Bash, from the project folder:

```bash
bash scripts/local/setup.sh
```

It asks for the PostgreSQL `postgres` password and your two keys, then creates the database, writes the settings files, installs the packages and builds the website. The first run downloads a lot (the backend includes torch, so expect several hundred MB, plus the website's packages). On a fast connection that is a few minutes; on a slow one it can take hours, and re-running the setup continues where it stopped. Later runs are quick.

## 3. Run

```bash
bash scripts/local/run.sh
```

Open **http://localhost:3107**, create an account and clip a video. Press **Ctrl+C** to stop everything. Logs are in `data/logs/`.

Add `--ai` to also start the worker for AI edits in the editor: `bash scripts/local/run.sh --ai`.

Each time you start the app, Redis and PostgreSQL must be running (both start with Windows by default).

## Settings

Your settings are in `.env` (created by setup, never committed).

- `SELF_HOST=false` applies the plans and the free early bird allowance (300 minutes a month). Set `SELF_HOST=true` for unlimited personal use.
- Change a key, then stop and start `run.sh` again.
- If you change an address or a `NEXT_PUBLIC_*` value, rebuild the website: `cd frontend && pnpm run build`.

## Updating

```bash
git pull
bash scripts/local/setup.sh      # safe to re-run: keeps your database and .env
bash scripts/local/run.sh
```

## Making it reachable at clip.weberslink.org

Running on your own computer means only you can open it, unless you add a tunnel. A free **Cloudflare Tunnel** can publish it, but the domain's DNS must be on Cloudflare, and your computer must stay on and awake for visitors to use it. That is fine for testing, not for real customers.

1. Create a tunnel with two public hostnames: `clip.weberslink.org` to `http://localhost:3107`, and `clip-api.weberslink.org` to `http://localhost:8000`.
2. Run setup with the public addresses so the website is built for them:

   ```bash
   APP_URL=https://clip.weberslink.org API_URL=https://clip-api.weberslink.org bash scripts/local/setup.sh
   ```

3. In `.env`, set `CORS_ORIGINS=https://clip.weberslink.org`, then run `bash scripts/local/run.sh`.

## If something fails

- **API or worker log says `Timeout connecting to server` (Redis):** use the IPv4 address. In `.env` set `REDIS_HOST=127.0.0.1` (and use `127.0.0.1` instead of `localhost` in `DATABASE_URL`), then restart.
- **"Redis is not running":** start Memurai (Windows Services) or `redis-server`.
- **Setup cannot connect to PostgreSQL:** check the password, and that the PostgreSQL service is running.
- **Port already in use:** another program uses 3107 or 8000. Close it, or stop the old run with Ctrl+C.
- **Downloads time out or crawl:** on a slow connection run `export UV_HTTP_TIMEOUT=900 UV_CONCURRENT_DOWNLOADS=1` first, and retry in a loop: `cd backend && until uv sync; do sleep 10; done`.
- **Website build fails with `EPERM ... Application Data`:** this happens when the project is on a different drive than your user folder. The setup script already works around it. To build by hand: `cd frontend && mkdir -p .home && USERPROFILE="$(pwd -W)/.home" HOME="$(pwd)/.home" pnpm exec next build`.
- **Transcription or clip selection errors:** open `data/logs/worker.log`; usually a missing or wrong API key.
