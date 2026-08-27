-- 003 — The branch record becomes editable, and bilingual.
--
--   psql -v ON_ERROR_STOP=1 -d kmq -f db/migrations/003_branch_editable.sql
--
-- Branches were the one collection the admin could not store as a document:
-- they carry an E.164 check on two columns, an HTTPS check on a third, and a
-- foreign key from every lead and every warranty. Those constraints are the
-- reason the table exists, so the branch editor writes the table and the
-- content overlay reads the branches list back out of it — rather than the
-- table and a content_entry document both claiming to be the branch.
--
-- What was missing for that: the display strings the templates render. The
-- table held one `hours` column and no Arabic city or short name, because
-- nothing read it yet. It now holds both languages of each.
--
-- Idempotent: safe to re-run.

BEGIN;

-- One `hours` column cannot say "9 ص - 10 م" and "9 AM - 10 PM" at once.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
                WHERE table_name = 'branch' AND column_name = 'hours')
       AND NOT EXISTS (SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'branch' AND column_name = 'hours_ar')
    THEN
        ALTER TABLE branch RENAME COLUMN hours TO hours_ar;
    END IF;
END
$$;

ALTER TABLE branch ADD COLUMN IF NOT EXISTS hours_ar text;
ALTER TABLE branch ADD COLUMN IF NOT EXISTS hours_en text;

-- `city` stays the Latin grouping key ("Riyadh"), which is also what the card
-- prints in upper case. `city_ar` is the name a visitor reading Arabic sees.
ALTER TABLE branch ADD COLUMN IF NOT EXISTS city_ar  text;

-- The short label the footer and the contact page use, where the full branch
-- name does not fit.
ALTER TABLE branch ADD COLUMN IF NOT EXISTS short_ar text;
ALTER TABLE branch ADD COLUMN IF NOT EXISTS short_en text;

-- Unpublishing a branch hides it from the site without deleting a row that
-- leads and warranties point at.
ALTER TABLE branch ADD COLUMN IF NOT EXISTS is_published boolean NOT NULL DEFAULT true;

ALTER TABLE branch ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE branch ADD COLUMN IF NOT EXISTS updated_by bigint REFERENCES admin_user (id) ON DELETE SET NULL;

-- The display strings are filled from app/content.py by `flask seed-content`,
-- which writes only into columns that are still null. Deliberately not
-- backfilled here: the Arabic belongs in the copy file, next to the rest of
-- the copy, not scattered into a migration.

COMMIT;
