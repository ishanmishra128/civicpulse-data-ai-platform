SELECT
    unique_key,
    closure_hours
FROM {{ ref('fct_311_closure_performance') }}
WHERE closure_hours < 0
