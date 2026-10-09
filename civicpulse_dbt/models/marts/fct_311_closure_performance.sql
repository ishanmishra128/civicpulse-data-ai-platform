SELECT
    unique_key,
    created_date,
    closed_date,
    complaint_type,
    agency,
    borough,
    closure_hours,
    DATE_TRUNC('day', created_date) AS created_day

FROM {{ ref('stg_nyc_311_requests') }}

WHERE closed_date IS NOT NULL
  AND closed_date >= created_date
