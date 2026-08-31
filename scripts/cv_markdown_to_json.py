#!/usr/bin/env python3
"""
Generate _data/cv.json (JSON Resume) from the repository's own content.

Originally from academicpages (author: Yuan Chen). Rewritten for this fork
because the upstream parser silently produced an empty CV here:

  * upstream expects setext headings ("Education" + "======") and "* " bullets;
    this fork's _pages/cv.md uses ATX headings ("# Education") and "- " bullets,
    so Education / Work / Skills all parsed as zero entries and the committed
    cv.json stayed at its template defaults ("GitHub University", ...);
  * upstream globs _publications/*.md, which on this multilingual (jekyll-
    polyglot) site matches cv.md, cv.es.md, cv.de.md and cv.eo.md alike and
    produced every entry four times;
  * upstream read `languages:` from _config.yml, which on a polyglot site is
    the list of *site* locales (en/es/de/eo), not spoken languages.

Sources of truth:
  _config.yml `author:`  -> basics (name, email, location, profiles)
  _pages/cv.md           -> education, work, skills, languages, portfolio,
                            interests
  _publications/*.md     -> publications   (English files only)
  _talks/*.md            -> presentations  (English files only)
  _teaching/*.md         -> teaching       (English files only)

The output schema is exactly what _includes/cv-template.html renders; do not
add fields the template ignores.

Usage:
    python3 scripts/cv_markdown_to_json.py \
        --input _pages/cv.md --output _data/cv.json --config _config.yml
"""

import argparse
import glob
import json
import os
import re
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path

import yaml

# Matches a jekyll-polyglot translation file, e.g. "cv.es.md" or "2023-toon.de.md".
TRANSLATION_RE = re.compile(r"\.[a-z]{2}\.md$")


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


# --------------------------------------------------------------------------- #
# Markdown helpers
# --------------------------------------------------------------------------- #

def split_sections(md_file):
    """Split the markdown CV into {heading: body}.

    Understands both ATX ('# Education') and setext ('Education' / '======')
    headings, so it keeps working if the page is ever restyled.
    """
    content = Path(md_file).read_text(encoding="utf-8")
    content = re.sub(r"^---.*?---\s*", "", content, flags=re.DOTALL)

    lines = content.split("\n")
    sections, current, buf = {}, None, []

    def flush():
        if current is not None:
            sections[current] = "\n".join(buf).strip()

    i = 0
    while i < len(lines):
        line = lines[i]
        atx = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
        setext = (
            i + 1 < len(lines)
            and line.strip()
            and re.match(r"^=+$", lines[i + 1].strip())
        )
        if atx:
            flush()
            current, buf = atx.group(1).strip(), []
        elif setext:
            flush()
            current, buf = line.strip(), []
            i += 1
        elif current is not None:
            buf.append(line)
        i += 1
    flush()
    return sections


def top_level_items(text):
    """Yield (first_line, [sub_bullets]) for each top-level '-'/'*' bullet.

    "Top level" is relative to the shallowest bullet indent in the section, not
    literal column 0 — some sections in cv.md indent their bullets by a single
    space, and hard-coding 0 silently dropped them. A bullet counts as nested
    only once it is indented at least NEST_INDENT past that baseline, because
    the caller strips the section body (which removes the first line's indent
    and would otherwise make every following sibling look like a child).
    """
    NEST_INDENT = 2
    lines = [ln for ln in text.split("\n") if ln.strip()]
    indents = [
        len(ln) - len(ln.lstrip())
        for ln in lines
        if re.match(r"^\s*[-*]\s+", ln)
    ]
    base = min(indents) if indents else 0

    items = []
    current = None
    for raw in text.split("\n"):
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip())
        bullet = re.match(r"^[-*]\s+(.*)$", raw.strip())
        if bullet and indent < base + NEST_INDENT:
            if current:
                items.append(current)
            current = (bullet.group(1).strip(), [])
        elif bullet and current:
            current[1].append(bullet.group(1).strip())
        elif current:
            # continuation of the current bullet's first line
            head, subs = current
            if subs:
                subs[-1] = f"{subs[-1]} {raw.strip()}"
            else:
                current = (f"{head} {raw.strip()}", subs)
    if current:
        items.append(current)
    return items


def strip_md_links(text):
    """'[**Name**](url) — desc' -> ('Name', 'url', 'desc')."""
    m = re.match(r"\[\*{0,2}(.+?)\*{0,2}\]\((.+?)\)\s*[—–-]?\s*(.*)$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
    return re.sub(r"\*+", "", text).strip(), "", ""


# --------------------------------------------------------------------------- #
# Section parsers
# --------------------------------------------------------------------------- #

def parse_basics(config):
    author = (config or {}).get("author", {}) or {}
    basics = {
        "name": author.get("name") or (config or {}).get("title", ""),
        "email": author.get("email", "") or "",
        "phone": "",
        "website": (config or {}).get("url", ""),
        "summary": "",
        "location": {
            "address": "",
            "postalCode": "",
            "city": "",
            "countryCode": "",
            "region": "",
        },
        "profiles": [],
    }

    if author.get("bio"):
        basics["summary"] = author["bio"]
    if author.get("employer"):
        basics["summary"] = (
            f"{basics['summary']}. Currently at {author['employer']}."
            if basics["summary"]
            else f"Currently at {author['employer']}."
        )

    loc = (author.get("location") or "").strip()
    if loc:
        parts = [p.strip() for p in loc.split(",")]
        basics["location"]["city"] = parts[0]
        if len(parts) > 1:
            basics["location"]["region"] = parts[-1]

    # Only emit profiles that are actually configured.
    url_fields = [
        ("Google Scholar", "googlescholar"),
        ("ORCID", "orcid"),
        ("Semantic Scholar", "semantic"),
        ("ResearchGate", "researchgate"),
        ("arXiv", "arxiv"),
        ("Academia.edu", "academia"),
        ("Mastodon", "mastodon"),
    ]
    handle_fields = [
        ("GitHub", "github", "https://github.com/{}"),
        ("LinkedIn", "linkedin", "https://www.linkedin.com/in/{}"),
        ("Bluesky", "bluesky", "https://bsky.app/profile/{}"),
        ("Kaggle", "kaggle", "https://www.kaggle.com/{}"),
        ("X", "twitter", "https://x.com/{}"),
    ]
    for network, key in url_fields:
        if author.get(key):
            basics["profiles"].append(
                {"network": network, "username": "", "url": author[key]}
            )
    for network, key, tmpl in handle_fields:
        if author.get(key):
            basics["profiles"].append(
                {
                    "network": network,
                    "username": author[key],
                    "url": tmpl.format(author[key]),
                }
            )
    return basics


def parse_education(text):
    """'Ph.D. in Informatics, Graz University of Technology, 2027 (expected). Field: ... Thesis: ...'"""
    out = []
    for head, _subs in top_level_items(text):
        entry = head
        # Trailing sentences after the year become courses/details.
        m = re.match(
            r"^(?P<degree>.+?),\s*(?P<institution>[^,]+),\s*(?P<year>\d{4}[^.]*)\.?\s*(?P<rest>.*)$",
            entry,
        )
        if not m:
            continue
        degree = m.group("degree").strip()
        area = degree
        deg_m = re.match(r"^(?P<type>[^ ]+(?: of [A-Za-z.]+)?)\s+in\s+(?P<area>.+)$", degree)
        if deg_m:
            area = deg_m.group("area").strip()
            degree_type = deg_m.group("type").strip()
        else:
            degree_type = ""

        courses = []
        rest = m.group("rest").strip()
        for chunk in re.split(r"(?<=\.)\s+(?=[A-Z])", rest):
            chunk = chunk.strip().rstrip(".")
            if chunk:
                courses.append(chunk)

        out.append(
            {
                "institution": m.group("institution").strip(),
                "area": f"{degree_type} in {area}".strip() if degree_type else area,
                "studyType": degree_type,
                "startDate": "",
                "endDate": m.group("year").strip(),
                "gpa": None,
                "courses": courses,
            }
        )
    return out


def parse_work(text):
    """'2026 - present: Statistician' + indented sub-bullets."""
    out = []
    for head, subs in top_level_items(text):
        m = re.match(
            r"^(?P<start>\d{4})\s*[-–]\s*(?P<end>\d{4}|present)\s*:\s*(?P<position>.+)$",
            head,
            re.IGNORECASE,
        )
        if not m:
            continue
        company, summary, highlights = "", "", []
        if subs:
            company = subs[0].split(":")[0].strip()
            # keep any "Institute of ..." detail from the first sub-bullet
            first = subs[0]
            summary = first.split(":", 1)[1].strip() if ":" in first else ""
            highlights = [s for s in subs[1:] if s]
        out.append(
            {
                "company": company,
                "position": m.group("position").strip(),
                "website": "",
                "startDate": m.group("start"),
                "endDate": m.group("end"),
                "summary": summary,
                "highlights": highlights,
            }
        )
    return out


class _SkillsTableParser(HTMLParser):
    """Reads the <table> in the Skills section: <th> = category, <li> = keyword."""

    def __init__(self):
        super().__init__()
        self.headers, self.columns = [], []
        self._mode = None
        self._cell = -1
        self._buf = ""

    def handle_starttag(self, tag, attrs):
        if tag == "th":
            self._mode, self._buf = "th", ""
        elif tag == "td":
            self._mode = "td"
            self._cell += 1
            self.columns.append([])
        elif tag == "li" and self._mode == "td":
            self._buf = ""

    def handle_endtag(self, tag):
        if tag == "th":
            if self._buf.strip():
                self.headers.append(self._buf.strip())
            self._mode, self._buf = None, ""
        elif tag == "li" and self._mode == "td":
            if self._buf.strip() and self._cell < len(self.columns):
                self.columns[self._cell].append(self._buf.strip())
            self._buf = ""
        elif tag == "td":
            self._mode = None

    def handle_data(self, data):
        if self._mode:
            self._buf += data


def parse_skills(text):
    if "<table" in text:
        p = _SkillsTableParser()
        p.feed(text)
        out = []
        for i, name in enumerate(p.headers):
            keywords = p.columns[i] if i < len(p.columns) else []
            out.append({"name": name, "level": "", "keywords": keywords})
        return [s for s in out if s["keywords"]]

    # Fallback: "Category: a, b, c" bullets
    out = []
    for head, subs in top_level_items(text):
        if ":" in head:
            name, rest = head.split(":", 1)
            kws = [k.strip() for k in rest.split(",") if k.strip()] + subs
            out.append({"name": name.strip(), "level": "", "keywords": kws})
    return out


def parse_languages(text):
    out = []
    for head, _ in top_level_items(text):
        if ":" in head:
            lang, fluency = head.split(":", 1)
            out.append({"language": lang.strip(), "fluency": fluency.strip()})
    return out


def parse_interests(text):
    """Free-form bullets (e.g. 'Service and leadership') -> one interest block."""
    items = [re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", head) for head, _ in top_level_items(text)]
    return [i.strip().rstrip(".") for i in items if i.strip()]


def parse_portfolio_from_cv(text):
    """'- [**HeartRateLab.jl**](url) — description' -> portfolio entries."""
    out = []
    for head, _ in top_level_items(text):
        name, url, desc = strip_md_links(head)
        if name:
            out.append(
                {
                    "name": name,
                    "category": "Open Source",
                    "date": "",
                    "url": url,
                    "description": desc,
                }
            )
    return out


# --------------------------------------------------------------------------- #
# Collection parsers
# --------------------------------------------------------------------------- #

def _front_matters(directory):
    """Yield front matter of English-only markdown files in a collection."""
    if not os.path.isdir(directory):
        return
    for path in sorted(glob.glob(os.path.join(directory, "*.md"))):
        if TRANSLATION_RE.search(os.path.basename(path)):
            continue  # skip .es.md / .de.md / .eo.md duplicates
        text = Path(path).read_text(encoding="utf-8")
        m = re.match(r"^---\s*(.*?)\s*---", text, re.DOTALL)
        if not m:
            continue
        try:
            fm = yaml.safe_load(m.group(1))
        except yaml.YAMLError as exc:
            # Never skip silently: a stray apostrophe in a single-quoted
            # excerpt once dropped a whole publication from the JSON CV while
            # the Markdown CV still listed it. Jekyll would fail on this too.
            raise SystemExit(f"ERROR: invalid YAML front matter in {path}:\n{exc}")
        if isinstance(fm, dict):
            yield fm


def _as_str(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value) if value is not None else ""


def parse_publications(directory):
    pubs = [
        {
            "name": fm.get("title", ""),
            "publisher": fm.get("venue", ""),
            "releaseDate": _as_str(fm.get("date")),
            "website": fm.get("paperurl") or fm.get("slidesurl") or "",
            "summary": fm.get("excerpt", ""),
        }
        for fm in _front_matters(directory)
    ]
    return sorted(pubs, key=lambda p: p["releaseDate"], reverse=True)


def parse_presentations(directory):
    talks = [
        {
            "name": fm.get("title", ""),
            "event": fm.get("venue", ""),
            "date": _as_str(fm.get("date")),
            "location": fm.get("location", ""),
            "description": fm.get("excerpt", ""),
        }
        for fm in _front_matters(directory)
    ]
    return sorted(talks, key=lambda t: t["date"], reverse=True)


def parse_teaching(directory):
    items = [
        {
            "course": fm.get("title", ""),
            "institution": fm.get("venue", ""),
            "date": _as_str(fm.get("date")),
            "role": fm.get("type", ""),
            "description": fm.get("excerpt", ""),
        }
        for fm in _front_matters(directory)
    ]
    return sorted(items, key=lambda t: t["date"], reverse=True)


# --------------------------------------------------------------------------- #

def build(md_file, config_file, repo_root, output_file):
    sections = split_sections(md_file)
    config = yaml.safe_load(Path(config_file).read_text(encoding="utf-8")) if config_file else {}

    def sec(*names):
        for n in names:
            if n in sections:
                return sections[n]
        return ""

    interests = parse_interests(sec("Service and leadership", "Interests"))

    cv = {
        "basics": parse_basics(config),
        "work": parse_work(sec("Experience", "Work experience")),
        "education": parse_education(sec("Education")),
        "skills": parse_skills(sec("Skills")),
        "languages": parse_languages(sec("Languages")),
        "interests": (
            [{"name": "Service and leadership", "keywords": interests}] if interests else []
        ),
        "references": [],
        "publications": parse_publications(os.path.join(repo_root, "_publications")),
        "presentations": parse_presentations(os.path.join(repo_root, "_talks")),
        "teaching": parse_teaching(os.path.join(repo_root, "_teaching")),
        "portfolio": parse_portfolio_from_cv(sec("Open Source Projects", "Portfolio")),
    }

    Path(output_file).write_text(
        json.dumps(cv, indent=2, ensure_ascii=False, cls=DateTimeEncoder) + "\n",
        encoding="utf-8",
    )

    print(f"Wrote {output_file}")
    for key in ("education", "work", "skills", "languages", "publications",
                "presentations", "teaching", "portfolio"):
        print(f"  {key:<14} {len(cv[key])}")

    # Fail loudly rather than silently republishing an empty CV.
    empty = [k for k in ("education", "work", "publications") if not cv[k]]
    if empty:
        raise SystemExit(f"ERROR: no entries parsed for: {', '.join(empty)}")
    return cv


def main():
    ap = argparse.ArgumentParser(description="Generate _data/cv.json from repository content")
    ap.add_argument("--input", "-i", required=True, help="Markdown CV (_pages/cv.md)")
    ap.add_argument("--output", "-o", required=True, help="Output JSON (_data/cv.json)")
    ap.add_argument("--config", "-c", help="Jekyll _config.yml")
    args = ap.parse_args()

    repo_root = str(Path(args.input).resolve().parent.parent)
    build(args.input, args.config, repo_root, args.output)


if __name__ == "__main__":
    main()
