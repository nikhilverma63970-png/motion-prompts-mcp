#!/usr/bin/env bash
# motion-prompts MCP — one-shot installer for Claude Code + Antigravity.
# Usage: bash install.sh   (run from the cloned repo folder)
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "1/4  installing python dependency (mcp SDK)..."
if ! python3 -m pip install --quiet "mcp>=2" 2>/dev/null \
  && ! python3 -m pip install --quiet --break-system-packages "mcp>=2" 2>/dev/null \
  && ! python3 -m pip install --quiet --user --break-system-packages "mcp>=2" 2>/dev/null; then
  echo "     WARNING: pip install failed — install manually: python3 -m pip install 'mcp>=2'"
  echo "     continuing with registration..."
else
  echo "     done"
fi

echo "2/4  registering with Claude Code..."
if command -v claude >/dev/null 2>&1; then
  (claude mcp add --scope user motion-prompts -- python3 "$DIR/server.py" 2>/dev/null \
    || claude mcp add motion-prompts -- python3 "$DIR/server.py" 2>/dev/null \
    || true)
  echo "     done — restart Claude Code (new session) to load it"
else
  echo "     'claude' CLI not found, skipping."
  echo "     add manually later: claude mcp add --scope user motion-prompts -- python3 $DIR/server.py"
fi

echo "3/4  registering with Antigravity..."
python3 - "$DIR" <<'EOF'
import json, os, shutil, sys
d = os.path.expanduser("~/.gemini/config")
os.makedirs(d, exist_ok=True)
p = os.path.join(d, "mcp_config.json")
cfg = {}
if os.path.exists(p):
    try:
        cfg = json.load(open(p))
    except Exception:
        cfg = {}
cfg.setdefault("mcpServers", {})["motion-prompts"] = {
    "command": shutil.which("python3") or "python3",
    "args": [os.path.join(sys.argv[1], "server.py")],
}
json.dump(cfg, open(p, "w"), indent=2)
print("     config written:", p)
EOF

echo "4/4  installing slash commands..."
mkdir -p "$HOME/.claude/commands"
cp "$DIR"/commands/*.md "$HOME/.claude/commands/"
echo "     /motion-search  /motion-make  /motion-trending  /motion-skills"

echo ""
echo "Done. In Claude Code run:  claude mcp list   (motion-prompts should appear)"
echo "In Antigravity the server is picked up automatically."
