"""Scenario definitions for the depot energy experiments."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    code: str
    label: str
    smart_charging: bool
    pv: bool
    bess: bool
    nearby_roofs: bool = False
    constrained_grid: bool = False
    fleet_growth: bool = False
    high_emission_factor: bool = False
    high_price: bool = False


@dataclass(frozen=True)
class RoofScenario:
    code: str
    label: str
    roof_scope: str
    availability_factor: float


OPERATIONAL_SCENARIOS: tuple[Scenario, ...] = (
    Scenario("S0", "Unmanaged charging, no PV/BESS", False, False, False),
    Scenario("S1", "Smart charging, no PV/BESS", True, False, False),
    Scenario("S2", "Smart charging with depot rooftop PV", True, True, False),
    Scenario("S3", "Smart charging with BESS only", True, False, True),
    Scenario("S4", "Smart charging with PV+BESS", True, True, True),
    Scenario("S5", "Depot and nearby rooftops with BESS", True, True, True, nearby_roofs=True),
    Scenario("S6", "PV+BESS under tight grid connection", True, True, True, constrained_grid=True),
    Scenario("S7", "Fleet expansion 2026-2035", True, True, True, fleet_growth=True),
    Scenario("S8", "High grid emission factor", True, True, True, high_emission_factor=True),
    Scenario("S9", "High electricity price", True, True, True, high_price=True),
)

ROOF_SCENARIOS: tuple[RoofScenario, ...] = (
    RoofScenario("R0", "No PV", "none", 0.00),
    RoofScenario("R1", "Internal depot roofs, conservative", "depot", 0.25),
    RoofScenario("R2", "Internal depot roofs, medium", "depot", 0.40),
    RoofScenario("R3", "Internal depot roofs, high", "depot", 0.55),
    RoofScenario("R4", "Depot plus nearby roofs, medium", "nearby", 0.40),
    RoofScenario("R5", "Maximum technical roof sensitivity", "nearby", 0.65),
)


def is_interpretable_pair(operational: Scenario, roof: RoofScenario) -> bool:
    """Return whether an operational-roof pair has a distinct interpretation."""
    if not operational.pv:
        return roof.code == "R0"
    if roof.code == "R0":
        return False
    if operational.code in {"S2", "S4"}:
        return roof.code in {"R1", "R2", "R3"}
    if operational.code == "S5":
        return roof.code in {"R4", "R5"}
    return roof.code in {"R1", "R2", "R3", "R4", "R5"}


def scenario_matrix() -> list[tuple[Scenario, RoofScenario]]:
    """Return the default operational-roof scenario combinations."""
    pairs: list[tuple[Scenario, RoofScenario]] = []
    for operational in OPERATIONAL_SCENARIOS:
        for roof in ROOF_SCENARIOS:
            if is_interpretable_pair(operational, roof):
                pairs.append((operational, roof))
    return pairs
