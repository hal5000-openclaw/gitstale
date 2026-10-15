#!/usr/bin/env python3
"""gitstale: list local git branches with age, flag stale and merged ones."""
import argparse
import json
import subprocess
import sys
import time

SEP = "\x1f"


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def is_repo(repo):
    try:
        r = git(repo, "rev-parse", "--git-dir")
    except OSError:
        return False
    return r.returncode == 0


def pick_base(repo, branches, explicit=None):
    if explicit:
        return explicit
    for name in ("main", "master"):
        if name in branches:
            return name
    r = git(repo, "symbolic-ref", "--short", "-q", "HEAD")
    head = r.stdout.strip()
    return head or None


def collect(repo, days=30, base=None, now=None):
    now = time.time() if now is None else now
    fmt = SEP.join(["%(refname:short)", "%(committerdate:unix)", "%(authorname)", "%(objectname:short)"])
    r = git(repo, "for-each-ref", "--format=" + fmt, "refs/heads")
    rows = []
    for line in r.stdout.splitlines():
        name, ts, author, sha = line.split(SEP)
        rows.append((name, int(ts), author, sha))
    names = [x[0] for x in rows]
    base = pick_base(repo, names, base)
    merged = set()
    if base:
        m = git(repo, "for-each-ref", "--merged=" + base, "--format=%(refname:short)", "refs/heads")
        if m.returncode == 0:
            merged = set(m.stdout.split())
    out = []
    for name, ts, author, sha in rows:
        age = max(0, int((now - ts) // 86400))
        is_base = name == base
        out.append({
            "branch": name,
            "last_commit": time.strftime("%Y-%m-%d", time.gmtime(ts)),
            "author": author,
            "age_days": age,
            "stale": age > days and not is_base,
            "merged": name in merged and not is_base,
            "base": is_base,
        })
    return out, base


def render(items):
    if not items:
        return "No branches found."
    headers = ["BRANCH", "LAST COMMIT", "AUTHOR", "AGE", "STATUS"]
    table = [headers]
    for i in items:
        flags = [f for f, on in (("base", i["base"]), ("stale", i["stale"]), ("merged", i["merged"])) if on]
        table.append([i["branch"], i["last_commit"], i["author"], f"{i['age_days']}d", ", ".join(flags) or "-"])
    w = [max(len(r[c]) for r in table) for c in range(5)]
    return "\n".join("  ".join(v.ljust(w[c]) for c, v in enumerate(r)).rstrip() for r in table)


def main(argv=None):
    p = argparse.ArgumentParser(description="List local git branches and flag stale/merged ones.")
    p.add_argument("path", nargs="?", default=".", help="repository path (default .)")
    p.add_argument("--days", type=int, default=30, help="stale threshold in days (default 30)")
    p.add_argument("--base", help="base branch for merged check (default main/master/HEAD)")
    p.add_argument("--json", action="store_true", help="JSON output")
    p.add_argument("--merged-only", action="store_true", help="only show merged branches")
    p.add_argument("--sort", choices=["name", "age"], default="name", help="sort order (age = oldest first)")
    a = p.parse_args(argv)

    if not is_repo(a.path):
        print(f"gitstale: not a git repository: {a.path}", file=sys.stderr)
        return 2
    items, base = collect(a.path, a.days, a.base)
    if a.merged_only:
        items = [i for i in items if i["merged"]]
    if a.sort == "age":
        items.sort(key=lambda i: (-i["age_days"], i["branch"]))
    else:
        items.sort(key=lambda i: i["branch"])
    if a.json:
        print(json.dumps({"base": base, "days": a.days, "branches": items}, indent=2))
    else:
        print(render(items))
    return 0


if __name__ == "__main__":
    sys.exit(main())
