# Deploying WeberslinkClip on a Hostinger VPS

This puts the app at **https://clip.weberslink.org**, with its API at **https://clip-api.weberslink.org**. HTTPS certificates are issued and renewed automatically.

Hostinger's regular web or Node hosting cannot run this app. It needs Docker, ffmpeg, PostgreSQL, Redis and background workers, so you need a **VPS**.

## 1. Get a VPS

In hPanel, choose **VPS** and a plan with at least **2 vCPU, 8 GB RAM and 100 GB disk** (KVM 2). Video processing is heavy, so KVM 4 (4 vCPU, 16 GB) is more comfortable once several people use it. When asked for an operating system, pick **Ubuntu 24.04 with Docker**. Note the server's IP address.

## 2. Point two DNS names at the server

Where `weberslink.org` DNS is managed (hPanel → Domains → DNS / Nameservers → DNS records), add two **A records** that both point to the VPS IP:

| Type | Name | Points to |
|---|---|---|
| A | `clip` | your VPS IP |
| A | `clip-api` | your VPS IP |

Wait a few minutes. Check with `nslookup clip.weberslink.org`.

## 3. Open the firewall

Allow ports **22** (SSH), **80** and **443** only. In hPanel this is VPS → Security → Firewall. The database and Redis are not exposed outside the server.

## 4. Install the app

Connect with SSH, then:

```bash
git clone https://github.com/AdilIshtiaq/weberslink_clipping.git
cd weberslink_clipping
git checkout claude/gracious-cerf-o7nw1d
cp deploy/env.production.example .env
nano .env
```

In `.env`, fill in the secrets. Generate each of `BETTER_AUTH_SECRET`, `BACKEND_AUTH_SECRET` and `APP_SETTINGS_ENCRYPTION_KEY` with:

```bash
openssl rand -hex 32
```

You also need an AssemblyAI key, an AI model key (Google by default) and AWS SES credentials (accounts cannot be verified without email). Stripe is only needed once you sell Starter or Studio.

## 5. Start it

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

The first build takes several minutes. Follow it with:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

When it settles, open https://clip.weberslink.org, create an account and clip a short video.

Check the API at https://clip-api.weberslink.org/docs.

## 6. Make yourself an admin

After creating your account:

```bash
docker exec -it weberslinkclip-postgres psql -U weberslinkclip -d weberslinkclip \
  -c "UPDATE users SET is_admin = true WHERE email = 'you@example.com';"
```

The admin panel is at `/admin`.

## 7. Connect the optional services

- **Stripe:** add a webhook endpoint `https://clip.weberslink.org/api/billing/webhook`, and put its signing secret in `STRIPE_WEBHOOK_SECRET`. Create Starter ($19/month) and Studio ($49/month) prices and put their IDs in `STRIPE_PRO_PRICE_ID` and `STRIPE_SCALE_PRICE_ID`.
- **YouTube, TikTok, Instagram publishing:** set each platform's redirect URL to `https://clip.weberslink.org/api/social/callback/<provider>` where the provider is `youtube`, `tiktok` or `instagram`.
- After changing `.env`, apply it with the same `up -d --build` command.

## Updating

```bash
cd weberslink_clipping
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Backups

Accounts and clip records live in PostgreSQL. Back it up regularly:

```bash
docker exec weberslinkclip-postgres pg_dump -U weberslinkclip weberslinkclip | gzip > backup-$(date +%F).sql.gz
```

Uploaded videos and rendered clips are in the Docker volumes `uploads` and `clips`. Hostinger's VPS snapshot or backup feature covers them.

## Troubleshooting

- **The page loads but sign-in fails:** `NEXT_PUBLIC_APP_URL` and `BETTER_AUTH_URL` must both be `https://clip.weberslink.org`. Changing them needs a rebuild.
- **Uploads fail:** `NEXT_PUBLIC_API_URL` must be `https://clip-api.weberslink.org` and `CORS_ORIGINS` must be `https://clip.weberslink.org`.
- **No certificate:** the DNS records must resolve to the VPS before the first start. Check `docker logs weberslinkclip-caddy`.
