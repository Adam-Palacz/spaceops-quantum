"""Command-line interface for solves, QUBO inspection, and experiment archives.

Importing this module does not import Qiskit. The sampled experiment path
loads Qiskit only when that method is selected.
"""

from __future__ import annotations

import argparse
import sys
import time
from fractions import Fraction
from pathlib import Path

from spaceops_quantum import __version__
from spaceops_quantum.classical import (
    ClassicalResult,
    GreedySolverError,
    solve_exact,
    solve_greedy,
)
from spaceops_quantum.domain import ScenarioValidationError, load_scenario
from spaceops_quantum.encoding import build_qubo, to_ising
from spaceops_quantum.experiment import (
    ExperimentArchiveError,
    capture_classical,
    capture_sampled,
    write_experiment,
)

_EPILOG = "Report commands are added in a later task."


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spaceops-quantum",
        description=(
            "Hybrid quantum-classical benchmark for Earth-observation task selection."
        ),
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print the installed package version and exit",
    )
    commands = parser.add_subparsers(dest="command")

    validate = commands.add_parser("validate", help="validate a scenario file")
    validate.add_argument("scenario", type=Path, help="path to a scenario YAML file")

    solve = commands.add_parser("solve", help="solve a scenario with a classical method")
    solve.add_argument(
        "--method",
        required=True,
        choices=("exact", "greedy"),
        help="exact enumerates every subset; greedy builds one feasible subset",
    )
    solve.add_argument("--scenario", required=True, type=Path, help="path to a scenario YAML file")
    solve.add_argument(
        "--strategy",
        default="resource_density",
        help="greedy ranking strategy (default: resource_density)",
    )
    solve.add_argument(
        "--seed",
        type=int,
        default=0,
        help="recorded greedy seed; it does not change resource_density ranking",
    )

    qubo = commands.add_parser("qubo", help="inspect the QUBO and Ising encoding")
    qubo_commands = qubo.add_subparsers(dest="qubo_command", required=True)
    inspect = qubo_commands.add_parser("inspect", help="print the QUBO and Ising summary")
    inspect.add_argument(
        "--scenario",
        required=True,
        type=Path,
        help="path to a scenario YAML file",
    )
    inspect.add_argument(
        "--penalty",
        required=True,
        type=int,
        help="penalty applied to every resource constraint",
    )

    experiment = commands.add_parser("experiment", help="write one experiment archive")
    experiment_commands = experiment.add_subparsers(dest="experiment_command", required=True)
    run = experiment_commands.add_parser(
        "run",
        help="solve once and write manifest, samples, and metrics",
    )
    run.add_argument(
        "--method",
        required=True,
        choices=("exact", "greedy", "sampled", "optimized"),
    )
    run.add_argument("--scenario", required=True, type=Path, help="path to a scenario YAML file")
    run.add_argument("--out", required=True, type=Path, help="parent directory for the archive")
    run.add_argument("--id", required=True, help="archive directory name")
    run.add_argument("--strategy", default="resource_density")
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--shots", type=int, help="shot count for the sampled method")
    run.add_argument("--penalty", type=int, help="penalty on every resource for the sampled method")
    run.add_argument("--gamma", type=float, help="fixed gamma, or the optimized start")
    run.add_argument("--beta", type=float, help="fixed beta, or the optimized start")
    run.add_argument("--max-evaluations", type=int, help="COBYLA evaluation budget for optimized")
    grid = experiment_commands.add_parser(
        "grid",
        help="execute the locked T15 manifest once and archive every cell",
    )
    grid.add_argument("--out", required=True, type=Path, help="parent directory for the archives")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.version:
        print(f"spaceops-quantum {__version__}")
        return 0
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "validate":
        return _validate(args.scenario)
    if args.command == "qubo":
        return _qubo_inspect(args.scenario, args.penalty)
    if args.command == "experiment":
        if args.experiment_command == "grid":
            return _experiment_grid(args)
        return _experiment_run(args)
    return _solve(args.method, args.scenario, args.strategy, args.seed)


def _validate(path: Path) -> int:
    try:
        scenario = load_scenario(path)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ScenarioValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"scenario_id: {scenario.scenario_id}")
    print(f"schema_version: {scenario.schema_version}")
    print(f"tasks: {len(scenario.tasks)}")
    print(f"energy_budget: {scenario.budgets.energy}")
    print(f"storage_budget: {scenario.budgets.storage}")
    print(f"downlink_budget: {scenario.budgets.downlink}")
    print("valid: true")
    return 0


def _solve(method: str, path: Path, strategy: str, seed: int) -> int:
    if method == "exact" and (strategy != "resource_density" or seed != 0):
        print("exact does not use --strategy or --seed", file=sys.stderr)
        return 2
    try:
        scenario = load_scenario(path)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ScenarioValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        if method == "exact":
            result = solve_exact(scenario)
        else:
            result = solve_greedy(scenario, strategy, seed)
    except GreedySolverError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _print_result(result)
    return 0


def _experiment_run(args: argparse.Namespace) -> int:
    if args.method == "sampled":
        return _experiment_sampled(args)
    if args.method == "optimized":
        return _experiment_optimized(args)
    if args.max_evaluations is not None:
        print("exact and greedy archives do not use --max-evaluations", file=sys.stderr)
        return 2
    if args.shots is not None or args.penalty is not None:
        print("exact and greedy archives do not use --shots or --penalty", file=sys.stderr)
        return 2
    if args.gamma is not None or args.beta is not None:
        print("exact and greedy archives do not use --gamma or --beta", file=sys.stderr)
        return 2
    try:
        scenario = load_scenario(args.scenario)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ScenarioValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    try:
        started = time.perf_counter()
        if args.method == "exact":
            if args.strategy != "resource_density" or args.seed != 0:
                print("exact does not use --strategy or --seed", file=sys.stderr)
                return 2
            result = solve_exact(scenario)
        else:
            result = solve_greedy(scenario, args.strategy, args.seed)
        elapsed = time.perf_counter() - started
    except GreedySolverError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        destination = write_experiment(
            args.out,
            capture_classical(
                args.id,
                str(args.scenario),
                scenario,
                result,
                wall_time_sec=elapsed,
            ),
            scenario,
        )
    except ExperimentArchiveError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"experiment_dir: {destination}")
    return 0


def _experiment_sampled(args: argparse.Namespace) -> int:
    if args.max_evaluations is not None:
        print("fixed-parameter sampling does not use --max-evaluations", file=sys.stderr)
        return 2
    if args.shots is None or args.penalty is None or args.gamma is None or args.beta is None:
        print("sampled archives require --shots, --penalty, --gamma, and --beta", file=sys.stderr)
        return 2
    if args.penalty < 0 or args.shots < 1:
        print("penalty must be >= 0 and shots must be >= 1", file=sys.stderr)
        return 2
    try:
        scenario = load_scenario(args.scenario)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ScenarioValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    from spaceops_quantum.quantum.qaoa import sample_qaoa

    penalties = {"energy": args.penalty, "storage": args.penalty, "downlink": args.penalty}
    started = time.perf_counter()
    record = sample_qaoa(
        scenario,
        parameters=(args.gamma, args.beta),
        shots=args.shots,
        seed=args.seed,
        lambda_by_constraint=penalties,
    )
    elapsed = time.perf_counter() - started
    try:
        destination = write_experiment(
            args.out,
            capture_sampled(
                args.id,
                str(args.scenario),
                scenario,
                record,
                penalties,
                wall_time_sec=elapsed,
            ),
            scenario,
        )
    except ExperimentArchiveError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"experiment_dir: {destination}")
    return 0


def _experiment_optimized(args: argparse.Namespace) -> int:
    if args.shots is not None:
        print("optimized archives do not use --shots", file=sys.stderr)
        return 2
    if args.penalty is None or args.max_evaluations is None:
        print("optimized archives require --penalty and --max-evaluations", file=sys.stderr)
        return 2
    if (args.gamma is None) != (args.beta is None):
        print("pass both --gamma and --beta, or neither", file=sys.stderr)
        return 2
    if args.penalty < 0 or args.max_evaluations < 1:
        print("penalty must be >= 0 and max-evaluations must be >= 1", file=sys.stderr)
        return 2
    try:
        scenario = load_scenario(args.scenario)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ScenarioValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    from spaceops_quantum.experiment.optimized import capture_optimized_run

    penalties = {"energy": args.penalty, "storage": args.penalty, "downlink": args.penalty}
    initial = None if args.gamma is None else (args.gamma, args.beta)
    try:
        capture = capture_optimized_run(
            args.id,
            str(args.scenario),
            scenario,
            seed=args.seed,
            max_evaluations=args.max_evaluations,
            penalties=penalties,
            initial_parameters=initial,
        )
        destination = write_experiment(args.out, capture, scenario)
    except ExperimentArchiveError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(f"experiment_dir: {destination}")
    return 0


def _experiment_grid(args: argparse.Namespace) -> int:
    from spaceops_quantum.experiment.execute import GridOutputError, execute_grid

    try:
        outcomes = execute_grid(args.out)
    except GridOutputError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    failed = [item["experiment_id"] for item in outcomes if item["status"] != "ok"]
    print(f"completed: {len(outcomes) - len(failed)}")
    print(f"failed: {len(failed)}")
    for experiment_id in failed:
        print(f"failed_run: {experiment_id}")
    return 1 if failed else 0


def _print_result(result: ClassicalResult) -> None:
    print(f"method: {result.method}")
    if result.strategy is not None:
        print(f"strategy: {result.strategy}")
    if result.seed is not None:
        print(f"seed: {result.seed}")
    print(f"scenario_id: {result.scenario_id}")
    print(f"examined_subsets: {result.examined_subsets}")
    print(f"feasible_subsets: {_optional(result.feasible_subsets)}")
    print(f"total_subsets: {_optional(result.total_subsets)}")
    print("selected_task_ids: " + ",".join(result.solution.selected_task_ids))
    print(f"priority: {result.solution.priority}")
    print(f"energy: {result.solution.used.energy}")
    print(f"storage: {result.solution.used.storage}")
    print(f"downlink: {result.solution.used.downlink}")
    print(f"feasible: {str(result.solution.feasible).lower()}")


def _qubo_inspect(path: Path, penalty: int) -> int:
    if penalty < 0:
        print("penalty must be an integer >= 0", file=sys.stderr)
        return 2
    try:
        scenario = load_scenario(path)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ScenarioValidationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    penalties = {"energy": penalty, "storage": penalty, "downlink": penalty}
    qubo = build_qubo(scenario, penalties)
    ising = to_ising(qubo)
    print(f"scenario_id: {scenario.scenario_id}")
    print(f"scenario_hash: {qubo.scenario_hash}")
    print(f"penalty_energy: {penalty}")
    print(f"penalty_storage: {penalty}")
    print(f"penalty_downlink: {penalty}")
    print(f"n_task_bits: {qubo.n_task_bits}")
    print(f"n_slack_bits: {qubo.n_slack_bits}")
    print(f"n_logical_qubits: {qubo.n_logical_qubits}")
    print(f"qubo_constant: {qubo.constant}")
    print(f"qubo_linear_terms: {_nonzero_count(qubo.linear)}")
    print(f"qubo_quadratic_terms: {len(qubo.quadratic)}")
    print(f"ising_constant: {_format_fraction(ising.constant)}")
    print(f"ising_linear_terms: {_nonzero_count(ising.linear)}")
    print(f"ising_quadratic_terms: {len(ising.quadratic)}")
    print("spin_map: s = 2v - 1")
    print("variable_names: " + ",".join(qubo.variable_names))
    return 0


def _nonzero_count(terms: tuple[tuple[str, object], ...]) -> int:
    return sum(1 for _name, coefficient in terms if coefficient != 0)


def _format_fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _optional(value: int | None) -> str:
    if value is None:
        return "null"
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
