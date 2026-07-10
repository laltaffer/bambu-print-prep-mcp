from __future__ import annotations

import argparse
from collections.abc import Sequence

from bambu_print_prep_mcp.analysis import inspect_model


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bambu-print-prep")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("file_path")
    inspect_parser.add_argument("--printer", default="bambu_lab_p2s")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    result = inspect_model(args.file_path, printer=args.printer)
    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
