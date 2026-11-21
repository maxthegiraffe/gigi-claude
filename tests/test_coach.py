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
        for bad in ["zsh: command not found: claude", "API Error: 500", "Prompt is too long", "Not logged in · Please run /login"]:
            self.assertIsNotNone(hook(h, "thread-check", session_id="r" + bad, prompt=bad), bad)

    def test_thread_check_big_is_fast(self):
        h = Home()
        t = os.path.join(h.path, "big.jsonl")
        transcript(t, 170_000, pad_bytes=300 * 2**20)
        started = time.time()
        sys.path.insert(0, SCRIPTS)
        self.assertEqual(coach.thread_tokens(t), 170_000)
        self.assertLess(time.time() - started, 0.2)


class ReviewFixTest(unittest.TestCase):
    """Fixes from the review of 2026-11-20."""

    def test_business_prompts_are_not_problems(self):
        h = Home()
        for ok in ["Write a promo for our $1,529 coaching package", "I'm overloaded this week, plan my Monday",
                   "This headline doesn't work, try three more", "My Facebook ads are not working, ideas?",
                   "I'm stuck on what to name my new product", "customers get logged out of Shopify", "call 415-529-0000",
                   "our 529 college plan", "I'm overloaded, I'm stuck at $10k a month"]:
            self.assertIsNone(hook(h, "thread-check", session_id="b" + ok, prompt=ok), ok)
        for bad in ["API Error: 529 {\"type\":\"overloaded_error\"}", "it says Overloaded error", "529 overloaded",
                    "Prompt is too long", "zsh: command not found: claude", "it says Please run /login", "API Error: 500"]:
            out = hook(h, "thread-check", session_id="e" + bad, prompt=bad)
            self.assertIn("gigi:stuck", out["hookSpecificOutput"]["additionalContext"], bad)
            self.assertIn("only if", out["hookSpecificOutput"]["additionalContext"].lower())

    def git_kit(self):
        h = Home()
        k = h.kit(setup=True)
        run = lambda *a: subprocess.run(["git", "-C", k, *a], capture_output=True, text=True, check=True)
        run("init", "-q")
        run("-c", "user.name=t", "-c", "user.email=t@t", "add", "-A")
        run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "save")
        return h, k

    def test_undo_keeps_a_copy(self):
        h, k = self.git_kit()
        h.write(f"{KIT_REL}/context/me.md", "my own edits")
        h.write(f"{KIT_REL}/new.md", "brand new")
        ch = json.loads(h.run("changes", stdin="").stdout if False else subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "coach.py"), "changes"], capture_output=True, text=True, cwd=k,
            env=dict(os.environ, HOME=h.path)).stdout)
        states = {c["path"]: c["state"] for c in ch["changed"]}
        self.assertEqual(states, {"context/me.md": "changed", "new.md": "new"})
        r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "coach.py"), "restore", "context/me.md", "new.md"],
                           capture_output=True, text=True, cwd=k, env=dict(os.environ, HOME=h.path))
        res = {x["path"]: x for x in json.loads(r.stdout)}
        self.assertTrue(res["context/me.md"]["restored"])
        self.assertEqual(open(os.path.join(k, "context/me.md")).read(), "me")
        self.assertEqual(open(res["context/me.md"]["backup"]).read(), "my own edits")
        self.assertFalse(res["new.md"]["restored"])
        self.assertTrue(os.path.exists(os.path.join(k, "new.md")))
        again = json.loads(subprocess.run([sys.executable, os.path.join(SCRIPTS, "coach.py"), "changes"], capture_output=True,
                                          text=True, cwd=k, env=dict(os.environ, HOME=h.path)).stdout)
        self.assertEqual([c["path"] for c in again["changed"]], ["new.md"])

    def test_hook_wrapper_is_quiet_without_python(self):
        r = subprocess.run(["/bin/sh", os.path.join(SCRIPTS, "run-hook"), "thread-check"], input="{}", capture_output=True,
                           text=True, env={"PATH": "/nonexistent", "HOME": tempfile.gettempdir()})
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
        h = Home()
        r = subprocess.run(["/bin/sh", os.path.join(SCRIPTS, "run-hook"), "thread-check"], input=json.dumps({"session_id": "w", "prompt": "Prompt is too long"}),
                           capture_output=True, text=True, env=dict(os.environ, HOME=h.path))
        self.assertIn("gigi:stuck", r.stdout)

    def test_off_a_mac(self):
        h = Home()
        names = [r["name"] for r in coach.checkup(h.path, h.path, quick=False, plat="win32")]
        self.assertNotIn("Claude app up to date", names)
        self.assertEqual(json.loads(h.run("usage").stdout)["platform"], sys.platform)

    def test_start_check_fresh_and_once(self):
        h = Home()
        k = h.kit(setup=True)
        h.meter(85, 40, age_s=2 * 3600)
        self.assertIsNone(hook(h, "session-start", cwd=k, session_id="s1"), "a 5-hour number 2 hours old is stale")
        h.meter(85, 40, age_s=10 * 60)
        self.assertIsNotNone(hook(h, "session-start", cwd=k, session_id="s1"))
        self.assertIsNone(hook(h, "session-start", cwd=k, session_id="s2"), "not again on resume or /clear")

    def test_said_file_under_four_sessions(self):
        h = Home()
        code = "import sys; sys.path.insert(0, sys.argv[1]); import coach\nfor i in range(50): coach.first_time(sys.argv[2], sys.argv[3] + str(i), 'k')"
        ps = [subprocess.Popen([sys.executable, "-c", code, SCRIPTS, h.path, f"s{n}-"], stderr=subprocess.PIPE, text=True) for n in range(4)]
        errs = [p.communicate()[1] for p in ps]
        self.assertEqual(errs, ["", "", "", ""])
        json.load(open(os.path.join(h.path, ".claude/gigi-plugin/said.json")))

    def test_small_app_updates_are_fine(self):
        self.assertTrue(coach.newer_or_same("6.28899.2", "6.28899.6"))
        self.assertFalse(coach.newer_or_same("6.28800.9", "6.28899.0"))


if __name__ == "__main__":
    unittest.main()
