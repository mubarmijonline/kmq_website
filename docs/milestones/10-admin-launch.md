# 10 — Admin launch

**Goal.** The admin is live on the production database, and the public site is
provably unchanged by it.

**Includes**
- `pytest` coverage for: auth gating on every admin route, CSRF rejection,
  role separation, the overlay's fallback when the pool is down, and the 42
  public URLs before and after seeding.
- Migration applied to `kmq_dev` first, then to prod `kmq`.
- A persistent `SECRET_KEY` in the deployment environment.
- Owner account seeded on prod, password handed over once.
- nginx: `/admin` gets the same TLS and headers as the rest; no separate
  vhost.

**Acceptance.** The whole PRD "how done is verified" list passes, items 1–8 for
the public site and 9–15 for the admin. `pytest` is green. All 42 public URLs
return 200 against the migrated production database. Signing in on prod,
changing a string, and seeing it on the public page completes end to end.

**Status.** Not started.
