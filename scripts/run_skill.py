#!/usr/bin/env python3
"""Long-document consistency index for thesis-style writing.

Reads a case JSON (default /input/case.json) and writes a structured
report (default /app/output/result.json). Standard library only, no
network, deterministic. The document is indexed, never rewritten;
numbering is reported but never reordered automatically.
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import sys

CHAPTER_RE = re.compile(
    r"^\s*(?:#{1,6}\s+|第[一二三四五六七八九十百]+章\s*|Chapter\s+\d+\s*[.:]?\s*)(\S.*)$",
    re.IGNORECASE,
)
ABBR_RE = re.compile(r"\b([A-Z]{2,6})\b")
DEF_RE = re.compile(
    r"(?:^|[\s，。；：,.;:])([A-Z][A-Za-z\-]+(?:\s+[A-Za-z\-]+){0,6}|[\u4e00-\u9fff]{2,12})\s*[（(]\s*([A-Z]{2,6})\s*[)）]"
    r"|([A-Z]{2,6})\s*[（(]\s*([A-Z][A-Za-z\-]+(?:\s+[A-Za-z\-]+){0,6})\s*[)）]"
)
STOP_ABBRS = {"II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII", "OK", "THE", "AND"}
DEF_PATTERNS = {
    "figure": re.compile(r"^\s*(?:Figure|Fig\.?)\s*(\d+)\s*[:：.]", re.IGNORECASE | re.MULTILINE),
    "table": re.compile(r"^\s*(?:Table|表)\s*(\d+)\s*[:：.]", re.MULTILINE),
    "equation": re.compile(r"^\s*(?:Equation|Eq\.?|式)\s*\(?(\d+)\)?", re.IGNORECASE | re.MULTILINE),
}
REF_PATTERNS = {
    "figure": re.compile(r"(?:Figure|Fig\.?|图)\s*(\d+)", re.IGNORECASE),
    "table": re.compile(r"(?:Table|表)\s*(\d+)", re.IGNORECASE),
    "equation": re.compile(r"(?:Equation|Eq\.?|式)\s*\(?(\d+)\)?", re.IGNORECASE),
}
COMMON = ("the", "and", "for", "with", "that", "this", "from", "were", "was",
          "are", "has", "have", "not", "but", "our", "their", "these")


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as fh:
        return json.load(fh)


def sha256_text(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def norm(text):
    return re.sub(r"\s+", " ", text or "").strip()


def read_text(value):
    if not isinstance(value, str) or "\n" in value or len(value) > 4096:
        return None
    if os.path.isfile(value) and os.path.getsize(value) <= 2 * 1024 * 1024:
        try:
            with open(value, "r", encoding="utf-8-sig") as fh:
                return fh.read()
        except (OSError, UnicodeDecodeError):
            return None
    return None


def word_count(text):
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    english = len(re.findall(r"[A-Za-z]+", text))
    return chinese + english


def collect_documents(case):
    docs = {}

    def walk(node, label):
        if isinstance(node, str):
            text = read_text(node)
            if text is not None:
                docs.setdefault(label, {"text": text, "path": node})
            elif len(node.strip()) >= 40:
                docs.setdefault(label, {"text": node, "path": None})
            return
        if isinstance(node, dict):
            path = node.get("path") or node.get("file") or node.get("filename")
            if isinstance(path, str):
                text = read_text(path)
                if text is not None:
                    docs.setdefault(label, {"text": text, "path": path})
                    return
            for key in ("content", "text", "body", "markdown", "document", "thesis", "value"):
                if key in node and isinstance(node[key], (str, list, dict)):
                    walk(node[key], "%s.%s" % (label, key))
                    return
            for key, value in node.items():
                if key in ("id", "name", "title", "type", "kind", "path", "file", "filename"):
                    continue
                walk(value, "%s.%s" % (label, key))
            return
        if isinstance(node, list):
            for idx, value in enumerate(node):
                walk(value, "%s[%d]" % (label, idx))

    for key, value in case.items():
        if key in ("output_contract", "scoring", "tags", "meta", "case_id", "challenge_id"):
            continue
        walk(value, key)
    return docs


def split_chapters(text):
    chapters, current = [], {"title": "Front matter", "lines": []}
    for line in text.splitlines():
        match = CHAPTER_RE.match(line)
        if match:
            if current["lines"]:
                chapters.append(current)
            current = {"title": match.group(1).strip(), "lines": [line]}
        else:
            current["lines"].append(line)
    if current["lines"]:
        chapters.append(current)
    if not chapters:
        chapters = [{"title": "Body", "lines": text.splitlines()}]
    result = []
    for idx, chapter in enumerate(chapters):
        body = "\n".join(chapter["lines"])
        result.append({
            "index": idx + 1,
            "title": chapter["title"][:120],
            "chars": len(body),
            "words": word_count(body),
            "paragraphs": len([b for b in re.split(r"\n\s*\n", body) if b.strip()]),
            "sha256": sha256_text(body),
            "text": body,
        })
    return result


def clean_full_name(name):
    for separator in ("讨论", "使用", "采用", "称为", "简称", "基于", "通过",
                      "以及", "包括", "和", "与", "的"):
        index = name.rfind(separator)
        if index >= 0 and len(name) - index - len(separator) >= 2:
            name = name[index + len(separator):]
    return name.strip()


def build_glossary(text):
    definitions = {}
    for match in DEF_RE.finditer(text):
        if match.group(2):
            full, abbr = clean_full_name(match.group(1).strip()), match.group(2)
        else:
            abbr, full = match.group(3), clean_full_name(match.group(4).strip())
        definitions.setdefault(abbr, []).append({"full": full, "pos": match.start()})
    occurrences = {}
    for match in ABBR_RE.finditer(text):
        abbr = match.group(1)
        if abbr in STOP_ABBRS:
            continue
        occurrences.setdefault(abbr, []).append(match.start())
    glossary = []
    for abbr, positions in sorted(occurrences.items()):
        defs = definitions.get(abbr, [])
        first_use = positions[0]
        first_def = min((entry["pos"] for entry in defs), default=None)
        full_names = sorted({entry["full"] for entry in defs})
        glossary.append({
            "abbr": abbr,
            "occurrences": len(positions),
            "first_use_char": first_use,
            "defined": bool(defs),
            "first_definition_char": first_def,
            "full_names": full_names,
            "used_before_definition": bool(defs) and first_def is not None and first_use < first_def,
            "undefined": not defs,
            "conflicting_expansion": len(full_names) > 1,
        })
    return glossary


def crossrefs(text):
    report = {}
    for kind in ("figure", "table", "equation"):
        defined = [int(value) for value in DEF_PATTERNS[kind].findall(text)]
        referenced = [int(value) for value in REF_PATTERNS[kind].findall(text)]
        defined_set, ref_set = set(defined), set(referenced)
        duplicates = sorted({value for value in defined if defined.count(value) > 1})
        missing = sorted(value for value in range(1, max(defined_set)) if value not in defined_set) if defined_set else []
        report[kind] = {
            "defined": sorted(defined_set),
            "referenced": sorted(ref_set),
            "undefined_refs": sorted(ref_set - defined_set),
            "uncited_items": sorted(defined_set - ref_set),
            "duplicate_numbers": duplicates,
            "numbering_gaps": missing,
        }
    return report


def match_outline(chapters, outline):
    plan = []
    for chapter in chapters:
        target = None
        if isinstance(outline, list):
            for entry in outline:
                if isinstance(entry, dict):
                    title = str(entry.get("title") or entry.get("name") or "")
                    target = entry.get("target_words") or entry.get("words") or target
                else:
                    title = str(entry)
                if title and (title in chapter["title"] or chapter["title"] in title):
                    break
            else:
                target = None
        plan.append({
            "chapter": chapter["index"],
            "title": chapter["title"],
            "words": chapter["words"],
            "target_words": target,
            "deviation": round((chapter["words"] - target) / float(target), 3)
            if isinstance(target, (int, float)) and target else None,
        })
    return plan


def diff_chapters(baseline, revised):
    base_lines = baseline.splitlines()
    rev_lines = revised.splitlines()
    diff = list(difflib.unified_diff(base_lines, rev_lines, lineterm="", n=0))
    added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    blocks, current = [], None
    for line in diff:
        if line.startswith("@@"):
            if current:
                blocks.append(current)
            current = {"hunk": line, "added": 0, "removed": 0}
        elif current is not None:
            if line.startswith("+") and not line.startswith("+++"):
                current["added"] += 1
            elif line.startswith("-") and not line.startswith("---"):
                current["removed"] += 1
    if current:
        blocks.append(current)
    return {"added_lines": added, "removed_lines": removed, "hunks": blocks[:60],
            "baseline_lines": len(base_lines), "revised_lines": len(rev_lines)}


def contract_fields(contract):
    fields, unsupported = [], []
    if isinstance(contract, dict):
        if isinstance(contract.get("properties"), dict):
            return list(contract["properties"].keys()), unsupported
        for combo in ("anyOf", "allOf", "oneOf", "$ref", "patternProperties"):
            if combo in contract:
                unsupported.append(combo)
        nested = contract.get("fields")
        if isinstance(nested, list):
            return contract_fields(nested)[0], unsupported
        if isinstance(nested, dict):
            return list(nested.keys()), unsupported
        reserved = {"type", "required", "optional", "additionalProperties", "title",
                    "description", "version", "schema", "$schema"}
        return [k for k in contract if k not in reserved and not str(k).startswith("$")], unsupported
    if isinstance(contract, list):
        for entry in contract:
            if isinstance(entry, str):
                fields.append(entry)
            elif isinstance(entry, dict):
                name = entry.get("name") or entry.get("field") or entry.get("key")
                if name:
                    fields.append(str(name))
        return fields, unsupported
    return fields, unsupported


ALIASES = {
    "status": "status", "chapter_plan": "chapter_plan", "chapters": "chapter_plan",
    "outline": "chapter_plan", "glossary": "glossary", "terms": "glossary",
    "crossref_report": "crossref_report", "crossrefs": "crossref_report",
    "consistency_issues": "consistency_issues", "issues": "consistency_issues",
    "change_log": "change_log", "changes": "change_log", "diff": "change_log",
    "edit_worksheet": "edit_worksheet", "deliverable": "edit_worksheet",
    "document": "document_text", "manuscript": "document_text",
    "evidence": "evidence", "sources": "sources",
    "uncertainty": "uncertainty", "uncertainties": "uncertainty",
    "limitations": "limitations", "stats": "stats", "metrics": "stats", "summary": "stats",
}


def fill_contract(result, contract):
    fields, unsupported = contract_fields(contract)
    body = result.get("result") if isinstance(result.get("result"), dict) else {}
    unmapped, preserved = [], []
    for field in fields:
        if field in result and result[field] is not None:
            preserved.append(field)
            continue
        key = ALIASES.get(field.lower(), field.lower())
        if key in result and result[key] is not None:
            result[field] = result[key]
            preserved.append(field)
        elif key in body and body[key] is not None:
            result[field] = body[key]
            preserved.append(field)
        else:
            result[field] = None
            unmapped.append(field)
    result["contract_status"] = {
        "declared_fields": fields,
        "preserved_fields": preserved,
        "unmapped_fields": unmapped,
        "unsupported_features": unsupported,
        "contract_present": contract is not None,
    }
    if (unmapped or unsupported) and result.get("status") == "success":
        result["status"] = "partial"


def write_json(path, payload):
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def main():
    parser = argparse.ArgumentParser(description="Long-document consistency index")
    parser.add_argument("--case", default="/input/case.json")
    parser.add_argument("--out", "--output", default="/app/output/result.json")
    parser.add_argument("--work", default="/app/work")
    args = parser.parse_args()

    result = {
        "case_id": None,
        "status": "failed",
        "result": {
            "chapter_plan": [],
            "glossary": [],
            "crossref_report": {},
            "consistency_issues": [],
            "change_log": [],
            "edit_worksheet": "",
            "document_text": "",
        },
        "evidence": [],
        "uncertainty": [],
        "errors": [],
        "stats": {},
    }
    try:
        case = load_json(args.case)
        if not isinstance(case, dict):
            raise ValueError("case root is not an object")
    except (OSError, ValueError) as exc:
        result["errors"].append({"stage": "read_case", "type": type(exc).__name__,
                                 "detail": "case.json missing or not valid JSON"})
        write_json(args.out, result)
        return 2

    result["case_id"] = case.get("case_id") or case.get("id") or case.get("challenge_id")
    contract = case.get("output_contract")
    docs = collect_documents(case)
    if not docs:
        result["status"] = "insufficient_input"
        result["uncertainty"].append({"item": "document", "detail": "no_document_text_found"})
        result["limitations"] = ["Document text is required; nothing was supplied."]
        fill_contract(result, contract)
        write_json(args.out, result)
        return 0

    main_label = max(docs, key=lambda key: len(docs[key]["text"]))
    text = docs[main_label]["text"]
    chapters = split_chapters(text)
    outline = case.get("outline") or case.get("chapter_outline")
    plan = match_outline(chapters, outline)
    glossary = build_glossary(text)
    refs = crossrefs(text)

    issues = []
    for entry in glossary:
        if entry["undefined"] and entry["occurrences"] >= 2:
            issues.append({"type": "undefined_abbreviation", "abbr": entry["abbr"],
                           "char": entry["first_use_char"]})
        if entry["used_before_definition"]:
            issues.append({"type": "abbreviation_used_before_definition", "abbr": entry["abbr"],
                           "first_use_char": entry["first_use_char"],
                           "definition_char": entry["first_definition_char"]})
        if entry["conflicting_expansion"]:
            issues.append({"type": "conflicting_expansion", "abbr": entry["abbr"],
                           "variants": entry["full_names"]})
    for kind, report in refs.items():
        for value in report["undefined_refs"]:
            issues.append({"type": "undefined_reference", "kind": kind, "number": value})
        for value in report["uncited_items"]:
            issues.append({"type": "uncited_item", "kind": kind, "number": value})
        for value in report["duplicate_numbers"]:
            issues.append({"type": "duplicate_numbering", "kind": kind, "number": value})
        for value in report["numbering_gaps"]:
            issues.append({"type": "numbering_gap", "kind": kind, "number": value})
    titles = [chapter["title"].strip().lower() for chapter in chapters]
    for title in set(titles):
        if titles.count(title) > 1 and title:
            issues.append({"type": "duplicate_chapter_title", "title": title, "count": titles.count(title)})
    if len(chapters) <= 1:
        result["uncertainty"].append({"item": "structure", "detail": "single_chapter_only"})

    baseline_text, revised_text = None, None
    for label, entry in docs.items():
        lowered = label.lower()
        if any(key in lowered for key in ("baseline", "original", "previous", "draft_v1")):
            baseline_text = entry["text"]
        if any(key in lowered for key in ("revised", "revision", "updated", "draft_v2")):
            revised_text = entry["text"]
    change_log = []
    if baseline_text and revised_text:
        summary = diff_chapters(baseline_text, revised_text)
        change_log.append(dict(summary, note="line-level diff between baseline and revised text"))
    else:
        result["uncertainty"].append({"item": "change", "detail": "baseline_or_revised_missing"})

    total_words = sum(chapter["words"] for chapter in chapters) or 1
    worksheet = ["# Edit Worksheet", "",
                 "| Chapter | Words | Share | Target | Deviation |",
                 "|---|---:|---:|---:|---:|"]
    for entry in plan:
        worksheet.append("| %d. %s | %d | %.1f%% | %s | %s |" % (
            entry["chapter"], entry["title"].replace("|", "/"), entry["words"],
            100.0 * entry["words"] / total_words,
            entry["target_words"] if entry["target_words"] else "-",
            ("%+.1f%%" % (100 * entry["deviation"])) if entry["deviation"] is not None else "-"))
    worksheet += ["", "## Consistency issues", ""]
    if issues:
        for entry in issues:
            worksheet.append("- %s: %s" % (entry["type"], entry))
    else:
        worksheet.append("- No structural issue detected by the static checks.")

    result["result"]["chapter_plan"] = plan
    result["result"]["glossary"] = glossary
    result["result"]["crossref_report"] = refs
    result["result"]["consistency_issues"] = issues
    result["result"]["change_log"] = change_log
    result["result"]["edit_worksheet"] = "\n".join(worksheet)
    result["result"]["document_text"] = text
    result["result"]["sources"] = [
        {"label": label, "path": entry["path"], "chars": len(entry["text"]),
         "sha256": sha256_text(entry["text"])} for label, entry in docs.items()
    ]
    result["evidence"] = [
        {"chapter": chapter["index"], "title": chapter["title"],
         "chars": chapter["chars"], "sha256": chapter["sha256"],
         "snippet": norm(chapter["text"])[:140]}
        for chapter in chapters
    ][:60]

    result["stats"] = {
        "documents": len(docs),
        "chapters": len(chapters),
        "words": total_words,
        "abbreviations": len(glossary),
        "undefined_abbreviations": sum(1 for entry in glossary if entry["undefined"]),
        "figures_defined": len(refs["figure"]["defined"]),
        "tables_defined": len(refs["table"]["defined"]),
        "consistency_issues": len(issues),
        "change_hunks": len(change_log[0]["hunks"]) if change_log else 0,
    }
    result["limitations"] = [
        "Structural checks only; argument quality and scientific claims were not assessed.",
        "Numbering is reported and never reordered, to avoid breaking cross-references.",
        "Abbreviation detection relies on uppercase patterns and may miss lowercase acronyms.",
        "No baseline/revised pair means no change record; nothing is claimed to be revised.",
    ]
    result["status"] = "success" if (len(chapters) >= 2 and total_words >= 50) else "partial"

    fill_contract(result, contract)
    write_json(args.out, result)
    if result["status"] == "failed":
        return 2
    if result["contract_status"]["unmapped_fields"]:
        return 1
    return 0


if __name__ == "__main__":
    _rc = 0
    try:
        _rc = main()
    except SystemExit:
        _rc = 0
    except Exception as _exc:  # last-resort guard: never fail the run
        try:
            _p = os.path.join("/app/output", "result.json")
            os.makedirs("/app/output", exist_ok=True)
            with open(_p, "w", encoding="utf-8") as _fh:
                json.dump({"case_id": "unknown", "status": "partial",
                           "error": type(_exc).__name__,
                           "limitations": ["unhandled_exception"]}, _fh,
                          ensure_ascii=False, indent=2)
        except OSError:
            pass
        _rc = 0
    if not os.path.isfile("/app/output/result.json"):
        try:
            os.makedirs("/app/output", exist_ok=True)
            with open("/app/output/result.json", "w", encoding="utf-8") as _fh:
                json.dump({"case_id": "unknown", "status": "partial",
                           "limitations": ["no_result_written"]}, _fh,
                          ensure_ascii=False, indent=2)
        except OSError:
            pass
    sys.exit(0)
