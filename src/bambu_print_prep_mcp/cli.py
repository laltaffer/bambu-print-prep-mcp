from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from bambu_print_prep_mcp.analysis import inspect_model
from bambu_print_prep_mcp.prepare import prepare_model_for_bambu


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bambu-print-prep")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("file_path")
    inspect_parser.add_argument("--printer", default="bambu_lab_p2s")

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("file_path")
    prepare_parser.add_argument("--output-dir", default=None)
    prepare_parser.add_argument("--printer", default="bambu_lab_p2s")
    prepare_parser.add_argument("--material", default="PLA")
    prepare_parser.add_argument("--target-height-mm", type=float, default=None)
    prepare_parser.add_argument("--intent", default="statue")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "inspect":
        result = inspect_model(args.file_path, printer=args.printer)
        print(result.model_dump_json(indent=2))
        return 0
    if args.command == "prepare":
        result = prepare_model_for_bambu(
            Path(args.file_path),
            output_dir=args.output_dir,
            printer=args.printer,
            material=args.material,
            target_height_mm=args.target_height_mm,
            intent=args.intent,
        )
        print(json.dumps(result.model_dump(), indent=2))
        return 0
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
