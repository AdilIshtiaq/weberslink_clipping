# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

WeberslinkClip is an AI video clipping tool by WebersLink: it turns long videos into short, captioned vertical clips. The product is deliberately small: clipping, editing, export and publishing. Language: English only.

## Development Commands

### Docker (recommended)

```bash
docker-compose up -d              # Start all 6 services
docker-compose up -d --build      # Rebuild after changes
docker-compose logs -f backend    # Debug backend
docker-compose logs -f worker     # Debug video processing
docker-compose logs -f ai-worker  # Debug AI editing in the clip studio
docker-compose down               # Stop all services
```

Services: Frontend (:3107), Backend API (:8000, docs at /docs), Worker (ARQ), AI worker (ARQ, `weberslinkclip_ai` queue), PostgreSQL (:5432), Redis (:6379)

### Backend (local)

Uses `uv` (not pip/poetry). Requires Python 3.11+, ffmpeg, running PostgreSQL and Redis.

```bash
cd backend
uv venv .venv && source .venv/bin/activate
uv sync

# API server (uses refactored entry point)
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Worker process (required for video processing). Also starts the cron worker.
python -m src.workers.run_workers
```

### Frontend (local)

```bash
cd frontend
pnpm install
pnpm run dev          # Dev server with Turbopack
pnpm run build        # Prisma generate + Next.js build
pnpm run lint
```

### Tests

```bash
cd backend && .venv/bin/pytest                  # unit + integration (needs Postgres/Redis; TEST_DATABASE_URL)
cd backend && .venv/bin/pytest --no-cov tests/unit/test_workflow_options.py   # one file (coverage gate is in addopts)
cd frontend && pnpm run test                    # vitest; pnpm run lint && pnpm exec tsc --noEmit
```

## Architecture

### System Overview

```
User → Frontend (Next.js 15) → Backend API (FastAPI) → Redis Queue → ARQ Worker
                                      ↓                                  ↓
                               PostgreSQL ←───────────────────────────────┘
```

Task creation returns immediately (<100ms). Video processing happens asynchronously in the worker. Frontend connects via SSE for real-time progress updates.

### Backend: Layered Architecture

The backend uses the layered application in `main.py`:

```
api/routes/          → HTTP handlers (tasks.py, media.py)
services/            → Business logic (task_service.py, video_service.py)
repositories/        → Raw SQL via asyncpg (task_repository.py, clip_repository.py, source_repository.py)
workers/             → ARQ job queue (tasks.py, job_queue.py, progress.py)
utils/               → Thread pool helpers for blocking operations (async_helpers.py)
```

**Key patterns:**
- All DB access goes through repository classes using raw SQL (`text()` queries), not SQLAlchemy ORM
- Blocking operations (video processing, downloads, transcription) wrapped in `run_in_thread()` to avoid blocking the async event loop
- Progress tracking uses Redis pub/sub → SSE to frontend
- Task status flow: `queued → processing → completed/error/cancelled`

### Video Processing Pipeline

1. **Input** → YouTube URL (yt-dlp) or uploaded file
2. **Transcription** → AssemblyAI word-level timestamps (cached as `.transcript_cache.json`)
3. **AI Analysis** → Pydantic AI selects viral segments (15-60s each) with virality scoring. Transcripts over 15 min are analysed in 12-min windows (2-min overlap, 3 concurrent), deduplicated, then reranked together in one comparative call (`RERANK_LLM`, default `LLM`); final count scales ~1 clip per 5 min, capped by `MAX_CLIPS` (default 10)
4. **Clip Generation** → MoviePy creates 9:16 clips with:
   - Face-centered cropping: MediaPipe → OpenCV DNN → Haar cascade (fallback chain)
   - Word-synced subtitles from AssemblyAI
   - Custom fonts (TTF files in `backend/fonts/`)
   - Optional transition effects (`backend/transitions/`)
   - Optional B-roll overlays (Pexels API)
   - Caption templates with animation styles
5. **Storage** → Clips to `{TEMP_DIR}/clips/`, metadata to PostgreSQL

### Frontend Architecture

- **Next.js 15** with App Router, React 19, TailwindCSS v4
- **ShadCN UI** (New York style, stone base color, Radix primitives)
- **Better Auth** with Prisma adapter for email/password auth
- **No global state library** — React hooks only (`useState`, `useEffect`, `useSession`)
- All pages use `"use client"` — SSR is minimal
- Prisma client generated to `frontend/src/generated/prisma/` (custom output path)
- Build: `prisma generate && next build` (Prisma generate runs on both build and postinstall)

**Auth flow:** Frontend calls Better Auth → session cookie → passes `user_id` header to backend API

### Database

PostgreSQL 15. Schema in `init.sql`. Mixed naming conventions:
- `tasks`, `sources`, `generated_clips` → snake_case
- `session`, `account`, `verification`, `users` → camelCase (Better Auth)
- UUIDs stored as VARCHAR(36)
- Auto-update triggers on `updated_at`/`updatedAt` columns

## Key Backend Files

| File | Purpose |
|------|---------|
| `src/main_refactored.py` | Compatibility import for existing deployments |
| `src/main.py` | Canonical FastAPI application factory |
| `src/api/routes/tasks.py` | Task CRUD, SSE progress, clip editing endpoints (711 lines) |
| `src/api/routes/media.py` | Fonts, transitions, uploads, templates |
| `src/services/task_service.py` | Task orchestration, clip editing logic (574 lines) |
| `src/services/video_service.py` | Video download, transcription, AI analysis, clip generation |
| `src/workers/tasks.py` | ARQ worker task definitions |
| `src/workers/job_queue.py` | Job queue management |
| `src/workers/progress.py` | Real-time progress via Redis |
| `src/ai.py` | Pydantic AI agents, system prompt, segment validation |
| `src/video_utils.py` | Video processing, cropping, subtitles (~820 lines) |
| `src/clip_editor.py` | Clip trim, split, merge, export presets |
| `src/editor_document.py` | Clip studio draft model (segments, words, captions, framing, B-roll) and server render |
| `src/workflows/` | Workflows (series, topic, recap, trailer): contracts, options/gate, units, outline, planners, solvers |
| `src/services/ai_edit_service.py` | Studio AI editing: Sonnet 5.5 plans typed operations, applied and validated here |
| `src/workers/ai_worker.py` | Light ARQ worker for AI edits (`weberslinkclip_ai` queue, own container) |
| `src/broll.py` | Pexels API B-roll integration |
| `src/caption_templates.py` | Caption template system |
| `src/config.py` | Environment variable configuration |
| `src/social/` | Social publishing providers (YouTube, TikTok, Instagram): OAuth, upload, metrics |
| `src/services/social_service.py` | Account connections, publish/schedule, metrics refresh, AI performance context |
| `src/repositories/social_repository.py` | `social_accounts`, `social_posts`, `social_post_metrics` SQL |
| `src/api/routes/social.py` | `/social/*` routes |

## API Endpoints (routes in `api/routes/`)

**Task lifecycle:**
- `POST /tasks/` — Create task, enqueue to worker (returns task_id); optional `workflow`, `workflow_options`, `instructions`
- `GET /tasks/workflows` — What the user can make on this platform (workflows flag, env gate, limits)
- `GET /feature-flags` — Feature flags evaluated for the caller and platform
- `GET /tasks/` — List user tasks
- `GET /tasks/{id}` — Get task with clips
- `GET /tasks/{id}/progress` — SSE real-time progress stream
- `POST /tasks/{id}/cancel` — Cancel processing
- `POST /tasks/{id}/resume` — Resume cancelled/errored task
- `DELETE /tasks/{id}` — Delete task

**Clip editing:**
- `PATCH /tasks/{id}/clips/{clip_id}` — Trim clip
- `POST /tasks/{id}/clips/{clip_id}/split` — Split at timestamp
- `POST /tasks/{id}/clips/merge` — Merge selected clips
- `PATCH /tasks/{id}/clips/{clip_id}/captions` — Update captions
- `GET /tasks/{id}/clips/{clip_id}/export?preset=tiktok` — Export with platform preset
- `GET /tasks/{id}/clips/zip` — Stream every existing clip as one ZIP, built on the fly (`clip_archive.py`); `GET .../clips/zip/preflight` runs the same checks first. One ZIP download per user at a time (Redis slot, 429)

**Media:**
- `GET /fonts`, `GET /transitions`, `GET /caption-templates`, `GET /broll/status`
- `POST /upload` — Upload video file
- `GET /clips/{filename}` — Serve generated clips

**Social publishing:**
- `GET /social/providers`, `GET /social/connections` — configured platforms and connected accounts
- `POST /social/connections/{provider}/authorize` + `/callback` — OAuth handshake (session auth only)
- `POST /social/captions` — draft a post pack for a clip with the configured LLM: caption, hashtags, suggested location, music suggestion, mentions (only from the optional `mentions` handles the caller sends) and a one-line reason it can travel. Nothing is published
- `POST /social/posts` — publish or schedule a clip; `GET /social/posts?task_id=` — list with metrics
- `POST /social/posts/{id}/cancel|retry|refresh-metrics`, `DELETE /social/posts/{id}`
- `GET /social/performance` — metrics by hook type / platform / clip length (also fed into the AI prompt)
- `GET /social/performance/timeseries?days=30` — daily new views from metrics snapshots (Analytics chart)
- `GET /social/media/{token}` — public token-gated clip stream for Instagram

Worker crons (`workers/tasks.py`): every minute `dispatch_scheduled_social_posts`, hourly `refresh_social_metrics`.
Post status flow: `scheduled → queued → publishing → published/failed/cancelled`.

**API keys (programmatic access):**
- `GET /api-keys/` — List the user's API keys (metadata only)
- `POST /api-keys/` — Create a key (plaintext `sk_...` returned exactly once)
- `DELETE /api-keys/{key_id}` — Revoke a key

API keys authenticate `/tasks/*`, `/fonts` and `/upload` directly via
`Authorization: Bearer sk_...` or `x-api-key`. Resolution lives in
`auth_headers.resolve_authenticated_user_id` (API key → DB lookup, else falls
back to the frontend's HMAC-signed session headers). Only the SHA-256 hash is
stored (`api_keys` table). The frontend manages keys at `/settings/api-keys`.

## Plans & billing

Plans: **Early bird** (free, derived at read time as plan id `early_bird`, never stored in
`users.plan`), **Starter** ($19/mo, internal id `pro`) and **Studio** ($49/mo, internal id `scale`).
Plans are month-to-month. Early bird applies when `SELF_HOST=false` and `EARLY_BIRD_ENABLED=true`
to any account without a paid plan: `EARLY_BIRD_MINUTE_LIMIT` (300) minutes of source video per
calendar month, 720p, YouTube up to `EARLY_BIRD_YOUTUBE_MAX_VIDEO_DURATION`, scheduling allowed.
Set `EARLY_BIRD_ENABLED=false` to end the offer; free accounts then must choose a paid plan.
The frontend mirrors these through `NEXT_PUBLIC_EARLY_BIRD_*` (see `frontend/src/lib/billing-plans.ts`).

- **Metered in minutes of source video** per month (`PRO_/SCALE_PLAN_MINUTE_LIMIT`,
  600/1500; Starter/Studio). `tasks.source_duration_seconds` is recorded at task creation (YouTube
  preflight, ffprobe for uploads) and `BillingService` sums started minutes.
  Yearly subscriptions still reset monthly (`_usage_window`).
- **Resolution:** Starter gets 720p via a final `cap_video_short_side` pass on generated
  clips and editor renders; Studio gets 1080p. Pro subscribers from before the
  change have `users.legacy_hd` (backfilled once) and keep 1080p until they cancel.
  Admins can grant or remove it per user in the `/admin` Users panel (searchable by
  email/name; `PATCH /api/admin/users/{id}/legacy-hd`).
  720p plans also *download* YouTube at 720p (`reduced_media_limits` → Apify quality /
  yt-dlp height cap), and their `processing_cache` key gets a `|q720` suffix so a 1080p
  request never reuses a 720p source. Full-quality keys are unchanged. The durable
  `youtube-cache/<video_id>` full file records its height (`full_height`, one file per
  height) and is reused only at or above the requested cap; sections always use the global cap.
- **Scheduling** social posts requires Studio (`can_schedule_posts`); publishing
  immediately works on Starter and early bird.
- **Annual** checkout: `interval: "year"` uses `STRIPE_PRO_/SCALE_ANNUAL_PRICE_ID`.

## Environment Variables

Required in `.env` (root) or `backend/.env`:

```bash
ASSEMBLY_AI_API_KEY=...              # Required: video transcription
TRANSCRIPTION_LANGUAGE=              # Optional: empty = auto-detect; e.g. es, de, en_us forces it
LLM=google-gla:gemini-3-flash-preview # Format: provider:model-name
GOOGLE_API_KEY=...                   # Or OPENAI_API_KEY / ANTHROPIC_API_KEY
OLLAMA_BASE_URL=http://localhost:11434/v1  # Optional for ollama:* models
OLLAMA_API_KEY=...                   # Optional; required for Ollama Cloud
RERANK_LLM=                          # Optional; model for the long-video candidate rerank (default: LLM)
YOUTUBE_DOWNLOAD_PROVIDER=yt_dlp     # yt_dlp | apify
YOUTUBE_PROXY_URL=                   # Optional residential proxy template; empty = off
YOUTUBE_POT_PROVIDER_URL=            # Optional bgutil base URL (http://bgutil:4416)
YOUTUBE_DOWNLOAD_MAX_BYTES=2000000000
YOUTUBE_MAX_HEIGHT=1080              # Hard cap; lower values are honored
APIFY_EXPENSIVE_FALLBACKS=false      # Skip high-cap Apify fallback actors

# Optional
PEXELS_API_KEY=...                   # B-roll stock footage
YOUTUBE_OAUTH_CLIENT_ID=...          # Social publishing: Google OAuth client (+ _SECRET)
TIKTOK_CLIENT_KEY=...                # Social publishing: TikTok app (+ TIKTOK_CLIENT_SECRET)
TIKTOK_APP_AUDITED=false             # true only after TikTok's audit; unaudited = private posts from private accounts
INSTAGRAM_APP_ID=...                 # Social publishing: Meta app with Instagram Login (+ _SECRET)
SOCIAL_PERFORMANCE_MIN_POSTS=3       # Measured posts before AI selection is personalized
SOCIAL_PUBLISHING_ACCESS=off         # Rollout gate: off (default) | admins (admins + allowlist) | all
SOCIAL_PUBLISHING_ALLOWED_EMAILS=    # Comma-separated beta emails when access=admins
WORKFLOWS_ACCESS=admins              # Series/topic/recap/trailer + instructions: off | admins | all (self-host: all)
WORKFLOWS_ALLOWED_EMAILS=            # Comma-separated beta emails when access=admins
WORKFLOWS_PUBLIC=                    # Workflows open to everyone while access=admins, e.g. trailer,topic
WORKFLOW_TOPIC_MAX_CLIPS=15          # Most clips a topic run returns
WORKFLOW_PLAN_TIMEOUT_SECONDS=1800   # Planning wall clock; past it the task fails with plan_failed
WORKFLOW_FULL_CONTEXT_MAX_WORDS=0    # Words read in one outline call; 0 = provider default
REDIS_HOST=localhost                 # Default: localhost
REDIS_PORT=6379                      # Default: 6379
QUEUED_TASK_TIMEOUT_SECONDS=180      # Fail-safe for stuck tasks
AI_EDIT_DAILY_LIMIT=150              # Studio AI edits per user per day (needs ANTHROPIC_API_KEY)
TEMP_DIR=/tmp                        # Temp file storage
DATABASE_URL=postgresql+asyncpg://...
BETTER_AUTH_SECRET=...               # Frontend auth secret
```

## Feature flags

`feature_flags` table (key, `web_enabled`, `ios_enabled`, `admins_bypass`, description, `updated_by`):
switch a feature per platform without a deploy, in the `/admin` "Feature Flags" panel
(`/api/admin/feature-flags/[key]`, written with Prisma). `backend/src/feature_flags.py` reads them with a
15-second in-process cache; a missing row or unreadable table falls back to `DEFAULT_FLAGS` (off, admins bypass).

- **Platform:** `x-weberslinkclip-client: ios` from a mobile client, forwarded by the web proxies
  (`backendTraceHeaders` in `server/backend-api.ts`); anything else, API keys included, is web.
- **On** = the platform column, or the caller is an admin and `admins_bypass` is set.
- `GET /feature-flags` (proxied at `/api/feature-flags`) returns the evaluated booleans for the caller.
- **`workflows`:** seeded off on web and mobile (admins bypass) until the mobile build with workflows is approved.
  It sits on top of `WORKFLOWS_ACCESS`: both must allow. Off hides workflows in `GET /tasks/workflows` for that
  platform and makes create/resume with a workflow 403 `WORKFLOW_NOT_AVAILABLE` before any charge.
- **`tiktok_publishing`:** seeded off on web and mobile, no admin bypass, until TikTok audits the app's Direct Post
  access (unaudited, TikTok rejects posts from public accounts). Off, `/social/providers` reports TikTok `configured: false,
  paused: true` (the web shows a short notice; mobile hides it) and connect/options/publish/retry return 503. Operators
  with their own audited TikTok app turn it on in /admin.
- Adding a flag: seed it in a migration (and `init.sql`), add its default to `DEFAULT_FLAGS`, check it with
  `feature_flags.is_enabled(db, key, platform=client_platform(request), user_id=...)`.

## Common Workflows

### Adding fonts/transitions

Drop `.ttf` files into `backend/fonts/` or `.mp4` files into `backend/transitions/`. They auto-appear via their respective `GET` endpoints.

### Social publishing & the performance loop

Users connect accounts at `/settings/social` (OAuth via `/api/social/connect/{provider}` →
`/api/social/callback/{provider}` → backend `/social/connections/{provider}/callback`).
Publishing runs in the ARQ worker (`publish_social_post`). Metrics are pulled back hourly into
`social_post_metrics` and summarized by `SocialService.build_performance_context()`, which
`TaskService.process_task` injects into `build_transcript_analysis_prompt(performance_context=...)`.
Personalized analyses skip the shared `processing_cache` analysis entry.

- **Pages:** `/settings/social` (accounts + every scheduled post) and `/analytics` (totals, daily
  views chart, top clips, breakdowns), both in the sidebar. Clips publish from the task page.
- **Rollout gate:** `SOCIAL_PUBLISHING_ACCESS` defaults to `off`. Social and Analytics stay out of
  the nav, command palette, and settings until it is `admins` or `all`. Outside the gate every
  `/social/*` route returns 403 except `GET /social/providers`, which reports `enabled: false` with
  all platforms unconfigured (clients hide publishing unless `enabled` is exactly true) and the
  disconnect routes (account deletion revokes tokens).
- **Mobile client:** `POST .../authorize` with `{"client": "ios"}` prefixes the OAuth state with `m.`; the
  web callback then redirects to `weberslinkclip://social-callback?provider&code&state` and the app
  completes `/callback` with its own session (the state stays bound to the starting user).
- **Platform approvals gate real users:** TikTok only allows sandbox target users until its audit,
  Instagram only app testers until Meta review, and YouTube uploads from an unaudited project stay
  private.

### Clip studio (editor)

Full-screen, classic NLE layout at `/tasks/{id}/edit` (`frontend/src/components/editor/`): clip picker in the header, viewer and
inspector on top, a full-width sequence timeline (`timeline.tsx`: V1 segments, B-roll, captions and audio tracks, in
edit time) below. Drafts are `EditDocument`s on the `clean.mp4` (source) timeline; `sequence`/`locate` map between
edit and source time. Preview and browser export draw through `lib/editor/render.ts`, the server export through
`render_document`. Generated clips' B-roll opens as editable items (`broll-panel.tsx`).

**AI editing:** the "AI edit" field under the viewer (`ai-prompt.tsx`, ⌘J) posts `POST .../editor/ai` → Redis → `ai_edit_job` on the
AI worker → Claude Sonnet 5.5 returns typed operations (`keep_ranges`, `remove_words`, `set`, `add_broll`, ...) →
`apply_plan` clamps and validates → the browser applies the result as one undoable change (never over edits made
meanwhile). Keep the output schema free of optional fields: the API rejects schemas whose grammar is too large.

### Workflows (series, topic clips, recap, trailer)

`tasks.workflow` picks what a task makes: `highlights` (default, unchanged), `series` (Part 1..N of one
story, adjacent parts share one exact cut), `topic` (every strong moment about `workflow_options.topic`),
`recap` (one clip of the main points) or `trailer` (one teaser that never reveals the payoff). Free-text
`instructions` steer any workflow. Code lives in `backend/src/workflows/`.

- **Units, not timestamps:** the transcript becomes numbered sentence units (clauses for trailers); the model
  returns unit ids and code converts them to word-exact seconds. A cached **source outline** (chapters, points,
  arcs, payoffs) is shared by every planner. Each planner is draft → validate → one repair → deterministic solve
  → critique → re-solve; budgets, contiguity and spoilers never depend on the model.
- **Locked render:** planned segments (`source_ranges`, `planned: True`) skip snapping, end extension and the
  cold-open teaser; multi-range clips use explicit output offsets everywhere. The plan is saved to
  `tasks.workflow_plan` before rendering; clips carry `workflow_role`, `part_number`, `workflow_meta`.
- **Invariant:** highlights without instructions is byte-identical (prompts, cache keys, job args, render path).
- **Fail loud, refund:** a workflow that can't deliver raises `WorkflowError` (`topic_not_found` with suggested
  topics, `no_story`, `trailer_unbuildable`, …); its clips are deleted so the minutes are refunded, and
  `error_code` drives the task page's next-step screen. Series/recap/trailer are all-or-nothing.
- **Gate:** `WORKFLOWS_ACCESS=off|admins|all` (default `admins`, plus verified `WORKFLOWS_ALLOWED_EMAILS`), checked on
  create and resume; self-hosters set `all`. The `workflows` feature flag (below) must also be on for the platform. Also `WORKFLOW_TOPIC_MAX_CLIPS`, `WORKFLOW_PLAN_TIMEOUT_SECONDS`, `WORKFLOW_FULL_CONTEXT_MAX_WORDS`.
- **Frontend:** contract in `lib/workflows.ts`; results in `components/app/series-view.tsx`,
  `hero-clip-view.tsx` and `workflow-failure.tsx`.

### Modifying AI clip selection

Edit `backend/src/ai.py`: `simplified_system_prompt` controls selection criteria, `TranscriptSegment` defines the output model, `get_most_relevant_parts_by_transcript()` runs analysis with validation.

### Video processing constraints

- Output: 9:16 vertical format, H.264, even pixel dimensions (`round_to_even()`)
- Subtitles positioned at 75% down the frame
- Virality scoring: `hook_score`, `engagement_score`, `value_score`, `shareability_score` (0-25 each, summed to `virality_score` 0-100)
- Each segment gets an AI-written `hook_title` (3-9 words) burned into the top safe area for the first ~4s (`build_hook_title_ass` in `video_utils.py`), persisted on `generated_clips.hook_title`
- Static talking-head crops get a slow ~5% Ken Burns punch-in (`kenburns_zoom_fragment`); tracked pans and split screens keep their own motion

## YouTube Downloads

`YOUTUBE_DOWNLOAD_PROVIDER` accepts `yt_dlp` (free default) or `apify`.
Apify requires `APIFY_API_TOKEN` and explicit worker configuration. Each provider
falls back to the other when available. Paid worker identities belong in private
environment configuration. See `backend/README.md` for setup.

`YOUTUBE_PROXY_URL` (empty by default) puts yt-dlp through a residential proxy
first: sticky `{session}` per job, IPv4, optional bgutil PO tokens, audio first,
then only the padded clip ranges at or below 1080p. Cached audio and sections
are reused by later edits. `APIFY_EXPENSIVE_FALLBACKS` defaults to off so
high-cap fallback actors are not called.

