-- Constraint checks for db/schema.sql.
--
-- Run against a database that has had schema.sql applied. Every block asserts
-- that a value the application must never write is actually rejected, and
-- that the values it does write are accepted. Ends with a single line.
--
--   psql -v ON_ERROR_STOP=1 -d kmq_schema_check -f db/schema.sql -f db/test_schema.sql

\set ON_ERROR_STOP on
-- NOTICE, not WARNING: the final "ALL SCHEMA CHECKS PASSED" is a NOTICE, and
-- a run that passes silently is indistinguishable from one that never ran.
SET client_min_messages TO NOTICE;

BEGIN;

DO $$
DECLARE
    n integer;
BEGIN

-- 1. The six branches seed. ------------------------------------------------
SELECT count(*) INTO n FROM branch;
IF n <> 6 THEN
    RAISE EXCEPTION 'CHECK 1 FAILED: expected 6 seeded branches, found %', n;
END IF;

-- 2. No branch ships with an invented phone number. -------------------------
SELECT count(*) INTO n FROM branch WHERE phone_e164 IS NOT NULL OR whatsapp_e164 IS NOT NULL;
IF n <> 0 THEN
    RAISE EXCEPTION 'CHECK 2 FAILED: % branch(es) carry a phone number the client has not supplied', n;
END IF;

-- 3. No branch ships with invented hours or a map URL. -----------------------
SELECT count(*) INTO n FROM branch WHERE hours IS NOT NULL OR map_url IS NOT NULL;
IF n <> 0 THEN
    RAISE EXCEPTION 'CHECK 3 FAILED: % branch(es) carry unconfirmed hours or map URL', n;
END IF;

-- 4. A malformed branch phone is rejected. -----------------------------------
BEGIN
    UPDATE branch SET phone_e164 = '0550000001' WHERE id = 'al-hamra';
    RAISE EXCEPTION 'CHECK 4 FAILED: a non-E.164 branch phone was accepted';
EXCEPTION WHEN check_violation THEN NULL;
END;

-- 5. A well-formed branch phone is accepted. ---------------------------------
BEGIN
    UPDATE branch SET phone_e164 = '+966550000001' WHERE id = 'al-hamra';
    UPDATE branch SET phone_e164 = NULL WHERE id = 'al-hamra';
EXCEPTION WHEN check_violation THEN
    RAISE EXCEPTION 'CHECK 5 FAILED: a valid E.164 branch phone was rejected';
END;

-- 6. A non-HTTPS map URL is rejected. ----------------------------------------
BEGIN
    UPDATE branch SET map_url = 'http://maps.example/x' WHERE id = 'al-hamra';
    RAISE EXCEPTION 'CHECK 6 FAILED: a non-HTTPS map URL was accepted';
EXCEPTION WHEN check_violation THEN NULL;
END;

-- 7. The three warranty statuses exist. --------------------------------------
SELECT count(*) INTO n FROM warranty_status WHERE code IN ('active', 'expired', 'void');
IF n <> 3 THEN
    RAISE EXCEPTION 'CHECK 7 FAILED: expected 3 warranty statuses, found %', n;
END IF;

-- 8. A well-formed warranty inserts. -----------------------------------------
INSERT INTO warranty (warranty_number, plate_number, invoice_number, service_type,
                      branch_id, install_date, activation_date, expiry_date, status)
VALUES ('KMQ-TEST-0001', 'ABJ1234', 'INV9001', 'PPF Gloss (Full)',
        'al-hamra', DATE '2026-03-10', DATE '2026-03-14', DATE '2036-03-14', 'active');

-- 9. An un-normalised plate number is rejected. ------------------------------
BEGIN
    INSERT INTO warranty (warranty_number, plate_number, service_type, branch_id,
                          install_date, activation_date, expiry_date, status)
    VALUES ('KMQ-TEST-0002', 'ABJ 1234', 'PPF Gloss (Full)', 'al-hamra',
            DATE '2026-03-10', DATE '2026-03-14', DATE '2036-03-14', 'active');
    RAISE EXCEPTION 'CHECK 9 FAILED: a plate number with a space was accepted';
EXCEPTION WHEN check_violation THEN NULL;
END;

-- 10. A lower-case plate number is rejected. ---------------------------------
BEGIN
    INSERT INTO warranty (warranty_number, plate_number, service_type, branch_id,
                          install_date, activation_date, expiry_date, status)
    VALUES ('KMQ-TEST-0003', 'abj1234', 'PPF Gloss (Full)', 'al-hamra',
            DATE '2026-03-10', DATE '2026-03-14', DATE '2036-03-14', 'active');
    RAISE EXCEPTION 'CHECK 10 FAILED: a lower-case plate number was accepted';
EXCEPTION WHEN check_violation THEN NULL;
END;

-- 11. Activation before installation is rejected. ----------------------------
BEGIN
    INSERT INTO warranty (warranty_number, plate_number, service_type, branch_id,
                          install_date, activation_date, expiry_date, status)
    VALUES ('KMQ-TEST-0004', 'XYZ9999', 'PPF Gloss (Full)', 'al-hamra',
            DATE '2026-03-14', DATE '2026-03-10', DATE '2036-03-14', 'active');
    RAISE EXCEPTION 'CHECK 11 FAILED: activation before installation was accepted';
EXCEPTION WHEN check_violation THEN NULL;
END;

-- 12. Expiry on or before activation is rejected. ----------------------------
BEGIN
    INSERT INTO warranty (warranty_number, plate_number, service_type, branch_id,
                          install_date, activation_date, expiry_date, status)
    VALUES ('KMQ-TEST-0005', 'XYZ8888', 'PPF Gloss (Full)', 'al-hamra',
            DATE '2026-03-10', DATE '2026-03-14', DATE '2026-03-14', 'active');
    RAISE EXCEPTION 'CHECK 12 FAILED: expiry equal to activation was accepted';
EXCEPTION WHEN check_violation THEN NULL;
END;

-- 13. An unknown status is rejected. -----------------------------------------
BEGIN
    INSERT INTO warranty (warranty_number, plate_number, service_type, branch_id,
                          install_date, activation_date, expiry_date, status)
    VALUES ('KMQ-TEST-0006', 'XYZ7777', 'PPF Gloss (Full)', 'al-hamra',
            DATE '2026-03-10', DATE '2026-03-14', DATE '2036-03-14', 'pending');
    RAISE EXCEPTION 'CHECK 13 FAILED: an unknown warranty status was accepted';
EXCEPTION WHEN foreign_key_violation THEN NULL;
END;

-- 14. A duplicate warranty number is rejected. -------------------------------
BEGIN
    INSERT INTO warranty (warranty_number, plate_number, service_type, branch_id,
                          install_date, activation_date, expiry_date, status)
    VALUES ('KMQ-TEST-0001', 'XYZ6666', 'PPF Gloss (Full)', 'al-hamra',
            DATE '2026-03-10', DATE '2026-03-14', DATE '2036-03-14', 'active');
    RAISE EXCEPTION 'CHECK 14 FAILED: a duplicate warranty number was accepted';
EXCEPTION WHEN unique_violation THEN NULL;
END;

-- 15. The lookup finds the seeded warranty by plate and by invoice. -----------
SELECT count(*) INTO n FROM warranty
 WHERE plate_number = 'ABJ1234' OR invoice_number = 'ABJ1234';
IF n <> 1 THEN
    RAISE EXCEPTION 'CHECK 15 FAILED: plate lookup returned % rows', n;
END IF;

SELECT count(*) INTO n FROM warranty
 WHERE plate_number = 'INV9001' OR invoice_number = 'INV9001';
IF n <> 1 THEN
    RAISE EXCEPTION 'CHECK 15 FAILED: invoice lookup returned % rows', n;
END IF;

-- 16. A well-formed lead inserts. --------------------------------------------
INSERT INTO lead (full_name, phone, service, car_model, branch_id, timing,
                  locale, ip_hash)
VALUES ('اختبار', '+966512345678', 'ppf-gloss', 'Porsche 911', 'al-hamra',
        'this-week', 'ar', repeat('a', 64));

-- 17. A non-Saudi phone is rejected. -----------------------------------------
BEGIN
    INSERT INTO lead (full_name, phone, service, car_model, branch_id, timing,
                      locale, ip_hash)
    VALUES ('Test', '+447700900000', 'ppf-gloss', 'Porsche 911', 'al-hamra',
            'this-week', 'en', repeat('b', 64));
    RAISE EXCEPTION 'CHECK 17 FAILED: a non-Saudi phone number was accepted';
EXCEPTION WHEN check_violation THEN NULL;
END;

-- 18. A local-format phone is rejected — the app must normalise first. -------
BEGIN
    INSERT INTO lead (full_name, phone, service, car_model, branch_id, timing,
                      locale, ip_hash)
    VALUES ('Test', '0512345678', 'ppf-gloss', 'Porsche 911', 'al-hamra',
            'this-week', 'en', repeat('c', 64));
    RAISE EXCEPTION 'CHECK 18 FAILED: an un-normalised phone number was accepted';
EXCEPTION WHEN check_violation THEN NULL;
END;

-- 19. An unknown service is rejected. ----------------------------------------
BEGIN
    INSERT INTO lead (full_name, phone, service, car_model, branch_id, timing,
                      locale, ip_hash)
    VALUES ('Test', '+966512345678', 'ppf-matt', 'Porsche 911', 'al-hamra',
            'this-week', 'en', repeat('d', 64));
    RAISE EXCEPTION 'CHECK 19 FAILED: an unknown service was accepted';
EXCEPTION WHEN check_violation THEN NULL;
END;

-- 20. An unknown branch is rejected. -----------------------------------------
BEGIN
    INSERT INTO lead (full_name, phone, service, car_model, branch_id, timing,
                      locale, ip_hash)
    VALUES ('Test', '+966512345678', 'ppf-gloss', 'Porsche 911', 'makkah',
            'this-week', 'en', repeat('e', 64));
    RAISE EXCEPTION 'CHECK 20 FAILED: an unknown branch was accepted';
EXCEPTION WHEN foreign_key_violation THEN NULL;
END;

-- 21. An unknown locale is rejected. -----------------------------------------
BEGIN
    INSERT INTO lead (full_name, phone, service, car_model, branch_id, timing,
                      locale, ip_hash)
    VALUES ('Test', '+966512345678', 'ppf-gloss', 'Porsche 911', 'al-hamra',
            'this-week', 'fr', repeat('f', 64));
    RAISE EXCEPTION 'CHECK 21 FAILED: an unknown locale was accepted';
EXCEPTION WHEN check_violation THEN NULL;
END;

-- 22. A blank name is rejected. ----------------------------------------------
BEGIN
    INSERT INTO lead (full_name, phone, service, car_model, branch_id, timing,
                      locale, ip_hash)
    VALUES ('   ', '+966512345678', 'ppf-gloss', 'Porsche 911', 'al-hamra',
            'this-week', 'en', repeat('0', 64));
    RAISE EXCEPTION 'CHECK 22 FAILED: a whitespace-only name was accepted';
EXCEPTION WHEN check_violation THEN NULL;
END;

RAISE NOTICE 'ALL SCHEMA CHECKS PASSED';

END $$;

ROLLBACK;
