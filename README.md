# gitstale

A single-file, stdlib-only Python 3 CLI that lists the local branches of a git repo with last commit date, author and age in days. It flags stale branches and branches already merged into a base branch.

## Why

Old branches pile up. `git branch` doesn't show how old they are or which ones are safe to delete. gitstale shows that at a glance, with no dependencies beyond Python 3 and git.

## Install

No install step. Copy `gitstale.py` anywhere and run it with `python3 gitstale.py`. Requires Python 3.8+ and git on PATH.

## Usage

```
python3 gitstale.py [path] [--days N] [--base BRANCH] [--json] [--merged-only] [--sort {name,age}]
```

- `path`: repository path (default `.`)
- `--days N`: branches older than N days are flagged `stale` (default 30)
- `--base BRANCH`: branch used for the merged check (default: `main`, else `master`, else the current HEAD branch)
- `--json`: machine-readable output
- `--merged-only`: only show branches merged into the base
- `--sort age`: oldest first (default sorts by name)

The base branch itself is marked `base` and is never flagged stale or merged.

Exit codes: 0 normally, 2 if the path is not a git repository.

## Example output

```
$ python3 gitstale.py --sort age
BRANCH       LAST COMMIT  AUTHOR  AGE    STATUS
main         2020-01-01   Tester  2113d  base
old-merged   2020-01-01   Tester  2113d  stale, merged
old-feature  2020-02-01   Tester  2082d  stale
fresh        2026-10-15   Tester  0d     -
```

JSON (`--json`) prints `{"base": ..., "days": ..., "branches": [{"branch", "last_commit", "author", "age_days", "stale", "merged", "base"}, ...]}`.

## Tests

```
python3 -m unittest discover tests
```

Tests build temporary git repos and fake old dates with `GIT_AUTHOR_DATE` / `GIT_COMMITTER_DATE`.

## License

MIT
