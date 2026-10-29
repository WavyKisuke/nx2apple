#!/usr/bin/env python3
"""Validate a rewritten module's fixups.tsv before it reaches the iOS loader.

The host loader intentionally aborts on old rewriter output.  Keep the same
required metadata check in the build pipeline so a stale cached rewrite fails
at build time instead of crashing on the device.
"""
import os
import re
import sys

REQUIRED = (
    "PATCH_OFF",
    "KEY_PAGE_OFF",
    "KEY_PAGE_SIZE",
    "TEXT_END",
    "RO_OFF",
    "DATA_OFF",
    "BUILD_ID",
)


def die(path, message):
    print(f"validate_fixups: {path}: {message}", file=sys.stderr)
    raise SystemExit(2)


def parse(path):
    fields = {}
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.rstrip("\n")
            if not line:
                continue
            if not line.startswith("# "):
                die(path, f"line {lineno}: old/non-header fixups format")
            parts = line[2:].split("\t", 1)
            if len(parts) != 2 or not parts[0] or not parts[1]:
                die(path, f"line {lineno}: malformed header")
            fields[parts[0]] = parts[1]
    return fields


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: validate_fixups.py <module.fixups.tsv> [...]")

    for path in sys.argv[1:]:
        if not os.path.isfile(path):
            die(path, "file does not exist")
        fields = parse(path)
        missing = [k for k in REQUIRED if k not in fields]
        if missing:
            die(path, "missing current-rewriter fields: " + ", ".join(missing))

        try:
            patch_off = int(fields["PATCH_OFF"], 0)
            key_off = int(fields["KEY_PAGE_OFF"], 0)
            key_size = int(fields["KEY_PAGE_SIZE"], 0)
            text_end = int(fields["TEXT_END"], 0)
            ro_off = int(fields["RO_OFF"], 0)
            data_off = int(fields["DATA_OFF"], 0)
        except ValueError as exc:
            die(path, f"invalid numeric header: {exc}")

        if key_off % 0x4000:
            die(path, f"KEY_PAGE_OFF is not 16 KiB aligned: {key_off:#x}")
        if key_size != 0x4000:
            die(path, f"KEY_PAGE_SIZE is {key_size:#x}, expected 0x4000")
        if not text_end or ro_off < text_end or data_off < ro_off:
            die(path, "invalid TEXT_END/RO_OFF/DATA_OFF layout")

        keys = set()
        for key, value in fields.items():
            m = re.fullmatch(r"KEY_(K18|KTLS|KTLR|KGATE)_IDX", key)
            if m:
                try:
                    keys.add(int(value, 0))
                except ValueError:
                    die(path, f"invalid {key}: {value!r}")

        required_keys = {"K18", "KTLS", "KTLR", "KGATE"}
        missing_keys = [f"KEY_{k}_IDX" for k in required_keys if f"KEY_{k}_IDX" not in fields]
        if missing_keys:
            die(path, "missing current key indexes: " + ", ".join(sorted(missing_keys)))
        if len(keys) != 4:
            die(path, "K18/KTLS/KTLR/KGATE indexes are not unique")

        if patch_off < 0 and ("IMAGE_SIZE" not in fields or "FILE_IMAGE_LEN" not in fields):
            die(path, "FAR rewrite is missing IMAGE_SIZE/FILE_IMAGE_LEN")

        build_id = fields["BUILD_ID"].strip()
        if not build_id or build_id == "0" or not re.fullmatch(r"[0-9A-Fa-f]{16,}", build_id):
            die(path, f"invalid BUILD_ID: {build_id!r}")

        print(f"validate_fixups: OK {path}")


if __name__ == "__main__":
    main()
