# motion-prompts MCP

Your own MCP server for Claude motion-graphics video work. It bundles a searchable
library of **236 motion prompts + skills collected from [prompt-motion.com](https://prompt-motion.com)**
(a gallery of motion videos made with Claude, with the prompts behind them),
plus tools to fetch and customize them for your own videos.

## What's inside

| File | Contents |
|---|---|
| `server.py` | The MCP server (9 tools, stdio) |
| `data/prompts.json` | 231 prompts: title, author, full prompt text, tags, video, source post, date |
| `data/prompts.json` | 5 installable Claude skills (`npx skills add ...`) for motion graphics |
| `data/templates.json` | The 2 "stronger" base templates: **showreel** + **realtime-3d** (three.js) |
| `data/trending.json` | The 24 most-liked prompts, ranked |
| `commands/` | 4 slash commands for Claude Code |
| `scrape_prompt_motion.py` | Re-scraper — refresh the library anytime |

**9 MCP tools:** `search_prompts` · `get_prompt` · `list_tags` · `browse_by_tag` ·
`trending` · `get_template` · `customize_prompt` · `list_skills` · `stats`

**4 slash commands:** `/motion-search` · `/motion-make` · `/motion-trending` · `/motion-skills`

## Setup

**One command** (repo must be public, or use `gh repo clone` for private):
```bash
git clone https://github.com/nikhilverma63970-png/motion-prompts-mcp.git ~/motion-mcp && bash ~/motion-mcp/install.sh
```
The installer handles everything: installs the `mcp` Python package, registers the
server with Claude Code (`claude mcp add --scope user`), writes the Antigravity
config (`~/.gemini/config/mcp_config.json`), and installs the 4 slash commands.
Restart Claude Code / open a new session afterwards.

**Manual setup** (if you prefer step by step):

**1. Copy this folder to your Mac** (e.g. `~/motion-mcp`).

**2. Install the MCP SDK:**
```bash
pip install "mcp>=2"
```

**3. Connect it to Claude Code:**
```bash
claude mcp add motion-prompts -- python3 ~/motion-mcp/server.py
```
Or for Claude Desktop, add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "motion-prompts": {
      "command": "python3",
      "args": ["/Users/you/motion-mcp/server.py"]
    }
  }
}
```
Then restart Claude / open a new session and check the tools are listed.

**4. Install the slash commands** (Claude Code):
```bash
mkdir -p ~/.claude/commands
cp ~/motion-mcp/commands/*.md ~/.claude/commands/
```

## Usage

- `/motion-search kinetic captions` — find prompts for a style/use-case
- `/motion-make talking-head intro for my Shopify reels, 9:16, 8 seconds, neon green on black` — builds a customized, copy-paste prompt from the best base
- `/motion-trending` — the most-liked starting points
- `/motion-skills` — installable motion-graphics skills

Run the resulting prompts on **Opus 5.5 with effort set to max** — that's what every
video in the library was made with, per Prompt Motion.

## Refresh the data

```bash
cd ~/motion-mcp && python3 scrape_prompt_motion.py
```
Re-scrapes prompt-motion.com (polite, ~1–2 min) and rewrites `data/prompts.json`.
Restart the MCP server afterwards.

## Credit

All prompts, skills and videos belong to their creators, linked on every entry
(`source_url`). Curated at prompt-motion.com by [@p4nthera_](https://x.com/p4nthera_).
