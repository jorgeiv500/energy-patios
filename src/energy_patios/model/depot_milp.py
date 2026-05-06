"""Initial Pyomo MILP for one depot-hour instance.

This module is intentionally small. It provides a tested starting point for the
full model after the raw data pipeline creates depot-hour parameter tables.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pyomo.environ as pyo


def build_single_depot_model(
    hours: Sequence[int],
    demand_kwh: Mapping[int, float],
    pv_profile_kw_per_kwp: Mapping[int, float],
    price_per_kwh: Mapping[int, float],
    grid_cap_kw: float,
    pv_cap_kwp: float,
    charger_cap_kw: float,
) -> pyo.ConcreteModel:
    """Build a linear dispatch model for one depot with fixed PV and grid cap."""
    model = pyo.ConcreteModel()
    model.T = pyo.Set(initialize=list(hours), ordered=True)

    model.grid = pyo.Var(model.T, domain=pyo.NonNegativeReals)
    model.pv_used = pyo.Var(model.T, domain=pyo.NonNegativeReals)
    model.pv_curtail = pyo.Var(model.T, domain=pyo.NonNegativeReals)
    model.bus_charge = pyo.Var(model.T, domain=pyo.NonNegativeReals)

    def balance_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return m.grid[t] + m.pv_used[t] == m.bus_charge[t]

    def demand_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return m.bus_charge[t] >= demand_kwh[t]

    def pv_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return m.pv_used[t] + m.pv_curtail[t] == pv_profile_kw_per_kwp[t] * pv_cap_kwp

    def grid_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return m.grid[t] <= grid_cap_kw

    def charger_rule(m: pyo.ConcreteModel, t: int) -> pyo.Constraint:
        return m.bus_charge[t] <= charger_cap_kw

    model.balance = pyo.Constraint(model.T, rule=balance_rule)
    model.demand = pyo.Constraint(model.T, rule=demand_rule)
    model.pv_limit = pyo.Constraint(model.T, rule=pv_rule)
    model.grid_limit = pyo.Constraint(model.T, rule=grid_rule)
    model.charger_limit = pyo.Constraint(model.T, rule=charger_rule)
    model.objective = pyo.Objective(
        expr=sum(price_per_kwh[t] * model.grid[t] for t in model.T),
        sense=pyo.minimize,
    )
    return model
