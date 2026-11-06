"""SRX 原生规则的构建边界，不读取或转换上游格式。"""

import re

PACKAGE_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+")
RECOMMENDATIONS = {"recommended", "unnecessary", "not_recommended", "cause_problems", "depends_on_situations", "custom"}
WARNING_CODES = {
    "direct_mapping", "filtered_export", "invalid_export_path", "android_export",
    "unrecognized_structure", "conflicting_exports", "cross_app_access",
    "non_standard_files", "corrected_metadata",
}


def valid_path(path, allow_rule_prefix=False):
    if not isinstance(path, str) or not path or path != path.strip():
        return False
    body = path[1:] if allow_rule_prefix and path[0] in "!^" else path
    if not body or body[0] in "/!^" or any(c in body for c in "\\*?") or any(ord(c) < 32 for c in body):
        return False
    segments = body.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        return False
    return not (len(segments) >= 2 and segments[0].lower() == "android" and segments[1].lower() == "data")


def validate_rule(rule, package):
    fields = {"package", "recommendation", "description", "authors", "upstream_verified", "updated_at", "upstream_file", "warnings", "allowed_real_paths", "path_mappings"}
    if set(rule) != fields or rule["package"] != package or not PACKAGE_PATTERN.fullmatch(package):
        raise ValueError(f"Invalid rule identity or fields: {package}")
    if rule["recommendation"] not in RECOMMENDATIONS:
        raise ValueError(f"Invalid recommendation: {package}")
    description = rule["description"]
    if not isinstance(description, dict) or not description or set(description) - {"en", "zh-CN", "zh-TW"}:
        raise ValueError(f"Invalid description: {package}")
    if not all(isinstance(v, str) and len(v) <= 32768 for v in description.values()):
        raise ValueError(f"Invalid description text: {package}")
    if not isinstance(rule["authors"], list) or not all(isinstance(v, str) for v in rule["authors"]):
        raise ValueError(f"Invalid authors: {package}")
    if type(rule["upstream_verified"]) is not bool or type(rule["updated_at"]) is not int or not 0 <= rule["updated_at"] <= 253402300799:
        raise ValueError(f"Invalid metadata: {package}")
    if not isinstance(rule["upstream_file"], str) or (rule["upstream_file"] and not re.fullmatch(r"[A-Za-z0-9_.-]+\.json", rule["upstream_file"])):
        raise ValueError(f"Invalid provenance: {package}")
    if not isinstance(rule["warnings"], list) or not set(rule["warnings"]) <= WARNING_CODES:
        raise ValueError(f"Invalid migration warning: {package}")
    paths, mappings = rule["allowed_real_paths"], rule["path_mappings"]
    if not isinstance(paths, list) or len(paths) > 256 or not all(valid_path(p, True) for p in paths) or len(set(paths)) != len(paths):
        raise ValueError(f"Invalid allowed paths: {package}")
    if not isinstance(mappings, dict) or len(mappings) > 256 or not all(valid_path(s) and valid_path(t) and s != t for s, t in mappings.items()):
        raise ValueError(f"Invalid path mappings: {package}")
