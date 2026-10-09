SELECT
    COALESCE(borough, 'Unspecified') AS borough,
    COUNT(*) AS total_requests,

    COUNT(*) FILTER (
        WHERE is_missing_closure_date
    ) AS requests_without_closure_date,

    COUNT(*) FILTER (
        WHERE has_invalid_closure_timestamp
    ) AS invalid_closure_timestamps,

    COUNT(*) FILTER (
        WHERE closure_hours IS NOT NULL
    ) AS valid_completed_requests,

    ROUND(
        AVG(closure_hours)::numeric,
        2
    ) AS avg_closure_hours,

    ROUND(
        (
            PERCENTILE_CONT(0.5)
            WITHIN GROUP (ORDER BY closure_hours)
        )::numeric,
        2
    ) AS median_closure_hours,

    ROUND(
        (
            PERCENTILE_CONT(0.9)
            WITHIN GROUP (ORDER BY closure_hours)
        )::numeric,
        2
    ) AS p90_closure_hours

FROM {{ ref('stg_nyc_311_requests') }}

GROUP BY COALESCE(borough, 'Unspecified')
