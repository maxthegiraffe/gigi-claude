#!/usr/bin/env python3
"""Gigi's coach inside Claude Code (Bootcamp 7, 2026-11-20).

  coach.py usage                 the plan meter and the fullest Claude Code threads, as JSON
  coach.py checkup               the usual causes of trouble, as JSON rows {name, ok, fix}
  coach.py threads               the last 14 days of Claude Code threads (open, waiting on them, clusters), as JSON
  coach.py changes               what changed in the kit since the last save, as JSON
  coach.py restore [--from C] F  put files back from the last save (or commit C), keeping a copy in .gigi-undo/
  coach.py kit                   the AgentOS kit folder, or nothing
  coach.py handoff-link FILE     the Claude link that opens a new thread on a handoff note (opened on a Mac)
  coach.py session-start         hook: a line when the plan is nearly used, a note when /setup hasn't run
  coach.py thread-check          hook: a note when this thread is getting long

It only reads. The hooks print nothing when there is nothing to say and never fail a session.
"""
import json
import os
import re
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

def sh(cmd, timeout=12, plat=None):
    import subprocess
    try:
        if (plat or sys.platform) == "darwin":
            r = subprocess.run(["/bin/zsh", "-lc", cmd], capture_output=True, text=True, timeout=timeout)
        else:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
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
    a = [int(x) if x.isdigit() else 0 for x in installed.split(".")][:2]
    b = [int(x) if x.isdigit() else 0 for x in latest.split(".")][:2]
    n = max(len(a), len(b))
    return (a + [0] * (n - len(a))) >= (b + [0] * (n - len(b)))


def checkup(home, cwd, quick=False, plat=None):
    """Gigi's checkup, worded for Claude Code. quick skips the checks that run programs or reach the internet."""
    from concurrent.futures import ThreadPoolExecutor
    plat = plat or sys.platform
    mac = plat == "darwin"
    rows = []
    kit = find_kit(cwd, home)
    slow = {}
    if not quick:
        with ThreadPoolExecutor(max_workers=6) as pool:
            jobs = {
                "claude": pool.submit(sh, "claude auth status", 12, plat),
                "gh": pool.submit(sh, "gh auth status", 12, plat),
                "git": pool.submit(sh, "git --version", 12, plat),
                "mcp": pool.submit(sh, f"cd {json.dumps(kit or home)} && claude mcp list", 20, plat),
                "changes": pool.submit(sh, f"git -C {json.dumps(kit)} status --porcelain" if kit else "git --version", 12, plat),
            }
            if mac:
                jobs["app"] = pool.submit(app_version)
                jobs["latest"] = pool.submit(latest_version)
            slow = {k: j.result() for k, j in jobs.items()}
        rows.append({"name": "Claude Code signed in", "ok": slow["claude"][0],
                     "fix": "Claude Code needs its own sign in, even when the Claude app is signed in. In Terminal, type: claude auth login"})
        rows.append({"name": "GitHub signed in", "ok": slow["gh"][0],
                     "fix": "GitHub isn't signed in, so saving your kit to GitHub will fail. In Terminal, type: gh auth login, then follow the code it shows."})
        app = slow.get("app")
        if mac:
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


# ---- undo: what changed since the last save, and putting files back with a copy kept

def git(kit, *args):
    import subprocess
    return subprocess.run(["git", "-C", kit, *args], capture_output=True, text=True, timeout=20)


def keep_backups_out(kit):
    """Her copies never show up as changes: .gigi-undo/ goes in git's local exclude list (never committed)."""
    p = os.path.join(kit, ".git", "info", "exclude")
    try:
        text = open(p).read() if os.path.exists(p) else ""
        if ".gigi-undo/" not in text.split():
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "a") as h:
                h.write(("" if text.endswith("\n") or not text else "\n") + ".gigi-undo/\n")
    except OSError:
        pass


def changes(kit):
    keep_backups_out(kit)
    out = git(kit, "status", "--porcelain", "-z", "--untracked-files=all").stdout.split("\0")
    rows, i = [], 0
    while i < len(out):
        e = out[i]
        i += 1
        if len(e) < 4:
            continue
        xy, path = e[:2], e[3:]
        if xy[0] in "RC":
            i += 1   # the old name follows a rename
        state = "new" if xy == "??" else "deleted" if "D" in xy else "changed"
        rows.append({"path": path, "state": state})
    last = git(kit, "log", "-1", "--format=%cr: %s").stdout.strip()
    return {"kit": kit, "last_save": last, "changed": rows}


def restore(kit, paths, source="HEAD"):
    import shutil
    keep_backups_out(kit)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    results = []
    for p in paths:
        rel = os.path.normpath(p)
        if os.path.isabs(rel) or rel.startswith(".."):
            results.append({"path": p, "restored": False, "backup": None, "why": "outside the kit"})
            continue
        if git(kit, "cat-file", "-e", f"{source}:{rel}").returncode != 0:
            results.append({"path": rel, "restored": False, "backup": None,
                            "why": "new since that save, so there is nothing to put back; it stays as it is"})
            continue
        cur, backup = os.path.join(kit, rel), None
        if os.path.isfile(cur):
            backup = os.path.join(kit, ".gigi-undo", stamp, rel)
            os.makedirs(os.path.dirname(backup), exist_ok=True)
            shutil.copy2(cur, backup)
        ok = git(kit, "checkout", source, "--", rel).returncode == 0
        results.append({"path": rel, "restored": ok, "backup": backup, "why": "" if ok else "git could not put it back"})
    return results


# ---- the two quiet checks (hooks): they tell, never block, and print nothing when there is nothing to say

def said_file(home):
    return os.path.join(home, ".claude", "gigi-plugin", "said.json")


def first_time(home, session, key):
    """True the first time this note comes up in this thread; remembered for the newest 200 threads. Safe when several
    sessions write at once: one lock, and a temp file of its own."""
    import tempfile
    p = said_file(home)
    folder = os.path.dirname(p)
    os.makedirs(folder, exist_ok=True)
    lock = open(p + ".lock", "a")
    try:
        try:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
        except ImportError:
            pass
        try:
            with open(p) as h:
                said = json.load(h)
            said = said if isinstance(said, dict) else {}
        except (OSError, ValueError):
            said = {}
        keys = said.pop(session, [])
        fresh = key not in keys
        said[session] = keys + ([key] if fresh else [])
        said = dict(list(said.items())[-200:])
        fd, tmp = tempfile.mkstemp(dir=folder, prefix="said.", suffix=".tmp")
        with os.fdopen(fd, "w") as h:
            json.dump(said, h)
        os.replace(tmp, p)
        return fresh
    finally:
        lock.close()


def k(n):
    return f"{round(n / 1000)}K"


def session_start(home, payload):
    cwd = payload.get("cwd") or os.getcwd()
    show, notes = [], []
    m = meter(home)
    if m and m["age_min"] < 360:
        if (m.get("fh") or 0) >= 80 and m["age_min"] < 60:
            show.append(f"{m['fh']}% of your 5-hour Claude limit")
        if (m.get("sd") or 0) >= 80:
            show.append(f"{m['sd']}% of this week's plan")
    if show:
        line = " and ".join(show)
        if not first_time(home, "_start", f"{line}:{int(time.time() // (3 * 3600))}"):
            show = []
    if show:
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


PROBLEM = re.compile(r"api error|overloaded_error|overloaded error|\bsay(s|ing)? overloaded\b|\b529\b.{0,20}\b(error|overloaded)\b|"
                     r"\b(error|overloaded)\b.{0,20}\b529\b|prompt is too long|command not found|please run /login|no module named|"
                     r"permission denied|rate_limit_error|usage limit reached", re.I)


def thread_check(home, payload):
    session = str(payload.get("session_id") or "none")
    notes = []
    hit = PROBLEM.search(str(payload.get("prompt") or ""))
    if hit and first_time(home, session, "problem:" + hit.group(0).lower()):
        notes.append("Gigi plugin: their message quotes what looks like an error. Only if it is about Claude Code, the Claude app or the "
                     "kit misbehaving (not their business content): load the gigi:stuck skill with the Skill tool and answer from it, "
                     "the fix first, in plain words, a few short lines.")
    tokens = thread_tokens(payload.get("transcript_path"))
    if tokens:
        w = window(tokens)
        marks = [m for m in ((160_000, 180_000) if w == 200_000 else (800_000, 900_000)) if tokens >= m]
        if marks and first_time(home, session, f"{w}:{marks[-1]}"):
            notes.append(f"Gigi plugin: this thread is now {k(tokens)} tokens long ({round(tokens * 100 / w)}% of its {k(w)} window), so "
                         "every reply is slower and uses more of their plan, and details may get lost when Claude compacts it. Before "
                         "answering, tell them in one short line and offer /gigi:fresh-start (a handoff note and a new thread with it). "
                         "Say it once, then do what they asked.")
    if not notes:
        return None
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "\n".join(notes)}}


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
        out["platform"] = sys.platform   # the plan meter is read from the Claude app's files on a Mac only
        print(json.dumps(out))
    elif cmd == "threads":
        sys.path.insert(0, HERE)
        import sweep
        print(sweep.dump(sweep.fit(sweep.build(home, 14))))
    elif cmd == "checkup":
        print(json.dumps(checkup(home, os.getcwd())))
    elif cmd == "session-start":
        return run_hook(session_start, home)
    elif cmd == "thread-check":
        return run_hook(thread_check, home)
    elif cmd == "changes":
        print(json.dumps(changes(find_kit(os.getcwd(), home) or os.getcwd())))
    elif cmd == "restore" and len(argv) > 2:
        args, source = argv[2:], "HEAD"
        if args[0] == "--from" and len(args) > 2:
            source, args = args[1], args[2:]
        print(json.dumps(restore(find_kit(os.getcwd(), home) or os.getcwd(), args, source)))
    elif cmd == "kit":
        print(find_kit(os.getcwd(), home) or "")
    elif cmd == "handoff-link" and len(argv) > 2:
        note = os.path.abspath(argv[2])
        kit = find_kit(os.getcwd(), home) or os.path.dirname(os.path.dirname(note))
        link = handoff_link(kit, note)
        print(link)
        opened = False
        if sys.platform == "darwin" and "--no-open" not in argv and not os.environ.get("GIGI_NO_OPEN"):
            import subprocess
            opened = subprocess.run(["/usr/bin/open", link], check=False, capture_output=True).returncode == 0
        print(f"opened: {'yes' if opened else 'no'}")
    else:
        print(__doc__.strip())
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
