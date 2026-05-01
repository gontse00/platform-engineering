#!/usr/bin/env python3
"""Check .ZA domain availability with WHOIS and write a CSV report."""

from __future__ import annotations

import argparse
import csv
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_DOMAINS = [
    "rescuenet.co.za",
    "rescue-net.co.za",
    "rescuenetza.co.za",
    "rescuenetapp.co.za",
    "rescueconnect.co.za",
    "ubunturescue.co.za",
    "safenetza.co.za",
    "rescuenet.org.za",
]

ZA_WHOIS_SERVER = "whois.registry.net.za"
ZA_TLDS = (".co.za", ".org.za", ".net.za", ".web.za")
CSV_OUTPUT = "domain_availability_report.csv"


@dataclass
class DomainResult:
    domain: str
    status: str
    registrar: str
    creation_date: str
    expiry_date: str
    snippet: str


def load_domains(domains_file: str | None) -> list[str]:
    if not domains_file:
        return DEFAULT_DOMAINS

    domains: list[str] = []
    for raw_line in Path(domains_file).read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().lower()
        if not line or line.startswith("#"):
            continue
        domains.append(line)
    return domains


def whois_socket(domain: str, server: str, timeout: int) -> str:
    query = f"{domain}\r\n".encode("utf-8")
    chunks: list[bytes] = []

    with socket.create_connection((server, 43), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(query)
        while True:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            chunks.append(chunk)

    return b"".join(chunks).decode("utf-8", errors="replace")


def whois_cli(domain: str, timeout: int) -> str:
    if not shutil.which("whois"):
        raise RuntimeError("whois CLI is not installed")

    completed = subprocess.run(
        ["whois", domain],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    output = "\n".join(part for part in [completed.stdout, completed.stderr] if part)
    if not output.strip():
        raise RuntimeError(f"whois CLI returned no output; exit={completed.returncode}")
    return output


def get_field(raw: str, field_names: Iterable[str]) -> str:
    wanted = {name.lower() for name in field_names}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized = key.strip().lower()
        if normalized in wanted:
            return value.strip()
    return ""


def classify_status(raw: str) -> str:
    lower = raw.lower()

    rate_limit_phrases = [
        "rate limit",
        "too many requests",
        "query limit",
        "quota exceeded",
        "exceeded the maximum",
    ]
    if any(phrase in lower for phrase in rate_limit_phrases):
        return "unknown"

    available_phrases = [
        "available",
        "no match",
        "not found",
        "domain not found",
        "no entries found",
        "nothing found",
    ]
    registered_phrases = [
        "domain name:",
        "domain:",
        "registrar:",
        "registration date:",
        "creation date:",
        "registered on:",
    ]

    if any(phrase in lower for phrase in available_phrases):
        return "available"
    if any(phrase in lower for phrase in registered_phrases):
        return "registered"
    return "unknown"


def make_snippet(raw: str, reason: str = "") -> str:
    if reason:
        return reason

    useful_lines: list[str] = []
    keywords = (
        "domain",
        "registrar",
        "creation",
        "registration",
        "expiry",
        "expiration",
        "available",
        "not found",
        "no match",
        "rate",
        "quota",
    )
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(keyword in stripped.lower() for keyword in keywords):
            useful_lines.append(stripped)
        if len(useful_lines) >= 6:
            break

    if not useful_lines:
        useful_lines = [line.strip() for line in raw.splitlines() if line.strip()][:6]
    return " | ".join(useful_lines)[:500]


def parse_result(domain: str, raw: str, source: str) -> DomainResult:
    status = classify_status(raw)
    registrar = get_field(raw, ["Registrar", "Sponsoring Registrar", "Registrar Name"])
    creation_date = get_field(
        raw,
        ["Creation Date", "Created", "Registration Date", "Registered On"],
    )
    expiry_date = get_field(
        raw,
        ["Expiry Date", "Expiration Date", "Registry Expiry Date", "Renewal Date"],
    )
    snippet = make_snippet(raw)
    if snippet:
        snippet = f"{source}: {snippet}"
    else:
        snippet = f"{source}: no useful WHOIS fields found"

    return DomainResult(
        domain=domain,
        status=status,
        registrar=registrar,
        creation_date=creation_date,
        expiry_date=expiry_date,
        snippet=snippet,
    )


def check_domain(domain: str, timeout: int, delay: float) -> DomainResult:
    normalized = domain.strip().lower()
    errors: list[str] = []

    if normalized.endswith(ZA_TLDS):
        try:
            raw = whois_socket(normalized, ZA_WHOIS_SERVER, timeout)
            if raw.strip():
                time.sleep(delay)
                return parse_result(normalized, raw, ZA_WHOIS_SERVER)
            errors.append(f"{ZA_WHOIS_SERVER}: empty response")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{ZA_WHOIS_SERVER}: {exc}")

    try:
        raw = whois_cli(normalized, timeout)
        time.sleep(delay)
        return parse_result(normalized, raw, "whois CLI")
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        errors.append(f"whois CLI: {exc}")

    return DomainResult(
        domain=normalized,
        status="unknown",
        registrar="",
        creation_date="",
        expiry_date="",
        snippet=make_snippet("", "; ".join(errors)),
    )


def write_csv(results: list[DomainResult], output_path: str) -> None:
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "domain",
                "status",
                "registrar",
                "creation_date",
                "expiry_date",
                "snippet",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for result in results:
            writer.writerow(result.__dict__)


def print_table(results: list[DomainResult]) -> None:
    headers = ["domain", "status", "registrar", "creation date", "expiry date", "snippet/reason"]
    rows = [
        [
            result.domain,
            result.status,
            result.registrar or "-",
            result.creation_date or "-",
            result.expiry_date or "-",
            result.snippet or "-",
        ]
        for result in results
    ]
    widths = [
        min(max(len(str(row[index])) for row in [headers, *rows]), 70)
        for index in range(len(headers))
    ]

    def clip(value: str, width: int) -> str:
        text = str(value)
        if len(text) <= width:
            return text
        return text[: width - 1] + "…"

    def render(row: list[str]) -> str:
        return " | ".join(clip(value, widths[index]).ljust(widths[index]) for index, value in enumerate(row))

    print(render(headers))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(render(row))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check .ZA domain availability with WHOIS.")
    parser.add_argument(
        "--domains-file",
        help="Optional newline-delimited domain list. Blank lines and # comments are ignored.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=12,
        help="WHOIS network timeout in seconds. Default: 12.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between WHOIS queries to reduce rate-limit risk. Default: 1.0.",
    )
    parser.add_argument(
        "--output",
        default=CSV_OUTPUT,
        help=f"CSV output path. Default: {CSV_OUTPUT}.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    domains = load_domains(args.domains_file)
    if not domains:
        print("No domains to check.", file=sys.stderr)
        return 2

    results = [check_domain(domain, args.timeout, args.delay) for domain in domains]
    print_table(results)
    write_csv(results, args.output)
    print(f"\nSaved CSV report to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
