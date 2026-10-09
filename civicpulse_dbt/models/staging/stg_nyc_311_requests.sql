SELECT
    unique_key,
    created_date,
    closed_date,
    NULLIF(TRIM(complaint_type), '') AS complaint_type,
    NULLIF(TRIM(agency), '') AS agency,
    NULLIF(TRIM(borough), '') AS borough,

    closed_date IS NULL AS is_missing_closure_date,

    (
        closed_date IS NOT NULL
        AND closed_date < created_date
    ) AS has_invalid_closure_timestamp,

    CASE
        WHEN closed_date IS NOT NULL
         AND closed_date >= created_date
        THEN EXTRACT(EPOCH FROM (closed_date - created_date)) / 3600.0
        ELSE NULL
    END AS closure_hours,

    raw_record,
    loaded_at

FROM raw.nyc_311_requests
