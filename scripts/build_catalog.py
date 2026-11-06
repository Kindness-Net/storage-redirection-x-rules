"""校验 SRX 原生规则并打包云端目录。"""

import argparse
import hashlib
import json
from pathlib import Path

from catalog_schema import validate_rule

ROOT = Path(__file__).resolve().parents[1]


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def load(path):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key in {path}: {key}")
            result[key] = value
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)


def generate():
    provenance = load(ROOT / "migration/source-files.json")
    rules = []
    for path in sorted((ROOT / "rules").glob("*.json")):
        rule = load(path)
        validate_rule(rule, path.stem)
        rules.append(rule)
    if not 1 <= len(rules) <= 10000:
        raise ValueError("Invalid rule count")
    baseline = set(provenance["packages"].values())
    if not baseline <= {rule["package"] for rule in rules}:
        raise ValueError("Migrated rule is missing; retain it with a corrected recommendation")
    content = {
        "schema_version": 1,
        "upstream": {"repository": provenance["repository"], "commit": provenance["commit"]},
        "rules": rules,
    }
    revision = hashlib.sha256(encoded(content)).hexdigest()
    catalog = encoded({**content, "revision": revision})
    if len(catalog) > 8 * 1024 * 1024:
        raise ValueError("Catalog exceeds Android download limit")
    return catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = generate()
    path = ROOT / "catalog-v1.json"
    if args.check:
        if not path.is_file() or path.read_bytes() != content:
            raise SystemExit("Outdated catalog; run python3 scripts/build_catalog.py")
    else:
        path.write_bytes(content)
    print(f"{'Checked' if args.check else 'Generated'} catalog-v1.json: {len(content)} bytes")


if __name__ == "__main__":
    main()
