-- KMQ schema. Applies clean to a fresh PostgreSQL 16 database.
--
-- Three tables. The site writes one of them (lead), reads one of them
-- (warranty, written by the quality team's back office), and joins against
-- the third (branch). Nothing else on the site touches the database.

BEGIN;

-- --------------------------------------------------------------------------
-- Branches
-- --------------------------------------------------------------------------
-- phone, address and hours are nullable on purpose. The content file's
-- pending list leaves all three open for every branch, and a NULL is what
-- makes the template print "to be confirmed" instead of a number nobody
-- has confirmed. Do not backfill these with placeholders.

CREATE TABLE branch (
    id            text PRIMARY KEY,
    city          text NOT NULL,
    sort_order    smallint NOT NULL,
    name_ar       text NOT NULL,
    name_en       text NOT NULL,
    location_ar   text NOT NULL,
    location_en   text NOT NULL,
    phone_e164    text,
    whatsapp_e164 text,
    hours         text,
    map_url       text,
    created_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT branch_phone_e164 CHECK (phone_e164 IS NULL OR phone_e164 ~ '^\+9665\d{8}$'),
    CONSTRAINT branch_wa_e164    CHECK (whatsapp_e164 IS NULL OR whatsapp_e164 ~ '^\+9665\d{8}$'),
    CONSTRAINT branch_map_https  CHECK (map_url IS NULL OR map_url LIKE 'https://%')
);

CREATE UNIQUE INDEX branch_sort_order_key ON branch (sort_order);


-- --------------------------------------------------------------------------
-- Warranty status
-- --------------------------------------------------------------------------
-- A table rather than a boolean: "expired" and "void" are different facts
-- and the quality team needs to record which one applies. A voided warranty
-- must never read as merely lapsed.

CREATE TABLE warranty_status (
    code  text PRIMARY KEY,
    label text NOT NULL
);

INSERT INTO warranty_status (code, label) VALUES
    ('active',  'Active and valid'),
    ('expired', 'Past its expiry date'),
    ('void',    'Voided — conditions not met');


-- --------------------------------------------------------------------------
-- Warranty
-- --------------------------------------------------------------------------
-- Written by the back office after the installation inspection. The public
-- site only ever SELECTs from this table.
--
-- plate_number and invoice_number hold the *normalised* form produced by
-- app/text.py:normalise_lookup — upper-case ASCII alphanumerics, Arabic-Indic
-- digits folded, Arabic plate letters mapped to their Latin twin. The lookup
-- normalises its query identically, so the two always meet.

CREATE TABLE warranty (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    warranty_number text NOT NULL UNIQUE,
    plate_number    text NOT NULL,
    invoice_number  text,
    service_type    text NOT NULL,
    branch_id       text NOT NULL REFERENCES branch (id),
    technician      text,
    install_date    date NOT NULL,
    activation_date date NOT NULL,
    expiry_date     date NOT NULL,
    status          text NOT NULL REFERENCES warranty_status (code),
    created_at      timestamptz NOT NULL DEFAULT now(),

    -- The normalised columns must actually be normalised. Catching a stray
    -- "ABC 1234" at write time beats a lookup that silently never matches.
    CONSTRAINT warranty_plate_normalised
        CHECK (plate_number ~ '^[0-9A-Z]+$'),
    CONSTRAINT warranty_invoice_normalised
        CHECK (invoice_number IS NULL OR invoice_number ~ '^[0-9A-Z]+$'),

    -- A warranty cannot be activated before the film went on, nor expire
    -- before it was activated.
    CONSTRAINT warranty_activation_after_install
        CHECK (activation_date >= install_date),
    CONSTRAINT warranty_expiry_after_activation
        CHECK (expiry_date > activation_date)
);

CREATE INDEX warranty_plate_idx   ON warranty (plate_number);
CREATE INDEX warranty_invoice_idx ON warranty (invoice_number) WHERE invoice_number IS NOT NULL;


-- --------------------------------------------------------------------------
-- Leads
-- --------------------------------------------------------------------------

CREATE TABLE lead (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    full_name  text NOT NULL,
    phone      text NOT NULL,
    service    text NOT NULL,
    car_model  text NOT NULL,
    branch_id  text NOT NULL REFERENCES branch (id),
    timing     text NOT NULL,
    notes      text,
    locale     text NOT NULL,
    -- A salted SHA-256 of the caller's address, not the address. Enough to
    -- rate-limit one client; not enough to identify one afterwards.
    ip_hash    char(64) NOT NULL,
    user_agent text,

    CONSTRAINT lead_phone_e164 CHECK (phone ~ '^\+9665\d{8}$'),
    CONSTRAINT lead_locale     CHECK (locale IN ('ar', 'en')),
    CONSTRAINT lead_service    CHECK (service IN ('ppf-gloss', 'ppf-matte',
                                                 'nano-ceramic', 'window-tint',
                                                 'colour-change', 'unsure')),
    CONSTRAINT lead_timing     CHECK (timing IN ('this-week', 'two-weeks', 'exploring')),
    CONSTRAINT lead_name_present CHECK (length(btrim(full_name)) > 0)
);

-- Supports the per-client throttle, which is the only query that reads leads.
CREATE INDEX lead_ip_hash_created_idx ON lead (ip_hash, created_at DESC);
CREATE INDEX lead_created_idx         ON lead (created_at DESC);


-- --------------------------------------------------------------------------
-- Seed: the six branches
-- --------------------------------------------------------------------------
-- Names and locations are from the content file's branch table, in the same
-- order: Al Rimal is the main branch and leads. Phone, hours and map URL are
-- deliberately absent — see the note at the top.

INSERT INTO branch (id, city, sort_order, name_ar, name_en, location_ar, location_en) VALUES
    ('al-rimal',            'Riyadh', 1, 'فرع حي الرمال',              'Al Rimal Branch',
     'حي الرمال، الرياض',                'Al Rimal district, Riyadh'),
    ('al-hamra',            'Riyadh', 2, 'فرع حي الحمرا',              'Al Hamra Branch',
     'حي الحمرا، الرياض',                'Al Hamra district, Riyadh'),
    ('tuwaiq',              'Riyadh', 3, 'فرع حي طويق',                'Tuwaiq Branch',
     'حي طويق، الرياض',                  'Tuwaiq district, Riyadh'),
    ('jeddah-madinah-road', 'Jeddah', 4, 'فرع طريق المدينة',           'Al Madinah Road Branch',
     'طريق المدينة، جدة',                'Al Madinah Road, Jeddah'),
    ('dammam-al-manar',     'Dammam', 5, 'فرع حي المنار',              'Al-Manar Branch',
     'حي المنار، الدمام',                'Al-Manar district, Dammam'),
    ('dammam-imam',         'Dammam', 6, 'فرع حي الإمام محمد بن سعود', 'Al-Imam Muhammad bin Saud Branch',
     'حي الإمام محمد بن سعود، الدمام',   'Al-Imam Muhammad bin Saud district, Dammam');

COMMIT;
