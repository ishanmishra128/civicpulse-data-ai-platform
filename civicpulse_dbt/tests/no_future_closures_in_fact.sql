SELECT
    unique_key,
    created_date,
    closed_date,
    closure_hours
FROM {{ ref('fct_311_closure_performance') }}
WHERE closed_date > CURRENT_TIMESTAMP