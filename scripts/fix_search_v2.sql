-- =============================================
-- FIX v2: search_tests timeout
-- Root cause: GIN index is on name but queries use lower(name),
-- and similarity() in WHERE = full table scan every time.
-- Fix: Add functional index on lower(name), use CTE to filter
-- canonical_tests FIRST, then join lab_tests only for matches.
-- =============================================

-- Step 1: Create functional GIN index on lower(name)
DROP INDEX IF EXISTS idx_canonical_tests_name_lower_trgm;
CREATE INDEX idx_canonical_tests_name_lower_trgm
    ON canonical_tests USING gin (lower(name) gin_trgm_ops);

-- Step 2: Set trigram threshold low enough for short queries (CBC, TSH)
SELECT set_limit(0.1);

-- Step 3: Drop and recreate function
DROP FUNCTION IF EXISTS search_tests(TEXT, TEXT, TEXT, INT);

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
DECLARE
    q TEXT := lower(trim(search_query));
BEGIN
    RETURN QUERY
    WITH matched_tests AS (
        -- Fast: uses GIN trigram index via % operator
        SELECT
            ct.id,
            ct.name,
            d.name AS dept_name,
            GREATEST(
                similarity(lower(ct.name), q),
                CASE WHEN lower(ct.name) LIKE '%' || q || '%'
                     THEN 0.5 ELSE 0.0 END
            )::REAL AS sim_score
        FROM canonical_tests ct
        LEFT JOIN departments d ON d.id = ct.department_id
        WHERE
            lower(ct.name) % q
            OR lower(ct.name) LIKE '%' || q || '%'
    ),
    price_stats AS (
        -- Aggregate pricing only for matched tests
        SELECT
            lt.canonical_test_id AS ct_id,
            count(DISTINCT lt.lab_id) AS lcount,
            min(lt.price) FILTER (WHERE lt.price > 0) AS pmin,
            max(lt.price) FILTER (WHERE lt.price > 0) AS pmax,
            round(avg(lt.price) FILTER (WHERE lt.price > 0), 2) AS pavg
        FROM lab_tests lt
        WHERE lt.canonical_test_id IN (SELECT id FROM matched_tests)
          AND lt.is_active = TRUE
          AND (
              city_filter IS NULL
              OR lt.lab_location_id IN (
                  SELECT ll.id FROM lab_locations ll
                  JOIN cities c ON c.id = ll.city_id
                  WHERE lower(c.name) = lower(city_filter)
              )
          )
        GROUP BY lt.canonical_test_id
    )
    SELECT
        mt.id,
        mt.name,
        mt.dept_name,
        mt.sim_score,
        COALESCE(ps.lcount, 0::BIGINT),
        ps.pmin,
        ps.pmax,
        ps.pavg
    FROM matched_tests mt
    LEFT JOIN price_stats ps ON ps.ct_id = mt.id
    WHERE
        (dept_filter IS NULL OR lower(mt.dept_name) = lower(dept_filter))
    ORDER BY mt.sim_score DESC, COALESCE(ps.lcount, 0) DESC
    LIMIT result_limit;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permissions
GRANT EXECUTE ON FUNCTION search_tests TO anon;
GRANT EXECUTE ON FUNCTION search_tests TO authenticated;
