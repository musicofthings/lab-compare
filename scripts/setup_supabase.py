"""Create all Supabase tables and indexes.

Run this once to set up the database schema.
Uses the Supabase REST API via the Python client for DDL operations
by executing raw SQL through the RPC endpoint.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from supabase import create_client
from pipeline.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY

SCHEMA_SQL = """
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =============================================
-- TABLE: labs
-- =============================================
CREATE TABLE IF NOT EXISTS labs (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    slug            TEXT NOT NULL UNIQUE,
    website_url     TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- TABLE: cities
-- =============================================
CREATE TABLE IF NOT EXISTS cities (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    state           TEXT,
    tier            SMALLINT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(name, state)
);

-- =============================================
-- TABLE: departments
-- =============================================
CREATE TABLE IF NOT EXISTS departments (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL UNIQUE,
    slug            TEXT NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- TABLE: lab_locations
-- =============================================
CREATE TABLE IF NOT EXISTS lab_locations (
    id              SERIAL PRIMARY KEY,
    lab_id          INT NOT NULL REFERENCES labs(id),
    city_id         INT REFERENCES cities(id),
    location_code   TEXT,
    location_name   TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(lab_id, location_code)
);

-- =============================================
-- TABLE: canonical_tests
-- =============================================
CREATE TABLE IF NOT EXISTS canonical_tests (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,
    department_id   INT REFERENCES departments(id),
    test_type       TEXT,
    sample_type     TEXT,
    methodology     TEXT,
    keywords        TEXT[],
    is_popular      BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- TABLE: lab_tests (fact table)
-- =============================================
CREATE TABLE IF NOT EXISTS lab_tests (
    id                  SERIAL PRIMARY KEY,
    lab_id              INT NOT NULL REFERENCES labs(id),
    canonical_test_id   INT REFERENCES canonical_tests(id),
    lab_location_id     INT REFERENCES lab_locations(id),
    source_test_code    TEXT,
    source_test_name    TEXT NOT NULL,
    source_product_id   TEXT,
    price               DECIMAL(10, 2),
    mrp                 DECIMAL(10, 2),
    discount_pct        DECIMAL(5, 2),
    test_type           TEXT,
    department_raw      TEXT,
    methodology         TEXT,
    sample_type         TEXT,
    sample_volume       TEXT,
    sample_container    TEXT,
    fasting_required    BOOLEAN,
    tat_text            TEXT,
    tat_hours           INT,
    home_collection     BOOLEAN,
    nabl_accredited     BOOLEAN,
    is_active           BOOLEAN DEFAULT TRUE,
    source_url          TEXT,
    raw_data            JSONB,
    match_confidence    DECIMAL(5, 4),
    match_method        TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================
-- TABLE: test_aliases
-- =============================================
CREATE TABLE IF NOT EXISTS test_aliases (
    id                  SERIAL PRIMARY KEY,
    canonical_test_id   INT NOT NULL REFERENCES canonical_tests(id),
    alias               TEXT NOT NULL,
    source_lab_id       INT REFERENCES labs(id),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(canonical_test_id, alias)
);

-- =============================================
-- INDEXES
-- =============================================
CREATE INDEX IF NOT EXISTS idx_canonical_tests_name_trgm ON canonical_tests USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_canonical_tests_keywords ON canonical_tests USING gin (keywords);
CREATE INDEX IF NOT EXISTS idx_lab_tests_canonical ON lab_tests(canonical_test_id) WHERE canonical_test_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_lab_tests_lab ON lab_tests(lab_id);
CREATE INDEX IF NOT EXISTS idx_lab_tests_location ON lab_tests(lab_location_id);
CREATE INDEX IF NOT EXISTS idx_lab_tests_source_name_trgm ON lab_tests USING gin (source_test_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_test_aliases_alias_trgm ON test_aliases USING gin (alias gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_test_aliases_canonical ON test_aliases(canonical_test_id);
CREATE INDEX IF NOT EXISTS idx_lab_tests_code_lab ON lab_tests(source_test_code, lab_id);

-- =============================================
-- VIEW: test_comparison
-- =============================================
CREATE OR REPLACE VIEW test_comparison AS
SELECT
    ct.id AS canonical_test_id,
    ct.name AS test_name,
    ct.test_type,
    d.name AS department,
    c.name AS city,
    l.name AS lab_name,
    l.slug AS lab_slug,
    lt.price,
    lt.mrp,
    lt.discount_pct,
    lt.tat_hours,
    lt.tat_text,
    lt.home_collection,
    lt.nabl_accredited,
    lt.match_confidence,
    lt.methodology,
    lt.sample_type
FROM canonical_tests ct
JOIN lab_tests lt ON lt.canonical_test_id = ct.id
JOIN labs l ON l.id = lt.lab_id
LEFT JOIN lab_locations ll ON ll.id = lt.lab_location_id
LEFT JOIN cities c ON c.id = ll.city_id
LEFT JOIN departments d ON d.id = ct.department_id
WHERE lt.is_active = TRUE;

-- =============================================
-- RLS policies
-- =============================================
ALTER TABLE labs ENABLE ROW LEVEL SECURITY;
ALTER TABLE cities ENABLE ROW LEVEL SECURITY;
ALTER TABLE departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE canonical_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE lab_tests ENABLE ROW LEVEL SECURITY;
ALTER TABLE test_aliases ENABLE ROW LEVEL SECURITY;
ALTER TABLE lab_locations ENABLE ROW LEVEL SECURITY;

-- Public read access
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Public read labs') THEN
        CREATE POLICY "Public read labs" ON labs FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Public read cities') THEN
        CREATE POLICY "Public read cities" ON cities FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Public read departments') THEN
        CREATE POLICY "Public read departments" ON departments FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Public read canonical_tests') THEN
        CREATE POLICY "Public read canonical_tests" ON canonical_tests FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Public read lab_tests') THEN
        CREATE POLICY "Public read lab_tests" ON lab_tests FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Public read test_aliases') THEN
        CREATE POLICY "Public read test_aliases" ON test_aliases FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Public read lab_locations') THEN
        CREATE POLICY "Public read lab_locations" ON lab_locations FOR SELECT USING (true);
    END IF;
END $$;

-- =============================================
-- FUNCTION: search_tests
-- =============================================
CREATE OR REPLACE FUNCTION search_tests(
    search_query TEXT,
    city_filter TEXT DEFAULT NULL,
    dept_filter TEXT DEFAULT NULL,
    result_limit INT DEFAULT 50
)
RETURNS TABLE (
    canonical_test_id INT,
    test_name TEXT,
    department TEXT,
    similarity_score REAL,
    lab_count BIGINT,
    min_price DECIMAL,
    max_price DECIMAL,
    avg_price DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ct.id,
        ct.name,
        d.name,
        similarity(lower(ct.name), lower(search_query)),
        count(DISTINCT lt.lab_id),
        min(lt.price),
        max(lt.price),
        round(avg(lt.price), 2)
    FROM canonical_tests ct
    LEFT JOIN departments d ON d.id = ct.department_id
    JOIN lab_tests lt ON lt.canonical_test_id = ct.id AND lt.is_active = TRUE
    LEFT JOIN lab_locations ll ON ll.id = lt.lab_location_id
    LEFT JOIN cities c ON c.id = ll.city_id
    WHERE
        (similarity(lower(ct.name), lower(search_query)) > 0.15
         OR lower(ct.name) LIKE '%' || lower(search_query) || '%'
         OR search_query ILIKE ANY(ct.keywords))
        AND (city_filter IS NULL OR lower(c.name) = lower(city_filter))
        AND (dept_filter IS NULL OR lower(d.name) = lower(dept_filter))
    GROUP BY ct.id, ct.name, d.name
    ORDER BY similarity(lower(ct.name), lower(search_query)) DESC, count(DISTINCT lt.lab_id) DESC
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;
"""


def main():
    print("\n=== IMPORTANT ===")
    print("The Supabase Python client cannot execute raw DDL SQL.")
    print("Please run the following SQL in the Supabase SQL Editor:")
    print("  Dashboard -> SQL Editor -> New Query -> Paste and Run")
    print("\nSQL has been saved to: scripts/schema.sql")

    # Write SQL to file
    sql_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(sql_path, "w") as f:
        f.write(SCHEMA_SQL)

    print(f"\nSchema SQL written to {sql_path}")
    print(f"Total length: {len(SCHEMA_SQL)} chars")


if __name__ == "__main__":
    main()
