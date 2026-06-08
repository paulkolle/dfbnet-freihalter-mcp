from __future__ import annotations

import argparse
import asyncio
import json

from .client import DfbnetClient
from .config import load_config


async def _run(args) -> object:
    client = DfbnetClient(load_config(args.env_file))
    if args.command == "auth-status":
        return await client.auth_status()
    if args.command == "dry-run":
        return client.dry_run_full_day_exemption(args.date, comment=args.comment)
    if args.command == "dry-run-range":
        return client.dry_run_date_range_exemption(args.start_date, args.end_date, comment=args.comment)
    if args.command == "dry-run-delete":
        return client.dry_run_delete_exemption(args.exemption_id)
    if args.command == "list":
        return await client.list_exemptions(args.from_iso)
    if args.command == "conflict":
        payload = client.dry_run_full_day_exemption(args.date)["payload"]
        return await client.check_exemption_conflict(payload["from"], payload["until"])
    if args.command == "create-full-day":
        return await client.create_full_day_exemption(args.date, comment=args.comment, check_conflicts=not args.no_conflict_check, verify=not args.no_verify)
    if args.command == "create-range":
        return await client.create_date_range_exemption(args.start_date, args.end_date, comment=args.comment, check_conflicts=not args.no_conflict_check, verify=not args.no_verify)
    if args.command == "delete":
        return await client.delete_exemption(args.exemption_id, verify=not args.no_verify)
    raise SystemExit(f"unknown command: {args.command}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=None)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("auth-status")
    p = sub.add_parser("dry-run"); p.add_argument("date"); p.add_argument("--comment")
    p = sub.add_parser("dry-run-range"); p.add_argument("start_date"); p.add_argument("end_date"); p.add_argument("--comment")
    p = sub.add_parser("dry-run-delete"); p.add_argument("exemption_id")
    p = sub.add_parser("list"); p.add_argument("--from-iso", default="2025-07-01T00:00:00.000Z")
    p = sub.add_parser("conflict"); p.add_argument("date")
    p = sub.add_parser("create-full-day"); p.add_argument("date"); p.add_argument("--comment"); p.add_argument("--no-conflict-check", action="store_true"); p.add_argument("--no-verify", action="store_true")
    p = sub.add_parser("create-range"); p.add_argument("start_date"); p.add_argument("end_date"); p.add_argument("--comment"); p.add_argument("--no-conflict-check", action="store_true"); p.add_argument("--no-verify", action="store_true")
    p = sub.add_parser("delete"); p.add_argument("exemption_id"); p.add_argument("--no-verify", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(_run(args))
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
