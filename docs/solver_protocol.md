# Protocolo de solucion Pyomo + NEOS

## Decision metodologica

El experimento usara Pyomo para formular los modelos MILP. Las instancias pequenas se resolveran localmente cuando sea posible. Las instancias grandes o las que requieran solvers comerciales academicos se podran enviar al NEOS Server.

## Texto metodologico recomendado

> The optimization models were formulated in Pyomo and solved either locally or through the NEOS Server, depending on instance size and solver availability. For NEOS runs, the specific solver, submission date, termination condition, optimality gap, wall-clock time, and solver settings were recorded. Since NEOS is a remote shared service, all reported conclusions were checked through model balance diagnostics and, for selected instances, local reruns or alternative solver configurations.

## Registro minimo por corrida

Cada resultado debe guardar:

- `run_id`
- `scenario`
- `roof_scenario`
- `depot_set`
- `time_resolution`
- `pyomo_version`
- `solver_manager`: `local` o `neos`
- `solver_name`
- `neos_submission_date`, si aplica
- `termination_condition`
- `solver_status`
- `objective_value`
- `mip_gap`
- `wall_time_seconds`
- `time_limit_seconds`
- `optimality_tolerance`
- `input_data_hash`
- `model_git_or_file_hash`, si se versiona

## Citas que deben aparecer en el paper

Pyomo:

- Hart, Watson and Woodruff (2011), `Mathematical Programming Computation`.
- Bynum et al. (2021), `Pyomo--optimization modeling in Python`, third edition.

NEOS:

- Gropp and More (1997), `Optimization Environments and the NEOS Server`.
- Czyzyk, Mesnier and More (1998), `The NEOS Server`.
- Dolan (2001), `The NEOS Server 4.0 Administrative Guide`.

## Advertencias para publicacion

- NEOS no debe recibir datos confidenciales.
- Reportar siempre el solver especifico, no solo "NEOS".
- Verificar balances energeticos y factibilidad operacional despues de cada corrida.
- Si hay resultados centrales, repetir al menos una instancia con solver local o solver alternativo cuando sea viable.
- Si se usa un solver comercial via NEOS, declarar que se uso a traves del servicio NEOS para investigacion academica.
