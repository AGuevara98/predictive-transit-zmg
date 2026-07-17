# W9 — Third-City GTFS Scouting Findings

**Purpose.** Monterrey's GTFS is unavailable, blocking W9's Tier-2 (W3 accessibility / coverage-gap)
for the transferability study. This document reports a verified scout for a replacement city with a
**usable, downloadable GTFS feed** plus Tier-1 data. It supersedes the stalled RA scouting (ClickUp
tasks 86bak20aw / 86bak20bm, both "to do" / 0 comments / overdue since 2026-06-30) by doing the
research directly.

**Date:** 2026-07-17. **Method:** authoritative check against the **Mobility Database catalog**
(the aggregator the RA tasks named; downloaded the full catalog CSV and filtered to `country=MX`),
plus per-operator web verification and **actual download + file-count validation** of the feeds
that resolved. Tier-1 (INEGI census/DENUE/AGEB shapefile) is nationally available for every Mexican
state, so it is not a differentiator; the deciding factor is GTFS.

---

## Bottom line

- **Recommended replacement: Toluca (Zona Metropolitana de Toluca).** Official state GTFS,
  **verified complete** (60,295 stops / 334,104 stop_times / 622 routes / shapes + fares), metro
  scale (16 municipios, 2.3M) comparable to ZMG (10 munis) and MTY (12 munis). One caveat: the host
  serves an **expired TLS certificate**, so the download needs a cert-bypass (`curl -k`) or the
  MobilityData mirror — trivial, not a blocker.
- **Clean alternative: Aguascalientes.** Official statewide GTFS, **verified complete** (1,507
  stops / 8,388 stop_times / 184 trips / 48 routes / shapes + frequencies), downloads over clean
  HTTPS with zero friction. Smaller metro (~3 municipios, ~1.1M) — a simpler but less ZMG-comparable
  transfer target.
- **Of the six RA candidates, only Toluca has a usable public feed.** León, Puebla, Querétaro,
  Chihuahua are Unavailable/Uncertain (no public feed found); Mérida "Va y Ven" has GTFS but it is
  **not published as a downloadable static feed** (powers the app / Google Maps only).

---

## Per-city findings (RA candidates)

Deliverable rows shaped like `docs/w9_data_requirements.md` row 5.

| City | Operator | GTFS status | Source checked | Notes |
|------|----------|-------------|----------------|-------|
| **Toluca** (ZM Toluca) | Gob. Edo. México — "Toluca y Área Metropolitana" | ✅ **Available (verified)** | Mobility Database src #2865; `https://datos.movimex.gob.mx/gtfs/toluca.gtfs.zip` | Downloaded + validated: 60,295 stops, 334,104 stop_times, 622 routes/trips, shapes, frequencies, fares. **Host cert expired → use `curl -k`.** Complete for W3. |
| León, Gto | SIT León / OptiBus | ⚠️ Uncertain → Unavailable | Mobility Database (absent); OptiBus app | Not catalogued. OptiBus app powers Google Maps, so a GTFS likely exists privately, but no public download found. |
| Puebla | RUTA (BRT) | ❌ Unavailable | Mobility Database (absent); web | Not catalogued; no public feed located. |
| Querétaro | Qrobus | ⚠️ Uncertain | Mobility Database (absent); Qrobus app | Not catalogued. Qrobus app advertises Google-Maps integration ⇒ GTFS exists but not published for download. Would require agency (IQT) request. |
| Chihuahua | Vivebus (BRT) | ❌ Unavailable | Mobility Database (absent); web | Not catalogued; only third-party (Moovit) data. No public feed. |
| Mérida, Yuc | Va y Ven (ATY) | ⚠️ Uncertain (exists, not open) | Mobility Database (absent); transporteyucatan.org.mx | Confirmed **dynamic GTFS** ("one of the first in Mexico") feeding the app + realtime; **no static-zip download** on the agency/open-data sites. Modern, high-ridership (~162k/day) — worth an ATY data request if a second option is wanted. |

## Bonus candidates (not on the RA list) with usable feeds

| City | GTFS status | Source | Notes |
|------|-------------|--------|-------|
| **Aguascalientes** (ZM Ags) | ✅ **Available (verified)** | Mobility Database src #3111; `https://www.aguascalientes.gob.mx/portalgea/file/otros/gdeda-aguascalientes-mx.zip` | Validated: 1,507 stops, 8,388 stop_times, 184 trips, 48 routes, shapes, frequencies. Clean HTTPS. Smaller metro. |
| Puerto Vallarta, Jal | ✅ Available | Mobility Database (datos.jalisco.gob.mx) | Same state as ZMG; small coastal city — limited transferability value. |
| Oaxaca | ✅ Available | Mobility Database (semovioaxaca.gob.mx) | Available; not further validated here. |
| CDMX (Mexico City) | ✅ Available | Mobility Database (SEMOVI) | Excluded per study design (one of the "big-3" already alongside GDL/MTY). |

**All 12 catalogued Mexican feeds** in the Mobility Database (2026-07-17): CDMX (×3 SEMOVI variants),
Guadalajara AMG (×3 — the ZMG/SITEUR feed already used), Puerto Vallarta, Oaxaca, Cancún (private
shuttle only), **Toluca**, Jilotepec (tiny), **Aguascalientes**. No Monterrey, León, Puebla,
Querétaro, Chihuahua, or Mérida.

---

## Tier-1 data (applies to every candidate)

INEGI datasets are national — **Available for all six cities** with no per-city sourcing risk:

- **CPV2020 census (AGEB):** `conjunto_de_datos_ageb_urbana_{CVE_ENT}_cpv2020_csv.zip`. CVE_ENT:
  **Toluca / Edo. México = 15**, **Aguascalientes = 01**, León/Gto = 11, Puebla = 21, Querétaro = 22,
  Chihuahua = 08, Mérida/Yucatán = 31. Schema identical to ZMG — no adaptation.
- **DENUE business registry:** per-state extract, same schema (SCIAN national standard).
- **AGEB shapefile (Marco Geoestadístico 2020):** per-state, joins on 13-char CVEGEO.
- **CONAPO 2020 metro delimitation:** ZM Toluca = **16 municipios, 2.3M** (good ZMG/MTY-scale
  comparison); ZM Aguascalientes ≈ **3 municipios, ~1.1M** (compact). Both need the exact municipio
  code list pulled from the *Metrópolis de México 2020* delimitation before onboarding.

**Tier-2 EOD survey (optional, W2):** not verified per city. Fallback is the ZMG-calibrated prior
(now β = 1.2005, or β = 2.0) with a documented sensitivity analysis — W2 is not a hard dependency.

---

## How to onboard the recommended city

Follow `docs/w9_city_onboarding.md`. To fetch the two verified feeds:

```bash
# Toluca (expired cert on the gov host -> -k required)
curl -k -L "https://datos.movimex.gob.mx/gtfs/toluca.gtfs.zip" -o data/gtfs_toluca.zip

# Aguascalientes (clean HTTPS)
curl -L "https://www.aguascalientes.gob.mx/portalgea/file/otros/gdeda-aguascalientes-mx.zip" \
  -o data/gtfs_aguascalientes.zip
```

Then set `CVE_ENT` (15 or 01), the CONAPO municipio list, and bbox in a new `w9_city_config`, and
run the W1→W3 pipeline. The Toluca feed's `frequencies.txt` is present, so `w3_accessibility.py`
gets headways directly.

---

## Note for the RAs / task follow-up

The RA task paired "Toluca" with **Mexibús** — but Mexibús runs in the **Valle de México**
(Ecatepec/Nezahualcóyotl), not the Valle de Toluca. The usable feed is the State of México's
official **"Toluca y Área Metropolitana"** metropolitan bus GTFS (not a BRT-only feed), which is
what matters. The RA scouting can be closed with Toluca as the winner (Aguascalientes as backup).
