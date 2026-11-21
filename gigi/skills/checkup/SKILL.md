---
name: checkup
description: Use when something isn't working, the person says "something's wrong", "check my setup", "why doesn't this work", sign-in or GitHub trouble, a missing kit, or runs /gigi:checkup. A read-only check of the usual causes with the fix.
allowed-tools: Bash(python3:*)
---

# Checkup

1. Say "Checking your setup, about 10 seconds."
2. Run `python3 "<base>/../../scripts/coach.py" checkup` with Bash, where `<base>` is this skill's base directory (shown above as "Base directory for this skill"). It prints JSON rows: `name`, `ok`, `fix`.
3. Report:
   - First line: "Everything looks right." or "N things to fix."
   - One line per row: ✓ or ✗ and the name.
   - Then the first problem's fix, step by step, in plain words.
4. Don't run fixes yourself unless they ask. Sign-ins (`claude auth login`, `gh auth login`) need them in Terminal: never type a password or code for them.
5. If everything is right but something still fails, ask them what they were doing and what the screen said, then try `/gigi:stuck`.
