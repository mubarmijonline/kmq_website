-- 004 — The branch order the client corrected.
--
--   psql -v ON_ERROR_STOP=1 -d kmq -f db/migrations/004_branch_order.sql
--
-- The client's review said two things about the branch list: Al Rimal is the
-- main branch and belongs first, and the two Dammam branches were the wrong
-- way round. app/content.py and db/schema.sql both say so now, but schema.sql
-- only seeds a database that does not exist yet — and once the content
-- overlay is live the branch cards are ordered by branch.sort_order, not by
-- the copy file. A deployed database therefore has to be told.
--
-- In two passes, because `branch_sort_order_key` is a plain unique index and
-- is therefore checked row by row: rewriting 1..6 in place fails the moment a
-- row takes a position another row still holds. Parking every branch above
-- the range first leaves all six targets free.
--
-- Safe to re-run, and safe on a fresh database seeded from schema.sql, where
-- it ends where it started. It does overwrite an order set by hand, which is
-- the point: this is the client's order, and it is the one being restored.

BEGIN;

UPDATE branch SET sort_order = sort_order + 100 WHERE sort_order < 100;

UPDATE branch SET sort_order = v.position
  FROM (VALUES
        ('al-rimal',            1),
        ('al-hamra',            2),
        ('tuwaiq',              3),
        ('jeddah-madinah-road', 4),
        ('dammam-al-manar',     5),
        ('dammam-imam',         6)
       ) AS v (id, position)
 WHERE branch.id = v.id;

-- A branch added since this was written keeps its order relative to the rest,
-- after the six the client ranked, rather than staying parked at 100-odd.
UPDATE branch SET sort_order = ranked.position
  FROM (SELECT id, 6 + row_number() OVER (ORDER BY sort_order) AS position
          FROM branch WHERE sort_order >= 100) AS ranked
 WHERE branch.id = ranked.id;

COMMIT;
