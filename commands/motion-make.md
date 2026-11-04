---
description: Build a customized motion-graphics video prompt for my project, based on a proven prompt or template
---

Build me a motion graphics video prompt for: **$ARGUMENTS**

Steps:
1. If the request names a style or use-case (e.g. "kinetic captions for talking-head reel", "product launch", "logo reveal"), use the `motion-prompts` MCP server's `search_prompts` to find the closest base. If it's a showreel-style or 3D piece, prefer the `showreel` or `realtime-3d` template via `get_template`.
2. If any of these are missing, ask briefly (one short question, or assume sensible defaults and say so): video format (default 9:16 for his talking-head reels), duration (default 15 seconds), colors, brand/product name.
3. Call `customize_prompt` with the chosen base slug or template id plus the specs.
4. Output the final customized prompt in a copy-paste code block, then add 2-3 lines: which base it came from (title + author + source link) and the one setting you'd tweak first if the output isn't right.

Run prompts on Opus 5.5 with effort set to max, per Prompt Motion's own guidance.
