---
name: what-first
description: Use when the person asks what to build first, what they can do with AgentOS or Claude Code, which skills fit their business, "where do I start", "what should I try", or runs /gigi:what-first. Suggests three skills that fit their business, each with the sentence to type.
allowed-tools: Bash(python3:*)
---

# What to build first

1. Find the kit: `python3 "<base>/../../scripts/coach.py" kit`, where `<base>` is this skill's base directory (shown above as "Base directory for this skill"); with nothing, use the current folder.
2. Read their business from `<kit>/context/` (start with `me.md` and `current-priorities.md`). If those are missing, say the setup interview comes first (`/setup`, about 25 minutes) and stop.
3. Read the `description` line of each skill in `<kit>/.claude/skills/*/SKILL.md` (only the top few lines of each).
4. Pick three that would help this week, given their priorities. Prefer quick wins that show a result in under 15 minutes. For each, in two lines:
   - What it does for them, in their words (their business, their customers).
   - The exact sentence to type to start it.
5. End with: "Pick one and paste its sentence." Nothing else.
