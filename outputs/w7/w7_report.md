# W7 Existing Route Audit -- Report

## Summary

- **Routes audited:** 247
- **Feasible routes:** 19
- **Routes flagged:** 229 (80 Low demand, 109 Indirect, 40 Redundant)

## Methodology

1. **GTFS loader:** Route geometries built from shapes.txt (EPSG:6372).
   Fallback to stop-sequence reconstruction if shape_id unavailable.
2. **Served AGEBs:** `ST_DWithin(ST_Centroid(ageb.geom), route_geom, 400m)`.
3. **W5 objective:** f1 demand-gain, f2 route length (efficiency), f3 equity.
4. **W5 constraints:** detour_ratio <= 1.8, stop spacing 300-1000m,    demand >= 500 trips/day, route_km <= 30km.
5. **Pareto ranking:** Non-dominated sort on (-f1, f2, -f3).
6. **Flags:**
   - Low demand: f1 < 0.2 AND total_score < 0.3
   - Indirect: detour_ratio > 1.5
   - Redundant: Jaccard overlap of served AGEBs >= 60% with higher-scoring route

## Score Distribution

- Mean total_score: 0.230
- Median total_score: 0.227
- Mean detour_ratio: 1.977
- Mean f1_demand_gain: 0.012
- Mean f3_equity: 0.549

## Top 10 Routes by Score

| route_id | route_short_name | total_score | f1_demand_gain | f3_equity | pareto_rank | flag |
|---|---|---|---|---|---|---|
| T16B-C08-M | T16B-C08-Mesitas | 0.7 | 0.348 | 0.51 | 1 | nan |
| T14B-C03-2 | T14B-C03-2 | 0.369 | 0.06 | 0.573 | 1 | nan |
| C131-V2 | C131-V2 | 0.368 | 0.023 | 0.538 | 1 | nan |
| MC-A03 | MC-A03 | 0.366 | 0.001 | 0.566 | 1 | nan |
| MC-A13 | MC-A13 | 0.365 | 0.003 | 0.564 | 1 | Indirect |
| T02-A02 | T02-A02 | 0.364 | 0.057 | 0.578 | 1 | nan |
| MC-A16 | MC-A16 | 0.364 | 0.014 | 0.566 | 1 | Indirect |
| MC-A06 | MC-A06 | 0.363 | 0.007 | 0.569 | 1 | nan |
| MC-A10 | MC-A10 | 0.363 | 0.005 | 0.583 | 1 | nan |
| MC-A05 | MC-A05 | 0.362 | 0.001 | 0.547 | 1 | nan |

## Bottom 10 Routes by Score

| route_id | route_short_name | total_score | f1_demand_gain | f3_equity | pareto_rank | flag |
|---|---|---|---|---|---|---|
| C129 | C129 | 0.134 | 0.005 | 0.515 | 11 | Low demand |
| T04A-1 | T04A-1 | 0.135 | 0.002 | 0.53 | 11 | Low demand |
| T11B | T11B | 0.135 | 0.002 | 0.535 | 12 | Low demand |
| C128 | C128 | 0.136 | 0.004 | 0.528 | 8 | Indirect |
| LM-V03 | LM-V03 | 0.136 | 0.003 | 0.531 | 9 | Low demand |
| C14-V1 | C14-V1 | 0.136 | 0.006 | 0.523 | 10 | Indirect |
| C98 | C98 | 0.137 | 0.003 | 0.536 | 9 | Indirect |
| C130 | C130 | 0.137 | 0.007 | 0.522 | 10 | Redundant |
| T04A-2 | T04A-2 | 0.137 | 0.005 | 0.53 | 8 | Indirect |
| LM-V01 | LM-V01 | 0.138 | 0.007 | 0.525 | 9 | Redundant |

## Flagged Routes

| route_id | route_short_name | total_score | detour_ratio | flag | overlap_route_id |
|---|---|---|---|---|---|
| C129 | C129 | 0.134 | 1.196 | Low demand | nan |
| T04A-1 | T04A-1 | 0.135 | 1.455 | Low demand | nan |
| T11B | T11B | 0.135 | 1.477 | Low demand | nan |
| C128 | C128 | 0.136 | 1.671 | Indirect | nan |
| LM-V03 | LM-V03 | 0.136 | 1.204 | Low demand | nan |
| C14-V1 | C14-V1 | 0.136 | 1.514 | Indirect | nan |
| C98 | C98 | 0.137 | 1.798 | Indirect | nan |
| C130 | C130 | 0.137 | 1.549 | Redundant | C125-V2 |
| T04A-2 | T04A-2 | 0.137 | 1.6 | Indirect | nan |
| LM-V01 | LM-V01 | 0.138 | 1.537 | Redundant | C125-V2 |
| C108 | C108 | 0.138 | 5.584 | Indirect | nan |
| T17-C01 | T17-C01 | 0.139 | 1.615 | Indirect | nan |
| C135 | C135 | 0.139 | 1.77 | Indirect | nan |
| T13A | T13A | 0.14 | 1.403 | Low demand | nan |
| C53 | C53 | 0.14 | 1.668 | Indirect | nan |
| C124 | C124 | 0.141 | 1.585 | Indirect | nan |
| C125-V1 | C125-V1 | 0.142 | 1.577 | Redundant | C125-V2 |
| MP-T01 | MP-T01 | 0.142 | 2.239 | Indirect | nan |
| C125-V2 | C125-V2 | 0.143 | 1.578 | Indirect | nan |
| LM-V02 | LM-V02 | 0.144 | 1.102 | Low demand | nan |
| C136 | C136 | 0.144 | 1.841 | Indirect | nan |
| C64 | C64 | 0.145 | 1.47 | Low demand | nan |
| T07 | T07 | 0.146 | 1.591 | Indirect | nan |
| C93 | C93 | 0.146 | 2.413 | Indirect | nan |
| C120 | C120 | 0.146 | 1.451 | Low demand | nan |
| C54 | C54 | 0.146 | 1.449 | Low demand | nan |
| C111-V1 | C111-V1 | 0.146 | 1.586 | Redundant | C111-V3 |
| MP-A05-1 | MP-A05-1 | 0.15 | 3.109 | Indirect | nan |
| MP-C01 | MP-C01 | 0.15 | 1.897 | Indirect | nan |
| C126-V1 | C126-V1 | 0.151 | 1.668 | Redundant | LM-C01 |
| LM-C01 | LM-C01 | 0.151 | 1.668 | Indirect | nan |
| MP-C02 | MP-C02 | 0.151 | 1.694 | Indirect | nan |
| C127-V1 | C127-V1 | 0.151 | 1.358 | Low demand | nan |
| C46-V2 | C46-V2 | 0.151 | 1.554 | Indirect | nan |
| C102 | C102 | 0.152 | 1.733 | Indirect | nan |
| C71 | C71 | 0.154 | 1.624 | Indirect | nan |
| C67-V1 | C67-V1 | 0.154 | 1.656 | Redundant | C111-V3 |
| C111-V3 | C111-V3 | 0.154 | 1.492 | Low demand | nan |
| C104 | C104 | 0.156 | 2.955 | Indirect | nan |
| C117 | C117 | 0.156 | 1.541 | Indirect | nan |
| C15 | C15 | 0.156 | 1.427 | Low demand | nan |
| T18-1-T | T18-1-Terranova | 0.158 | 3.173 | Redundant | T18-2-L |
| C27 | C27 | 0.159 | 2.041 | Indirect | nan |
| T15 | T15 | 0.159 | 1.534 | Indirect | nan |
| C133-V1 | C133-V1 | 0.161 | 2.735 | Indirect | nan |
| T18-2-T | T18-2-Terranova | 0.161 | 3.069 | Redundant | T18-2-L |
| T18-1-L | T18-1-Lopez | 0.163 | 3.098 | Redundant | T18-2-L |
| C65 | C65 | 0.164 | 1.381 | Low demand | nan |
| C41-V1 | C41-V1 | 0.165 | 1.698 | Indirect | nan |
| T18-2-L | T18-2-Lopez | 0.165 | 3.013 | Indirect | nan |
| C105 | C105 | 0.168 | 2.453 | Indirect | nan |
| T17 | T17 | 0.168 | 1.303 | Low demand | nan |
| C103 | C103 | 0.169 | 2.353 | Indirect | nan |
| T09-O | T09-Oblatos | 0.17 | 2.934 | Indirect | nan |
| C80-V1 | C80-V1 | 0.171 | 1.907 | Indirect | nan |
| T14B | T14B | 0.171 | 86.302 | Indirect | nan |
| ST_L1 | L1 | 0.173 | 1.298 | Redundant | C109 |
| C110-V2 | C110-V2 | 0.175 | 1.105 | Redundant | C109 |
| C67-V2 | C67-V2 | 0.175 | 1.629 | Indirect | nan |
| C17 | C17 | 0.176 | 1.922 | Indirect | nan |
| MP-A06 | MP-A06 | 0.176 | 1.237 | Low demand | nan |
| T16B | T16B | 0.176 | 1.357 | Low demand | nan |
| C101 | C101 | 0.177 | 1.6 | Indirect | nan |
| MP-C03 | MP-C03 | 0.178 | 1.559 | Redundant | MP-T03 |
| C116-B | C116-B | 0.18 | 1.627 | Indirect | nan |
| C123-V1 | C123-V1 | 0.181 | 1.27 | Low demand | nan |
| C14-V2 | C14-V2 | 0.181 | 1.571 | Indirect | nan |
| T04B-1 | T04B-1 | 0.182 | 1.295 | Low demand | nan |
| C128A-V1 | C128A-V1 | 0.182 | 1.368 | Low demand | nan |
| C19 | C19 | 0.183 | 1.764 | Indirect | nan |
| C28 | C28 | 0.188 | 1.639 | Indirect | nan |
| C46-V1 | C46-V1 | 0.189 | 1.389 | Low demand | nan |
| C89 | C89 | 0.189 | 1.812 | Redundant | C88-V2 |
| C39-V2 | C39-V2 | 0.19 | 1.348 | Redundant | C39-V1 |
| C66-V2 | C66-V2 | 0.19 | 1.638 | Indirect | nan |
| MP-T02 | MP-T02 | 0.192 | 1.365 | Low demand | nan |
| C99 | C99 | 0.193 | 1.985 | Indirect | nan |
| C122 | C122 | 0.193 | 1.976 | Indirect | nan |
| C06 | C06 | 0.193 | 1.95 | Indirect | nan |
| C38-V2 | C38-V2 | 0.194 | 1.659 | Redundant | C39-V1 |
| C37-V1 | C37-V1 | 0.196 | 1.755 | Redundant | C37-V2 |
| C58-V2 | C58-V2 | 0.196 | 1.572 | Indirect | nan |
| C38-V1 | C38-V1 | 0.196 | 1.484 | Redundant | C39-V1 |
| C20-V1 | C20-V1 | 0.197 | 1.663 | Indirect | nan |
| C76-V1 | C76-V1 | 0.198 | 1.622 | Redundant | C76-V2 |
| C116-A | C116-A | 0.199 | 1.699 | Indirect | nan |
| C112 | C112 | 0.2 | 1.32 | Low demand | nan |
| C106 | C106 | 0.2 | 1.764 | Indirect | nan |
| C70 | C70 | 0.201 | 2.496 | Indirect | nan |
| C66-V1 | C66-V1 | 0.202 | 1.29 | Low demand | nan |
| C79 | C79 | 0.203 | 1.738 | Indirect | nan |
| C37-V2 | C37-V2 | 0.203 | 1.71 | Indirect | nan |
| C39-V1 | C39-V1 | 0.204 | 1.307 | Low demand | nan |
| C26 | C26 | 0.204 | 1.459 | Low demand | nan |
| C110-V1 | C110-V1 | 0.206 | 1.523 | Indirect | nan |
| C41-V2 | C41-V2 | 0.208 | 1.559 | Indirect | nan |
| C134 | C134 | 0.209 | 1.118 | Low demand | nan |
| C73 | C73 | 0.211 | 2.645 | Indirect | nan |
| C138 | C138 | 0.212 | 4.931 | Indirect | nan |
| C118 | C118 | 0.213 | 1.392 | Low demand | nan |
| T04B-3 | T04B-3 | 0.214 | 1.267 | Low demand | nan |
| C60 | C60 | 0.214 | 1.481 | Redundant | C58-V1 |
| C88-V2 | C88-V2 | 0.215 | 1.299 | Low demand | nan |
| C76-V2 | C76-V2 | 0.217 | 1.481 | Low demand | nan |
| C43-V1 | C43-V1 | 0.217 | 2.518 | Indirect | nan |
| C05 | C05 | 0.217 | 1.449 | Low demand | nan |
| C111-V2 | C111-V2 | 0.217 | 1.174 | Low demand | nan |
| T07-C02 | T07-C02 | 0.218 | 1.726 | Indirect | nan |
| T11A-C03 | T11A-C03 | 0.219 | 1.515 | Redundant | T11A-C02 |
| C132 | C132 | 0.219 | 2.289 | Indirect | nan |
| MC-A19 | MC-A19 | 0.22 | 1.554 | Indirect | nan |
| C07-V2 | C07-V2 | 0.221 | 1.368 | Low demand | nan |
| T11A-C02 | T11A-C02 | 0.222 | 1.471 | Low demand | nan |
| C121-B | C121-B | 0.223 | 1.807 | Indirect | nan |
| MT_L3 | L3 | 0.223 | 1.084 | Low demand | nan |
| C31 | C31 | 0.224 | 1.839 | Indirect | nan |
| C35 | C35 | 0.224 | 1.599 | Indirect | nan |
| C97-V2 | C97-V2 | 0.225 | 1.408 | Low demand | nan |
| C33 | C33 | 0.225 | 1.803 | Indirect | nan |
| C62 | C62 | 0.226 | 1.336 | Low demand | nan |
| C74 | C74 | 0.226 | 1.463 | Low demand | nan |
| T03 | T03 | 0.226 | 1.549 | Indirect | nan |
| T11A-C01 | T11A-C01 | 0.226 | 1.373 | Redundant | T11A |
| C03 | C03 | 0.227 | 1.332 | Low demand | nan |
| LM-V05 | LM-V05 | 0.227 | 1.617 | Indirect | nan |
| C123-V2 | C123-V2 | 0.228 | 1.511 | Redundant | C107 |
| MP-A02 | MP-A02 | 0.228 | 1.669 | Indirect | nan |
| MP-A04 | MP-A04 | 0.23 | 1.564 | Indirect | nan |
| C58-V1 | C58-V1 | 0.231 | 1.234 | Low demand | nan |
| C07-V1 | C07-V1 | 0.233 | 1.437 | Low demand | nan |
| C115 | C115 | 0.234 | 1.666 | Indirect | nan |
| T08 | T08 | 0.234 | 1.692 | Indirect | nan |
| T11A | T11A | 0.236 | 1.291 | Low demand | nan |
| C95 | C95 | 0.236 | 1.517 | Indirect | nan |
| C42 | C42 | 0.236 | 1.644 | Indirect | nan |
| T04B-2 | T04B-2 | 0.236 | 1.302 | Low demand | nan |
| C43-V3 | C43-V3 | 0.237 | 1.636 | Redundant | C43-V2 |
| T09-B | T09-Belisario | 0.238 | 3.057 | Indirect | nan |
| C97-V1 | C97-V1 | 0.239 | 1.386 | Low demand | nan |
| C107 | C107 | 0.239 | 1.558 | Indirect | nan |
| MP-T03 | MP-T03 | 0.239 | 1.222 | Low demand | nan |
| C34 | C34 | 0.239 | 1.289 | Low demand | nan |
| C43-V2 | C43-V2 | 0.24 | 1.616 | Indirect | nan |
| T06 | T06 | 0.24 | 1.238 | Low demand | nan |
| MP-A01 | MP-A01 | 0.241 | 1.429 | Low demand | nan |
| C90 | C90 | 0.241 | 1.339 | Redundant | C92 |
| C113-V1 | C113-V1 | 0.243 | 1.513 | Indirect | nan |
| C80-V2 | C80-V2 | 0.243 | 1.434 | Redundant | C100 |
| T04B-4 | T04B-4 | 0.244 | 1.512 | Indirect | nan |
| T10 | T10 | 0.245 | 1.203 | Redundant | T10-C01 |
| C96-V2 | C96-V2 | 0.245 | 1.294 | Low demand | nan |
| T16B-C07-V | T16B-C07-Vistas | 0.246 | 1.253 | Redundant | T16B-C08-P |
| T02 | T02 | 0.247 | 1.319 | Low demand | nan |
| C86 | C86 | 0.248 | 1.588 | Indirect | nan |
| C69 | C69 | 0.249 | 2.262 | Indirect | nan |
| T10-C02 | T10-C02 | 0.249 | 1.473 | Redundant | T10-C01 |
| C113-V2 | C113-V2 | 0.25 | 1.534 | Indirect | nan |
| T10-C01 | T10-C01 | 0.251 | 1.366 | Low demand | nan |
| T16B-C06 | T16B-C06 | 0.251 | 1.496 | Low demand | nan |
| T16B-C08-P | T16B-C08-Piedrera | 0.251 | 1.277 | Low demand | nan |
| C50-V2 | C50-V2 | 0.252 | 1.651 | Redundant | C50-V1 |
| C29-V2 | C29-V2 | 0.252 | 2.094 | Indirect | nan |
| T10-C03 | T10-C03 | 0.252 | 1.363 | Low demand | nan |
| C114-V1 | C114-V1 | 0.252 | 1.482 | Redundant | C114-V2 |
| C40 | C40 | 0.253 | 1.483 | Low demand | nan |
| ST_L4 | L4 | 0.254 | 1.436 | Low demand | nan |
| C36 | C36 | 0.255 | 1.43 | Low demand | nan |
| MT_L1 | L1 | 0.256 | 1.054 | Low demand | nan |
| C133-V2 | C133-V2 | 0.257 | 1.251 | Low demand | nan |
| C50-V1 | C50-V1 | 0.257 | 1.633 | Indirect | nan |
| T04A-C01 | T04A-C01 | 0.258 | 1.186 | Low demand | nan |
| C18 | C18 | 0.259 | 1.376 | Low demand | nan |
| C02 | C02 | 0.259 | 1.179 | Low demand | nan |
| LM-V04 | LM-V04 | 0.261 | 1.293 | Low demand | nan |
| MC-L1 | MC-L1 | 0.262 | 1.066 | Redundant | MC-L1E |
| C21 | C21 | 0.262 | 2.289 | Redundant | C16 |
| MC-L1E | MC-L1E | 0.262 | 1.066 | Low demand | nan |
| C100 | C100 | 0.263 | 1.359 | Low demand | nan |
| C01 | C01 | 0.263 | 1.324 | Low demand | nan |
| C16 | C16 | 0.263 | 2.265 | Indirect | nan |
| C13-V1 | C13-V1 | 0.264 | 1.565 | Indirect | nan |
| T08-C01 | T08-C01 | 0.264 | 1.664 | Indirect | nan |
| C09 | C09 | 0.265 | 1.335 | Redundant | LM-C02 |
| LM-C02 | LM-C02 | 0.265 | 1.335 | Low demand | nan |
| MP-A07 | MP-A07 | 0.266 | 2.014 | Indirect | nan |
| C32-V1 | C32-V1 | 0.267 | 1.791 | Redundant | C32-V2 |
| C49-V1 | C49-V1 | 0.267 | 1.972 | Redundant | C49-V2 |
| C30 | C30 | 0.268 | 1.611 | Indirect | nan |
| C47-V2 | C47-V2 | 0.269 | 1.33 | Low demand | nan |
| MC-A20 | MC-A20 | 0.269 | 1.321 | Low demand | nan |
| C22 | C22 | 0.27 | 1.912 | Indirect | nan |
| C51-V2 | C51-V2 | 0.271 | 1.838 | Indirect | nan |
| C94 | C94 | 0.273 | 1.752 | Redundant | C92 |
| C25 | C25 | 0.275 | 1.078 | Low demand | nan |
| C114-V2 | C114-V2 | 0.275 | 1.319 | Low demand | nan |
| C32-V2 | C32-V2 | 0.276 | 1.73 | Indirect | nan |
| MC-A21 | MC-A21 | 0.276 | 1.377 | Low demand | nan |
| MP-A03 | MP-A03 | 0.279 | 2.209 | Indirect | nan |
| C10 | C10 | 0.279 | 1.453 | Redundant | LM-C03 |
| LM-C03 | LM-C03 | 0.279 | 1.453 | Low demand | nan |
| C08 | C08 | 0.282 | 1.871 | Indirect | nan |
| T01 | T01 | 0.282 | 1.596 | Indirect | nan |
| C12-V1 | C12-V1 | 0.283 | 1.531 | Indirect | nan |
| C109 | C109 | 0.284 | 1.147 | Low demand | nan |
| C85 | C85 | 0.284 | 1.154 | Low demand | nan |
| C04 | C04 | 0.285 | 2.03 | Indirect | nan |
| C75 | C75 | 0.285 | 1.449 | Low demand | nan |
| C92 | C92 | 0.287 | 1.28 | Low demand | nan |
| C49-V2 | C49-V2 | 0.292 | 1.646 | Indirect | nan |
| C77 | C77 | 0.292 | 1.323 | Low demand | nan |
| C23 | C23 | 0.293 | 1.646 | Indirect | nan |
| MC-A08 | MC-A08 | 0.294 | 1.458 | Low demand | nan |
| C29-V1 | C29-V1 | 0.294 | 1.335 | Low demand | nan |
| MC-A18 | MC-A18 | 0.304 | 1.319 | Redundant | MC-A15 |
| C47-V1 | C47-V1 | 0.308 | 1.556 | Indirect | nan |
| C83 | C83 | 0.311 | 1.244 | Redundant | C48 |
| C61 | C61 | 0.312 | 1.838 | Indirect | nan |
| C13-V2 | C13-V2 | 0.312 | 1.562 | Indirect | nan |
| C13-V3 | C13-V3 | 0.313 | 2.362 | Indirect | nan |
| ST_L2 | L2 | 0.318 | 1.831 | Indirect | nan |
| T14B-C03-1 | T14B-C03-1 | 0.321 | 1.235 | Redundant | T14B-C03-2 |
| C44 | C44 | 0.328 | 1.779 | Indirect | nan |
| C78-V1 | C78-V1 | 0.34 | 2.138 | Indirect | nan |
| MC-A17 | MC-A17 | 0.342 | 1.749 | Indirect | nan |
| T16B-C07-C | T16B-C07-Ceibas | 0.342 | 1.549 | Indirect | nan |
| MC-A07 | MC-A07 | 0.345 | 1.923 | Indirect | nan |
| MC-A15 | MC-A15 | 0.355 | 1.552 | Indirect | nan |
| MC-A16 | MC-A16 | 0.364 | 2.706 | Indirect | nan |
| MC-A13 | MC-A13 | 0.365 | 1.859 | Indirect | nan |

## Modification Proposals

- **C01** (retire): Route has low demand-gain (f1=0.006, score=0.263) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C02** (retire): Route has low demand-gain (f1=0.005, score=0.259) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C03** (retire): Route has low demand-gain (f1=0.002, score=0.227) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C04** (shortcut): Route detour_ratio=2.03 > 1.5. Current route_km=12.7km; estimated shortcut=6.9km (straight_line_km=6.3km x 1.1).
  - Current score: 0.285 -> Proposed score: 0.333
- **C05** (retire): Route has low demand-gain (f1=0.003, score=0.217) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C06** (shortcut): Route detour_ratio=1.95 > 1.5. Current route_km=23.8km; estimated shortcut=13.4km (straight_line_km=12.2km x 1.1).
  - Current score: 0.193 -> Proposed score: 0.280
- **C07-V1** (retire): Route has low demand-gain (f1=0.003, score=0.233) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C07-V2** (retire): Route has low demand-gain (f1=0.002, score=0.221) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C08** (shortcut): Route detour_ratio=1.87 > 1.5. Current route_km=13.2km; estimated shortcut=7.8km (straight_line_km=7.1km x 1.1).
  - Current score: 0.282 -> Proposed score: 0.327
- **C09** (merge): Route overlaps 100.0% of served AGEBs with LM-C02 (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: LM-C02
- **C10** (merge): Route overlaps 100.0% of served AGEBs with LM-C03 (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: LM-C03
- **C100** (retire): Route has low demand-gain (f1=0.021, score=0.263) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C101** (shortcut): Route detour_ratio=1.60 > 1.5. Current route_km=25.1km; estimated shortcut=17.2km (straight_line_km=15.7km x 1.1).
  - Current score: 0.177 -> Proposed score: 0.242
- **C102** (shortcut): Route detour_ratio=1.73 > 1.5. Current route_km=47.6km; estimated shortcut=30.2km (straight_line_km=27.4km x 1.1).
  - Current score: 0.152 -> Proposed score: 0.152
- **C103** (shortcut): Route detour_ratio=2.35 > 1.5. Current route_km=39.3km; estimated shortcut=18.4km (straight_line_km=16.7km x 1.1).
  - Current score: 0.169 -> Proposed score: 0.266
- **C104** (shortcut): Route detour_ratio=2.96 > 1.5. Current route_km=27.6km; estimated shortcut=10.3km (straight_line_km=9.3km x 1.1).
  - Current score: 0.156 -> Proposed score: 0.300
- **C105** (shortcut): Route detour_ratio=2.45 > 1.5. Current route_km=26.7km; estimated shortcut=12.0km (straight_line_km=10.9km x 1.1).
  - Current score: 0.168 -> Proposed score: 0.291
- **C106** (shortcut): Route detour_ratio=1.76 > 1.5. Current route_km=24.5km; estimated shortcut=15.3km (straight_line_km=13.9km x 1.1).
  - Current score: 0.200 -> Proposed score: 0.277
- **C107** (shortcut): Route detour_ratio=1.56 > 1.5. Current route_km=18.7km; estimated shortcut=13.2km (straight_line_km=12.0km x 1.1).
  - Current score: 0.239 -> Proposed score: 0.285
- **C108** (shortcut): Route detour_ratio=5.58 > 1.5. Current route_km=82.8km; estimated shortcut=16.3km (straight_line_km=14.8km x 1.1).
  - Current score: 0.138 -> Proposed score: 0.253
- **C109** (retire): Route has low demand-gain (f1=0.002, score=0.284) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C110-V1** (shortcut): Route detour_ratio=1.52 > 1.5. Current route_km=21.8km; estimated shortcut=15.8km (straight_line_km=14.3km x 1.1).
  - Current score: 0.206 -> Proposed score: 0.256
- **C110-V2** (merge): Route overlaps 65.5% of served AGEBs with C109 (Jaccard=0.66). Consolidation improves frequency without expanding coverage.
  - Paired with: C109
- **C111-V1** (merge): Route overlaps 63.9% of served AGEBs with C111-V3 (Jaccard=0.64). Consolidation improves frequency without expanding coverage.
  - Paired with: C111-V3
- **C111-V2** (retire): Route has low demand-gain (f1=0.036, score=0.217) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C111-V3** (retire): Route has low demand-gain (f1=0.015, score=0.154) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C112** (retire): Route has low demand-gain (f1=0.065, score=0.200) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C113-V1** (shortcut): Route detour_ratio=1.51 > 1.5. Current route_km=19.9km; estimated shortcut=14.5km (straight_line_km=13.2km x 1.1).
  - Current score: 0.243 -> Proposed score: 0.288
- **C113-V2** (shortcut): Route detour_ratio=1.53 > 1.5. Current route_km=20.2km; estimated shortcut=14.5km (straight_line_km=13.2km x 1.1).
  - Current score: 0.250 -> Proposed score: 0.298
- **C114-V1** (merge): Route overlaps 68.0% of served AGEBs with C114-V2 (Jaccard=0.68). Consolidation improves frequency without expanding coverage.
  - Paired with: C114-V2
- **C114-V2** (retire): Route has low demand-gain (f1=0.024, score=0.275) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C115** (shortcut): Route detour_ratio=1.67 > 1.5. Current route_km=21.4km; estimated shortcut=14.1km (straight_line_km=12.9km x 1.1).
  - Current score: 0.234 -> Proposed score: 0.294
- **C116-A** (shortcut): Route detour_ratio=1.70 > 1.5. Current route_km=31.3km; estimated shortcut=20.3km (straight_line_km=18.4km x 1.1).
  - Current score: 0.199 -> Proposed score: 0.280
- **C116-B** (shortcut): Route detour_ratio=1.63 > 1.5. Current route_km=30.0km; estimated shortcut=20.3km (straight_line_km=18.4km x 1.1).
  - Current score: 0.180 -> Proposed score: 0.261
- **C117** (shortcut): Route detour_ratio=1.54 > 1.5. Current route_km=30.6km; estimated shortcut=21.9km (straight_line_km=19.9km x 1.1).
  - Current score: 0.156 -> Proposed score: 0.224
- **C118** (retire): Route has low demand-gain (f1=0.002, score=0.213) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C120** (retire): Route has low demand-gain (f1=0.001, score=0.146) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C121-B** (shortcut): Route detour_ratio=1.81 > 1.5. Current route_km=19.8km; estimated shortcut=12.1km (straight_line_km=11.0km x 1.1).
  - Current score: 0.223 -> Proposed score: 0.287
- **C122** (shortcut): Route detour_ratio=1.98 > 1.5. Current route_km=24.3km; estimated shortcut=13.5km (straight_line_km=12.3km x 1.1).
  - Current score: 0.193 -> Proposed score: 0.282
- **C123-V1** (retire): Route has low demand-gain (f1=0.003, score=0.181) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C123-V2** (merge): Route overlaps 62.3% of served AGEBs with C107 (Jaccard=0.62). Consolidation improves frequency without expanding coverage.
  - Paired with: C107
- **C124** (shortcut): Route detour_ratio=1.58 > 1.5. Current route_km=30.2km; estimated shortcut=20.9km (straight_line_km=19.0km x 1.1).
  - Current score: 0.141 -> Proposed score: 0.216
- **C125-V1** (merge): Route overlaps 71.2% of served AGEBs with C125-V2 (Jaccard=0.71). Consolidation improves frequency without expanding coverage.
  - Paired with: C125-V2
- **C125-V2** (shortcut): Route detour_ratio=1.58 > 1.5. Current route_km=38.4km; estimated shortcut=26.8km (straight_line_km=24.3km x 1.1).
  - Current score: 0.143 -> Proposed score: 0.170
- **C126-V1** (merge): Route overlaps 100.0% of served AGEBs with LM-C01 (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: LM-C01
- **C127-V1** (retire): Route has low demand-gain (f1=0.003, score=0.151) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C128** (shortcut): Route detour_ratio=1.67 > 1.5. Current route_km=35.0km; estimated shortcut=23.0km (straight_line_km=20.9km x 1.1).
  - Current score: 0.136 -> Proposed score: 0.194
- **C128A-V1** (retire): Route has low demand-gain (f1=0.007, score=0.182) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C129** (retire): Route has low demand-gain (f1=0.005, score=0.134) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C12-V1** (shortcut): Route detour_ratio=1.53 > 1.5. Current route_km=13.5km; estimated shortcut=9.7km (straight_line_km=8.8km x 1.1).
  - Current score: 0.283 -> Proposed score: 0.315
- **C130** (merge): Route overlaps 63.2% of served AGEBs with C125-V2 (Jaccard=0.63). Consolidation improves frequency without expanding coverage.
  - Paired with: C125-V2
- **C132** (shortcut): Route detour_ratio=2.29 > 1.5. Current route_km=24.3km; estimated shortcut=11.7km (straight_line_km=10.6km x 1.1).
  - Current score: 0.219 -> Proposed score: 0.324
- **C133-V1** (shortcut): Route detour_ratio=2.73 > 1.5. Current route_km=27.3km; estimated shortcut=11.0km (straight_line_km=10.0km x 1.1).
  - Current score: 0.161 -> Proposed score: 0.297
- **C133-V2** (retire): Route has low demand-gain (f1=0.006, score=0.257) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C134** (retire): Route has low demand-gain (f1=0.002, score=0.209) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C135** (shortcut): Route detour_ratio=1.77 > 1.5. Current route_km=34.8km; estimated shortcut=21.7km (straight_line_km=19.7km x 1.1).
  - Current score: 0.139 -> Proposed score: 0.209
- **C136** (shortcut): Route detour_ratio=1.84 > 1.5. Current route_km=35.4km; estimated shortcut=21.1km (straight_line_km=19.2km x 1.1).
  - Current score: 0.144 -> Proposed score: 0.218
- **C138** (shortcut): Route detour_ratio=4.93 > 1.5. Current route_km=34.0km; estimated shortcut=7.6km (straight_line_km=6.9km x 1.1).
  - Current score: 0.212 -> Proposed score: 0.399
- **C13-V1** (shortcut): Route detour_ratio=1.56 > 1.5. Current route_km=16.6km; estimated shortcut=11.7km (straight_line_km=10.6km x 1.1).
  - Current score: 0.264 -> Proposed score: 0.305
- **C13-V2** (shortcut): Route detour_ratio=1.56 > 1.5. Current route_km=9.6km; estimated shortcut=6.7km (straight_line_km=6.1km x 1.1).
  - Current score: 0.312 -> Proposed score: 0.336
- **C13-V3** (shortcut): Route detour_ratio=2.36 > 1.5. Current route_km=10.2km; estimated shortcut=4.7km (straight_line_km=4.3km x 1.1).
  - Current score: 0.313 -> Proposed score: 0.358
- **C14-V1** (shortcut): Route detour_ratio=1.51 > 1.5. Current route_km=36.8km; estimated shortcut=26.8km (straight_line_km=24.3km x 1.1).
  - Current score: 0.136 -> Proposed score: 0.163
- **C14-V2** (shortcut): Route detour_ratio=1.57 > 1.5. Current route_km=24.6km; estimated shortcut=17.2km (straight_line_km=15.7km x 1.1).
  - Current score: 0.181 -> Proposed score: 0.243
- **C15** (retire): Route has low demand-gain (f1=0.019, score=0.156) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C16** (shortcut): Route detour_ratio=2.27 > 1.5. Current route_km=15.4km; estimated shortcut=7.5km (straight_line_km=6.8km x 1.1).
  - Current score: 0.263 -> Proposed score: 0.329
- **C17** (shortcut): Route detour_ratio=1.92 > 1.5. Current route_km=25.9km; estimated shortcut=14.8km (straight_line_km=13.5km x 1.1).
  - Current score: 0.176 -> Proposed score: 0.268
- **C18** (retire): Route has low demand-gain (f1=0.002, score=0.259) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C19** (shortcut): Route detour_ratio=1.76 > 1.5. Current route_km=25.0km; estimated shortcut=15.6km (straight_line_km=14.1km x 1.1).
  - Current score: 0.183 -> Proposed score: 0.261
- **C20-V1** (shortcut): Route detour_ratio=1.66 > 1.5. Current route_km=23.4km; estimated shortcut=15.5km (straight_line_km=14.1km x 1.1).
  - Current score: 0.197 -> Proposed score: 0.263
- **C21** (merge): Route overlaps 97.5% of served AGEBs with C16 (Jaccard=0.97). Consolidation improves frequency without expanding coverage.
  - Paired with: C16
- **C22** (shortcut): Route detour_ratio=1.91 > 1.5. Current route_km=15.5km; estimated shortcut=8.9km (straight_line_km=8.1km x 1.1).
  - Current score: 0.270 -> Proposed score: 0.324
- **C23** (shortcut): Route detour_ratio=1.65 > 1.5. Current route_km=11.9km; estimated shortcut=8.0km (straight_line_km=7.2km x 1.1).
  - Current score: 0.293 -> Proposed score: 0.326
- **C25** (retire): Route has low demand-gain (f1=0.005, score=0.275) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C26** (retire): Route has low demand-gain (f1=0.001, score=0.204) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C27** (shortcut): Route detour_ratio=2.04 > 1.5. Current route_km=27.8km; estimated shortcut=15.0km (straight_line_km=13.6km x 1.1).
  - Current score: 0.159 -> Proposed score: 0.266
- **C28** (shortcut): Route detour_ratio=1.64 > 1.5. Current route_km=24.7km; estimated shortcut=16.6km (straight_line_km=15.1km x 1.1).
  - Current score: 0.188 -> Proposed score: 0.256
- **C29-V1** (retire): Route has low demand-gain (f1=0.001, score=0.294) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C29-V2** (shortcut): Route detour_ratio=2.09 > 1.5. Current route_km=18.9km; estimated shortcut=9.9km (straight_line_km=9.0km x 1.1).
  - Current score: 0.252 -> Proposed score: 0.326
- **C30** (shortcut): Route detour_ratio=1.61 > 1.5. Current route_km=14.3km; estimated shortcut=9.8km (straight_line_km=8.9km x 1.1).
  - Current score: 0.268 -> Proposed score: 0.306
- **C31** (shortcut): Route detour_ratio=1.84 > 1.5. Current route_km=20.0km; estimated shortcut=11.9km (straight_line_km=10.9km x 1.1).
  - Current score: 0.224 -> Proposed score: 0.291
- **C32-V1** (merge): Route overlaps 67.6% of served AGEBs with C32-V2 (Jaccard=0.68). Consolidation improves frequency without expanding coverage.
  - Paired with: C32-V2
- **C32-V2** (shortcut): Route detour_ratio=1.73 > 1.5. Current route_km=14.6km; estimated shortcut=9.3km (straight_line_km=8.4km x 1.1).
  - Current score: 0.276 -> Proposed score: 0.321
- **C33** (shortcut): Route detour_ratio=1.80 > 1.5. Current route_km=20.7km; estimated shortcut=12.7km (straight_line_km=11.5km x 1.1).
  - Current score: 0.225 -> Proposed score: 0.292
- **C34** (retire): Route has low demand-gain (f1=0.002, score=0.239) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C35** (shortcut): Route detour_ratio=1.60 > 1.5. Current route_km=21.4km; estimated shortcut=14.7km (straight_line_km=13.4km x 1.1).
  - Current score: 0.224 -> Proposed score: 0.280
- **C36** (retire): Route has low demand-gain (f1=0.008, score=0.255) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C37-V1** (merge): Route overlaps 82.4% of served AGEBs with C37-V2 (Jaccard=0.82). Consolidation improves frequency without expanding coverage.
  - Paired with: C37-V2
- **C37-V2** (shortcut): Route detour_ratio=1.71 > 1.5. Current route_km=23.4km; estimated shortcut=15.1km (straight_line_km=13.7km x 1.1).
  - Current score: 0.203 -> Proposed score: 0.273
- **C38-V1** (merge): Route overlaps 80.0% of served AGEBs with C39-V1 (Jaccard=0.80). Consolidation improves frequency without expanding coverage.
  - Paired with: C39-V1
- **C38-V2** (merge): Route overlaps 72.6% of served AGEBs with C39-V1 (Jaccard=0.73). Consolidation improves frequency without expanding coverage.
  - Paired with: C39-V1
- **C39-V1** (retire): Route has low demand-gain (f1=0.004, score=0.204) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C39-V2** (merge): Route overlaps 92.9% of served AGEBs with C39-V1 (Jaccard=0.93). Consolidation improves frequency without expanding coverage.
  - Paired with: C39-V1
- **C40** (retire): Route has low demand-gain (f1=0.021, score=0.253) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C41-V1** (shortcut): Route detour_ratio=1.70 > 1.5. Current route_km=28.1km; estimated shortcut=18.2km (straight_line_km=16.6km x 1.1).
  - Current score: 0.165 -> Proposed score: 0.248
- **C41-V2** (shortcut): Route detour_ratio=1.56 > 1.5. Current route_km=25.8km; estimated shortcut=18.2km (straight_line_km=16.6km x 1.1).
  - Current score: 0.208 -> Proposed score: 0.272
- **C42** (shortcut): Route detour_ratio=1.64 > 1.5. Current route_km=18.1km; estimated shortcut=12.1km (straight_line_km=11.0km x 1.1).
  - Current score: 0.236 -> Proposed score: 0.286
- **C43-V1** (shortcut): Route detour_ratio=2.52 > 1.5. Current route_km=20.2km; estimated shortcut=8.8km (straight_line_km=8.0km x 1.1).
  - Current score: 0.217 -> Proposed score: 0.312
- **C43-V2** (shortcut): Route detour_ratio=1.62 > 1.5. Current route_km=18.2km; estimated shortcut=12.4km (straight_line_km=11.2km x 1.1).
  - Current score: 0.240 -> Proposed score: 0.288
- **C43-V3** (merge): Route overlaps 74.5% of served AGEBs with C43-V2 (Jaccard=0.74). Consolidation improves frequency without expanding coverage.
  - Paired with: C43-V2
- **C44** (shortcut): Route detour_ratio=1.78 > 1.5. Current route_km=8.2km; estimated shortcut=5.1km (straight_line_km=4.6km x 1.1).
  - Current score: 0.328 -> Proposed score: 0.354
- **C46-V1** (retire): Route has low demand-gain (f1=0.002, score=0.189) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C46-V2** (shortcut): Route detour_ratio=1.55 > 1.5. Current route_km=28.3km; estimated shortcut=20.0km (straight_line_km=18.2km x 1.1).
  - Current score: 0.151 -> Proposed score: 0.220
- **C47-V1** (shortcut): Route detour_ratio=1.56 > 1.5. Current route_km=13.3km; estimated shortcut=9.4km (straight_line_km=8.5km x 1.1).
  - Current score: 0.308 -> Proposed score: 0.340
- **C47-V2** (retire): Route has low demand-gain (f1=0.019, score=0.269) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C49-V1** (merge): Route overlaps 89.7% of served AGEBs with C49-V2 (Jaccard=0.90). Consolidation improves frequency without expanding coverage.
  - Paired with: C49-V2
- **C49-V2** (shortcut): Route detour_ratio=1.65 > 1.5. Current route_km=11.8km; estimated shortcut=7.9km (straight_line_km=7.2km x 1.1).
  - Current score: 0.292 -> Proposed score: 0.324
- **C50-V1** (shortcut): Route detour_ratio=1.63 > 1.5. Current route_km=20.4km; estimated shortcut=13.8km (straight_line_km=12.5km x 1.1).
  - Current score: 0.257 -> Proposed score: 0.313
- **C50-V2** (merge): Route overlaps 91.2% of served AGEBs with C50-V1 (Jaccard=0.91). Consolidation improves frequency without expanding coverage.
  - Paired with: C50-V1
- **C51-V2** (shortcut): Route detour_ratio=1.84 > 1.5. Current route_km=14.5km; estimated shortcut=8.7km (straight_line_km=7.9km x 1.1).
  - Current score: 0.271 -> Proposed score: 0.319
- **C53** (shortcut): Route detour_ratio=1.67 > 1.5. Current route_km=35.8km; estimated shortcut=23.6km (straight_line_km=21.5km x 1.1).
  - Current score: 0.140 -> Proposed score: 0.194
- **C54** (retire): Route has low demand-gain (f1=0.003, score=0.146) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C58-V1** (retire): Route has low demand-gain (f1=0.014, score=0.231) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C58-V2** (shortcut): Route detour_ratio=1.57 > 1.5. Current route_km=26.3km; estimated shortcut=18.4km (straight_line_km=16.7km x 1.1).
  - Current score: 0.196 -> Proposed score: 0.262
- **C60** (merge): Route overlaps 68.8% of served AGEBs with C58-V1 (Jaccard=0.69). Consolidation improves frequency without expanding coverage.
  - Paired with: C58-V1
- **C61** (shortcut): Route detour_ratio=1.84 > 1.5. Current route_km=11.6km; estimated shortcut=7.0km (straight_line_km=6.3km x 1.1).
  - Current score: 0.312 -> Proposed score: 0.351
- **C62** (retire): Route has low demand-gain (f1=0.002, score=0.226) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C64** (retire): Route has low demand-gain (f1=0.006, score=0.145) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C65** (retire): Route has low demand-gain (f1=0.002, score=0.164) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C66-V1** (retire): Route has low demand-gain (f1=0.001, score=0.202) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C66-V2** (shortcut): Route detour_ratio=1.64 > 1.5. Current route_km=24.3km; estimated shortcut=16.3km (straight_line_km=14.8km x 1.1).
  - Current score: 0.190 -> Proposed score: 0.257
- **C67-V1** (merge): Route overlaps 72.6% of served AGEBs with C111-V3 (Jaccard=0.73). Consolidation improves frequency without expanding coverage.
  - Paired with: C111-V3
- **C67-V2** (shortcut): Route detour_ratio=1.63 > 1.5. Current route_km=31.8km; estimated shortcut=21.5km (straight_line_km=19.5km x 1.1).
  - Current score: 0.175 -> Proposed score: 0.246
- **C69** (shortcut): Route detour_ratio=2.26 > 1.5. Current route_km=17.8km; estimated shortcut=8.7km (straight_line_km=7.9km x 1.1).
  - Current score: 0.249 -> Proposed score: 0.325
- **C70** (shortcut): Route detour_ratio=2.50 > 1.5. Current route_km=22.5km; estimated shortcut=9.9km (straight_line_km=9.0km x 1.1).
  - Current score: 0.201 -> Proposed score: 0.306
- **C71** (shortcut): Route detour_ratio=1.62 > 1.5. Current route_km=28.2km; estimated shortcut=19.1km (straight_line_km=17.4km x 1.1).
  - Current score: 0.154 -> Proposed score: 0.229
- **C73** (shortcut): Route detour_ratio=2.65 > 1.5. Current route_km=21.2km; estimated shortcut=8.8km (straight_line_km=8.0km x 1.1).
  - Current score: 0.211 -> Proposed score: 0.314
- **C74** (retire): Route has low demand-gain (f1=0.001, score=0.226) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C75** (retire): Route has low demand-gain (f1=0.001, score=0.285) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C76-V1** (merge): Route overlaps 87.2% of served AGEBs with C76-V2 (Jaccard=0.87). Consolidation improves frequency without expanding coverage.
  - Paired with: C76-V2
- **C76-V2** (retire): Route has low demand-gain (f1=0.029, score=0.217) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C77** (retire): Route has low demand-gain (f1=0.056, score=0.292) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C78-V1** (shortcut): Route detour_ratio=2.14 > 1.5. Current route_km=17.1km; estimated shortcut=8.8km (straight_line_km=8.0km x 1.1).
  - Current score: 0.340 -> Proposed score: 0.409
- **C79** (shortcut): Route detour_ratio=1.74 > 1.5. Current route_km=22.3km; estimated shortcut=14.1km (straight_line_km=12.8km x 1.1).
  - Current score: 0.203 -> Proposed score: 0.271
- **C80-V1** (shortcut): Route detour_ratio=1.91 > 1.5. Current route_km=28.1km; estimated shortcut=16.2km (straight_line_km=14.7km x 1.1).
  - Current score: 0.171 -> Proposed score: 0.270
- **C80-V2** (merge): Route overlaps 100.0% of served AGEBs with C100 (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: C100
- **C83** (merge): Route overlaps 71.4% of served AGEBs with C48 (Jaccard=0.71). Consolidation improves frequency without expanding coverage.
  - Paired with: C48
- **C85** (retire): Route has low demand-gain (f1=0.002, score=0.284) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C86** (shortcut): Route detour_ratio=1.59 > 1.5. Current route_km=21.7km; estimated shortcut=15.1km (straight_line_km=13.7km x 1.1).
  - Current score: 0.248 -> Proposed score: 0.303
- **C88-V2** (retire): Route has low demand-gain (f1=0.006, score=0.215) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C89** (merge): Route overlaps 80.8% of served AGEBs with C88-V2 (Jaccard=0.81). Consolidation improves frequency without expanding coverage.
  - Paired with: C88-V2
- **C90** (merge): Route overlaps 100.0% of served AGEBs with C92 (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: C92
- **C92** (retire): Route has low demand-gain (f1=0.045, score=0.287) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C93** (shortcut): Route detour_ratio=2.41 > 1.5. Current route_km=33.1km; estimated shortcut=15.1km (straight_line_km=13.7km x 1.1).
  - Current score: 0.146 -> Proposed score: 0.270
- **C94** (merge): Route overlaps 100.0% of served AGEBs with C92 (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: C92
- **C95** (shortcut): Route detour_ratio=1.52 > 1.5. Current route_km=18.6km; estimated shortcut=13.5km (straight_line_km=12.3km x 1.1).
  - Current score: 0.236 -> Proposed score: 0.278
- **C96-V2** (retire): Route has low demand-gain (f1=0.002, score=0.245) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C97-V1** (retire): Route has low demand-gain (f1=0.024, score=0.239) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C97-V2** (retire): Route has low demand-gain (f1=0.021, score=0.225) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C99** (shortcut): Route detour_ratio=1.99 > 1.5. Current route_km=25.1km; estimated shortcut=13.9km (straight_line_km=12.7km x 1.1).
  - Current score: 0.193 -> Proposed score: 0.286
- **T01** (shortcut): Route detour_ratio=1.60 > 1.5. Current route_km=12.7km; estimated shortcut=8.7km (straight_line_km=7.9km x 1.1).
  - Current score: 0.282 -> Proposed score: 0.315
- **T02** (retire): Route has low demand-gain (f1=0.001, score=0.247) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T03** (shortcut): Route detour_ratio=1.55 > 1.5. Current route_km=23.0km; estimated shortcut=16.4km (straight_line_km=14.9km x 1.1).
  - Current score: 0.226 -> Proposed score: 0.282
- **T04A-1** (retire): Route has low demand-gain (f1=0.002, score=0.135) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T04A-2** (shortcut): Route detour_ratio=1.60 > 1.5. Current route_km=35.9km; estimated shortcut=24.7km (straight_line_km=22.5km x 1.1).
  - Current score: 0.137 -> Proposed score: 0.181
- **T04A-C01** (retire): Route has low demand-gain (f1=0.019, score=0.258) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T04B-1** (retire): Route has low demand-gain (f1=0.011, score=0.182) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T04B-2** (retire): Route has low demand-gain (f1=0.003, score=0.236) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T04B-3** (retire): Route has low demand-gain (f1=0.001, score=0.214) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T04B-4** (shortcut): Route detour_ratio=1.51 > 1.5. Current route_km=15.6km; estimated shortcut=11.3km (straight_line_km=10.3km x 1.1).
  - Current score: 0.244 -> Proposed score: 0.280
- **T06** (retire): Route has low demand-gain (f1=0.002, score=0.240) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T07** (shortcut): Route detour_ratio=1.59 > 1.5. Current route_km=29.3km; estimated shortcut=20.2km (straight_line_km=18.4km x 1.1).
  - Current score: 0.146 -> Proposed score: 0.221
- **T07-C02** (shortcut): Route detour_ratio=1.73 > 1.5. Current route_km=23.0km; estimated shortcut=14.7km (straight_line_km=13.3km x 1.1).
  - Current score: 0.218 -> Proposed score: 0.287
- **T08** (shortcut): Route detour_ratio=1.69 > 1.5. Current route_km=18.3km; estimated shortcut=11.9km (straight_line_km=10.8km x 1.1).
  - Current score: 0.234 -> Proposed score: 0.288
- **T08-C01** (shortcut): Route detour_ratio=1.66 > 1.5. Current route_km=14.4km; estimated shortcut=9.5km (straight_line_km=8.7km x 1.1).
  - Current score: 0.264 -> Proposed score: 0.305
- **T09-B** (shortcut): Route detour_ratio=3.06 > 1.5. Current route_km=18.4km; estimated shortcut=6.6km (straight_line_km=6.0km x 1.1).
  - Current score: 0.238 -> Proposed score: 0.336
- **T09-O** (shortcut): Route detour_ratio=2.93 > 1.5. Current route_km=26.4km; estimated shortcut=9.9km (straight_line_km=9.0km x 1.1).
  - Current score: 0.170 -> Proposed score: 0.308
- **T10** (merge): Route overlaps 65.0% of served AGEBs with T10-C01 (Jaccard=0.65). Consolidation improves frequency without expanding coverage.
  - Paired with: T10-C01
- **T10-C01** (retire): Route has low demand-gain (f1=0.002, score=0.251) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T10-C02** (merge): Route overlaps 70.3% of served AGEBs with T10-C01 (Jaccard=0.70). Consolidation improves frequency without expanding coverage.
  - Paired with: T10-C01
- **T10-C03** (retire): Route has low demand-gain (f1=0.012, score=0.252) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T11A** (retire): Route has low demand-gain (f1=0.002, score=0.236) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T11A-C01** (merge): Route overlaps 76.4% of served AGEBs with T11A (Jaccard=0.76). Consolidation improves frequency without expanding coverage.
  - Paired with: T11A
- **T11A-C02** (retire): Route has low demand-gain (f1=0.002, score=0.222) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T11A-C03** (merge): Route overlaps 66.2% of served AGEBs with T11A-C02 (Jaccard=0.66). Consolidation improves frequency without expanding coverage.
  - Paired with: T11A-C02
- **T11B** (retire): Route has low demand-gain (f1=0.002, score=0.135) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T13A** (retire): Route has low demand-gain (f1=0.017, score=0.140) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T14B** (shortcut): Route detour_ratio=86.30 > 1.5. Current route_km=1691.7km; estimated shortcut=21.6km (straight_line_km=19.6km x 1.1).
  - Current score: 0.171 -> Proposed score: 0.242
- **T14B-C03-1** (merge): Route overlaps 68.4% of served AGEBs with T14B-C03-2 (Jaccard=0.68). Consolidation improves frequency without expanding coverage.
  - Paired with: T14B-C03-2
- **T15** (shortcut): Route detour_ratio=1.53 > 1.5. Current route_km=28.4km; estimated shortcut=20.4km (straight_line_km=18.5km x 1.1).
  - Current score: 0.159 -> Proposed score: 0.226
- **T16B** (retire): Route has low demand-gain (f1=0.016, score=0.176) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T16B-C06** (retire): Route has low demand-gain (f1=0.037, score=0.251) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T16B-C07-C** (shortcut): Route detour_ratio=1.55 > 1.5. Current route_km=3.4km; estimated shortcut=2.4km (straight_line_km=2.2km x 1.1).
  - Current score: 0.342 -> Proposed score: 0.350
- **T16B-C07-V** (merge): Route overlaps 83.8% of served AGEBs with T16B-C08-P (Jaccard=0.84). Consolidation improves frequency without expanding coverage.
  - Paired with: T16B-C08-P
- **T16B-C08-P** (retire): Route has low demand-gain (f1=0.035, score=0.251) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T17** (retire): Route has low demand-gain (f1=0.001, score=0.168) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **T17-C01** (shortcut): Route detour_ratio=1.61 > 1.5. Current route_km=40.2km; estimated shortcut=27.4km (straight_line_km=24.9km x 1.1).
  - Current score: 0.139 -> Proposed score: 0.161
- **T18-1-L** (merge): Route overlaps 93.7% of served AGEBs with T18-2-L (Jaccard=0.94). Consolidation improves frequency without expanding coverage.
  - Paired with: T18-2-L
- **T18-1-T** (merge): Route overlaps 78.3% of served AGEBs with T18-2-L (Jaccard=0.78). Consolidation improves frequency without expanding coverage.
  - Paired with: T18-2-L
- **T18-2-L** (shortcut): Route detour_ratio=3.01 > 1.5. Current route_km=26.9km; estimated shortcut=9.8km (straight_line_km=8.9km x 1.1).
  - Current score: 0.165 -> Proposed score: 0.308
- **T18-2-T** (merge): Route overlaps 83.8% of served AGEBs with T18-2-L (Jaccard=0.84). Consolidation improves frequency without expanding coverage.
  - Paired with: T18-2-L
- **MC-A07** (shortcut): Route detour_ratio=1.92 > 1.5. Current route_km=4.2km; estimated shortcut=2.4km (straight_line_km=2.2km x 1.1).
  - Current score: 0.345 -> Proposed score: 0.360
- **MC-A08** (retire): Route has low demand-gain (f1=0.004, score=0.294) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MC-A13** (shortcut): Route detour_ratio=1.86 > 1.5. Current route_km=3.4km; estimated shortcut=2.0km (straight_line_km=1.8km x 1.1).
  - Current score: 0.365 -> Proposed score: 0.377
- **MC-A15** (shortcut): Route detour_ratio=1.55 > 1.5. Current route_km=4.6km; estimated shortcut=3.3km (straight_line_km=3.0km x 1.1).
  - Current score: 0.355 -> Proposed score: 0.366
- **MC-A16** (shortcut): Route detour_ratio=2.71 > 1.5. Current route_km=5.0km; estimated shortcut=2.0km (straight_line_km=1.9km x 1.1).
  - Current score: 0.364 -> Proposed score: 0.389
- **MC-A17** (shortcut): Route detour_ratio=1.75 > 1.5. Current route_km=4.0km; estimated shortcut=2.5km (straight_line_km=2.3km x 1.1).
  - Current score: 0.342 -> Proposed score: 0.354
- **MC-A18** (merge): Route overlaps 60.0% of served AGEBs with MC-A15 (Jaccard=0.60). Consolidation improves frequency without expanding coverage.
  - Paired with: MC-A15
- **MC-A19** (shortcut): Route detour_ratio=1.55 > 1.5. Current route_km=20.3km; estimated shortcut=14.4km (straight_line_km=13.1km x 1.1).
  - Current score: 0.220 -> Proposed score: 0.269
- **MC-A20** (retire): Route has low demand-gain (f1=0.006, score=0.269) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MC-A21** (retire): Route has low demand-gain (f1=0.034, score=0.276) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MP-A01** (retire): Route has low demand-gain (f1=0.001, score=0.241) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MP-A02** (shortcut): Route detour_ratio=1.67 > 1.5. Current route_km=19.3km; estimated shortcut=12.7km (straight_line_km=11.6km x 1.1).
  - Current score: 0.228 -> Proposed score: 0.283
- **MP-A03** (shortcut): Route detour_ratio=2.21 > 1.5. Current route_km=13.1km; estimated shortcut=6.5km (straight_line_km=5.9km x 1.1).
  - Current score: 0.279 -> Proposed score: 0.334
- **MP-A04** (shortcut): Route detour_ratio=1.56 > 1.5. Current route_km=18.4km; estimated shortcut=12.9km (straight_line_km=11.8km x 1.1).
  - Current score: 0.230 -> Proposed score: 0.276
- **MP-A05-1** (shortcut): Route detour_ratio=3.11 > 1.5. Current route_km=47.1km; estimated shortcut=16.7km (straight_line_km=15.1km x 1.1).
  - Current score: 0.150 -> Proposed score: 0.261
- **MP-A06** (retire): Route has low demand-gain (f1=0.002, score=0.176) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MP-A07** (shortcut): Route detour_ratio=2.01 > 1.5. Current route_km=15.6km; estimated shortcut=8.5km (straight_line_km=7.8km x 1.1).
  - Current score: 0.266 -> Proposed score: 0.325
- **MP-C01** (shortcut): Route detour_ratio=1.90 > 1.5. Current route_km=32.9km; estimated shortcut=19.1km (straight_line_km=17.4km x 1.1).
  - Current score: 0.150 -> Proposed score: 0.241
- **MP-C02** (shortcut): Route detour_ratio=1.69 > 1.5. Current route_km=28.7km; estimated shortcut=18.7km (straight_line_km=17.0km x 1.1).
  - Current score: 0.151 -> Proposed score: 0.235
- **MP-C03** (merge): Route overlaps 67.3% of served AGEBs with MP-T03 (Jaccard=0.67). Consolidation improves frequency without expanding coverage.
  - Paired with: MP-T03
- **MC-L1** (merge): Route overlaps 100.0% of served AGEBs with MC-L1E (Jaccard=1.00). Consolidation improves frequency without expanding coverage.
  - Paired with: MC-L1E
- **MC-L1E** (retire): Route has low demand-gain (f1=0.003, score=0.262) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MP-T01** (shortcut): Route detour_ratio=2.24 > 1.5. Current route_km=42.3km; estimated shortcut=20.8km (straight_line_km=18.9km x 1.1).
  - Current score: 0.142 -> Proposed score: 0.219
- **MP-T02** (retire): Route has low demand-gain (f1=0.002, score=0.192) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MP-T03** (retire): Route has low demand-gain (f1=0.012, score=0.239) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **C98** (shortcut): Route detour_ratio=1.80 > 1.5. Current route_km=45.3km; estimated shortcut=27.7km (straight_line_km=25.2km x 1.1).
  - Current score: 0.137 -> Proposed score: 0.156
- **MT_L3** (retire): Route has low demand-gain (f1=0.002, score=0.223) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **MT_L1** (retire): Route has low demand-gain (f1=0.001, score=0.256) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **ST_L1** (merge): Route overlaps 66.7% of served AGEBs with C109 (Jaccard=0.67). Consolidation improves frequency without expanding coverage.
  - Paired with: C109
- **ST_L2** (shortcut): Route detour_ratio=1.83 > 1.5. Current route_km=8.6km; estimated shortcut=5.2km (straight_line_km=4.7km x 1.1).
  - Current score: 0.318 -> Proposed score: 0.347
- **ST_L4** (retire): Route has low demand-gain (f1=0.025, score=0.254) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **LM-V03** (retire): Route has low demand-gain (f1=0.003, score=0.136) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **LM-V04** (retire): Route has low demand-gain (f1=0.006, score=0.261) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **LM-V05** (shortcut): Route detour_ratio=1.62 > 1.5. Current route_km=19.7km; estimated shortcut=13.4km (straight_line_km=12.2km x 1.1).
  - Current score: 0.227 -> Proposed score: 0.280
- **LM-V01** (merge): Route overlaps 62.3% of served AGEBs with C125-V2 (Jaccard=0.62). Consolidation improves frequency without expanding coverage.
  - Paired with: C125-V2
- **LM-V02** (retire): Route has low demand-gain (f1=0.003, score=0.144) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **LM-C01** (shortcut): Route detour_ratio=1.67 > 1.5. Current route_km=29.5km; estimated shortcut=19.5km (straight_line_km=17.7km x 1.1).
  - Current score: 0.151 -> Proposed score: 0.234
- **LM-C02** (retire): Route has low demand-gain (f1=0.011, score=0.265) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.
- **LM-C03** (retire): Route has low demand-gain (f1=0.011, score=0.279) with no high-scoring overlapping route. Consider service reduction or rerouting to higher-demand corridor.

## W5 Config Used

```
w_demand_gain=0.50, w_efficiency=0.25, w_equity=0.25
max_detour_ratio=1.8, min_stop_spacing=300m, max_stop_spacing=1000m
min_daily_demand=500 trips/day, max_route_km=30km
```