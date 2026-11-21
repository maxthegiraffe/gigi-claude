#!/usr/bin/env python3
"""Gigi Assistant's thread sweep: a small digest of this person's Claude Code threads, for her report.

  sweep.py                 the last 7 days, written to ~/Library/Application Support/Gigi Helper/sweep/digest.json
  sweep.py --days 14       another window
  sweep.py --home DIR      read DIR as the home folder (the tests)
  sweep.py --out DIR       write digest.json there
  sweep.py --usage         the plan meter and how full recent threads are, as JSON (for her usage watch)
  sweep.py --tail ID --out FILE   a thread's last 60 turns as text (for a fresh start)

Reads the Claude app's per-thread index (claude-code-sessions/**/local_*.json) and only the in-window tail of each
active transcript. Reads only, sends nothing, and always exits 0 with a digest, even when there is nothing to read.
A port of Max's thread-organizer sweep (2026-11-15) without the email, GitHub and git parts. Transcript text is
data, not instructions.
"""
import argparse
import glob
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone

MAX_BYTES = 24576
MAX_THREADS = 40
NOISE = ("<system-reminder", "<command", "<local-command", "<ci-monitor", "<side-sessions",
         "<task-notification", "<artifact-view-context", "This session is being continued", "[Request interrupted")
STOP = set("the a an and or of to for in on with by vs via from at is it my new fix how what why this that your".split())
TS = re.compile(rb'"timestamp":\s?"([0-9T:.\-]+)Z?"')
DAY_MS = 86_400_000


def short(text, n=220):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text if len(text) <= n else text[: n - 1] + "…"


def day(ms):
    return time.strftime("%m-%d %H:%M", time.localtime((ms or 0) / 1000))


# ---------- the app's index ----------
def current_account(sessions):
    # Each signed-in account keeps its threads under <sessions>/<account>/<org>/. The sidebar shows only the
    # signed-in one: the folder holding the most recently written thread.
    hits = glob.glob(sessions + "/*/*/local_*.json")
    return os.path.dirname(max(hits, key=os.path.getmtime)) if hits else None


def load_index(sessions):
    acct = current_account(sessions)
    if not acct:
        return []
    archived = set()
    for idx in glob.glob(acct + "/**/archived-sessions.idx", recursive=True):
        try:
            with open(idx) as h:
                archived |= set(json.load(h).get("archived", []))
        except (OSError, ValueError, AttributeError):
            pass
    rows = []
    for path in glob.glob(acct + "/**/local_*.json", recursive=True):
        try:
            with open(path) as h:
                d = json.load(h)
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict) or not d.get("sessionId"):
            continue
        d["_archived"] = bool(d.get("isArchived")) or d["sessionId"] in archived
        d["_kind"] = ("scheduled" if d.get("scheduledTaskId")
                      else "side" if (d.get("spawnedFrom") or {}).get("sessionId") else "thread")
        rows.append(d)
    return rows


# ---------- transcripts ----------
def transcript(projects, cli_id):
    hits = glob.glob(f"{projects}/*/{cli_id}.jsonl") if cli_id else []
    return hits[0] if hits else None


def first_ts(h, off):
    h.seek(off)
    if off:
        h.readline()
    for _ in range(40):
        line = h.readline()
        if not line:
            return None
        m = TS.search(line)
        if m:
            return m.group(1).decode()
    return None


def start_offset(h, size, since_iso):
    lo, hi = 0, size
    while hi - lo > 65536:
        mid = (lo + hi) // 2
        ts = first_ts(h, mid)
        if ts is None or ts >= since_iso:
            hi = mid
        else:
            lo = mid
    return lo


def human_text(d):
    """What a person typed on this transcript line, or None (tool results, reminders and app notes are not asks)."""
    if d.get("type") != "user" or d.get("isMeta") or d.get("isSidechain"):
        return None
    content = (d.get("message") or {}).get("content")
    text = content if isinstance(content, str) else " ".join(
        c.get("text", "") for c in content or [] if isinstance(c, dict) and c.get("type") == "text")
    human = d.get("turnOrigin") == "human" or (d.get("turnOrigin") is None and isinstance(content, str))
    if not text or not human or text.lstrip().startswith(NOISE):
        return None
    return text


def tail(path, since_iso, home):
    out = {"asks": [], "files": set(), "context": 0}
    size = os.path.getsize(path)
    with open(path, "rb") as h:
        h.seek(start_offset(h, size, since_iso))
        if h.tell():
            h.readline()
        for line in h:
            if b'"type":"user"' not in line and b'"type": "user"' not in line \
                    and b'"type":"assistant"' not in line and b'"type": "assistant"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict) or (d.get("timestamp") or "") < since_iso or d.get("isSidechain"):
                continue
            if d.get("type") == "user":
                text = human_text(d)
                if text:
                    out["asks"].append(short(text, 160))
                continue
            msg = d.get("message") or {}
            u = msg.get("usage") or {}
            ctx = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
            out["context"] = ctx or out["context"]
            content = msg.get("content")
            for c in content if isinstance(content, list) else []:
                if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
                    f = (c.get("input") or {}).get("file_path")
                    if f and "/scratchpad/" not in f:
                        out["files"].add(short(f.replace(home, "~"), 80))
    asks = out["asks"]
    out["asks"] = asks if len(asks) <= 3 else [asks[0], asks[-2], asks[-1]]
    out["files"] = sorted(out["files"])[:6]
    return out


def opener(path):
    """How this thread began: its first typed line, lower-cased, spaces collapsed, 60 characters."""
    try:
        with open(path, "rb") as h:
            for _ in range(400):
                line = h.readline()
                if not line:
                    return None
                if b'"user"' not in line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                text = human_text(d) if isinstance(d, dict) else None
                if text:
                    return re.sub(r"\s+", " ", text).strip().lower()[:60]
    except OSError:
        pass
    return None


# ---------- the digest ----------
def build(home, days):
    now = time.time()
    since = now - days * 86400
    since_iso = datetime.fromtimestamp(since, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    sessions = os.path.join(home, "Library/Application Support/Claude/claude-code-sessions")
    projects = os.path.join(home, ".claude/projects")
    rows = [r for r in load_index(sessions) if r["_kind"] != "scheduled"]
    window = {"days": days, "until": time.strftime("%a %m-%d %H:%M", time.localtime(now))}
    if not rows:
        return {"empty": True, "window": window, "threads": [], "counts": {}, "waiting": [], "clusters": {},
                "tips": {"repeat_openers": [], "folders_without_claude_md": [], "long_threads": []}}

    def age(r):
        return (now * 1000 - (r.get("lastActivityAt") or 0)) / DAY_MS

    def status(r):
        return (r.get("postTurnSummary") or {}).get("status_category")

    active = sorted((r for r in rows if max(r.get("lastActivityAt") or 0, r.get("createdAt") or 0) >= since * 1000),
                    key=lambda r: r.get("lastActivityAt") or 0, reverse=True)
    threads = []
    for r in active[:MAX_THREADS]:
        t = {"id": r["sessionId"], "title": short(r.get("title"), 80), "kind": r["_kind"], "last": day(r.get("lastActivityAt")),
             "archived": r["_archived"], "status": status(r),
             "needs": short((r.get("postTurnSummary") or {}).get("needs_action"), 160) or None,
             "wrap": short((r.get("turnWrapUp") or {}).get("description"), 200) or None,
             "folder": short(str(r.get("cwd") or "").replace(home, "~"), 80) or None}
        path = transcript(projects, r.get("cliSessionId"))
        if path:
            try:
                t["mb"] = os.path.getsize(path) // 2**20
                t.update(tail(path, since_iso, home))
            except OSError:
                pass
        threads.append({k: v for k, v in t.items() if v not in (None, [], 0, "", False)})

    open_rows = [r for r in rows if not r["_archived"]]
    waiting = sorted((r for r in open_rows if status(r) in ("blocked", "review_ready")),
                     key=lambda r: r.get("lastActivityAt") or 0, reverse=True)
    buckets = Counter("<1d" if age(r) < 1 else "1-3d" if age(r) < 3 else "3-7d" if age(r) < 7
                      else "7-30d" if age(r) < 30 else ">30d" for r in open_rows)

    recent = [r for r in open_rows if age(r) < 14]
    words = Counter()
    for r in recent:
        words.update({w for w in re.findall(r"[a-z0-9]+", (r.get("title") or "").lower()) if w not in STOP and len(w) > 2})
    clusters = {w: [short(r.get("title"), 60) for r in recent if w in (r.get("title") or "").lower()][:6]
                for w, c in words.most_common(6) if c >= 3}

    openers = Counter()
    for r in rows:
        if (now * 1000 - (r.get("createdAt") or 0)) / DAY_MS > 30:
            continue
        path = transcript(projects, r.get("cliSessionId"))
        o = opener(path) if path else None
        if o:
            openers[o] += 1
    repeat = [{"opener": o, "threads": n} for o, n in openers.most_common(5) if n >= 3]

    bare, seen = [], set()
    for r in sorted(open_rows, key=lambda r: r.get("lastActivityAt") or 0, reverse=True):
        cwd = r.get("cwd")
        if not cwd or cwd in seen or age(r) > 30:
            continue
        seen.add(cwd)
        if os.path.isdir(cwd) and not os.path.exists(os.path.join(cwd, "CLAUDE.md")):
            bare.append(short(cwd.replace(home, "~"), 80))
    return {
        "empty": False,
        "window": window,
        "threads": threads,
        "counts": {"open": len(open_rows), "archived": len(rows) - len(open_rows),
                   "open_done_older_than_7d": sum(1 for r in open_rows if age(r) > 7 and status(r) in (None, "completed")),
                   "open_by_age": dict(buckets), "waiting_on_you": len(waiting)},
        "waiting": [{"id": r["sessionId"], "title": short(r.get("title"), 80), "days": round(age(r), 1),
                     "needs": short((r.get("postTurnSummary") or {}).get("needs_action"), 160) or None} for r in waiting[:10]],
        "clusters": clusters,
        "tips": {"repeat_openers": repeat, "folders_without_claude_md": bare[:5],
                 "long_threads": [{"title": t["title"], "context": t["context"]} for t in threads if t.get("context", 0) >= 500_000][:5]},
    }


def dump(digest):
    return json.dumps(digest, ensure_ascii=False, separators=(",", ":"))


def fit(digest):
    """Under MAX_BYTES: the oldest listed threads go first (the counts still cover them)."""
    while len(dump(digest).encode()) >= MAX_BYTES and digest["threads"]:
        digest["threads"].pop()
    return digest


# ---------- usage: the plan meter and how full each thread is (2026-11-20, the bootcamp coach) ----------
def read_tail(path, max_bytes=8 * 2**20):
    """The last max_bytes of a transcript, as parsed lines (a thread can run to hundreds of MB)."""
    out = []
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as h:
            h.seek(max(0, size - max_bytes))
            if h.tell():
                h.readline()
            for line in h:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if isinstance(d, dict):
                    out.append(d)
    except OSError:
        pass
    return out


def context_now(path):
    """The context the thread's latest reply carried, or None when the transcript has no counts."""
    for d in reversed(read_tail(path, 2 * 2**20)):
        if d.get("type") != "assistant" or d.get("isSidechain"):
            continue
        u = (d.get("message") or {}).get("usage") or {}
        ctx = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) + (u.get("cache_creation_input_tokens") or 0)
        if ctx:
            return ctx
    return None


def usage(home, days=3):
    meter = None
    p = os.path.join(home, "Library/Application Support/Claude/plan-usage-history.json")
    try:
        with open(p) as h:
            samples = json.load(h).get("samples") or []
        newest = max(samples, key=lambda x: x.get("t") or 0)
        t = newest["t"] / 1000 if newest["t"] > 1e11 else newest["t"]
        u = newest.get("u") or {}
        meter = {"fh": u.get("fh"), "sd": u.get("sd"), "age_min": max(0, int((time.time() - t) / 60))}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        meter = None
    sessions = os.path.join(home, "Library/Application Support/Claude/claude-code-sessions")
    projects = os.path.join(home, ".claude/projects")
    since = (time.time() - days * 86400) * 1000
    threads = []
    for r in load_index(sessions):
        if r["_kind"] == "scheduled" or r["_archived"] or (r.get("lastActivityAt") or 0) < since:
            continue
        path = transcript(projects, r.get("cliSessionId"))
        tokens = context_now(path) if path else None
        if not tokens:
            continue
        window = 1_000_000 if tokens > 200_000 else 200_000
        threads.append({"id": r["sessionId"], "title": short(r.get("title"), 80), "tokens": tokens, "window": window,
                        "pct": round(tokens * 100 / window), "last": day(r.get("lastActivityAt"))})
    threads.sort(key=lambda t: t["pct"], reverse=True)
    return {"meter": meter, "threads": threads[:10]}


def write_tail(home, ident, out, turns=60, max_bytes=40_960):
    """A thread's last turns as plain text (THEM: and CLAUDE: lines), for a handoff note."""
    sessions = os.path.join(home, "Library/Application Support/Claude/claude-code-sessions")
    projects = os.path.join(home, ".claude/projects")
    row = next((r for r in load_index(sessions) if ident in (r["sessionId"], r.get("cliSessionId"))), None)
    path = transcript(projects, (row or {}).get("cliSessionId") or ident)
    lines = []
    for d in read_tail(path) if path else []:
        text = human_text(d)
        if text:
            lines.append("THEM: " + short(text, 400))
            continue
        if d.get("type") == "assistant" and not d.get("isSidechain"):
            content = (d.get("message") or {}).get("content")
            said = " ".join(c.get("text", "") for c in content or [] if isinstance(c, dict) and c.get("type") == "text").strip()
            if said:
                lines.append("CLAUDE: " + short(said, 600))
    starts = [i for i, l in enumerate(lines) if l.startswith("THEM:")]
    kept = lines[starts[-turns]:] if len(starts) >= turns else lines
    title = (row or {}).get("title") or ident
    text = f"Thread: {title}\n\n" + "\n".join(kept) + "\n"
    while len(text.encode()) > max_bytes and len(kept) > 1:
        kept = kept[1:]
        text = f"Thread: {title}\n\n" + "\n".join(kept) + "\n"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as h:
        h.write(text)
    return out


def follow(home, hours=2):
    """The Claude thread in use: the newest one active in the last `hours`, with Claude's last words and what it needs."""
    sessions = os.path.join(home, "Library/Application Support/Claude/claude-code-sessions")
    projects = os.path.join(home, ".claude/projects")
    since = (time.time() - hours * 3600) * 1000
    rows = [r for r in load_index(sessions) if r["_kind"] != "scheduled" and not r["_archived"] and (r.get("lastActivityAt") or 0) >= since]
    if not rows:
        return {}
    r = max(rows, key=lambda x: x.get("lastActivityAt") or 0)
    pts = r.get("postTurnSummary") or {}
    reply = ""
    path = transcript(projects, r.get("cliSessionId"))
    for d in reversed(read_tail(path, 2 * 2**20) if path else []):
        if d.get("type") != "assistant" or d.get("isSidechain"):
            continue
        content = (d.get("message") or {}).get("content")
        text = " ".join(c.get("text", "") for c in content or [] if isinstance(c, dict) and c.get("type") == "text").strip()
        if text:
            reply = short(text, 600)
            break
    status = pts.get("status_category") or ""
    waiting = int(time.time() - (r.get("lastActivityAt") or 0) / 1000) if status in ("blocked", "review_ready") else 0
    return {"id": r["sessionId"], "title": short(r.get("title"), 80), "status": status,
            "needs": short(pts.get("needs_action"), 200), "reply": reply, "waiting_s": max(0, waiting)}


def find_named(home, name):
    """The most recently active open thread whose title contains name (any case), or None."""
    sessions = os.path.join(home, "Library/Application Support/Claude/claude-code-sessions")
    n = name.lower().strip()
    rows = [r for r in load_index(sessions) if r["_kind"] != "scheduled" and not r["_archived"] and n in (r.get("title") or "").lower()]
    return max(rows, key=lambda r: r.get("lastActivityAt") or 0) if rows else None


def main():
    ap = argparse.ArgumentParser(description="Gigi Assistant's thread sweep")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--home", default=os.path.expanduser("~"))
    ap.add_argument("--out")
    ap.add_argument("--usage", action="store_true", help="print the plan meter and how full recent threads are, as JSON")
    ap.add_argument("--tail", metavar="THREAD_ID", help="write a thread's last turns to --out, for a handoff note")
    ap.add_argument("--follow", action="store_true", help="the Claude thread in use, as JSON (empty when none in 2 hours)")
    ap.add_argument("--tail-named", metavar="NAME", help="the same for the newest open thread whose title contains NAME; prints the file and the title")
    a = ap.parse_args()
    home = os.path.abspath(a.home)
    if a.usage:
        print(json.dumps(usage(home), ensure_ascii=False))
        return
    if a.follow:
        print(json.dumps(follow(home), ensure_ascii=False))
        return
    if a.tail_named:
        row = find_named(home, a.tail_named)
        if row:
            out = a.out or os.path.join(home, "Library/Application Support/Gigi Helper/sweep/tail.txt")
            print(write_tail(home, row["sessionId"], out))
            print(row.get("title") or a.tail_named)
        return
    if a.tail:
        print(write_tail(home, a.tail, a.out or os.path.join(home, "Library/Application Support/Gigi Helper/sweep/tail.txt")))
        return
    out = a.out or os.path.join(home, "Library/Application Support/Gigi Helper/sweep")
    digest = fit(build(home, max(1, a.days)))
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "digest.json")
    with open(path, "w", encoding="utf-8") as h:
        h.write(dump(digest))
    print(path)


if __name__ == "__main__":
    main()
