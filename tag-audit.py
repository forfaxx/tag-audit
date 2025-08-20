#!/usr/bin/env python3
"""
hugo-taxonomy-audit.py

Scan a Hugo content directory (or a single file) for tag and category usage in
front matter. Outputs per-file usage (optional), totals, singletons, and
inverse mappings (which files use a given tag/category). Multiple output
formats supported for summary/singletons/mappings.

Usage examples:
  # Default: summary + singletons (text)
  python3 hugo-taxonomy-audit.py

  # One file only
  python3 hugo-taxonomy-audit.py --file content/posts/metaclean.md

  # Show which files use each tag (markdown)
  python3 hugo-taxonomy-audit.py --by-tag --format markdown

  # Top 20 tags/categories by count, then mappings for those
  python3 hugo-taxonomy-audit.py --top 20 --by-tag --by-cat

  # Ignore drafts, only items used >= 2 times
  python3 hugo-taxonomy-audit.py --ignore-drafts --min-count 2
"""

from __future__ import annotations

import os
import sys
import argparse
import json
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Iterable, Optional

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan Hugo content for tag/category usage and mappings."
    )
    # Scope
    parser.add_argument(
        "--dir", "-d",
        default="./content",
        help="Path to Hugo content directory (default: ./content)"
    )
    parser.add_argument(
        "--file", "-f",
        help="Scan just a single file (overrides --dir and extension filtering)."
    )
    parser.add_argument(
        "--ext",
        default=".md",
        help="Comma-separated list of file extensions to include (default: .md)"
    )
    parser.add_argument(
        "--ignore-drafts",
        action="store_true",
        help="Skip files where front matter has draft: true."
    )

    # Section toggles
    parser.add_argument(
        "--per-file",
        action="store_true",
        help="Show tag/category usage per file (off by default)."
    )
    parser.add_argument(
        "--summary",
        dest="summary", action="store_true",
        help="Include totals tables (on by default)."
    )
    parser.add_argument(
        "--no-summary",
        dest="summary", action="store_false",
        help="Disable totals."
    )
    parser.set_defaults(summary=True)

    parser.add_argument(
        "--singletons",
        dest="singletons", action="store_true",
        help="Include singleton lists (on by default)."
    )
    parser.add_argument(
        "--no-singletons",
        dest="singletons", action="store_false",
        help="Disable singleton lists."
    )
    parser.set_defaults(singletons=True)

    # Inverse mappings
    parser.add_argument(
        "--by-tag",
        action="store_true",
        help="Show which files use each tag (respects filters/sort)."
    )
    parser.add_argument(
        "--by-cat",
        action="store_true",
        help="Show which files use each category (respects filters/sort)."
    )

    # Formatting & filters (apply to summary/singletons/mappings)
    parser.add_argument(
        "--format",
        choices=["text", "markdown", "csv", "json"],
        default="text",
        help="Output format for summary/singletons/mappings (default: text). "
             "Per-file view is always text."
    )
    parser.add_argument(
        "--sort",
        choices=["count", "alpha"],
        default="count",
        help="Sort order for totals/mapping keys (default: count)."
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=0,
        help="Only show items with count >= N (default: 0)."
    )
    parser.add_argument(
        "--top",
        type=int,
        default=0,
        help="Limit to top N items after filtering (default: 0 = no limit)."
    )

    return parser.parse_args()


def is_front_matter_yaml(lines: List[str]) -> Tuple[int, int]:
    """Return (start_idx, end_idx) of YAML front matter if present, else (-1, -1)."""
    if not lines or lines[0].strip() != "---":
        return -1, -1
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            return 0, idx
    return -1, -1


def coerce_list(value) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        s = value.strip().lower()
        return [s] if s else []
    if isinstance(value, list):
        out = []
        for v in value:
            if isinstance(v, str):
                s = v.strip().lower()
                if s:
                    out.append(s)
        return out
    return []


def read_front_matter(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"⚠️  Error reading {path}: {e}", file=sys.stderr)
        return None

    s, e = is_front_matter_yaml(lines)
    if s == -1:
        return {}

    frontmatter = "".join(lines[s + 1:e])
    try:
        data = yaml.safe_load(frontmatter) or {}
    except Exception as e:
        print(f"⚠️  Error parsing YAML in {path}: {e}", file=sys.stderr)
        return None
    return data


def iter_paths(content_dir: str, exts: List[str]) -> Iterable[str]:
    for root, _dirs, files in os.walk(content_dir):
        for filename in files:
            if any(filename.endswith(ext) for ext in exts):
                yield os.path.join(root, filename)


def collect(content_dir: str,
            exts: List[str],
            ignore_drafts: bool,
            file_paths: Optional[List[str]] = None
            ) -> Tuple[Counter, Counter, Dict[str, Dict[str, List[str]]],
                       Dict[str, List[str]], Dict[str, List[str]]]:
    tags_counter = Counter()
    cats_counter = Counter()
    file_usage: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: {"tags": [], "categories": []})
    tag_to_files: Dict[str, List[str]] = defaultdict(list)
    cat_to_files: Dict[str, List[str]] = defaultdict(list)

    paths: Iterable[str]
    if file_paths:
        paths = file_paths
    else:
        paths = iter_paths(content_dir, exts)

    for path in paths:
        data = read_front_matter(path)
        if data is None:
            continue  # read/parse failed
        if data == {}:
            # No front matter; skip quietly
            continue

        if ignore_drafts and bool(data.get("draft", False)):
            continue

        tags = coerce_list(data.get("tags"))
        cats = coerce_list(data.get("categories"))

        tags_counter.update(tags)
        cats_counter.update(cats)
        file_usage[path] = {"tags": tags, "categories": cats}
        for t in tags:
            tag_to_files[t].append(path)
        for c in cats:
            cat_to_files[c].append(path)

    return tags_counter, cats_counter, file_usage, tag_to_files, cat_to_files


def sort_and_filter(counter: Counter, mode: str, min_count: int, top: int) -> List[Tuple[str, int]]:
    items = [(k, v) for k, v in counter.items() if v >= min_count]
    if mode == "alpha":
        items.sort(key=lambda kv: kv[0])
    else:
        items.sort(key=lambda kv: (-kv[1], kv[0]))
    if top > 0:
        items = items[:top]
    return items


def print_per_file(file_usage: Dict[str, Dict[str, List[str]]]) -> None:
    print("\n🗂️  Tag & Category Usage Per File\n")
    for fname in sorted(file_usage.keys()):
        tags = ", ".join(file_usage[fname]["tags"]) if file_usage[fname]["tags"] else "(none)"
        cats = ", ".join(file_usage[fname]["categories"]) if file_usage[fname]["categories"] else "(none)"
        print(f"{fname}:")
        print(f"    tags: {tags}")
        print(f"    categories: {cats}")
    print("\n---\n")


def render_table_text(rows: List[Tuple[str, int]], header: str) -> str:
    if not rows:
        return f"{header}\n{'=' * len(header)}\n(none)\n"
    width_item = max(len(header), max(len(name) for name, _ in rows))
    width_cnt = max(5, max(len(str(cnt)) for _, cnt in rows))
    out = []
    out.append(f"{header}")
    out.append("=" * len(header))
    out.append(f"{'count':>{width_cnt}}  {'name':<{width_item}}")
    out.append(f"{'-' * width_cnt}  {'-' * width_item}")
    for name, cnt in rows:
        out.append(f"{cnt:>{width_cnt}}  {name:<{width_item}}")
    out.append(f"\nTotal {header.lower()}: {sum(cnt for _, cnt in rows)}")
    return "\n".join(out) + "\n"


def render_table_markdown(rows: List[Tuple[str, int]], header: str) -> str:
    if not rows:
        return f"### {header}\n\n*(none)*\n"
    out = [f"### {header}", "", "| count | name |", "| ---: | :---- |"]
    for name, cnt in rows:
        out.append(f"| {cnt} | {name} |")
    out.append("")
    out.append(f"_Total {header.lower()}: **{sum(cnt for _, cnt in rows)}**_")
    out.append("")
    return "\n".join(out)


def render_table_csv(rows: List[Tuple[str, int]], header: str) -> str:
    out = ["count,name"]
    for name, cnt in rows:
        safe = name.replace('"', '""')
        out.append(f"{cnt},\"{safe}\"")
    return "\n".join(out) + "\n"


def render_table_json(rows: List[Tuple[str, int]], header: str) -> str:
    return json.dumps(
        {"header": header, "total": sum(cnt for _, cnt in rows),
         "rows": [{"name": name, "count": cnt} for name, cnt in rows]},
        indent=2
    )


def render_by_format(rows: List[Tuple[str, int]], header: str, fmt: str) -> str:
    if fmt == "markdown":
        return render_table_markdown(rows, header)
    if fmt == "csv":
        return render_table_csv(rows, header)
    if fmt == "json":
        return render_table_json(rows, header)
    return render_table_text(rows, header)


# ---------- Inverse mapping renderers ----------

def render_mapping_text(header: str, ordered_keys: List[str], mapping: Dict[str, List[str]]) -> str:
    out = [f"{header}", "=" * len(header)]
    if not ordered_keys:
        out.append("(none)")
        return "\n".join(out) + "\n"
    for key in ordered_keys:
        out.append(f"\n{key}")
        out.append("-" * len(key))
        for path in sorted(mapping.get(key, [])):
            out.append(f"  {path}")
    out.append("")
    return "\n".join(out)


def render_mapping_markdown(header: str, ordered_keys: List[str], mapping: Dict[str, List[str]]) -> str:
    out = [f"### {header}", ""]
    if not ordered_keys:
        out.append("*(none)*")
        out.append("")
        return "\n".join(out)
    for key in ordered_keys:
        out.append(f"#### {key}")
        for path in sorted(mapping.get(key, [])):
            out.append(f"- `{path}`")
        out.append("")
    return "\n".join(out)


def render_mapping_csv(ordered_keys: List[str], mapping: Dict[str, List[str]]) -> str:
    # name,file
    out = ["name,file"]
    for key in ordered_keys:
        files = sorted(mapping.get(key, []))
        if not files:
            out.append(f"\"{key}\",")
        else:
            for path in files:
                out.append(f"\"{key}\",\"{path}\"")
    return "\n".join(out) + "\n"


def render_mapping_json(ordered_keys: List[str], mapping: Dict[str, List[str]], header_key: str) -> str:
    payload = {header_key: {k: sorted(mapping.get(k, [])) for k in ordered_keys}}
    return json.dumps(payload, indent=2)


def main() -> None:
    args = parse_args()

    raw_exts = [x.strip() for x in args.ext.split(",") if x.strip()]
    exts = [e if e.startswith(".") else f".{e}" for e in raw_exts]

    file_paths = [args.file] if args.file else None

    tags_counter, cats_counter, file_usage, tag_to_files, cat_to_files = collect(
        content_dir=args.dir,
        exts=exts,
        ignore_drafts=args.ignore_drafts,
        file_paths=file_paths,
    )

    # Per-file view (text only)
    if args.per_file:
        print_per_file(file_usage)

    # Summary tables
    if args.summary:
        tag_rows = sort_and_filter(tags_counter, args.sort, args.min_count, args.top)
        cat_rows = sort_and_filter(cats_counter, args.sort, args.min_count, args.top)
        print(render_by_format(tag_rows, "Tags", args.format), end="")
        print(render_by_format(cat_rows, "Categories", args.format), end="")

    # Singletons (text/markdown/csv/json)
    if args.singletons:
        single_tag_rows = sorted([(t, 1) for t, files in tag_to_files.items() if len(files) == 1],
                                 key=lambda kv: kv[0])
        single_cat_rows = sorted([(c, 1) for c, files in cat_to_files.items() if len(files) == 1],
                                 key=lambda kv: kv[0])

        if args.format == "text":
            print(render_table_text(single_tag_rows, "Singleton tags (used only once)"), end="")
            print(render_table_text(single_cat_rows, "Singleton categories (used only once)"), end="")
        elif args.format == "markdown":
            print(render_table_markdown(single_tag_rows, "Singleton tags (used only once)"))
            print(render_table_markdown(single_cat_rows, "Singleton categories (used only once)"))
        elif args.format == "csv":
            sys.stdout.write("# singleton_tags\n")
            sys.stdout.write(render_table_csv(single_tag_rows, "singleton_tags"))
            sys.stdout.write("# singleton_categories\n")
            sys.stdout.write(render_table_csv(single_cat_rows, "singleton_categories"))
        else:  # json
            payload = {
                "singletons": {
                    "tags": [r[0] for r in single_tag_rows],
                    "categories": [r[0] for r in single_cat_rows],
                }
            }
            print(json.dumps(payload, indent=2))

    # Inverse mappings (respect filters/sort/top)
    def ordered_keys_from(counter: Counter) -> List[str]:
        rows = sort_and_filter(counter, args.sort, args.min_count, args.top)
        return [name for name, _ in rows]

    if args.by_tag:
        ordered = ordered_keys_from(tags_counter)
        header = "Files by Tag"
        if args.format == "markdown":
            print(render_mapping_markdown(header, ordered, tag_to_files))
        elif args.format == "csv":
            sys.stdout.write("# files_by_tag\n")
            sys.stdout.write(render_mapping_csv(ordered, tag_to_files))
        elif args.format == "json":
            print(render_mapping_json(ordered, tag_to_files, "files_by_tag"))
        else:
            print(render_mapping_text(header, ordered, tag_to_files), end="")

    if args.by_cat:
        ordered = ordered_keys_from(cats_counter)
        header = "Files by Category"
        if args.format == "markdown":
            print(render_mapping_markdown(header, ordered, cat_to_files))
        elif args.format == "csv":
            sys.stdout.write("# files_by_category\n")
            sys.stdout.write(render_mapping_csv(ordered, cat_to_files))
        elif args.format == "json":
            print(render_mapping_json(ordered, cat_to_files, "files_by_category"))
        else:
            print(render_mapping_text(header, ordered, cat_to_files), end="")

    # Friendly footer (TTY only, text mode)
    if args.format == "text" and sys.stdout.isatty():
        print("\nDone. Need a tag merge/rename tool or fuzzy dup detector next? Say the word.\n")


if __name__ == "__main__":
    main()
