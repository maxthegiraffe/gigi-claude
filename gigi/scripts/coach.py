#!/usr/bin/env python3
"""Gigi's coach inside Claude Code (Bootcamp 7, 2026-11-20).

  coach.py usage                 the plan meter and the fullest Claude Code threads, as JSON
  coach.py checkup               the usual causes of trouble, as JSON rows {name, ok, fix}
  coach.py kit                   the AgentOS kit folder, or nothing
  coach.py handoff-link FILE     the Claude link that opens a new thread on a handoff note (opened on a Mac)
  coach.py session-start         hook: a line when the plan is nearly used, a note when /setup hasn't run
  coach.py thread-check          hook: a note when this thread is getting long

It only reads. The hooks print nothing when there is nothing to say and never fail a session.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

KIT_REL = os.path.join("Documents", "Claude Code", "agentic-business-os-pkg")
FEED = "https://downloads.claude.ai/releases/darwin/universal/RELEASES.json"


# ---- readers

def is_kit(path):
    return bool(path) and os.path.isfile(os.path.join(path, "CLAUDE.md")) and os.path.isdir(os.path.join(path, ".claude", "skills", "setup"))


def find_kit(cwd, home):
    """The session's own folder when it is a kit, else the usual place, else None."""
    if is_kit(cwd):
        return cwd
    usual = os.path.join(home, KIT_REL)
    return usual if os.path.isfile(os.path.join(usual, "CLAUDE.md")) else None


def setup_done(kit):
    def written(name):
        try:
            return os.path.getsize(os.path.join(kit, "context", name)) > 0
        except OSError:
            return False
    return written("me.md") and written("current-priorities.md")


def meter(home):
    """The Claude app's newest plan reading: {fh: 5-hour %, sd: week %, age_min}, or None."""
    p = os.path.join(home, "Library", "Application Support", "Claude", "plan-usage-history.json")
    try:
        with open(p) as h:
            samples = json.load(h).get("samples") or []
        newest = max(samples, key=lambda x: x.get("t") or 0)
        t = newest["t"] / 1000 if newest["t"] > 1e11 else newest["t"]
        u = newest.get("u") or {}
        return {"fh": u.get("fh"), "sd": u.get("sd"), "age_min": max(0, int((time.time() - t) / 60))}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def thread_tokens(path):
    """How much context this thread's latest reply carried, read from the transcript's last megabyte, newest line first."""
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as h:
            h.seek(max(0, size - 2**20))
            lines = h.read().splitlines()
    except (OSError, TypeError):
        return None
    for raw in reversed(lines):
        if b'"usage"' not in raw or b'"assistant"' not in raw:
            continue
        try:
            d = json.loads(raw)
        except ValueError:
            continue
        if d.get("type") != "assistant" or d.get("isSidechain"):
            continue
        u = (d.get("message") or {}).get("usage") or {}
        ctx = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
        if ctx:
            return ctx
    return None


def window(tokens):
    return 1_000_000 if tokens > 200_000 else 200_000


def handoff_link(kit, note):
    import urllib.parse
    rel = os.path.relpath(note, kit)
    q = f"Read {rel} and carry on from where it leaves off. First tell me in two lines where we are and what's next."
    return "claude://code/new?" + urllib.parse.urlencode({"q": q, "folder": kit, "source": "gigi"}, quote_via=urllib.parse.quote)


# ---- checkup

def sh(cmd, timeout=12):
    import subprocess
    try:
        r = subprocess.run(["/bin/zsh", "-lc", cmd], capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, r.stdout
    except (OSError, subprocess.SubprocessError):
        return False, ""


def app_version():
    import subprocess
    try:
        out = subprocess.run(["/usr/bin/defaults", "read", "/Applications/Claude.app/Contents/Info", "CFBundleShortVersionString"],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None


def latest_version():
    import urllib.request
    try:
        with urllib.request.urlopen(FEED, timeout=5) as r:
            return json.load(r).get("currentRelease")
    except Exception:
        return None


def newer_or_same(installed, latest):
    if not latest:
        return True
    a = [int(x) if x.isdigit() else 0 for x in installed.split(".")]
    b = [int(x) if x.isdigit() else 0 for x in latest.split(".")]
    n = max(len(a), len(b))
    return (a + [0] * (n - len(a))) >= (b + [0] * (n - len(b)))


def checkup(home, cwd, quick=False):
    """Gigi's checkup, worded for Claude Code. quick skips the checks that run programs or reach the internet."""
    from concurrent.futures import ThreadPoolExecutor
    rows = []
    kit = find_kit(cwd, home)
    slow = {}
    if not quick:
        with ThreadPoolExecutor(max_workers=6) as pool:
            jobs = {
                "claude": pool.submit(sh, "claude auth status"),
                "gh": pool.submit(sh, "gh auth status"),
                "git": pool.submit(sh, "git --version"),
                "app": pool.submit(app_version),
                "latest": pool.submit(latest_version),
                "mcp": pool.submit(sh, f"cd {json.dumps(kit or home)} && claude mcp list", 20),
                "changes": pool.submit(sh, f"git -C {json.dumps(kit)} status --porcelain" if kit else "true"),
            }
            slow = {k: j.result() for k, j in jobs.items()}
        rows.append({"name": "Claude Code signed in", "ok": slow["claude"][0],
                     "fix": "Claude Code needs its own sign in, even when the Claude app is signed in. In Terminal, type: claude auth login"})
        rows.append({"name": "GitHub signed in", "ok": slow["gh"][0],
                     "fix": "GitHub isn't signed in, so saving your kit to GitHub will fail. In Terminal, type: gh auth login, then follow the code it shows."})
        app = slow["app"]
        rows.append({"name": "Claude app up to date", "ok": app is not None and newer_or_same(app, slow["latest"]),
                     "fix": "I can't find the Claude app. Download it from claude.ai/download." if app is None
                     else f"Your Claude app ({app}) is out of date. Quit it and open it again to update, or download it from claude.ai/download."})
    rows.append({"name": "AgentOS kit found", "ok": kit is not None,
                 "fix": "I can't find your AgentOS kit. It should be in Documents/Claude Code/agentic-business-os-pkg. Ask the bootcamp team to help install it."})
    if kit:
        rows.append({"name": "Working in your kit folder", "ok": os.path.realpath(cwd) == os.path.realpath(kit),
                     "fix": "This session isn't in your kit folder, so Claude can't see your business files. Click + New session and pick Documents/Claude Code/agentic-business-os-pkg."})
    rows.append({"name": "Setup interview done", "ok": bool(kit) and setup_done(kit),
                 "fix": "Your setup interview hasn't finished, so Claude doesn't know your business yet. In a session in your kit folder, type: /setup (about 25 minutes)."})
    if not quick:
        changed = len([l for l in slow["changes"][1].splitlines() if l.strip()]) if kit else 0
        rows.append({"name": f"Unsaved kit changes: {changed} files", "ok": True, "fix": ""})
        connected = len([l for l in slow["mcp"][1].splitlines() if ":" in l and "checking" not in l.lower()])
        rows.append({"name": f"Connectors Claude Code knows: {connected}", "ok": True, "fix": ""})
        rows.append({"name": "git installed", "ok": slow["git"][0], "fix": "git is missing. Ask the bootcamp team to rerun your Gigi line."})
    rows.append({"name": "Python 3.9 or newer", "ok": sys.version_info >= (3, 9),
                 "fix": "Python 3.9 or newer is missing. Ask the bootcamp team to rerun your Gigi line."})
    return rows


# ---- the two quiet checks (hooks): they tell, never block, and print nothing when there is nothing to say

def said_file(home):
    return os.path.join(home, ".claude", "gigi-plugin", "said.json")


def first_time(home, session, key):
    """True the first time this note comes up in this thread; remembered for the newest 200 threads."""
    p = said_file(home)
    try:
        with open(p) as h:
            said = json.load(h)
    except (OSError, ValueError):
        said = {}
    keys = said.pop(session, [])
    fresh = key not in keys
    said[session] = keys + ([key] if fresh else [])
    said = dict(list(said.items())[-200:])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w") as h:
        json.dump(said, h)
    os.replace(tmp, p)
    return fresh


def k(n):
    return f"{round(n / 1000)}K"


def session_start(home, payload):
    cwd = payload.get("cwd") or os.getcwd()
    show, notes = [], []
    m = meter(home)
    if m and m["age_min"] < 360:
        if (m.get("fh") or 0) >= 80:
            show.append(f"{m['fh']}% of your 5-hour Claude limit")
        if (m.get("sd") or 0) >= 80:
            show.append(f"{m['sd']}% of this week's plan")
    if show:
        line = " and ".join(show)
        notes.append(f"Gigi plugin: the person has used {line} (the Claude app's meter, {m['age_min']} min old). If they start something "
                     "heavy, mention it once in one line and suggest /gigi:usage. Don't block or repeat it.")
    if is_kit(cwd) and not setup_done(cwd):
        notes.append("Gigi plugin: this AgentOS kit's setup interview hasn't run (context/me.md or context/current-priorities.md is "
                     "missing), so Claude doesn't know their business yet. Early on, suggest once that they type /setup (about 25 minutes).")
    if not notes:
        return None
    out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n".join(notes)}}
    if show:
        out["systemMessage"] = f"Gigi: you've used {line}. Fresh threads and lighter work stretch it; /gigi:usage has the details."
    return out


def thread_check(home, payload):
    tokens = thread_tokens(payload.get("transcript_path"))
    if not tokens:
        return None
    w = window(tokens)
    marks = [m for m in ((160_000, 180_000) if w == 200_000 else (800_000, 900_000)) if tokens >= m]
    if not marks or not first_time(home, str(payload.get("session_id") or "none"), f"{w}:{marks[-1]}"):
        return None
    note = (f"Gigi plugin: this thread is now {k(tokens)} tokens long ({round(tokens * 100 / w)}% of its {k(w)} window), so every "
            "reply is slower and uses more of their plan, and details may get lost when Claude compacts it. Before answering, tell them "
            "in one short line and offer /gigi:fresh-start (a handoff note and a new thread with it). Say it once, then do what they asked.")
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": note}}


def run_hook(fn, home):
    try:
        payload = json.loads(sys.stdin.read() or "{}")
        out = fn(home, payload if isinstance(payload, dict) else {})
        if out:
            print(json.dumps(out))
    except Exception:
        pass
    return 0


# ---- the CLI

def main(argv):
    home = os.path.expanduser("~")
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "usage":
        try:
            sys.path.insert(0, HERE)
            import sweep  # Gigi's thread sweep, the same file she ships; only usage needs it
            out = sweep.usage(home)
        except Exception:
            out = {"meter": meter(home), "threads": []}
        print(json.dumps(out))
    elif cmd == "checkup":
        print(json.dumps(checkup(home, os.getcwd())))
    elif cmd == "session-start":
        return run_hook(session_start, home)
    elif cmd == "thread-check":
        return run_hook(thread_check, home)
    elif cmd == "kit":
        print(find_kit(os.getcwd(), home) or "")
    elif cmd == "handoff-link" and len(argv) > 2:
        note = os.path.abspath(argv[2])
        kit = find_kit(os.getcwd(), home) or os.path.dirname(os.path.dirname(note))
        link = handoff_link(kit, note)
        print(link)
        if sys.platform == "darwin" and "--no-open" not in argv:
            import subprocess
            subprocess.run(["/usr/bin/open", link], check=False)
    else:
        print(__doc__.strip())
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
