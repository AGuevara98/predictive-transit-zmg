# src/w5_types.py
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class W5Config:
    max_detour_ratio: float = 1.8
    min_stop_spacing_m: float = 300.0
    max_stop_spacing_m: float = 1000.0
    min_daily_demand: float = 500.0
    max_route_km: float = 30.0
    w_demand_gain: float = 0.50
    w_efficiency: float = 0.25
    w_equity: float = 0.25
    connected_gain_factor: float = 0.50
    isolated_gain_factor: float = 0.20
    transfer_penalty: float = 0.10


@dataclass
class RouteCandidate:
    candidate_id: str
    served_ageb_ids: List[str]
    route_km: float
    n_stops: int
    straight_line_km: float
    connects_to_existing: bool = False
    # Straight-line spanning length of the corridor's demand anchors (km). When set,
    # the feasibility gate uses anchor-directness (route_km / anchor_span_km) instead of
    # endpoint detour -- the right measure for a demand-coverage corridor that curves.
    # None for routes with no anchor concept (W7 existing routes, W5 demo) -> endpoint.
    anchor_span_km: Optional[float] = None


@dataclass
class AgebContext:
    cvegeo: str
    transit_demand: float
    unserved_fraction: float   # coverage_gap_normalized: 1=unserved, 0=well-served
    equity_score: float


@dataclass
class ObjectiveResult:
    candidate_id: str
    f1_demand_gain: float      # demand-weighted accessibility gain [0, gain_factor]
    f2_route_km: float         # raw route length in km
    f3_equity: float           # mean equity score [0, 1]
    transfer_penalty: float    # flat deduction
    composite_score: float     # weighted sum of normalized objectives
    total_score: float         # composite - transfer_penalty


@dataclass
class ConstraintViolation:
    name: str
    value: float
    limit: float
    message: str


@dataclass
class ConstraintResult:
    feasible: bool
    violations: List[ConstraintViolation] = field(default_factory=list)
