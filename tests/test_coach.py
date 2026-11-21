"""Checks for gigi/scripts/coach.py: python3 -W error -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.parse import unquote

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "..", "gigi", "scripts")
sys.path.insert(0, SCRIPTS)
import coach  # noqa: E402

KIT_REL = "Documents/Claude Code/agentic-business-os-pkg"


class Home:
    """A throwaway home folder."""

    def __init__(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = self.dir.name

    def write(self, rel, text):
        p = os.path.join(self.path, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as h:
            h.write(text)
        return p

    def kit(self, rel=KIT_REL, setup=False):
        self.write(f"{rel}/CLAUDE.md", "# kit")
        os.makedirs(os.path.join(self.path, rel, ".claude/skills/setup"), exist_ok=True)
        if setup:
            self.write(f"{rel}/context/me.md", "me")
            self.write(f"{rel}/context/current-priorities.md", "p")
        return os.path.join(self.path, rel)

    def meter(self, fh, sd, age_s=60):
        t = int((time.time() - age_s) * 1000)
        self.write("Library/Application Support/Claude/plan-usage-history.json",
                   json.dumps({"samples": [{"t": t, "org": "o", "u": {"fh": fh, "sd": sd}}]}))

    def run(self, *args, stdin=""):
        env = dict(os.environ, HOME=self.path)
        return subprocess.run([sys.executable, os.path.join(SCRIPTS, "coach.py"), *args], input=stdin,
                              capture_output=True, text=True, env=env, timeout=60)


def transcript(path, tokens, pad_bytes=0):
    """A transcript whose last assistant reply carried `tokens` of context."""
    with open(path, "w") as h:
        if pad_bytes:
            h.truncate(pad_bytes)
            h.seek(pad_bytes)
            h.write("\n")
        h.write(json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n")
        h.write(json.dumps({"type": "assistant", "message": {"usage": {
            "input_tokens": 5, "cache_read_input_tokens": tokens - 1005, "cache_creation_input_tokens": 1000}}}) + "\n")


class KitTest(unittest.TestCase):
    def test_kit_in_cwd(self):
        h = Home()
        k = h.kit("work/mykit")
        self.assertEqual(coach.find_kit(k, h.path), k)

    def test_kit_fallback(self):
        h = Home()
        k = h.kit()
        self.assertEqual(coach.find_kit(h.path, h.path), k)

    def test_kit_missing(self):
        h = Home()
        self.assertIsNone(coach.find_kit(h.path, h.path))
        rows = {r["name"]: r for r in coach.checkup(h.path, h.path, quick=True)}
        kit = [r for n, r in rows.items() if "kit" in n.lower()][0]
        self.assertFalse(kit["ok"])
        self.assertIn("Documents/Claude Code/agentic-business-os-pkg", kit["fix"])

    def test_setup_done(self):
        h = Home()
        k = h.kit(setup=True)
        self.assertTrue(coach.setup_done(k))
        h.write(f"{KIT_REL}/context/me.md", "")
        self.assertFalse(coach.setup_done(k))


class MeterTest(unittest.TestCase):
    def test_meter(self):
        h = Home()
        h.meter(82, 40, age_s=60)
        m = coach.meter(h.path)
        self.assertEqual((m["fh"], m["sd"], m["age_min"]), (82, 40, 1))

    def test_no_meter(self):
        h = Home()
        self.assertIsNone(coach.meter(h.path))
        r = h.run("usage")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIsNone(json.loads(r.stdout)["meter"])

    def test_window(self):
        self.assertEqual(coach.window(150_000), 200_000)
        self.assertEqual(coach.window(250_000), 1_000_000)


class ThreadsTest(unittest.TestCase):
    def test_threads_empty(self):
        h = Home()
        r = h.run("threads")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(json.loads(r.stdout)["empty"])
        self.assertFalse(os.path.exists(os.path.join(h.path, "Library/Application Support/Gigi Helper")))


class LinkTest(unittest.TestCase):
    def test_handoff_link(self):
        h = Home()
        k = h.kit(setup=True)
        link = coach.handoff_link(k, os.path.join(k, "handoffs/2026-11-21-pricing-page.md"))
        self.assertTrue(link.startswith("claude://code/new?q="))
        self.assertIn("2026-11-21-pricing-page.md", unquote(link))
        self.assertIn("folder=" + k, unquote(link))
        self.assertLess(len(link), 600)

    def test_handoff_link_says_if_opened(self):
        h = Home()
        k = h.kit(setup=True)
        note = h.write(f"{KIT_REL}/handoffs/2026-11-21-x.md", "note")
        env = dict(os.environ, HOME=h.path, GIGI_NO_OPEN="1")
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "coach.py"), "handoff-link", note], capture_output=True, text=True, env=env, cwd=k)
        lines = r.stdout.strip().splitlines()
        self.assertTrue(lines[0].startswith("claude://code/new?q="))
        self.assertEqual(lines[1], "opened: no")


def hook(h, sub, **payload):
    r = h.run(sub, stdin=json.dumps(payload))
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else None


class SessionStartTest(unittest.TestCase):
    def test_session_start_high(self):
        h = Home()
        k = h.kit(setup=True)
        h.meter(85, 40, age_s=300)
        out = hook(h, "session-start", cwd=k, session_id="s1")
        self.assertIn("85%", out["systemMessage"])
        self.assertIn("5-hour", out["systemMessage"])
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "SessionStart")
        h.meter(50, 81)
        self.assertIn("week", hook(h, "session-start", cwd=k, session_id="s1")["systemMessage"])

    def test_session_start_quiet(self):
        h = Home()
        k = h.kit(setup=True)
        h.meter(70, 40)
        self.assertIsNone(hook(h, "session-start", cwd=k, session_id="s1"))

    def test_session_start_stale(self):
        h = Home()
        k = h.kit(setup=True)
        h.meter(85, 85, age_s=7 * 3600)
        self.assertIsNone(hook(h, "session-start", cwd=k, session_id="s1"))

    def test_session_start_setup(self):
        h = Home()
        k = h.kit(setup=False)
        out = hook(h, "session-start", cwd=k, session_id="s1")
        self.assertIn("/setup", out["hookSpecificOutput"]["additionalContext"])
        self.assertNotIn("systemMessage", out)


class ThreadCheckTest(unittest.TestCase):
    def test_thread_check_160k(self):
        h = Home()
        t = os.path.join(h.path, "t.jsonl")
        transcript(t, 165_000)
        out = hook(h, "thread-check", session_id="a", transcript_path=t)
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertIn("/gigi:fresh-start", ctx)
        self.assertIn("165K", ctx)
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")

    def test_thread_check_once(self):
        h = Home()
        t = os.path.join(h.path, "t.jsonl")
        transcript(t, 165_000)
        self.assertIsNotNone(hook(h, "thread-check", session_id="a", transcript_path=t))
        self.assertIsNone(hook(h, "thread-check", session_id="a", transcript_path=t))
        transcript(t, 182_000)
        self.assertIsNotNone(hook(h, "thread-check", session_id="a", transcript_path=t))
        self.assertIsNone(hook(h, "thread-check", session_id="a", transcript_path=t))
        transcript(t, 820_000)
        self.assertIn("820K", hook(h, "thread-check", session_id="a", transcript_path=t)["hookSpecificOutput"]["additionalContext"])

    def test_thread_check_quiet(self):
        h = Home()
        t = os.path.join(h.path, "t.jsonl")
        transcript(t, 100_000)
        self.assertIsNone(hook(h, "thread-check", session_id="a", transcript_path=t))
        transcript(t, 300_000)
        self.assertIsNone(hook(h, "thread-check", session_id="a", transcript_path=t))

    def test_thread_check_missing(self):
        h = Home()
        self.assertIsNone(hook(h, "thread-check", session_id="a", transcript_path=os.path.join(h.path, "nope.jsonl")))
        for stdin in ["", "not json", "[]"]:
            r = h.run("thread-check", stdin=stdin)
            self.assertEqual((r.returncode, r.stdout), (0, ""), stdin)

    def test_problem_words_point_at_the_guide(self):
        h = Home()
        out = hook(h, "thread-check", session_id="p", prompt="it keeps saying Overloaded, what do I do")
        self.assertIn("gigi:stuck", out["hookSpecificOutput"]["additionalContext"])
        self.assertIsNone(hook(h, "thread-check", session_id="p", prompt="still Overloaded"))
        for ok in ["hello", "write my newsletter about the error of our ways"]:
            self.assertIsNone(hook(h, "thread-check", session_id="q", prompt=ok), ok)
        for bad in ["zsh: command not found: claude", "API Error: 500", "Prompt is too long", "it says I'm not logged in", "I'm stuck"]:
            self.assertIsNotNone(hook(h, "thread-check", session_id="r" + bad, prompt=bad), bad)

    def test_thread_check_big_is_fast(self):
        h = Home()
        t = os.path.join(h.path, "big.jsonl")
        transcript(t, 170_000, pad_bytes=300 * 2**20)
        started = time.time()
        sys.path.insert(0, SCRIPTS)
        self.assertEqual(coach.thread_tokens(t), 170_000)
        self.assertLess(time.time() - started, 0.2)


if __name__ == "__main__":
    unittest.main()
