#!/usr/bin/env python3
"""Print the current experiment scenario matrix."""

from __future__ import annotations

from energy_patios.scenarios import OPERATIONAL_SCENARIOS, ROOF_SCENARIOS, scenario_matrix


def main() -> None:
    print("Operational scenarios")
    for scenario in OPERATIONAL_SCENARIOS:
        print(f"{scenario.code}: {scenario.label}")

    print("\nRoof scenarios")
    for scenario in ROOF_SCENARIOS:
        print(f"{scenario.code}: {scenario.label} [{scenario.roof_scope}, {scenario.availability_factor:.2f}]")

    print(f"\nDefault combinations: {len(scenario_matrix())}")


if __name__ == "__main__":
    main()
