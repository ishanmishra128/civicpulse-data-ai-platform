SELECT
    f.unique_key,
    f.closure_hours
FROM {{ ref('fct_311_closure_performance') }} AS f
INNER JOIN {{ ref('stg_nyc_311_requests') }} AS s
    ON f.unique_key = s.unique_key
WHERE s.has_invalid_closure_timestamp = TRUE
