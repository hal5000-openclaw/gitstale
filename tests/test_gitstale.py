import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import gitstale  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def run(repo, *args, date=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="Tester", GIT_AUTHOR_EMAIL="t@example.com",
               GIT_COMMITTER_NAME="Tester", GIT_COMMITTER_EMAIL="t@example.com")
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = date
    subprocess.run(["git", "-C", repo, *args], env=env, check=True, capture_output=True)


def commit(repo, name, date):
    with open(os.path.join(repo, name), "w") as f:
        f.write(name)
    run(repo, "add", name)
    run(repo, "commit", "-m", name, date=date)


def cli(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = gitstale.main(list(args))
    return code, out.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name
        run(self.repo, "init", "-b", "main")
        commit(self.repo, "a", "2020-01-01T12:00:00Z")
        # old, unmerged branch
        run(self.repo, "checkout", "-b", "old-feature")
        commit(self.repo, "b", "2020-02-01T12:00:00Z")
        # old, merged branch (points at main's commit)
        run(self.repo, "checkout", "main")
        run(self.repo, "branch", "old-merged")
        # fresh branch
        run(self.repo, "checkout", "-b", "fresh")
        commit(self.repo, "c", None)
        run(self.repo, "checkout", "main")

    def data(self, *args):
        code, out = cli(self.repo, "--json", *args)
        self.assertEqual(code, 0)
        d = json.loads(out)
        return d, {b["branch"]: b for b in d["branches"]}


class Tests(Base):
    def test_stale(self):
        _, b = self.data()
        self.assertTrue(b["old-feature"]["stale"])
        self.assertFalse(b["fresh"]["stale"])
        self.assertFalse(b["main"]["stale"])
        self.assertEqual(b["old-feature"]["author"], "Tester")
        self.assertEqual(b["old-feature"]["last_commit"], "2020-02-01")

    def test_days_threshold(self):
        _, b = self.data("--days", "100000")
        self.assertFalse(b["old-feature"]["stale"])

    def test_merged(self):
        d, b = self.data()
        self.assertEqual(d["base"], "main")
        self.assertTrue(b["old-merged"]["merged"])
        self.assertFalse(b["old-feature"]["merged"])
        self.assertTrue(b["main"]["base"])

    def test_merged_only(self):
        _, b = self.data("--merged-only")
        self.assertEqual(list(b), ["old-merged"])

    def test_sort_age(self):
        d, _ = self.data("--sort", "age")
        names = [x["branch"] for x in d["branches"]]
        self.assertEqual(names[0], "main")
        self.assertEqual(names[-1], "fresh")

    def test_text_output(self):
        code, out = cli(self.repo)
        self.assertEqual(code, 0)
        self.assertIn("old-feature", out)
        self.assertIn("stale", out)
        self.assertIn("merged", out)

    def test_not_a_repo(self):
        with tempfile.TemporaryDirectory() as d:
            code, _ = cli(d)
            self.assertEqual(code, 2)
            r = subprocess.run([sys.executable, os.path.join(ROOT, "gitstale.py"), d],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertIn("not a git repository", r.stderr)


if __name__ == "__main__":
    unittest.main()
