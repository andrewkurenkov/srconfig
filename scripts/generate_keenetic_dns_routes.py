#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys


SUPPORTED_PREFIXES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"}
DEFAULT_KEYWORD_TLDS = [
    "com",
    "net",
    "org",
    "ru",
    "de",
    "nl",
    "uk",
    "co",
    "io",
    "info",
    "biz",
    "app",
    "dev",
    "me",
    "tv",
    "eu",
    "us",
    "ca",
    "fr",
    "es",
    "it",
    "pl",
    "cz",
    "tr",
    "ua",
    "by",
    "kz",
    "cn",
    "jp",
    "kr",
    "in",
    "br",
    "au",
    "sg",
]


def parse_line(raw_line):
    line = raw_line.strip()
    if not line or line.startswith("#") or line.startswith("//"):
        return None

    if "," in line:
        prefix, value = line.split(",", 1)
        prefix = prefix.strip()
        value = value.strip()
        if prefix == "DOMAIN" or prefix == "DOMAIN-SUFFIX":
            return ("domain", value)
        if prefix == "DOMAIN-KEYWORD":
            return ("keyword", value)
        if prefix in SUPPORTED_PREFIXES:
            return ("unknown", line)
        return ("raw", line)

    return ("domain", line)


def normalize(value):
    v = value.strip().lower()
    if v.endswith("."):
        v = v[:-1]
    return v


def expand_keyword(keyword, tlds):
    normalized = normalize(keyword)
    if not normalized:
        return []
    if "." in normalized:
        return [normalized]
    return [f"{normalized}.{tld}" for tld in tlds]


def write_list(path, items):
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(items)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Generate a Keenetic DNS-Based Routes domain list from *.list files."
    )
    parser.add_argument(
        "--input-dir",
        default="litsts",
        help="Directory with *.list files (default: litsts)",
    )
    parser.add_argument(
        "--output-file",
        default="generated/keenetic_dns_routes.txt",
        help="Output file path for domain list",
    )
    parser.add_argument(
        "--unsupported-file",
        default="generated/keenetic_dns_routes_unsupported.txt",
        help="Output file path for unsupported entries (DOMAIN-KEYWORD, unknown)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if unsupported entries are found",
    )
    parser.add_argument(
        "--keyword-tlds",
        default=",".join(DEFAULT_KEYWORD_TLDS),
        help="Comma-separated TLDs for DOMAIN-KEYWORD expansion",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"Input directory not found: {input_dir}", file=sys.stderr)
        return 2

    list_files = sorted(input_dir.glob("*.list"))
    if not list_files:
        print(f"No .list files found in {input_dir}", file=sys.stderr)
        return 2

    domains = []
    seen = set()
    unsupported = []
    unsupported_seen = set()
    keyword_tlds = [t.strip().lower() for t in args.keyword_tlds.split(",") if t.strip()]

    for path in list_files:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            parsed = parse_line(raw_line)
            if parsed is None:
                continue
            kind, value = parsed
            if kind == "domain":
                normalized = normalize(value)
                if normalized and normalized not in seen:
                    seen.add(normalized)
                    domains.append(normalized)
            elif kind == "keyword":
                for keyword_domain in expand_keyword(value, keyword_tlds):
                    if keyword_domain and keyword_domain not in seen:
                        seen.add(keyword_domain)
                        domains.append(keyword_domain)
            elif kind in ("unknown", "raw"):
                normalized = normalize(value)
                if normalized and normalized not in unsupported_seen:
                    unsupported_seen.add(normalized)
                    unsupported.append(normalized)

    write_list(Path(args.output_file), domains)
    unsupported_path = Path(args.unsupported_file) if args.unsupported_file else None
    write_list(unsupported_path, unsupported)

    if unsupported and args.strict:
        print(
            f"Found {len(unsupported)} unsupported entries. See {args.unsupported_file}.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
