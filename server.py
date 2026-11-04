#!/usr/bin/env python3
"""motion-prompts MCP server.

Exposes a curated library of Claude motion-graphics video prompts
(collected from prompt-motion.com) plus customization tools, so Claude
can search, fetch and tailor motion prompts via / commands.

Run (stdio):  python3 server.py
Requires: pip install "mcp>=2"
"""
import json
import re
from pathlib import Path
from typing import Optional

from mcp.server.mcpserver import MCPServer

DATA = Path(__file__).parent / "data"

def _load(name):
    with open(DATA / name, encoding="utf-8") as f:
        return json.load(f)

def _load_prompts():
    # sharded files (for GitHub push size limits) take precedence when present
    import glob
    parts = sorted(glob.glob(str(DATA / "prompts-*.json")))
    if parts:
        out = []
        for p in parts:
            with open(p, encoding="utf-8") as f:
                out.extend(json.load(f))
        return out
    return _load("prompts.json")

PROMPTS = _load_prompts()
TEMPLATES = _load("templates.json")
TRENDING = _load("trending.json")
BY_SLUG = {p["slug"]: p for p in PROMPTS}
TREND_SLUGS = {t["slug"] for t in TRENDING}

server = MCPServer("motion-prompts")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _summary(p: dict) -> dict:
    return {
        "slug": p["slug"],
        "title": p.get("title"),
        "author": p.get("author"),
        "type": p.get("type"),
        "tags": p.get("tags", []),
        "published": p.get("published"),
        "url": p.get("url"),
        "trending": p["slug"] in TREND_SLUGS,
        "prompt_preview": (p.get("prompt") or "")[:180],
        "install": p.get("install"),  # present on skill entries
    }


@server.tool(description="Search the motion-graphics prompt library by keyword. Searches titles, tags and prompt text. Returns ranked matches.")
def search_prompts(query: str, kind: str = "all", limit: int = 8) -> dict:
    terms = [t for t in _norm(query).split() if t]
    if not terms:
        return {"results": [], "count": 0}
    scored = []
    for p in PROMPTS:
        if kind in ("prompt", "skill") and p.get("type") != kind:
            continue
        title, tags = _norm(p.get("title")), " ".join(p.get("tags", []))
        body = _norm(p.get("prompt"))
        score = 0
        for t in terms:
            if t in title:
                score += 3
            if t in tags:
                score += 2
            if t in body:
                score += 1
        if score:
            if p["slug"] in TREND_SLUGS:
                score += 1
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    results = [_summary(p) for _, p in scored[: max(1, min(limit, 25))]]
    return {"results": results, "count": len(results), "query": query}


@server.tool(description="Get the full details of one prompt by its slug: complete prompt text, author, source post, tags, video and stronger-template link.")
def get_prompt(slug: str) -> dict:
    p = BY_SLUG.get(slug)
    if not p:
        return {"error": f"no prompt with slug '{slug}'. Use search_prompts or trending to find slugs."}
    return {
        "slug": p["slug"], "title": p.get("title"), "author": p.get("author"),
        "type": p.get("type"), "tags": p.get("tags", []),
        "published": p.get("published"), "model": p.get("model"),
        "url": p.get("url"), "source_url": p.get("source_url"),
        "video_url": p.get("video_url"),
        "stronger_template": p.get("stronger_template"),
        "prompt": p.get("prompt"),
        "install": p.get("install"),  # skill entries: npx skills add ...
    }


@server.tool(description="List every tag in the library with how many prompts carry it. Use a tag with browse_by_tag.")
def list_tags() -> dict:
    from collections import Counter
    c = Counter()
    for p in PROMPTS:
        for t in p.get("tags", []):
            c[t] += 1
    return {"tags": [{"tag": t, "count": n} for t, n in c.most_common()], "total_prompts": len(PROMPTS)}


@server.tool(description="Browse prompts carrying a given tag (from list_tags), newest first.")
def browse_by_tag(tag: str, limit: int = 10) -> dict:
    tag = _norm(tag).replace(" ", "-")
    matches = [p for p in PROMPTS if tag in [t.replace(" ", "-") for t in p.get("tags", [])]]
    matches.sort(key=lambda p: p.get("published") or "", reverse=True)
    return {"tag": tag, "count": len(matches),
            "results": [_summary(p) for p in matches[: max(1, min(limit, 25))]]}


@server.tool(description="The site's most-liked prompts, ranked. Great defaults when the user has no specific idea.")
def trending(limit: int = 10) -> dict:
    out = []
    for t in TRENDING[: max(1, min(limit, 24))]:
        p = BY_SLUG.get(t["slug"])
        out.append(_summary(p) if p else t)
    return {"results": out, "count": len(out)}


@server.tool(description="Get one of Prompt Motion's 'stronger' base templates: 'showreel' (15s motion-design showreel, the most-used prompt, rewritten with full direction) or 'realtime-3d' (three.js real-time 3D piece template). Use as the base for customize_prompt.")
def get_template(template_id: str = "showreel") -> dict:
    t = next((x for x in TEMPLATES if x["id"] == template_id), None)
    if not t:
        return {"error": f"unknown template '{template_id}'. Available: {[x['id'] for x in TEMPLATES]}"}
    return t


def _apply_specs(text: str, purpose: str, video_format: str, duration: str,
                 colors: str, brand: str, notes: str) -> str:
    """Targeted field swaps on a template prompt, mirroring the site's Customize page."""
    out = text
    if duration:
        out = re.sub(r"\b15-second\b", duration, out)
        out = re.sub(r"\b15 second\b", duration, out, flags=re.I)
        out = re.sub(r"\bA ([89]\b)", r"An \1", out)  # "A 8 seconds" -> "An 8 seconds"
    if video_format and video_format.strip().lower() not in ("16:9", "1920x1080"):
        out = re.sub(r"1920x1080", video_format, out)
    spec_lines = []
    if purpose:
        spec_lines.append(f"Subject/purpose: {purpose}.")
    if video_format:
        spec_lines.append(f"Format: {video_format}.")
    if duration:
        spec_lines.append(f"Duration: {duration}.")
    if colors:
        spec_lines.append(f"Palette: {colors} (replace the template's default palette with this).")
    if brand:
        spec_lines.append(f"Brand: {brand} — feature its name, product and visual identity; keep the label readable in hero shots.")
    if notes:
        spec_lines.append(f"Extra direction: {notes}")
    if spec_lines:
        block = "## MY PROJECT\n\n" + "\n".join(spec_lines)
        block += "\n\nAdapt every section above to this project: keep the direction, structure, banned list and build steps, but swap the subject, format, duration and palette for mine."
        out = out.rstrip() + "\n\n" + block + "\n"
    return out


@server.tool(description="Customize a base prompt for the user's own video. 'base' is a gallery slug (from search/trending) or a template id ('showreel', 'realtime-3d'). Returns a ready-to-paste prompt adapted to the given purpose, format, duration, colors and brand.")
def customize_prompt(base: str, purpose: str, video_format: str = "9:16",
                     duration: str = "15 seconds", colors: str = "",
                     brand: str = "", notes: str = "") -> dict:
    tpl = next((x for x in TEMPLATES if x["id"] == base), None)
    if tpl:
        customized = _apply_specs(tpl["prompt"], purpose, video_format, duration, colors, brand, notes)
        return {"base": f"template:{tpl['id']}", "base_name": tpl["name"],
                "best_model": tpl.get("best_model"),
                "customized_prompt": customized}
    p = BY_SLUG.get(base)
    if not p:
        return {"error": f"unknown base '{base}'. Use a gallery slug or template id ('showreel', 'realtime-3d')."}
    header = (p.get("prompt") or "").rstrip()
    spec = ["## MY PROJECT", ""]
    if purpose: spec.append(f"Subject/purpose: {purpose}.")
    if video_format: spec.append(f"Format: {video_format}.")
    if duration: spec.append(f"Duration: {duration}.")
    if colors: spec.append(f"Palette: {colors}.")
    if brand: spec.append(f"Brand: {brand} — feature its name/product; keep labels readable in hero shots.")
    if notes: spec.append(f"Extra direction: {notes}")
    spec.append("")
    spec.append("Rewrite the prompt above for my project: keep its structure, energy and technique, but swap the subject, format, duration and palette for mine. Output only the final prompt.")
    return {"base": f"prompt:{p['slug']}", "base_name": p.get("title"),
            "author": p.get("author"), "source_url": p.get("source_url"),
            "customized_prompt": header + "\n\n" + "\n".join(spec)}


@server.tool(description="List the Claude motion-graphics skills in the library (installable via 'npx skills add ...'), with what each one does.")
def list_skills() -> dict:
    skills = [p for p in PROMPTS if p.get("type") == "skill"]
    return {"skills": [{
        "slug": p["slug"], "title": p.get("title"), "author": p.get("author"),
        "install": p.get("install"), "url": p.get("url"),
        "video_url": p.get("video_url"), "source_url": p.get("source_url"),
    } for p in skills], "count": len(skills)}


@server.tool(description="Library stats: total prompts, skills, templates, tags and date range.")
def stats() -> dict:
    from collections import Counter
    kinds = Counter(p.get("type") for p in PROMPTS)
    dates = sorted(p.get("published") for p in PROMPTS if p.get("published"))
    return {"prompts": len(PROMPTS), "by_type": dict(kinds),
            "templates": len(TEMPLATES), "trending": len(TRENDING),
            "date_range": [dates[0], dates[-1]] if dates else []}


if __name__ == "__main__":
    server.run()
