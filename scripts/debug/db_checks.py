import os
import sys
# Ensure project root is on sys.path so `import config` works
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import create_engine, text
import pandas as pd

# Try to load DB config from config.py, else environment
PG_URI = None
try:
    import config as cfg
    PG_URI = getattr(cfg, 'PG_URI', None)
    DB_HOST = getattr(cfg, 'DB_HOST', None)
    DB_USER = getattr(cfg, 'DB_USER', None)
    DB_NAME = getattr(cfg, 'DB_NAME', None)
    DB_PASS = getattr(cfg, 'DB_PASS', None)
    DB_PORT = getattr(cfg, 'DB_PORT', None)
except Exception:
    DB_HOST = os.environ.get('DB_HOST')
    DB_USER = os.environ.get('DB_USER')
    DB_NAME = os.environ.get('DB_NAME')
    DB_PASS = os.environ.get('DB_PASS')
    DB_PORT = os.environ.get('DB_PORT')

if PG_URI is None:
    if DB_HOST and DB_USER and DB_NAME:
        pwd = DB_PASS or os.environ.get('PGPASSWORD') or ''
        port = DB_PORT or '5432'
        if pwd:
            PG_URI = f"postgresql+psycopg2://{DB_USER}:{pwd}@{DB_HOST}:{port}/{DB_NAME}"
        else:
            PG_URI = f"postgresql+psycopg2://{DB_USER}@{DB_HOST}:{port}/{DB_NAME}"

if PG_URI is None:
    print('ERROR: Could not determine PG_URI. Set PG_URI in config.py or export DB_HOST/DB_USER/DB_NAME (and DB_PASS if needed).')
    sys.exit(2)

engine = create_engine(PG_URI)

queries = [
    ("base_gtfs_stops_count", "SELECT COUNT(*) FROM base.gtfs_stops"),
    ("base_ageb_count", "SELECT COUNT(*) FROM base.ageb"),
    ("station_npv_audit_count", "SELECT COUNT(*) FROM features.station_npv_audit"),
    ("v_critic_weights_count", "SELECT COUNT(*) FROM features.v_critic_weights"),
    ("training_labels_count", "SELECT COUNT(*) FROM features.training_labels"),
    ("station_npv_audit_nulls", "SELECT COUNT(*) AS total, SUM((npv_score IS NULL)::int) AS null_npv_score FROM features.station_npv_audit"),
    ("master_suitability_nulls", "SELECT COUNT(*) AS total, SUM((stops_800m IS NULL)::int) AS null_stops_800m, SUM((min_stop_dist_m IS NULL)::int) AS null_min_stop_dist_m, SUM((employment_proxy IS NULL)::int) AS null_employment_proxy, SUM((route_km_800m IS NULL)::int) AS null_route_km_800m, SUM((slope_mean IS NULL)::int) AS null_slope_mean FROM features.master_suitability"),
    ("stops_stats", "SELECT MIN(stops_800m) AS min, MAX(stops_800m) AS max, AVG(stops_800m) AS avg, STDDEV_POP(stops_800m) AS std FROM features.master_suitability"),
    ("min_dist_stats", "SELECT MIN(min_stop_dist_m) AS min, MAX(min_stop_dist_m) AS max, AVG(min_stop_dist_m) AS avg, STDDEV_POP(min_stop_dist_m) AS std FROM features.master_suitability"),
    ("employment_stats", "SELECT MIN(employment_proxy) AS min, MAX(employment_proxy) AS max, AVG(employment_proxy) AS avg, STDDEV_POP(employment_proxy) AS std FROM features.master_suitability"),
    ("critic_weights_sum", "SELECT SUM(weight_normalized) AS sum_weights, COUNT(*) AS n FROM features.v_critic_weights"),
    ("critic_weights_top", "SELECT feature, variance, avg_abs_correlation, weight_unnormalized, weight_normalized, feature_rank FROM features.v_critic_weights ORDER BY weight_normalized DESC LIMIT 10"),
    ("correlations", "SELECT CORR(stops_800m::double precision, employment_proxy::double precision) AS corr_stops_emp, CORR(stops_800m::double precision, route_km_800m::double precision) AS corr_stops_route FROM features.master_suitability"),
    ("training_labels_balance", "SELECT label, COUNT(*) FROM features.training_labels GROUP BY label ORDER BY label"),
    ("training_labels_unique_ageb", "SELECT COUNT(DISTINCT ageb_id) FROM features.training_labels"),
    ("training_labels_dup_ageb", "SELECT ageb_id, COUNT(*) FROM features.training_labels GROUP BY ageb_id HAVING COUNT(*) > 1 LIMIT 10")
]

print('\n=== DB checks ===')
with engine.connect() as conn:
    for name, q in queries:
        print(f'\n-- {name} --')
        try:
            res = conn.execute(text(q))
            rows = res.fetchall()
            for r in rows:
                print(r)
        except Exception as e:
            print('ERROR running query:', e)

print('\n=== Artifact checks ===')
base_path = os.path.join(os.getcwd(), 'outputs', 'phase1')
training_csv = os.path.join(base_path, 'training_labels.csv')
critic_csv = os.path.join(base_path, 'critic_weights.csv')
report = os.path.join(base_path, 'report.html')

print('\ntraining_labels.csv:')
if os.path.exists(training_csv):
    try:
        df = pd.read_csv(training_csv)
        print('rows=', len(df))
        print(df.head(5).to_string(index=False))
    except Exception as e:
        print('ERROR reading CSV:', e)
else:
    print('file not found:', training_csv)

print('\ncritic_weights.csv:')
if os.path.exists(critic_csv):
    try:
        df = pd.read_csv(critic_csv)
        print('rows=', len(df))
        print(df.head(5).to_string(index=False))
    except Exception as e:
        print('ERROR reading CSV:', e)
else:
    print('file not found:', critic_csv)

print('\nreport.html exists:', os.path.exists(report))

print('\nDone.')
