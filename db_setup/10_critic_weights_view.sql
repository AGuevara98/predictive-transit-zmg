-- ==============================================================================
-- PHASE 1: CRITIC WEIGHTING FOR NP-RV MODEL
-- ==============================================================================
-- This script computes CRITIC (Criteria Importance Through Intercriteria Correlation)
-- weights for the 7 NP-RV dimensions in master_suitability.
--
-- CRITIC method:
-- 1. Compute Pearson correlation matrix between all features
-- 2. For each feature: weight_intermediate = (1 - avg_correlation_to_others)
-- 3. Normalize weights to sum to 1.0
--
-- References: Diakoulaki et al. (1995)
-- ==============================================================================

-- Step 1: Create normalized feature matrix (0-1 scale for correlation computation)
DROP TABLE IF EXISTS features.master_suitability_normalized CASCADE;
CREATE TABLE features.master_suitability_normalized AS
SELECT 
    m.ageb_id,
    CASE WHEN max_stops_400m > 0 THEN COALESCE(acc.stops_400m, 0)::float / max_stops_400m ELSE 0 END AS stops_400m_norm,
    CASE WHEN max_stops_800m > 0 THEN m.stops_800m::float / max_stops_800m ELSE 0 END AS stops_800m_norm,
    CASE WHEN max_min_dist > 0 THEN (max_min_dist - m.min_stop_dist_m)::float / max_min_dist ELSE 0 END AS min_dist_inverted_norm,
    CASE WHEN max_employment > 0 THEN m.employment_proxy::float / max_employment ELSE 0 END AS employment_norm,
    CASE WHEN max_route_km > 0 THEN m.route_km_800m::float / max_route_km ELSE 0 END AS route_km_norm,
    CASE WHEN max_slope > 0 THEN (max_slope - m.slope_mean)::float / max_slope ELSE 0 END AS slope_inverted_norm
FROM features.master_suitability m
LEFT JOIN features.ageb_accessibility acc ON acc.ageb_id = m.ageb_id,
LATERAL (
    SELECT 
        MAX(COALESCE(a.stops_400m, 0)) as max_stops_400m,
        MAX(m2.stops_800m) as max_stops_800m,
        MAX(m2.min_stop_dist_m) as max_min_dist,
        MAX(m2.employment_proxy) as max_employment,
        MAX(m2.route_km_800m) as max_route_km,
        MAX(m2.slope_mean) as max_slope
    FROM features.master_suitability m2
    LEFT JOIN features.ageb_accessibility a ON a.ageb_id = m2.ageb_id
) ranges;

CREATE INDEX idx_master_norm_ageb ON features.master_suitability_normalized (ageb_id);
ANALYZE features.master_suitability_normalized;

-- Step 2: Compute CRITIC weights via SQL window functions
DROP VIEW IF EXISTS features.v_critic_weights CASCADE;
CREATE VIEW features.v_critic_weights AS
WITH feature_stats AS (
    SELECT
        -- Feature 1: Accessibility - 400m buffer
        'stops_400m' AS feature,
        VAR_POP(stops_400m_norm) AS variance,
        1.0 AS placeholder
    FROM features.master_suitability_normalized
    UNION ALL
    SELECT
        'stops_800m',
        VAR_POP(stops_800m_norm),
        1.0
    FROM features.master_suitability_normalized
    UNION ALL
    SELECT
        'min_dist_inverted',
        VAR_POP(min_dist_inverted_norm),
        1.0
    FROM features.master_suitability_normalized
    UNION ALL
    SELECT
        'employment_proxy',
        VAR_POP(employment_norm),
        1.0
    FROM features.master_suitability_normalized
    UNION ALL
    SELECT
        'route_km_800m',
        VAR_POP(route_km_norm),
        1.0
    FROM features.master_suitability_normalized
    UNION ALL
    SELECT
        'slope_inverted',
        VAR_POP(slope_inverted_norm),
        1.0
    FROM features.master_suitability_normalized
),
correlation_matrix AS (
    -- Compute Pearson correlations between feature pairs
    SELECT
        'stops_400m' AS feature_i,
        'stops_800m' AS feature_j,
        (SELECT COALESCE(CORR(stops_400m_norm, stops_800m_norm), 0) FROM features.master_suitability_normalized) AS corr
    UNION ALL
    SELECT 'stops_400m', 'min_dist_inverted', (SELECT COALESCE(CORR(stops_400m_norm, min_dist_inverted_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'stops_400m', 'employment_proxy', (SELECT COALESCE(CORR(stops_400m_norm, employment_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'stops_400m', 'route_km_800m', (SELECT COALESCE(CORR(stops_400m_norm, route_km_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'stops_400m', 'slope_inverted', (SELECT COALESCE(CORR(stops_400m_norm, slope_inverted_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'stops_800m', 'stops_400m', (SELECT COALESCE(CORR(stops_800m_norm, stops_400m_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'stops_800m', 'min_dist_inverted', (SELECT COALESCE(CORR(stops_800m_norm, min_dist_inverted_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'stops_800m', 'employment_proxy', (SELECT COALESCE(CORR(stops_800m_norm, employment_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'stops_800m', 'route_km_800m', (SELECT COALESCE(CORR(stops_800m_norm, route_km_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'stops_800m', 'slope_inverted', (SELECT COALESCE(CORR(stops_800m_norm, slope_inverted_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'min_dist_inverted', 'stops_400m', (SELECT COALESCE(CORR(min_dist_inverted_norm, stops_400m_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'min_dist_inverted', 'stops_800m', (SELECT COALESCE(CORR(min_dist_inverted_norm, stops_800m_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'min_dist_inverted', 'employment_proxy', (SELECT COALESCE(CORR(min_dist_inverted_norm, employment_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'min_dist_inverted', 'route_km_800m', (SELECT COALESCE(CORR(min_dist_inverted_norm, route_km_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'min_dist_inverted', 'slope_inverted', (SELECT COALESCE(CORR(min_dist_inverted_norm, slope_inverted_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'employment_proxy', 'stops_400m', (SELECT COALESCE(CORR(employment_norm, stops_400m_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'employment_proxy', 'stops_800m', (SELECT COALESCE(CORR(employment_norm, stops_800m_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'employment_proxy', 'min_dist_inverted', (SELECT COALESCE(CORR(employment_norm, min_dist_inverted_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'employment_proxy', 'route_km_800m', (SELECT COALESCE(CORR(employment_norm, route_km_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'employment_proxy', 'slope_inverted', (SELECT COALESCE(CORR(employment_norm, slope_inverted_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'route_km_800m', 'stops_400m', (SELECT COALESCE(CORR(route_km_norm, stops_400m_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'route_km_800m', 'stops_800m', (SELECT COALESCE(CORR(route_km_norm, stops_800m_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'route_km_800m', 'min_dist_inverted', (SELECT COALESCE(CORR(route_km_norm, min_dist_inverted_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'route_km_800m', 'employment_proxy', (SELECT COALESCE(CORR(route_km_norm, employment_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'route_km_800m', 'slope_inverted', (SELECT COALESCE(CORR(route_km_norm, slope_inverted_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'slope_inverted', 'stops_400m', (SELECT COALESCE(CORR(slope_inverted_norm, stops_400m_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'slope_inverted', 'stops_800m', (SELECT COALESCE(CORR(slope_inverted_norm, stops_800m_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'slope_inverted', 'min_dist_inverted', (SELECT COALESCE(CORR(slope_inverted_norm, min_dist_inverted_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'slope_inverted', 'employment_proxy', (SELECT COALESCE(CORR(slope_inverted_norm, employment_norm), 0) FROM features.master_suitability_normalized)
    UNION ALL
    SELECT 'slope_inverted', 'route_km_800m', (SELECT COALESCE(CORR(slope_inverted_norm, route_km_norm), 0) FROM features.master_suitability_normalized)
),
avg_correlation_per_feature AS (
    SELECT 
        feature_i AS feature,
        AVG(ABS(corr)) AS avg_abs_correlation
    FROM correlation_matrix
    WHERE feature_i <> feature_j
    GROUP BY feature_i
),
intermediate_weights AS (
    SELECT 
        fs.feature,
        fs.variance,
        acpf.avg_abs_correlation,
        (CASE WHEN acpf.avg_abs_correlation > 0 THEN (1 - acpf.avg_abs_correlation) ELSE 1 END) * COALESCE(fs.variance, 0.001) AS weight_unnormalized
    FROM feature_stats fs
    LEFT JOIN avg_correlation_per_feature acpf ON fs.feature = acpf.feature
)
SELECT 
    feature,
    variance,
    avg_abs_correlation,
    weight_unnormalized,
    weight_unnormalized / SUM(weight_unnormalized) OVER () AS weight_normalized,
    RANK() OVER (ORDER BY weight_unnormalized DESC) AS feature_rank
FROM intermediate_weights
ORDER BY feature_rank;

-- Verification query
SELECT 
    'CRITIC Weights Validation' AS check_name,
    CASE 
        WHEN ABS(SUM(weight_normalized) - 1.0) < 0.0001 THEN 'PASS'
        ELSE 'FAIL'
    END AS result,
    SUM(weight_normalized) AS weights_sum,
    COUNT(*) AS feature_count
FROM features.v_critic_weights;
