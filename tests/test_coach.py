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


class LinkTest(unittest.TestCase):
    def test_handoff_link(self):
        h = Home()
        k = h.kit(setup=True)
        link = coach.handoff_link(k, os.path.join(k, "handoffs/2026-11-21-pricing-page.md"))
        self.assertTrue(link.startswith("claude://code/new?q="))
        self.assertIn("2026-11-21-pricing-page.md", unquote(link))
        self.assertIn("folder=" + k, unquote(link))
        self.assertLess(len(link), 600)


if __name__ == "__main__":
    unittest.main()
