#!/usr/bin/env python3
"""Run the multi-depot scenario experiment from processed input tables."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
import pyomo.environ as pyo


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from energy_patios.model import build_depot_energy_hub_model  # noqa: E402


HOURS = tuple(range(24))


def solve_model(
    model: pyo.ConcreteModel,
    *,
    solver: str,
    solver_manager: str,
    neos_email: str | None,
    tee: bool,
) -> pyo.results.results_.SolverResults:
    if solver_manager == "neos":
        if not neos_email:
            raise RuntimeError("NEOS requires --neos-email or NEOS_EMAIL.")
        os.environ["NEOS_EMAIL"] = neos_email
        manager = pyo.SolverManagerFactory("neos")
        return manager.solve(model, opt=solver, tee=tee)

    opt = pyo.SolverFactory(solver)
    if not opt.available(exception_flag=False):
        raise RuntimeError(f"Local solver is not available: {solver}")
    return opt.solve(model, tee=tee)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    base = ROOT / "data" / "processed"
    required = [
        "depot_parameters.csv",
        "depot_hour_demand.csv",
        "roof_potential_by_depot.csv",
        "price_emission_hourly.csv",
        "scenario_parameters.csv",
    ]
    missing = [name for name in required if not (base / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing processed inputs: {', '.join(missing)}")
    return (
        pd.read_csv(base / "depot_parameters.csv"),
        pd.read_csv(base / "depot_hour_demand.csv"),
        pd.read_csv(base / "roof_potential_by_depot.csv"),
        pd.read_csv(base / "price_emission_hourly.csv"),
        pd.read_csv(base / "scenario_parameters.csv"),
    )


def parse_filter(values: list[str] | None) -> set[str] | None:
    if not values:
        return None
    parsed: set[str] = set()
    for item in values:
        parsed.update(part.strip().upper() for part in item.split(",") if part.strip())
    return parsed


def value_by_hour(df: pd.DataFrame, column: str) -> dict[int, float]:
    return {int(row["hour"]): float(row[column]) for _, row in df.iterrows()}


def bool_by_hour(df: pd.DataFrame, column: str) -> dict[int, bool]:
    return {int(row["hour"]): bool(row[column]) for _, row in df.iterrows()}


def roof_cap_max_kwp(roofs: pd.DataFrame, depot_id: str, buffer_m: int, column: str) -> float:
    if column == "none":
        return 0.0
    row = roofs[(roofs["depot_id"].eq(depot_id)) & (roofs["buffer_m"].eq(buffer_m))]
    if row.empty:
        return 0.0
    return max(0.0, float(row.iloc[0][column]))


def extract_dispatch(
    model: pyo.ConcreteModel,
    *,
    scenario: str,
    roof_scenario: str,
    depot_id: str,
    dt_hours: float,
) -> pd.DataFrame:
    rows = []
    for hour in HOURS:
        rows.append(
            {
                "scenario": scenario,
                "roof_scenario": roof_scenario,
                "depot_id": depot_id,
                "hour": hour,
                "grid_kw": pyo.value(model.grid[hour]),
                "pv_used_kw": pyo.value(model.pv_used[hour]),
                "pv_curtail_kw": pyo.value(model.pv_curtail[hour]),
                "bus_charge_kw": pyo.value(model.bus_charge[hour]),
                "bess_charge_kw": pyo.value(model.bess_charge[hour]),
                "bess_discharge_kw": pyo.value(model.bess_discharge[hour]),
                "bess_soc_kwh": pyo.value(model.bess_soc[hour]),
                "unserved_kwh": pyo.value(model.unserved[hour]),
                "dt_hours": dt_hours,
            }
        )
    return pd.DataFrame(rows)


def summarize(
    dispatch: pd.DataFrame,
    *,
    model: pyo.ConcreteModel,
    depot: pd.Series,
    scenario_row: pd.Series,
    pv_cap_max_kwp: float,
    grid_cap_kw: float,
    price_by_hour: dict[int, float],
    emission_by_hour: dict[int, float],
    termination: str,
    solver: str,
    solver_manager: str,
) -> dict[str, float | str]:
    dt = float(dispatch["dt_hours"].iloc[0])
    grid_energy = float((dispatch["grid_kw"] * dt).sum())
    pv_used = float((dispatch["pv_used_kw"] * dt).sum())
    pv_curtail = float((dispatch["pv_curtail_kw"] * dt).sum())
    bus_energy = float((dispatch["bus_charge_kw"] * dt).sum())
    bess_charge = float((dispatch["bess_charge_kw"] * dt).sum())
    bess_discharge = float((dispatch["bess_discharge_kw"] * dt).sum())
    unserved = float(dispatch["unserved_kwh"].sum())
    peak = float(dispatch["grid_kw"].max())
    energy_cost = float(
        sum(
            price_by_hour[int(row["hour"])] * float(row["grid_kw"]) * dt
            for _, row in dispatch.iterrows()
        )
    )
    co2 = float(
        sum(
            emission_by_hour[int(row["hour"])] * float(row["grid_kw"]) * dt
            for _, row in dispatch.iterrows()
        )
    )
    pv_generation = pv_used + pv_curtail
    installed_pv = float(pyo.value(model.pv_cap))
    installed_bess_energy = float(pyo.value(model.bess_energy_cap))
    installed_bess_power = float(pyo.value(model.bess_power_cap))

    return {
        "scenario": scenario_row["scenario"],
        "scenario_label": scenario_row["scenario_label"],
        "roof_scenario": scenario_row["roof_scenario"],
        "roof_label": scenario_row["roof_label"],
        "depot_id": depot["depot_id"],
        "depot_name": depot["depot_name"],
        "grid_cap_kw": grid_cap_kw,
        "pv_cap_max_kwp": pv_cap_max_kwp,
        "installed_pv_kwp": installed_pv,
        "installed_bess_energy_kwh": installed_bess_energy,
        "installed_bess_power_kw": installed_bess_power,
        "grid_energy_kwh": grid_energy,
        "peak_grid_kw": peak,
        "bus_charge_kwh": bus_energy,
        "unserved_kwh": unserved,
        "pv_generation_kwh": pv_generation,
        "pv_used_kwh": pv_used,
        "pv_curtailment_pct": 0.0 if pv_generation <= 0 else 100.0 * pv_curtail / pv_generation,
        "bess_charge_kwh": bess_charge,
        "bess_discharge_kwh": bess_discharge,
        "energy_cost_cop": energy_cost,
        "co2_kg": co2,
        "objective_cop": float(pyo.value(model.objective)),
        "termination_condition": termination,
        "solver": solver,
        "solver_manager": solver_manager,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solver", default="appsi_highs")
    parser.add_argument("--solver-manager", choices=("local", "neos"), default="local")
    parser.add_argument("--neos-email", default=os.getenv("NEOS_EMAIL"))
    parser.add_argument("--scenario", nargs="*", help="Scenario codes, e.g. S0 S1 or S0,S1.")
    parser.add_argument("--roof", nargs="*", help="Roof scenario codes, e.g. R0 R2 or R0,R2.")
    parser.add_argument("--depot", nargs="*", help="Depot ids, e.g. PZ001 PZ050.")
    parser.add_argument(
        "--capacity-mode",
        choices=("optimized", "technical"),
        default="optimized",
        help="Optimize PV/BESS sizes or force each enabled technology to its scenario maximum.",
    )
    parser.add_argument("--max-combinations", type=int)
    parser.add_argument("--dt-hours", type=float, default=1.0)
    parser.add_argument("--tee", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    depots, depot_hour, roofs, price_emission, scenario_params = load_inputs()

    scenario_filter = parse_filter(args.scenario)
    roof_filter = parse_filter(args.roof)
    depot_filter = parse_filter(args.depot)

    if scenario_filter is not None:
        scenario_params = scenario_params[scenario_params["scenario"].str.upper().isin(scenario_filter)]
    if roof_filter is not None:
        scenario_params = scenario_params[scenario_params["roof_scenario"].str.upper().isin(roof_filter)]
    if depot_filter is not None:
        depots = depots[depots["depot_id"].str.upper().isin(depot_filter)]

    combinations = [(scenario_row, depot_row) for _, scenario_row in scenario_params.iterrows() for _, depot_row in depots.iterrows()]
    if args.max_combinations:
        combinations = combinations[: args.max_combinations]

    price_columns = set(scenario_params["price_column"])
    emission_columns = set(scenario_params["emission_column"])
    price_profiles = {column: value_by_hour(price_emission, column) for column in price_columns}
    emission_profiles = {column: value_by_hour(price_emission, column) for column in emission_columns}
    pv_profile = value_by_hour(price_emission, "pv_kw_per_kwp")

    summaries: list[dict[str, float | str]] = []
    dispatch_frames: list[pd.DataFrame] = []

    for index, (scenario_row, depot) in enumerate(combinations, start=1):
        depot_id = str(depot["depot_id"])
        scenario = str(scenario_row["scenario"])
        roof_scenario = str(scenario_row["roof_scenario"])
        print(f"[{index}/{len(combinations)}] {scenario}-{roof_scenario} {depot_id}")

        hours = depot_hour[depot_hour["depot_id"].eq(depot_id)].sort_values("hour")
        price_by_hour = price_profiles[str(scenario_row["price_column"])]
        emission_by_hour = emission_profiles[str(scenario_row["emission_column"])]
        fleet_multiplier = float(scenario_row["fleet_multiplier"])
        required_energy = float(hours["daily_required_energy_kwh"].iloc[0]) * fleet_multiplier
        fixed = None
        if not bool(scenario_row["smart_charging"]):
            fixed = {
                int(row["hour"]): float(row["unmanaged_demand_kwh"]) * fleet_multiplier / args.dt_hours
                for _, row in hours.iterrows()
            }
        allowed = bool_by_hour(hours, "charge_allowed")

        if bool(scenario_row["pv_enabled"]):
            pv_cap_max = roof_cap_max_kwp(
                roofs,
                depot_id,
                int(scenario_row["roof_buffer_m"]),
                str(scenario_row["roof_capacity_column"]),
            )
        else:
            pv_cap_max = 0.0

        bess_energy_cap_max = float(depot["bess_energy_cap_max_kwh"]) if bool(scenario_row["bess_enabled"]) else 0.0
        bess_power_cap_max = float(depot["bess_power_cap_max_kw"]) if bool(scenario_row["bess_enabled"]) else 0.0
        grid_cap_kw = float(depot[str(scenario_row["grid_cap_column"])])

        if args.capacity_mode == "technical":
            pv_cap_kwp = pv_cap_max
            pv_cap_max_kwp = None
            bess_energy_cap_kwh = bess_energy_cap_max
            bess_energy_cap_max_kwh = None
            bess_power_cap_kw = bess_power_cap_max
            bess_power_cap_max_kw = None
        else:
            pv_cap_kwp = 0.0
            pv_cap_max_kwp = pv_cap_max
            bess_energy_cap_kwh = 0.0
            bess_energy_cap_max_kwh = bess_energy_cap_max
            bess_power_cap_kw = 0.0
            bess_power_cap_max_kw = bess_power_cap_max

        model = build_depot_energy_hub_model(
            hours=HOURS,
            price_per_kwh=price_by_hour,
            pv_kw_per_kwp=pv_profile,
            emission_kg_per_kwh=emission_by_hour,
            charger_cap_kw=float(depot["charger_cap_kw"]),
            grid_cap_kw=grid_cap_kw,
            required_energy_kwh=required_energy,
            charge_allowed=allowed,
            fixed_bus_charge_kw=fixed,
            pv_cap_kwp=pv_cap_kwp,
            pv_cap_max_kwp=pv_cap_max_kwp,
            bess_energy_cap_kwh=bess_energy_cap_kwh,
            bess_energy_cap_max_kwh=bess_energy_cap_max_kwh,
            bess_power_cap_kw=bess_power_cap_kw,
            bess_power_cap_max_kw=bess_power_cap_max_kw,
            dt_hours=args.dt_hours,
            demand_charge_per_kw=float(scenario_row["demand_charge_cop_per_kw_day"]),
            carbon_price_per_kg=float(scenario_row.get("carbon_price_cop_per_kg", 0.0)),
            pv_capex_daily_per_kwp=float(scenario_row["pv_capex_cop_per_kwp_day"]) if pv_cap_max > 0 else 0.0,
            bess_energy_capex_daily_per_kwh=(
                float(scenario_row["bess_energy_capex_cop_per_kwh_day"]) if bess_energy_cap_max > 0 else 0.0
            ),
            bess_power_capex_daily_per_kw=(
                float(scenario_row["bess_power_capex_cop_per_kw_day"]) if bess_power_cap_max > 0 else 0.0
            ),
            unserved_penalty_per_kwh=float(scenario_row["unserved_penalty_cop_per_kwh"]),
        )
        results = solve_model(
            model,
            solver=args.solver,
            solver_manager=args.solver_manager,
            neos_email=args.neos_email,
            tee=args.tee,
        )
        termination = str(results.solver.termination_condition)
        dispatch = extract_dispatch(
            model,
            scenario=scenario,
            roof_scenario=roof_scenario,
            depot_id=depot_id,
            dt_hours=args.dt_hours,
        )
        summaries.append(
            summarize(
                dispatch,
                model=model,
                depot=depot,
                scenario_row=scenario_row,
                pv_cap_max_kwp=pv_cap_max,
                grid_cap_kw=grid_cap_kw,
                price_by_hour=price_by_hour,
                emission_by_hour=emission_by_hour,
                termination=termination,
                solver=args.solver,
                solver_manager=args.solver_manager,
            )
        )
        summaries[-1]["capacity_mode"] = args.capacity_mode
        dispatch_frames.append(dispatch)

    out = ROOT / "results" / "tables"
    out.mkdir(parents=True, exist_ok=True)
    scenario_tag = "all" if scenario_filter is None else "-".join(sorted(scenario_filter))
    roof_tag = "all" if roof_filter is None else "-".join(sorted(roof_filter))
    depot_tag = "all" if depot_filter is None else "-".join(sorted(depot_filter))
    suffix = f"{args.solver_manager}_{args.solver}_{args.capacity_mode}_{scenario_tag}_{roof_tag}_{depot_tag}".replace("/", "_")
    summary_path = out / f"full_scenario_summary_{suffix}.csv"
    dispatch_path = out / f"full_depot_dispatch_{suffix}.csv"
    summary = pd.DataFrame(summaries)
    dispatch = pd.concat(dispatch_frames, ignore_index=True)
    summary.to_csv(summary_path, index=False)
    dispatch.to_csv(dispatch_path, index=False)

    print("\nScenario totals")
    totals = (
        summary.groupby(["scenario", "roof_scenario"], as_index=False)
        .agg(
            grid_energy_kwh=("grid_energy_kwh", "sum"),
            peak_grid_kw=("peak_grid_kw", "sum"),
            installed_pv_kwp=("installed_pv_kwp", "sum"),
            installed_bess_energy_kwh=("installed_bess_energy_kwh", "sum"),
            unserved_kwh=("unserved_kwh", "sum"),
            co2_kg=("co2_kg", "sum"),
            objective_cop=("objective_cop", "sum"),
        )
        .sort_values(["scenario", "roof_scenario"])
    )
    print(totals.round(2).to_string(index=False))
    print(f"\nWrote {summary_path.relative_to(ROOT)}")
    print(f"Wrote {dispatch_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
