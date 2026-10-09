-- 1. Overall volume and unique IDs
SELECT
    COUNT(*) AS total_records,
    COUNT(DISTINCT unique_key) AS distinct_keys
FROM raw.nyc_311_requests;

-- 2. Required fields and important missing values
SELECT
    COUNT(*) FILTER (WHERE unique_key IS NULL OR unique_key = '') AS missing_keys,
    COUNT(*) FILTER (WHERE created_date IS NULL) AS missing_created_dates,
    COUNT(*) FILTER (WHERE complaint_type IS NULL OR complaint_type = '') AS missing_complaint_types,
    COUNT(*) FILTER (WHERE agency IS NULL OR agency = '') AS missing_agencies,
    COUNT(*) FILTER (WHERE borough IS NULL OR borough = '') AS missing_boroughs,
    COUNT(*) FILTER (WHERE closed_date IS NULL) AS missing_closure_dates
FROM raw.nyc_311_requests;

-- 3. Chronological validity
SELECT
    COUNT(*) FILTER (WHERE closed_date < created_date) AS closure_before_creation,
    COUNT(*) FILTER (WHERE created_date > NOW()) AS future_creation_dates
FROM raw.nyc_311_requests;

-- 4. Request status coverage
SELECT
    COALESCE(borough, '(missing)') AS borough,
    COUNT(*) AS request_count,
    COUNT(*) FILTER (WHERE closed_date IS NULL) AS without_closure_date,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE closed_date IS NULL)
        / NULLIF(COUNT(*), 0),
        2
    ) AS pct_without_closure
FROM raw.nyc_311_requests
GROUP BY borough
ORDER BY request_count DESC;

-- 5. Closure duration distribution for completed requests
SELECT
    COUNT(*) AS completed_requests,
    ROUND(
        (PERCENTILE_CONT(0.5) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (closed_date - created_date)) / 3600
        ))::numeric, 2
    ) AS median_hours_to_close,
    ROUND(
        (PERCENTILE_CONT(0.9) WITHIN GROUP (
            ORDER BY EXTRACT(EPOCH FROM (closed_date - created_date)) / 3600
        ))::numeric, 2
    ) AS p90_hours_to_close
FROM raw.nyc_311_requests
WHERE closed_date IS NOT NULL
  AND closed_date >= created_date;
