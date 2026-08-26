# 05 — Launch

**Goal.** The site answers on its subdomain over HTTPS and on `ExternalIP:Port`.

## Done (2026-08-15)

Deployed with the `deploy-flask-site` skill.

| Thing | Value |
|---|---|
| FQDN | `kmq-ksa.com` (was `kmq.mubarmijonline.com` until 2026-08-26) |
| Public HTTPS port (origin) | `4023` |
| gunicorn upstream | `127.0.0.1:4024` |
| External IP | `34.45.108.75` |
| Certificate | `/etc/nginx/certs/elamal.pem` — SAN `*.mubarmijonline.com`, valid to 2037-02-16 |
| Service account | `omar_ashraf:www-data` |
| systemd unit | `kmq.service` — active, enabled |
| Database | PostgreSQL `kmq`, owned by `omar_ashraf`, schema applied, 6 branches seeded |

Verified on the origin:

- Routes return 200 through nginx, not just the dev server; `/` 302s to `/ar/`.
- Requests carrying `Host: kmq-ksa.com` on `:443` resolve to this
  vhost, so the site is ready for proxied traffic the moment DNS exists.
- The wildcard certificate is served for the name.
- HTTP/2 negotiated on `:4023`; `gzip_static` serves the pre-compressed bundle
  with `cache-control: public, immutable`.
- `SECRET_KEY` and `IP_HASH_SALT` generated per-deployment; `.env` is mode 600,
  owned by the service account, git-ignored.

## Not done

**Superseded 2026-08-26.** The site now answers on its own domain, `kmq-ksa.com`, with a Let's Encrypt certificate renewed over HTTP-01 against `/var/www/acme`. The `kmq.mubarmijonline.com` record was deleted rather than redirected, which was the client's decision; the sentence below described the state before that name ever existed and is kept because the reasoning still applies to the new one.

**The DNS record does not exist.** `kmq.mubarmijonline.com` does not resolve.

`scripts/cf_dns.sh` needs a Cloudflare API token and there is none on this
machine — the path the global machine notes give (`~/.claude/.cf_token`) is
absent, and no `CF_*` variable is set. The token is scoped to DNS records only.

Once supplied:

```bash
CF_TOKEN=<token> ~/.claude/skills/deploy-flask-site/scripts/cf_dns.sh \
    --name kmq --domain mubarmijonline.com --comment kmq_website
```

**Port 4023 may need opening in the cloud VPC firewall.** It answers on the
box, but VPC rules are not visible from inside the host. If
`https://34.45.108.75:4023/` times out from outside while the subdomain works,
that is the firewall rule and not nginx — a console change, outside the DNS
token's scope.

## Outstanding, not blocking

`KMQ_WHATSAPP` is unset, so every WhatsApp call to action routes to
`/contact-us`. Setting it in `.env` and restarting the unit switches them all
over; no code change. See the README.

**Status.** Deployed and serving on the origin. Public subdomain pending the
Cloudflare token.
