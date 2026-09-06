from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .layout import build_family_layout
from .parser import PedigreeFormatError, parse_pedigree
from .render import render_report
from .validate import summarize_pedigree, validate_pedigree


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pedview",
        description="Build interactive pedigree reports from pedigree-style family files.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate", help="Validate a pedigree file."
    )
    validate_parser.add_argument(
        "input_path", help="Path to a pedigree file (.ped, .fam)."
    )

    preview_parser = subparsers.add_parser(
        "preview", help="Summarize pedigree contents."
    )
    preview_parser.add_argument(
        "input_path", help="Path to a pedigree file (.ped, .fam)."
    )

    build_parser_ = subparsers.add_parser(
        "build", help="Generate a standalone HTML report."
    )
    build_parser_.add_argument(
        "input_path", help="Path to a pedigree file (.ped, .fam)."
    )
    build_parser_.add_argument(
        "-o",
        "--output",
        help="Path to the output HTML file. Defaults to <input>.html.",
    )
    build_parser_.add_argument(
        "--family",
        help="Optional family ID filter. Only render the requested family.",
    )
    build_parser_.add_argument(
        "--title",
        help="Optional report title. Defaults to a title derived from the input filename.",
    )
    build_parser_.add_argument(
        "--ancestor-inbreeding",
        type=float,
        help="Global Wright ancestor inbreeding coefficient (f_a). Defaults to 0.0 when omitted.",
    )
    build_parser_.add_argument(
        "--variant-name",
        help="Optional label or name of the candidate variant being analyzed (e.g. SCN1A:c.1234G>A).",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return run_validate(args.input_path)
    if args.command == "preview":
        return run_preview(args.input_path)
    if args.command == "build":
        return run_build(
            args.input_path,
            args.output,
            args.family,
            args.title,
            args.ancestor_inbreeding,
            args.variant_name,
        )
    parser.error("Unknown command.")
    return 2


def run_validate(input_path: str) -> int:
    pedigree, messages = load_with_messages(input_path)
    print_validation_result(pedigree.source_path, messages)
    return 1 if any(message.severity == "error" for message in messages) else 0


def run_preview(input_path: str) -> int:
    pedigree, messages = load_with_messages(input_path)
    summaries = summarize_pedigree(pedigree)
    print(f"Source: {pedigree.source_path}")
    print(f"Families: {len(summaries)}")
    print(f"Individuals: {pedigree.people_count()}")
    for summary in summaries:
        print(
            f"- {summary.family_id}: {summary.people_count} individuals, "
            f"{summary.founders_count} founders, "
            f"{summary.relationship_count} parent references, "
            f"{summary.generation_count} generations"
        )
    if messages:
        print()
        print_validation_messages(messages)
    return 1 if any(message.severity == "error" for message in messages) else 0


def run_build(
    input_path: str,
    output_path: str | None,
    family_filter: str | None,
    title: str | None,
    ancestor_inbreeding: float | None,
    variant_name: str | None = None,
) -> int:
    pedigree, messages = load_with_messages(input_path)
    if family_filter:
        if family_filter not in pedigree.families:
            print(
                f"Family '{family_filter}' was not found in the input.", file=sys.stderr
            )
            return 1
        pedigree.families = {family_filter: pedigree.families[family_filter]}
    if any(message.severity == "error" for message in messages):
        print_validation_result(pedigree.source_path, messages)
        return 1

    summaries = summarize_pedigree(pedigree)
    family_layouts = {
        summary.family_id: build_family_layout(pedigree.families[summary.family_id])
        for summary in summaries
    }
    ancestor_inbreeding_value = (
        ancestor_inbreeding if ancestor_inbreeding is not None else 0.0
    )
    output = (
        Path(output_path)
        if output_path
        else default_output_path(input_path, family_filter)
    )
    report_title = title or f"pedview report: {Path(input_path).stem}"
    html = render_report(
        pedigree=pedigree,
        family_layouts=family_layouts,
        family_summaries=summaries,
        messages=[message for message in messages if message.severity == "warning"],
        title=report_title,
        ancestor_inbreeding=ancestor_inbreeding_value,
        used_default_ancestor_inbreeding=ancestor_inbreeding is None,
        variant_name=variant_name,
    )
    output.write_text(html, encoding="utf-8")
    if ancestor_inbreeding is None:
        print(
            "Using Wright ancestor inbreeding coefficient f_a = 0.0 (default). "
            "Pass --ancestor-inbreeding to override."
        )
    else:
        print(
            f"Using Wright ancestor inbreeding coefficient f_a = {ancestor_inbreeding_value:.4f}."
        )
    print(f"Wrote {output}")
    return 0


def load_with_messages(input_path: str):
    try:
        pedigree = parse_pedigree(input_path)
    except PedigreeFormatError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    messages = [*pedigree.messages, *validate_pedigree(pedigree)]
    return pedigree, messages


def default_output_path(input_path: str, family_filter: str | None) -> Path:
    input_file = Path(input_path)
    suffix = f".{family_filter}" if family_filter else ""
    return input_file.with_suffix(f"{suffix}.html")


def print_validation_result(source_path: str, messages) -> None:
    print(f"Validation result for {source_path}")
    if not messages:
        print("No validation issues found.")
        return
    print_validation_messages(messages)
    error_count = sum(message.severity == "error" for message in messages)
    warning_count = sum(message.severity == "warning" for message in messages)
    print(f"{error_count} error(s), {warning_count} warning(s)")


def print_validation_messages(messages) -> None:
    for message in messages:
        print(message.format_for_cli())
