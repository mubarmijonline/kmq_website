-- 002 — Admin and the editable content store.
--
-- Applies on top of db/schema.sql. Idempotent at the DDL level (IF NOT EXISTS
-- throughout) so re-running it against a partially migrated database is safe.
--
--   psql -v ON_ERROR_STOP=1 -d kmq -f db/migrations/002_admin.sql
--
-- Nothing here is required for the public site to render. That is deliberate:
-- app/content.py keeps the shipped copy as its fallback, so a database that is
-- missing every one of these tables still serves all 42 pages.

BEGIN;

-- --------------------------------------------------------------------------
-- Roles and accounts
-- --------------------------------------------------------------------------
-- A table, not an is_admin boolean. Two roles today; a third ("viewer", say)
-- is an INSERT rather than a migration and a scattering of new conditionals.

CREATE TABLE IF NOT EXISTS admin_role (
    code  text PRIMARY KEY,
    label text NOT NULL,
    rank  smallint NOT NULL          -- higher outranks lower
);

INSERT INTO admin_role (code, label, rank) VALUES
    ('editor', 'Editor — content and leads', 10),
    ('owner',  'Owner — everything',         20)
ON CONFLICT (code) DO NOTHING;


CREATE TABLE IF NOT EXISTS admin_user (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email         text NOT NULL UNIQUE,
    display_name  text NOT NULL,
    -- werkzeug.security.generate_password_hash output. Never a password.
    password_hash text NOT NULL,
    role          text NOT NULL REFERENCES admin_role (code),
    -- Set on a seeded or reset account. Every admin page except the change
    -- form and logout refuses to render while it is true.
    must_change_password boolean NOT NULL DEFAULT true,
    -- Disabled, never deleted: audit rows must keep pointing at a real person.
    is_disabled   boolean NOT NULL DEFAULT false,
    created_at    timestamptz NOT NULL DEFAULT now(),
    last_login_at timestamptz,
    -- Bumping this invalidates the account's existing session cookies without
    -- a server-side session table.
    session_epoch integer NOT NULL DEFAULT 0,

    CONSTRAINT admin_user_email_shape CHECK (email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'),
    CONSTRAINT admin_user_name_present CHECK (length(btrim(display_name)) > 0)
);

CREATE INDEX IF NOT EXISTS admin_user_role_idx ON admin_user (role);


-- Failed sign-in attempts, keyed on the same salted IP hash the lead form
-- throttle uses. Rows are only ever counted over a short window and swept.
CREATE TABLE IF NOT EXISTS admin_login_attempt (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ip_hash    char(64) NOT NULL,
    email      text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS admin_login_attempt_idx
    ON admin_login_attempt (ip_hash, created_at DESC);


-- --------------------------------------------------------------------------
-- Audit
-- --------------------------------------------------------------------------
-- One row per mutating admin action. before_value/after_value are jsonb so a
-- copy string, a package price and a warranty status can all be recorded the
-- same way. actor_id is nullable only so that ON DELETE cannot orphan a row —
-- accounts are disabled rather than deleted, so in practice it is always set.

CREATE TABLE IF NOT EXISTS audit_log (
    id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    at           timestamptz NOT NULL DEFAULT now(),
    actor_id     bigint REFERENCES admin_user (id) ON DELETE SET NULL,
    actor_email  text NOT NULL,      -- denormalised: survives a rename
    action       text NOT NULL,      -- create | update | delete | login | ...
    entity       text NOT NULL,      -- copy | service | package | warranty | ...
    entity_id    text,               -- slug, key, or numeric id as text
    before_value jsonb,
    after_value  jsonb
);

CREATE INDEX IF NOT EXISTS audit_log_at_idx     ON audit_log (at DESC);
CREATE INDEX IF NOT EXISTS audit_log_entity_idx ON audit_log (entity, entity_id, at DESC);


-- --------------------------------------------------------------------------
-- Content: flat strings
-- --------------------------------------------------------------------------
-- The couple of hundred scalar strings in app/content.py's AR and EN dicts —
-- contact_title, hero_sub and the rest. A row here overrides the shipped
-- value; no row means the shipped value stands. Deleting a row is therefore
-- "revert to what we shipped", which is the only rollback this design has.

CREATE TABLE IF NOT EXISTS copy_string (
    locale     text NOT NULL,
    key        text NOT NULL,
    value      text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by bigint REFERENCES admin_user (id) ON DELETE SET NULL,

    PRIMARY KEY (locale, key),
    CONSTRAINT copy_string_locale CHECK (locale IN ('ar', 'en'))
);


-- --------------------------------------------------------------------------
-- Content: collections
-- --------------------------------------------------------------------------
-- Every list in app/content.py's locale dicts: services, packages, posts,
-- branches, the FAQ, the nav, the trust strip, the film spec table, and the
-- rest. Twenty of them at the time of writing.
--
-- One table with a jsonb payload rather than twenty typed tables and twenty
-- i18n siblings. The shapes are already fixed in Python by _svc/_pkg/_post and
-- friends, the application is the only writer, and the templates consume these
-- as lists of dicts — so the document *is* the shape. Validation lives in
-- app/store.py where the shape is declared, not in forty tables of columns.
--
-- `kind` is the content.py key the list lives under ("services", "faq", …).
-- The constraint checks its shape rather than enumerating the twenty names:
-- an enumeration here would mean a migration every time the copy grows a new
-- list, and the real guard is store.KINDS, which is derived from the dicts.
--
-- `slug` is the record's natural id where it has one (slug, id) and its
-- ordinal where it does not — the FAQ and the trust strip are ordered
-- editorial lists, not keyed ones. Scalar lists (not_covered, conditions,
-- tags, war_rows) store {"value": "…"}.
--
-- Records that carry real constraints stay relational: branch and warranty
-- have E.164 checks, a status foreign key and the normalisation contract, and
-- those are worth more than uniformity.

CREATE TABLE IF NOT EXISTS content_entry (
    kind       text NOT NULL,
    slug       text NOT NULL,
    locale     text NOT NULL,
    sort_order smallint NOT NULL DEFAULT 0,
    is_published boolean NOT NULL DEFAULT true,
    data       jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by bigint REFERENCES admin_user (id) ON DELETE SET NULL,

    PRIMARY KEY (kind, slug, locale),
    CONSTRAINT content_entry_locale CHECK (locale IN ('ar', 'en')),
    CONSTRAINT content_entry_kind CHECK (kind ~ '^[a-z][a-z0-9_]*$'),
    CONSTRAINT content_entry_slug CHECK (length(btrim(slug)) > 0),
    CONSTRAINT content_entry_data_object CHECK (jsonb_typeof(data) = 'object')
);

CREATE INDEX IF NOT EXISTS content_entry_kind_idx
    ON content_entry (kind, locale, sort_order);


-- --------------------------------------------------------------------------
-- Settings
-- --------------------------------------------------------------------------
-- The three deployment flags that become editable: KMQ_WHATSAPP,
-- KMQ_SHOW_PRICES, KMQ_SHOW_BEFORE_AFTER. An environment variable, where set,
-- still wins — see app/store.py:setting. That ordering is deliberate: a
-- deploy must be able to pin a value that no admin can override.

CREATE TABLE IF NOT EXISTS site_setting (
    key        text PRIMARY KEY,
    value      text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by bigint REFERENCES admin_user (id) ON DELETE SET NULL
);


-- --------------------------------------------------------------------------
-- Cache invalidation
-- --------------------------------------------------------------------------
-- Two gunicorn workers each hold their own overlay. A worker re-reads this
-- counter at most once every few seconds and rebuilds when it has moved, so an
-- edit made in one worker reaches the other without a restart. One row, always.

CREATE TABLE IF NOT EXISTS content_version (
    id      boolean PRIMARY KEY DEFAULT true,
    version bigint  NOT NULL DEFAULT 1,
    bumped_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT content_version_single_row CHECK (id)
);

INSERT INTO content_version (id, version) VALUES (true, 1)
ON CONFLICT (id) DO NOTHING;


-- --------------------------------------------------------------------------
-- Leads gain a handled state
-- --------------------------------------------------------------------------
-- The public insert path does not touch these; only the admin inbox does.

ALTER TABLE lead ADD COLUMN IF NOT EXISTS handled_at timestamptz;
ALTER TABLE lead ADD COLUMN IF NOT EXISTS handled_by bigint REFERENCES admin_user (id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS lead_unhandled_idx
    ON lead (created_at DESC) WHERE handled_at IS NULL;

COMMIT;
