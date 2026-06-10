-- ==============================================================================
-- PHASE 1: STATION AUDIT - JOIN GTFS STOPS WITH NP-RV FEATURES
-- ==============================================================================
-- This script joins existing transit stops with AGEB-level features and computes
-- weighted NP-RV suitability scores using CRITIC weights from Phase 1.
--
-- Output: features.station_npv_audit table with one row per existing transit stop
-- ==============================================================================

-- Step 1: Create table with stations joined to AGEBs and feature values
DROP TABLE IF EXISTS features.station_npv_audit CASCADE;
CREATE TABLE features.station_npv_audit AS
WITH critic_weights AS (
    -- Load CRITIC weights for each feature
    SELECT 
        feature,
        weight_normalized
    FROM features.v_critic_weights
),
stop_accessibility AS (
    -- Stop-level accessibility: distinct GTFS stops within 400m of each stop
    SELECT
        s.stop_id,
        s.stop_name,
        a.cvegeo AS ageb_id,
        (
            SELECT COUNT(DISTINCT s2.stop_id)
            FROM base.gtfs_stops s2
            WHERE ST_DWithin(s.geom, s2.geom, 400)
        ) AS stops_400m
    FROM base.gtfs_stops s
    JOIN base.ageb a ON ST_Within(s.geom, a.geom)
),
stop_employment AS (
    -- Stop-level employment: sum DENUE employment proxy within 400m of each stop
    SELECT
        s.stop_id,
        SUM(
            CASE
                WHEN d.estrato_personal = '11 a 30 personas' THEN 20
                WHEN d.estrato_personal = '31 a 50 personas' THEN 40
                WHEN d.estrato_personal = '51 a 100 personas' THEN 75
                WHEN d.estrato_personal = '101 a 250 personas' THEN 175
                WHEN d.estrato_personal = '251 y más personas' THEN 500
                ELSE 0
            END
        ) AS employment_proxy
    FROM base.gtfs_stops s
    LEFT JOIN raw.denue d
        ON ST_DWithin(s.geom, ST_Transform(d.geom, 6372), 400)
       AND d.estrato_personal NOT IN ('0 a 5 personas', '6 a 10 personas')
    GROUP BY s.stop_id
),
stops_with_features AS (
    -- Spatial join: each stop → containing AGEB → features + weighted score
    SELECT 
        sa.stop_id,
        sa.stop_name,
        sa.ageb_id,
        COALESCE(sa.stops_400m, 0) AS stops_400m,
        m.stops_800m,
        m.min_stop_dist_m,
        COALESCE(se.employment_proxy, 0) AS employment_proxy,
        m.route_km_800m,
        m.slope_mean,
        -- Normalize each feature to [0, 1] for scoring
        CASE WHEN max_val.max_stops_400m > 0 THEN COALESCE(sa.stops_400m, 0)::float / max_val.max_stops_400m ELSE 0 END AS stops_400m_norm,
        CASE WHEN max_val.max_stops_800m > 0 THEN m.stops_800m::float / max_val.max_stops_800m ELSE 0 END AS stops_800m_norm,
        CASE WHEN max_val.max_min_dist > 0 THEN (max_val.max_min_dist - m.min_stop_dist_m)::float / max_val.max_min_dist ELSE 0 END AS min_dist_inverted_norm,
        CASE WHEN max_val.max_employment > 0 THEN COALESCE(se.employment_proxy, 0)::float / max_val.max_employment ELSE 0 END AS employment_norm,
        CASE WHEN max_val.max_route_km > 0 THEN m.route_km_800m::float / max_val.max_route_km ELSE 0 END AS route_km_norm,
        CASE WHEN max_val.max_slope > 0 THEN (max_val.max_slope - m.slope_mean)::float / max_val.max_slope ELSE 0 END AS slope_inverted_norm
    FROM stop_accessibility sa
    LEFT JOIN stop_employment se ON se.stop_id = sa.stop_id
    JOIN features.master_suitability m ON sa.ageb_id = m.ageb_id
    CROSS JOIN LATERAL (
        SELECT 
            MAX(sa2.stops_400m) as max_stops_400m,
            MAX(m2.stops_800m) as max_stops_800m,
            MAX(m2.min_stop_dist_m) as max_min_dist,
            MAX(COALESCE(se2.employment_proxy, 0)) as max_employment,
            MAX(m2.route_km_800m) as max_route_km,
            MAX(m2.slope_mean) as max_slope
        FROM stop_accessibility sa2
        LEFT JOIN stop_employment se2 ON se2.stop_id = sa2.stop_id
        JOIN features.master_suitability m2 ON sa2.ageb_id = m2.ageb_id
    ) max_val
),
weighted_scores AS (
    -- Apply CRITIC weights to normalized features and sum for NP-RV score
    SELECT 
        s.stop_id,
        s.stop_name,
        s.ageb_id,
        s.stops_400m,
        s.stops_800m,
        s.min_stop_dist_m,
        s.employment_proxy,
        s.route_km_800m,
        s.slope_mean,
        -- Compute weighted NP-RV score
        (
            s.stops_400m_norm * (SELECT weight_normalized FROM critic_weights WHERE feature = 'stops_400m')
            + s.stops_800m_norm * (SELECT weight_normalized FROM critic_weights WHERE feature = 'stops_800m')
            + s.min_dist_inverted_norm * (SELECT weight_normalized FROM critic_weights WHERE feature = 'min_dist_inverted')
            + s.employment_norm * (SELECT weight_normalized FROM critic_weights WHERE feature = 'employment_proxy')
            + s.route_km_norm * (SELECT weight_normalized FROM critic_weights WHERE feature = 'route_km_800m')
            + s.slope_inverted_norm * (SELECT weight_normalized FROM critic_weights WHERE feature = 'slope_inverted')
        ) AS npv_score
    FROM stops_with_features s
)
SELECT 
    stop_id,
    stop_name,
    ageb_id,
    stops_400m,
    stops_800m,
    ROUND(min_stop_dist_m::numeric, 2) AS min_stop_dist_m,
    employment_proxy,
    ROUND(route_km_800m::numeric, 2) AS route_km_800m,
    ROUND(slope_mean::numeric, 3) AS slope_mean,
    ROUND(npv_score::numeric, 4) AS npv_score,
    RANK() OVER (ORDER BY npv_score DESC) AS npv_rank,
    PERCENT_RANK() OVER (ORDER BY npv_score) * 100 AS npv_percentile
FROM weighted_scores
ORDER BY npv_score DESC;

-- Add primary key and indexes
ALTER TABLE features.station_npv_audit ADD PRIMARY KEY (stop_id);
CREATE INDEX idx_station_audit_ageb ON features.station_npv_audit (ageb_id);
CREATE INDEX idx_station_audit_score ON features.station_npv_audit (npv_score DESC);
ANALYZE features.station_npv_audit;

-- Verification query
SELECT 
    'Station Audit Validation' AS check_name,
    COUNT(*) AS total_stations,
    COUNT(DISTINCT ageb_id) AS ageb_coverage,
    MIN(npv_score)::numeric(6,4) AS min_score,
    MAX(npv_score)::numeric(6,4) AS max_score,
    AVG(npv_score)::numeric(6,4) AS avg_score
FROM features.station_npv_audit;
