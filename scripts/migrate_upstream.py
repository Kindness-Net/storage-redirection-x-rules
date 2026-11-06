"""一次性迁移到空输出目录，不覆盖日常维护的 SRX 规则。"""

import argparse
import hashlib
from collections import Counter
from pathlib import Path

from build_catalog import ROOT, encoded, load
from catalog_schema import validate_rule
from legacy_rules import convert_legacy

UPSTREAM_COMMIT = "fa1040c6443844dfcd36275820b1c3285ae012bc"
UPSTREAM_REPOSITORY = "https://github.com/RikkaApps/StorageRedirect-assets"


def migrate(source, output):
    if output.exists() and any(output.iterdir()):
        raise ValueError("Migration output must be empty")
    definitions = load(source / "app_rule/app_recommendation_data.json")
    corrections = load(ROOT / "migration/corrections.json")
    manifest = load(ROOT / "migration/source-files.json")
    files = {
        str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ("app_rule", "app_category")
        for p in sorted((source / folder).rglob("*")) if p.is_file()
    }
    if files != manifest["files"]:
        raise ValueError("Source does not match the pinned upstream snapshot")
    rules, audit, packages = {}, {}, {}
    for path in sorted((source / "app_rule/apps").glob("*.json")):
        original = load(path)
        corrected = {**original, **corrections.get(path.name, {}).get("fields", {})}
        rule, skipped = convert_legacy(corrected, definitions)
        rule["upstream_file"] = path.name
        if path.name in corrections:
            rule["warnings"] = sorted(set(rule["warnings"]) | {"corrected_metadata"})
        package = rule["package"]
        validate_rule(rule, package)
        if package in rules:
            raise ValueError(f"Duplicate package: {package}")
        rules[package] = rule
        packages[path.name] = package
        audit[package] = {
            "source_file": path.name,
            "source_sha256": files[str(path.relative_to(source))],
            "skipped_exports": skipped,
            "warnings": rule["warnings"],
            "source_metadata": original,
        }
    (output / "rules").mkdir(parents=True, exist_ok=True)
    (output / "migration").mkdir(parents=True, exist_ok=True)
    for package, rule in rules.items():
        (output / "rules" / f"{package}.json").write_bytes(encoded(rule))
    provenance = {"repository": UPSTREAM_REPOSITORY, "commit": UPSTREAM_COMMIT, "files": files, "packages": packages}
    (output / "migration/source-files.json").write_bytes(encoded(provenance))
    report = {
        "app_count": len(rules),
        "apps_with_paths": sum(bool(r["allowed_real_paths"] or r["path_mappings"]) for r in rules.values()),
        "allowed_path_count": sum(len(r["allowed_real_paths"]) for r in rules.values()),
        "mapping_count": sum(len(r["path_mappings"]) for r in rules.values()),
        "warning_app_counts": dict(sorted(Counter(w for r in rules.values() for w in r["warnings"]).items())),
        "apps": audit,
    }
    (output / "migration/report.json").write_bytes(encoded(report))
    references = [source / "app_rule/app_recommendation_data.json", source / "app_rule/verified_apps.json", *sorted((source / "app_category").glob("*.json"))]
    (output / "migration/reference-data.json").write_bytes(encoded({str(p.relative_to(source)): load(p) for p in references}))
    print(f"Migrated {len(rules)} native SRX rules to {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    migrate(args.source, args.output)


if __name__ == "__main__":
    main()
