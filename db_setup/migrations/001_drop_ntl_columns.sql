-- W0.1 remediation: drop dead v_ntl_median columns from features.nppv_features
-- v_ntl_median was all-zero due to a silent rasterio zonal-stats failure.
-- Vitality is now represented by v_ridership_annual alone.
ALTER TABLE features.nppv_features
    DROP COLUMN IF EXISTS v_ntl_median,
    DROP COLUMN IF EXISTS v_ntl_median_n;
