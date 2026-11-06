"""将上游规则转换为明确标注语义差异的 SRX 建议。"""

from html.parser import HTMLParser
from catalog_schema import RECOMMENDATIONS, valid_path


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"p", "br", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"p", "li"}:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value):
    parser = PlainText()
    parser.feed(value)
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


def localized(value, definitions=None):
    if isinstance(value, str) and value.startswith("@"):
        value = (definitions or {}).get(value[1:], value)
    if isinstance(value, str):
        return {"en": plain_text(value), "zh-CN": plain_text(value)}
    if not isinstance(value, dict):
        return {}
    result = {}
    for locale, aliases in {"en": ["en"], "zh-CN": ["zh_CN", "zh-CN"], "zh-TW": ["zh", "zh_TW"]}.items():
        text = next((value[key] for key in aliases if isinstance(value.get(key), str)), None)
        if text:
            result[locale] = plain_text(text)
    return result


def convert_legacy(rule, definitions):
    package = rule["package"]
    recommendation = rule["recommendation"]
    status = recommendation.removeprefix("@") if isinstance(recommendation, str) else "custom"
    if status not in RECOMMENDATIONS:
        status = "custom"
    notes = localized(recommendation, definitions["recommendations"])
    for behavior in rule.get("behaviors", []):
        for locale, text in localized(behavior, definitions["behaviors"]).items():
            if text:
                notes[locale] = "\n".join(filter(None, [notes.get(locale), text]))

    warnings = set()
    skipped = []
    candidates = []
    exports = rule.get("export_folders", {})
    if set(exports) - {"data"} or "data" in rule:
        warnings.add("unrecognized_structure")
    for key, item in exports.get("data", {}).items():
        source, target = item.get("source"), item.get("target")
        reason = None
        if "mask" in item:
            reason = "filtered_export"
        elif not valid_path(source) or not valid_path(target):
            reason = "invalid_export_path"
        elif source.lower().split("/")[0] == "android" or target.lower().split("/")[0] == "android":
            reason = "android_export"
        elif set(item) - {"source", "target", "title", "summary", "call_media_scan", "add_to_downloads", "allow_child", "allow_temp"}:
            reason = "unrecognized_structure"
        if reason:
            warnings.add(reason)
            skipped.append({"id": key, "reason": reason})
        else:
            candidates.append((key, source, target))
    targets_by_source = {}
    for _, source, target in candidates:
        targets_by_source.setdefault(source.lower(), set()).add(target)
    allowed, mappings = set(), {}
    for key, source, target in candidates:
        if len(targets_by_source[source.lower()]) > 1:
            warnings.add("conflicting_exports")
            skipped.append({"id": key, "reason": "conflicting_exports"})
        elif source == target:
            allowed.add(source)
        else:
            mappings[source] = target
    if allowed or mappings:
        warnings.add("direct_mapping")
    if rule.get("accessible_folders"):
        warnings.add("cross_app_access")
    if rule.get("non_standard_files"):
        warnings.add("non_standard_files")
    known = {"package", "label", "verified", "authors", "last_update", "recommendation", "behaviors", "export_folders", "accessible_folders", "non_standard_files", "device_info", "data"}
    if set(rule) - known:
        warnings.add("unrecognized_structure")
    result = {
        "package": package,
        "recommendation": status,
        "description": notes,
        "authors": rule.get("authors", []),
        "upstream_verified": rule.get("verified", False),
        "updated_at": rule.get("last_update", {}).get("timestamp", 0),
        "warnings": sorted(warnings),
        "allowed_real_paths": sorted(allowed),
        "path_mappings": dict(sorted(mappings.items())),
    }
    return result, skipped
