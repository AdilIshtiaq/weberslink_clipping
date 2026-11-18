# Deploying WeberslinkClip on a server (Oracle Cloud or any VPS)

This puts the app at **https://clip.weberslink.org**, with its API at **https://clip-api.weberslink.org**. HTTPS certificates are issued and renewed automatically.

The app needs Docker, ffmpeg, PostgreSQL, Redis and background workers, so it needs a server of its own. Shared web hosting, Node hosting and GitHub cannot run it. The steps below use **Oracle Cloud**; any Ubuntu VPS works the same way from step 4 on.

## 1. Create the server (Oracle Cloud)

In the Oracle Cloud console choose **Compute → Instances → Create instance**:

- **Image:** Ubuntu 24.04.
- **Shape:** `VM.Standard.A1.Flex` (Ampere ARM), **4 OCPU and 24 GB RAM**. That fits in Oracle's Always Free allowance and is plenty for video work. If the console says "Out of capacity", try another availability domain or retry later.
- Do **not** use the tiny `VM.Standard.E2.1.Micro` shape (1 GB RAM). It cannot process video.
- **Boot volume:** 100 GB or more.
- Add your SSH public key, then create the instance and note its **public IP**.
- Make the IP permanent: open the instance, then Attached VNICs → IPv4 addresses → edit, and choose a **Reserved public IP**. Otherwise it can change when the instance restarts.

## 2. Open the network, in two places

Oracle blocks web traffic twice. You need both.

1. **Oracle's network rules.** Go to Networking → Virtual cloud networks → your VCN → Security Lists → Default → **Add ingress rules**. Add two rules with source `0.0.0.0/0`, protocol TCP, and destination ports `80` and `443`.
2. **The server's own firewall.** On the server (after step 4 connects you), run:

```bash
sudo iptables -I INPUT 5 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 5 -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 5 -p udp --dport 443 -j ACCEPT
sudo apt-get install -y iptables-persistent && sudo netfilter-persistent save
```

## 3. Point two DNS names at the server

Where `weberslink.org` DNS is managed, add two **A records** that both point to the server's public IP:

| Type | Name | Points to |
|---|---|---|
| A | `clip` | your server IP |
| A | `clip-api` | your server IP |

Wait a few minutes. Check with `nslookup clip.weberslink.org`.

## 4. Install the app

Connect with SSH (`ssh ubuntu@YOUR_SERVER_IP`) and install Docker:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
```

Then get the app:

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

**On the Oracle ARM shape**, also set these two lines in `.env` (the template has them commented out):

```env
BACKEND_PLATFORM=linux/arm64
BACKEND_CPU_ONLY=true
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

Uploaded videos and rendered clips are in the Docker volumes `uploads` and `clips`. Oracle boot volume backups (Block Storage → Boot Volumes → Backups) cover them.

## Troubleshooting

- **The page loads but sign-in fails:** `NEXT_PUBLIC_APP_URL` and `BETTER_AUTH_URL` must both be `https://clip.weberslink.org`. Changing them needs a rebuild.
- **Uploads fail:** `NEXT_PUBLIC_API_URL` must be `https://clip-api.weberslink.org` and `CORS_ORIGINS` must be `https://clip.weberslink.org`.
- **No certificate:** the DNS records must resolve to the VPS before the first start. Check `docker logs weberslinkclip-caddy`.
