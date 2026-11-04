#!/usr/bin/env python3
"""Scrape prompt-motion.com gallery entries into data/prompts.json.

Polite, read-only scrape of public prompt pages. Run: python3 scrape_prompt_motion.py
"""
import json, re, time, html as htmllib
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://prompt-motion.com"
OUT = "data/prompts.json"

def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "motion-mcp-builder/1.0 (personal research)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")

def clean(t):
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S)
    t = htmllib.unescape(re.sub(r"\s+", " ", t))
    return t.strip()

def unesc(page):
    # page content is embedded JS-escaped inside the RSC flight payload
    return (page.replace('\\"','"').replace("\\'","'")
                .replace('\\n','\n').replace('\\/','/').replace('\\u0026','&'))

def parse_entry(slug, page):
    text = clean(page)
    u = unesc(page)
    d = {"slug": slug, "url": f"{BASE}/{slug}", "site": "prompt-motion.com"}

    m = re.search(r"<title>(.*?)</title>", page, re.S)
    if m:
        d["title"] = clean(m.group(1)).replace(" · Prompt Motion", "").strip()

    # author + source post
    m = re.search(r'href="(https://x\.com/([A-Za-z0-9_]+)/status/\d+)"', page)
    if m:
        d["source_url"] = m.group(1)
        d["author"] = "@" + m.group(2)

    # tags
    d["tags"] = sorted(set(re.findall(r'href="/tags/([a-z0-9-]+)"', page)))

    # type: Prompt vs Skill (h2 badge near the prompt block)
    m = re.search(r'<h2[^>]*>(Prompt|Skill)</h2>', u)
    d["type"] = m.group(1).lower() if m else "prompt"

    # prompt text: inside the entry-prompt div (unescaped payload)
    m = re.search(r'<div id="entry-prompt"[^>]*>(.*?)</div>', u, re.S)
    if m:
        d["prompt"] = clean(m.group(1)).strip()

    # skill entries: install command instead of a prompt
    if d.get("type") == "skill":
        m = re.search(r'npx skills add ([^\s<`"\']+)', text)
        if m:
            d["install"] = "npx skills add " + m.group(1).strip()
        else:
            m = re.search(r'github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)', u)
            if m:
                d["install"] = "npx skills add " + m.group(1)

    # video
    m = re.search(r'<video[^>]*src="([^"]+)"', page)
    if m:
        d["video_url"] = m.group(1).replace("\\", "")

    # model + posted date (from unescaped payload)
    m = re.search(r"Model\s+([A-Za-z0-9 .+]+?)\s+Posted", text)
    if m:
        d["model"] = m.group(1).strip()
    m = re.search(r'dateTime="(\d{4}-\d{2}-\d{2})"', u)
    if m:
        d["published"] = m.group(1)
    else:
        m = re.search(r"Posted\s+([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})", text)
        if m:
            d["published"] = m.group(1)

    # stronger template link
    m = re.search(r'href="(/templates/[a-z0-9-]+)"[^>]*>\s*A stronger version of this prompt', page)
    if m:
        d["stronger_template"] = BASE + m.group(1)

    return d

def get_slugs():
    home = fetch(BASE + "/")
    # aria-label cards are the authoritative list (covers prompts + skills,
    # whose slugs can have 7-char suffixes)
    cards = re.findall(r'<a aria-label="[^"]*"[^>]*href="(/[^"]*)"', home)
    slugs = sorted(set(h.strip("/") for h in cards if re.match(r"^/[a-z0-9][a-z0-9-]*-[a-f0-9]{6,8}$", h)))
    return slugs

def one(slug):
    try:
        page = fetch(f"{BASE}/{slug}")
        time.sleep(0.4)
        d = parse_entry(slug, page)
        if "prompt" not in d and "install" not in d:
            d["_warn"] = "no prompt or install extracted"
        return d
    except Exception as e:
        return {"slug": slug, "url": f"{BASE}/{slug}", "_error": str(e)}

def main():
    import os
    os.makedirs("data", exist_ok=True)
    slugs = get_slugs()
    print("entries:", len(slugs), flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        for i, d in enumerate(ex.map(one, slugs)):
            results.append(d)
            if (i + 1) % 25 == 0:
                print(f"  {i+1}/{len(slugs)}", flush=True)
    ok = [d for d in results if "prompt" in d or "install" in d]
    print(f"done: {len(ok)}/{len(results)} with prompt/install", flush=True)
    with open(OUT, "w") as f:
        json.dump(ok, f, indent=1, ensure_ascii=False)
    print("wrote", OUT, flush=True)
    write_parts(ok)


def write_parts(entries, n=3):
    """Shard prompts.json into n minified parts (push_files arg-size limits)."""
    import os
    chunk = (len(entries) + n - 1) // n
    for i in range(n):
        part = entries[i * chunk:(i + 1) * chunk]
        if not part:
            continue
        path = f"data/prompts-{i+1}.json"
        with open(path, "w") as f:
            json.dump(part, f, ensure_ascii=False, separators=(",", ":"))
        print(f"wrote {path} ({os.path.getsize(path)//1024} KB)", flush=True)

if __name__ == "__main__":
    main()
