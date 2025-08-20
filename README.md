# tag-audit.py

*A quick taxonomy sleuth for Hugo sites. See which tags & categories you’ve used, which ones are lonely singletons, and which posts hang out where. Markdown/csv/json output options make it easy to paste into docs or crunch further.*  

---

## 🏃 Quick Start

```bash
# Install dep
python3 -m pip install pyyaml

# Basic run (from your Hugo repo root)
python3 tag-audit.py

# One file only
python3 tag-audit.py --file content/posts/metaclean.md

# Show which files use each tag (markdown output)
python3 tag-audit.py --by-tag --format markdown

# Top 20 tags/categories by count, with mappings
python3 tag-audit.py --top 20 --by-tag --by-cat

# Ignore drafts, only include items used ≥ 2 times
python3 tag-audit.py --ignore-drafts --min-count 2
```

---

## ✨ Features

- Scan entire Hugo `content/` tree or just one file  
- Reports: totals, per-file usage, singletons, and inverse mappings  
- Multiple output formats: `text`, `markdown`, `csv`, `json`  
- Filters: `--min-count`, `--top`, `--ignore-drafts`, `--ext`  
- Lowercases and trims values consistently  

---

## ⚙️ Usage flags (common ones)

| Flag | Purpose |
|------|---------|
| `--dir/-d PATH` | Content root (default: `./content`) |
| `--file/-f FILE` | Scan a single file |
| `--ignore-drafts` | Skip files with `draft: true` |
| `--per-file` | Show per-file tag/category usage |
| `--by-tag` | Map: files grouped by tag |
| `--by-cat` | Map: files grouped by category |
| `--format` | `text` (default), `markdown`, `csv`, `json` |
| `--sort` | `count` (default) or `alpha` |
| `--min-count N` | Only include items used ≥ N times |
| `--top N` | Limit to top N items |

---

## 🖼 Sample Output

**Default text view**  
```
Tags
====
count  name
-----  ----
   42  linux
   37  docker

Total tags: 91
```

**Markdown**  
```markdown
### Tags

| count | name |
| ---: | :---- |
| 42 | linux |
| 37 | docker |

_Total tags: **91**_
```

**JSON**  
```json
{
  "header": "Tags",
  "total": 91,
  "rows": [
    { "name": "linux", "count": 42 },
    { "name": "docker", "count": 37 }
  ]
}
```

---

## 💡 Notes

- Front matter must start with `---` and be valid YAML.  
- Tags/categories are normalized to lowercase.  
- Per-file output is text-only (always).  
- Inverse mappings respect filters (`--min-count`, `--top`, `--sort`).  

---

## 📜 License

MIT (or whatever you choose).  
