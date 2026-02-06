-- Fix canonical_test_id linkage for lab_tests
-- Problem: Only representative rows got linked, not all location variants

-- Step 1: Propagate canonical_test_id within same (lab_id, source_test_code)
-- If any row with a given (lab_id, source_test_code) has a canonical_test_id,
-- copy it to all other rows with the same (lab_id, source_test_code)

UPDATE lab_tests lt
SET
    canonical_test_id = linked.canonical_test_id,
    match_confidence = linked.match_confidence,
    match_method = linked.match_method
FROM (
    SELECT DISTINCT ON (lab_id, source_test_code)
        lab_id,
        source_test_code,
        canonical_test_id,
        match_confidence,
        match_method
    FROM lab_tests
    WHERE canonical_test_id IS NOT NULL
      AND source_test_code IS NOT NULL
    ORDER BY lab_id, source_test_code, match_confidence DESC NULLS LAST
) linked
WHERE lt.lab_id = linked.lab_id
  AND lt.source_test_code = linked.source_test_code
  AND lt.canonical_test_id IS NULL;

-- Step 2: Link by exact source_test_name match to canonical_tests.name
UPDATE lab_tests lt
SET
    canonical_test_id = ct.id,
    match_confidence = 0.85,
    match_method = 'name_propagation'
FROM canonical_tests ct
WHERE lt.canonical_test_id IS NULL
  AND lower(trim(lt.source_test_name)) = lower(trim(ct.name));

-- Step 3: Link by matching source_test_name to any keyword in canonical_tests.keywords
UPDATE lab_tests lt
SET
    canonical_test_id = ct.id,
    match_confidence = 0.80,
    match_method = 'keyword_propagation'
FROM canonical_tests ct
WHERE lt.canonical_test_id IS NULL
  AND lower(trim(lt.source_test_name)) = ANY(
      SELECT lower(trim(kw)) FROM unnest(ct.keywords) AS kw
  );

-- Report results
SELECT
    CASE WHEN canonical_test_id IS NULL THEN 'unlinked' ELSE 'linked' END AS status,
    count(*) AS row_count
FROM lab_tests
GROUP BY 1;
