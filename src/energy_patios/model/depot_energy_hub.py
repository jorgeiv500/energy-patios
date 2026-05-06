"""Depot energy-hub optimization model.

The formulation is intentionally compact so it can be solved locally during
pipeline development and remotely through NEOS when commercial MILP solvers are
needed. It represents one depot and one representative day.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pyomo.environ as pyo


def build_depot_energy_hub_model(
    *,
    hours: Sequence[int],
    price_per_kwh: Mapping[int, float],
    pv_kw_per_kwp: Mapping[int, float],
    emission_kg_per_kwh: Mapping[int, float] | None = None,
    charger_cap_kw: float,
    grid_cap_kw: float,
    required_energy_kwh: float,
    charge_allowed: Mapping[int, bool],
    fixed_bus_charge_kw: Mapping[int, float] | None = None,
    pv_cap_kwp: float = 0.0,
    pv_cap_max_kwp: float | None = None,
    bess_energy_cap_kwh: float = 0.0,
    bess_energy_cap_max_kwh: float | None = None,
    bess_power_cap_kw: float = 0.0,
    bess_power_cap_max_kw: float | None = None,
    bess_charge_efficiency: float = 0.95,
    bess_discharge_efficiency: float = 0.95,
    dt_hours: float = 1.0,
    demand_charge_per_kw: float = 0.0,
    carbon_price_per_kg: float = 0.0,
    pv_capex_daily_per_kwp: float = 0.0,
    bess_energy_capex_daily_per_kwh: float = 0.0,
    bess_power_capex_daily_per_kw: float = 0.0,
    unserved_penalty_per_kwh: float = 1_000_000.0,
) -> pyo.ConcreteModel:
    """Build a one-depot PV-BESS-smart-charging MILP.

    Args:
        hours: Ordered time steps, typically ``range(24)``.
        price_per_kwh: Energy price by hour.
        emission_kg_per_kwh: Grid emission factor by hour. If omitted, the
            carbon term is disabled.
        pv_kw_per_kwp: PV generation profile in kW per installed kWp.
        charger_cap_kw: Aggregate charger capacity at the depot.
        grid_cap_kw: Exogenous grid connection capacity.
        required_energy_kwh: Daily charging energy requirement. Used when
            ``fixed_bus_charge_kw`` is not provided.
        charge_allowed: Whether buses can charge during each hour.
        fixed_bus_charge_kw: If provided, bus charging is fixed hour by hour,
            with an unserved slack for infeasibility diagnostics. If omitted,
            the model optimizes the charging schedule over allowed hours.
        pv_cap_kwp: Fixed installed PV capacity if ``pv_cap_max_kwp`` is not
            provided.
        pv_cap_max_kwp: Optional upper bound for optimized PV capacity.
        bess_energy_cap_kwh: Fixed stationary battery energy capacity if
            ``bess_energy_cap_max_kwh`` is not provided.
        bess_energy_cap_max_kwh: Optional upper bound for optimized BESS energy
            capacity.
        bess_power_cap_kw: Fixed stationary battery charge/discharge power
            capacity if ``bess_power_cap_max_kw`` is not provided.
        bess_power_cap_max_kw: Optional upper bound for optimized BESS power
            capacity.
        bess_charge_efficiency: Battery charge efficiency.
        bess_discharge_efficiency: Battery discharge efficiency.
        dt_hours: Duration of each time step.
        demand_charge_per_kw: Dailyized peak-demand penalty.
        carbon_price_per_kg: Shadow price of grid-related CO2 emissions.
        pv_capex_daily_per_kwp: Dailyized PV investment cost.
        bess_energy_capex_daily_per_kwh: Dailyized BESS energy investment cost.
        bess_power_capex_daily_per_kw: Dailyized BESS power investment cost.
        unserved_penalty_per_kwh: Penalty for unmet bus charging energy.
    """
    ordered_hours = list(hours)
    if not ordered_hours:
        raise ValueError("hours must not be empty")
    emissions = emission_kg_per_kwh or {hour: 0.0 for hour in ordered_hours}

    model = pyo.ConcreteModel()
    model.T = pyo.Set(initialize=ordered_hours, ordered=True)

    pv_bounds = (pv_cap_kwp, pv_cap_kwp) if pv_cap_max_kwp is None else (0.0, pv_cap_max_kwp)
    bess_energy_bounds = (
        (bess_energy_cap_kwh, bess_energy_cap_kwh)
        if bess_energy_cap_max_kwh is None
        else (0.0, bess_energy_cap_max_kwh)
    )
    bess_power_bounds = (
        (bess_power_cap_kw, bess_power_cap_kw)
        if bess_power_cap_max_kw is None
        else (0.0, bess_power_cap_max_kw)
    )

    model.pv_cap = pyo.Var(domain=pyo.NonNegativeReals, bounds=pv_bounds)
    model.bess_energy_cap = pyo.Var(domain=pyo.NonNegativeReals, bounds=bess_energy_bounds)
    model.bess_power_cap = pyo.Var(domain=pyo.NonNegativeReals, bounds=bess_power_bounds)
    model.grid = pyo.Var(model.T, domain=pyo.NonNegativeReals)
    model.grid_peak = pyo.Var(domain=pyo.NonNegativeReals)
    model.pv_used = pyo.Var(model.T, domain=pyo.NonNegativeReals)
    model.pv_curtail = pyo.Var(model.T, domain=pyo.NonNegativeReals)
    model.bus_charge = pyo.Var(model.T, domain=pyo.NonNegativeReals)
    model.unserved = pyo.Var(model.T, domain=pyo.NonNegativeReals)
    model.bess_charge = pyo.Var(model.T, domain=pyo.NonNegativeReals)
    model.bess_discharge = pyo.Var(model.T, domain=pyo.NonNegativeReals)
    model.bess_soc = pyo.Var(model.T, domain=pyo.NonNegativeReals)
    model.bess_mode = pyo.Var(model.T, domain=pyo.Binary)

    def balance_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return (
            m.grid[t] + m.pv_used[t] + m.bess_discharge[t]
            == m.bus_charge[t] + m.bess_charge[t]
        )

    def pv_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return m.pv_used[t] + m.pv_curtail[t] == pv_kw_per_kwp[t] * m.pv_cap

    def grid_cap_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return m.grid[t] <= grid_cap_kw

    def grid_peak_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return m.grid[t] <= m.grid_peak

    def charger_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        allowed = 1.0 if charge_allowed[t] else 0.0
        return m.bus_charge[t] <= charger_cap_kw * allowed

    def fixed_charge_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        assert fixed_bus_charge_kw is not None
        return m.bus_charge[t] * dt_hours + m.unserved[t] == fixed_bus_charge_kw[t] * dt_hours

    def flexible_charge_rule(m: pyo.ConcreteModel) -> pyo.Constraint:
        return (
            sum(m.bus_charge[t] * dt_hours for t in m.T)
            + sum(m.unserved[t] for t in m.T)
            >= required_energy_kwh
        )

    def bess_soc_bound_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return m.bess_soc[t] <= m.bess_energy_cap

    def bess_charge_power_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return m.bess_charge[t] <= m.bess_power_cap

    def bess_discharge_power_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return m.bess_discharge[t] <= m.bess_power_cap

    def bess_charge_mode_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return m.bess_charge[t] <= bess_power_bounds[1] * m.bess_mode[t]

    def bess_discharge_mode_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return m.bess_discharge[t] <= bess_power_bounds[1] * (1 - m.bess_mode[t])

    def bess_transition_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        index = ordered_hours.index(t)
        next_t = ordered_hours[(index + 1) % len(ordered_hours)]
        return m.bess_soc[next_t] == (
            m.bess_soc[t]
            + bess_charge_efficiency * m.bess_charge[t] * dt_hours
            - (m.bess_discharge[t] * dt_hours) / bess_discharge_efficiency
        )

    model.energy_balance = pyo.Constraint(model.T, rule=balance_rule)
    model.pv_balance = pyo.Constraint(model.T, rule=pv_rule)
    model.grid_cap = pyo.Constraint(model.T, rule=grid_cap_rule)
    model.grid_peak_limit = pyo.Constraint(model.T, rule=grid_peak_rule)
    model.charger_limit = pyo.Constraint(model.T, rule=charger_rule)
    model.bess_soc_bound = pyo.Constraint(model.T, rule=bess_soc_bound_rule)
    model.bess_charge_power = pyo.Constraint(model.T, rule=bess_charge_power_rule)
    model.bess_discharge_power = pyo.Constraint(model.T, rule=bess_discharge_power_rule)
    model.bess_charge_mode = pyo.Constraint(model.T, rule=bess_charge_mode_rule)
    model.bess_discharge_mode = pyo.Constraint(model.T, rule=bess_discharge_mode_rule)
    model.bess_transition = pyo.Constraint(model.T, rule=bess_transition_rule)

    if fixed_bus_charge_kw is None:
        model.flexible_charge_requirement = pyo.Constraint(rule=flexible_charge_rule)
    else:
        model.fixed_charge_requirement = pyo.Constraint(model.T, rule=fixed_charge_rule)

    model.objective = pyo.Objective(
        expr=(
            sum(price_per_kwh[t] * model.grid[t] * dt_hours for t in model.T)
            + demand_charge_per_kw * model.grid_peak
            + carbon_price_per_kg * sum(emissions[t] * model.grid[t] * dt_hours for t in model.T)
            + pv_capex_daily_per_kwp * model.pv_cap
            + bess_energy_capex_daily_per_kwh * model.bess_energy_cap
            + bess_power_capex_daily_per_kw * model.bess_power_cap
            + unserved_penalty_per_kwh * sum(model.unserved[t] for t in model.T)
        ),
        sense=pyo.minimize,
    )
    return model
