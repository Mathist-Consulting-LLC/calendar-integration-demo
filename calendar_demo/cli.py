from __future__ import annotations

import argparse
import copy
import json
import sys

from .storage import load_json, reset_generated, save_json, scenario_paths
from .workflow import execute


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Credential-free calendar reconciliation demo")
    subparsers = result.add_subparsers(dest="command")
    run = subparsers.add_parser("run", help="plan or apply a simulated reconciliation")
    run.add_argument("--scenario", default="portfolio", choices=("portfolio", "provider-failure", "uncertain-write"))
    run.add_argument("--apply", action="store_true", help="apply approved create/update operations to local generated state")
    run.add_argument("--approve", action="append", choices=("create", "update"), default=[], help="action type approved for this apply run; repeat as needed")
    subparsers.add_parser("reset", help="remove only known generated state/report JSON files")
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments or arguments[0].startswith("-"):
        arguments.insert(0, "run")
    args = parser().parse_args(arguments)
    if args.command == "reset":
        removed = reset_generated()
        print("Reset complete. Removed: " + (", ".join(removed) if removed else "nothing"))
        return 0
    if args.apply and not args.approve:
        parser().error("--apply requires at least one explicit --approve create|update")
    if args.approve and not args.apply:
        parser().error("--approve is valid only with --apply")

    source_path, fixture_state_path, generated_state_path, report_path = scenario_paths(args.scenario)
    source = load_json(source_path)
    base_state = load_json(generated_state_path if generated_state_path.exists() else fixture_state_path)
    working_state = copy.deepcopy(base_state)
    state, report = execute(source, working_state, apply=args.apply, approved_actions=set(args.approve))
    if args.apply:
        save_json(generated_state_path, state)
        save_json(report_path, report)
    print_report(args.scenario, report)
    return 0


def print_report(scenario: str, report: dict) -> None:
    print(f"Calendar integration demo | scenario={scenario} | mode={report['mode']}")
    print("Plan: " + _counts(report["plan_summary"]))
    print("Outcomes: " + _counts(report["outcome_summary"]))
    print(f"Provider operations: {len(report['operations'])}")
    for item in report["items"]:
        changes = f" [{', '.join(item['changes'])}]" if item["changes"] else ""
        print(f"- {item['source_id']}: {item['action']} -> {item['outcome']}{changes} | {item['reason']}")
    if report["mode"] == "dry-run":
        print("Dry run complete: no local state or report files were written.")
    else:
        print("Apply complete: only generated scenario state/report JSON files were written.")


def _counts(values: dict[str, int]) -> str:
    return ", ".join(f"{key}={value}" for key, value in values.items()) or "none"
