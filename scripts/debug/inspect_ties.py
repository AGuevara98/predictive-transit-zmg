import json
from sqlalchemy import create_engine, text
import config

engine = create_engine(config.PG_URI)

def col_list(conn, schema, table):
    q = text("""
    SELECT column_name FROM information_schema.columns
    WHERE table_schema = :schema AND table_name = :table
    ORDER BY ordinal_position;
    """)
    return [r[0] for r in conn.execute(q, {"schema": schema, "table": table}).fetchall()]

with engine.connect() as conn:
    cols = col_list(conn, 'features', 'station_npv_audit')

    sample = conn.execute(text('SELECT * FROM features.station_npv_audit LIMIT 5')).mappings().all()
    # 1) Top stations (max npv_score)
    top_q = text("""
    SELECT stop_id, stop_name, ageb_id, stops_400m, employment_proxy, npv_score
    FROM features.station_npv_audit
    WHERE npv_score = (SELECT MAX(npv_score) FROM features.station_npv_audit)
    ORDER BY stop_id;
    """)
    top = conn.execute(top_q).mappings().all()

    # 2) Group identical feature tuples (stops_400m, employment_proxy, ageb_id)
    groups_q = text("""
    SELECT stops_400m, employment_proxy, ageb_id, COUNT(*) AS n_stations
    FROM features.station_npv_audit
    GROUP BY stops_400m, employment_proxy, ageb_id
    ORDER BY n_stations DESC
    LIMIT 50;
    """)
    groups = conn.execute(groups_q).mappings().all()

    # 3) Detect available stops table and for each top station count DISTINCT stops within 400m using that table's geometry
    tbls_q = text("""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_name ILIKE '%stop%'
    ORDER BY table_schema, table_name;
    """)
    candidate_tbls = conn.execute(tbls_q).fetchall()

    # prefer candidate schemas
    preferred = None
    for schema, table in candidate_tbls:
        if schema == 'base' and table == 'stops':
            preferred = (schema, table)
            break
    if not preferred:
        for schema, table in candidate_tbls:
            if table == 'stops':
                preferred = (schema, table)
                break
    if not preferred and candidate_tbls:
        preferred = (candidate_tbls[0][0], candidate_tbls[0][1])

    stop_counts = []
    if preferred:
        schema, table = preferred
        full = f"{schema}.{table}"
        for r in top:
            sid = r['stop_id']
            cnt_q = text(f"""
            SELECT COUNT(DISTINCT s2.stop_id) AS distinct_stops
            FROM {full} s1
            JOIN {full} s2 ON ST_DWithin(s1.geom, s2.geom, 400)
            WHERE s1.stop_id = :sid;
            """)
            cnt = conn.execute(cnt_q, {"sid": sid}).scalar()
            stop_counts.append({"stop_id": sid, "distinct_stops_400m": int(cnt) if cnt is not None else None})
    else:
        stop_counts = [{'error': 'no stops table found'}]

    # 4) Basic duplicate/uniqueness checks on chosen stops table
    dups = {}
    if preferred:
        schema, table = preferred
        full = f"{schema}.{table}"
        # list columns for the chosen stops table
        stop_cols = col_list(conn, schema, table)
        # basic counts
        total_q = text(f"SELECT COUNT(*) FROM {full}")
        total = conn.execute(total_q).scalar()
        distinct_id_q = text(f"SELECT COUNT(DISTINCT stop_id) FROM {full}")
        distinct_ids = conn.execute(distinct_id_q).scalar()
        distinct_name = None
        if 'stop_name' in stop_cols:
            dnq = text(f"SELECT COUNT(DISTINCT stop_name) FROM {full}")
            distinct_name = conn.execute(dnq).scalar()

        dups = {
            'chosen_table_columns': stop_cols,
            'total_rows': int(total) if total is not None else None,
            'distinct_stop_ids': int(distinct_ids) if distinct_ids is not None else None,
            'distinct_stop_names': int(distinct_name) if distinct_name is not None else None,
        }

    out = {
        'columns': cols,
        'sample_rows': sample,
        'top_stations': top,
        'feature_groups': groups,
        'stops_table_candidates': [{'schema': r[0], 'table': r[1]} for r in candidate_tbls],
        'chosen_stops_table': f"{preferred[0]}.{preferred[1]}" if preferred else None,
        'top_station_distinct_stop_counts': stop_counts,
        'duplicate_stops_sample': dups,
    }
    print(json.dumps(out, default=str, ensure_ascii=False, indent=2))
