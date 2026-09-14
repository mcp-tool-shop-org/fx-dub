"""No git-tracked file may carry an operator's filesystem path.

**The repo is public, and a receipt is a published artifact.** An absolute path
from the machine that produced it names a home directory, a username, and often a
session UUID — none of which is a property of the thing being measured. A later
commit does not unpublish a tag, an sdist, or a Pages build.

Earned 2026-09-14, during the v1.2.0 treatment: the Phase-0 identity gate halted
on `runs/2026-08-22-audition-01/receipt.json`, which carried the full temp path of
the session that generated it. The published sdists were clean — `runs/` is not in
the package — but the public repo carried it from v1.0.0 onward and nothing in the
suite could see it.

Two gates, because fixing only the first would have re-leaked on the next run:

1. the tracked tree carries no home-shaped path;
2. `audition_receipt.check_run` does not *record* one, whatever it is handed.

**These patterns are SHAPES, not needles.** The studio's identity needles live off
-repo at `~/.grok/secrets/identity-needles.txt` and must never be copied into a
file that ships. `C:/Users/<name>` is a generic Windows home prefix and carries no
operator identity on its own — which is exactly why it is safe to match on here.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import audition_receipt  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Home-directory prefixes on the three platforms this package supports, each
#: requiring a following path segment so a bare mention of the word cannot fire.
HOME_PATH = re.compile(
    r"(?:[A-Za-z]:[\\/]{1,2}Users[\\/]{1,2}[\w.\-]+"      # C:\Users\<name>
    r"|/home/[\w.\-]+/"                                    # /home/<name>/
    r"|/Users/[\w.\-]+/)",                                 # /Users/<name>/
    re.IGNORECASE,
)

#: This file necessarily contains the patterns it searches for, so it would match
#: itself. Excluded deliberately and named here rather than silently skipped.
SELF = os.path.basename(__file__)

#: Binary and media artifacts — the run evidence this repo commits on purpose.
BINARY_SUFFIXES = (".db", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".flac",
                   ".wav", ".mp4", ".mp3", ".pyc", ".whl", ".gz", ".zip", ".woff",
                   ".woff2", ".ttf", ".pdf")


def tracked_text_files():
    """Every git-tracked file that is plausibly text. Empty list fails the gate."""
    out = subprocess.run(["git", "-C", REPO_ROOT, "ls-files"],
                         capture_output=True, text=True, encoding="utf-8")
    paths = []
    for rel in out.stdout.splitlines():
        if not rel.strip() or rel.lower().endswith(BINARY_SUFFIXES):
            continue
        if os.path.basename(rel) == SELF:
            continue
        paths.append(rel)
    return paths


def scan(text):
    """Return the home-path shapes found, de-duplicated, order preserved."""
    seen, hits = set(), []
    for match in HOME_PATH.findall(text or ""):
        if match not in seen:
            seen.add(match)
            hits.append(match)
    return hits


class TrackedTreeTests(unittest.TestCase):
    def setUp(self):
        self.files = tracked_text_files()

    def test_the_gate_has_something_to_scan(self):
        """A gate that finds no files to check reads as a pass. Prove it has input."""
        self.assertGreater(len(self.files), 20,
                           "git ls-files returned almost nothing — the scan is vacuous")

    def test_no_tracked_file_carries_a_home_path(self):
        offenders = {}
        for rel in self.files:
            path = os.path.join(REPO_ROOT, rel)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                    hits = scan(handle.read())
            except (OSError, UnicodeDecodeError):
                continue
            if hits:
                # Report the FILE and the count, never the matched text — a test
                # failure message is itself output that gets pasted around.
                offenders[rel] = len(hits)
        self.assertEqual(
            {}, offenders,
            "operator filesystem paths in tracked files (file -> count): {0}. "
            "The repo is public. Scrub the file AND whatever wrote it.".format(offenders))


class ReceiptGeneratorTests(unittest.TestCase):
    """The root cause: a receipt recorded whatever absolute path it was handed."""

    def test_a_run_under_the_cwd_is_recorded_relatively(self):
        label = audition_receipt._run_label(os.path.join(os.getcwd(), "runs", "x"))
        self.assertEqual(label, "runs/x")

    def test_a_run_outside_the_cwd_keeps_only_its_name(self):
        for raw in ("C:/Users/someone/AppData/Local/Temp/abc/run1",
                    "/home/someone/scratch/run1",
                    "/Users/someone/scratch/run1"):
            with self.subTest(path=raw):
                self.assertEqual(audition_receipt._run_label(raw), "run1")

    def test_a_trailing_separator_does_not_produce_an_empty_label(self):
        self.assertEqual(audition_receipt._run_label("/home/someone/scratch/run1/"), "run1")

    def test_the_label_never_matches_the_home_path_shape(self):
        for raw in ("C:/Users/someone/AppData/Local/Temp/sess-uuid/scratchpad/run1",
                    "C:\\Users\\someone\\Temp\\run1",
                    "/home/someone/run1"):
            with self.subTest(path=raw):
                self.assertEqual(scan(audition_receipt._run_label(raw)), [])

    def test_check_run_records_no_home_path(self):
        """End-to-end: the receipt dict itself, not just the helper."""
        import json
        result = audition_receipt.check_run("C:/Users/someone/Temp/sess/run1")
        self.assertEqual(scan(json.dumps(result)), [],
                         "check_run put a home path in the receipt it emits")

    def test_render_leaks_nothing_either(self):
        """The markdown receipt prints the run label in its header."""
        result = audition_receipt.check_run("/home/someone/scratch/run1")
        self.assertEqual(scan(audition_receipt.render(result)), [])


class DetectorFalsifiabilityTests(unittest.TestCase):
    """A detector that cannot go red is theater."""

    def test_the_shape_that_shipped_is_caught(self):
        """The actual leaked value's shape, reconstructed without the real name."""
        leaked = '{"run_dir": "C:/Users/someone/AppData/Local/Temp/claude/a-uuid/scratchpad/run1"}'
        self.assertTrue(scan(leaked))

    def test_posix_homes_are_caught(self):
        for raw in ("/home/someone/thing", "/Users/someone/thing"):
            with self.subTest(path=raw):
                self.assertTrue(scan(raw))

    def test_a_backslash_windows_path_is_caught(self):
        self.assertTrue(scan(r"C:\Users\someone\thing"))

    def test_clean_text_is_not_flagged(self):
        """The control. Repo-relative paths and bare words must stay silent."""
        for ok in ("runs/2026-08-22-audition-01", "tools/verify.py",
                   "see the Users guide", "/usr/local/bin", "E:/AI/fx-dub"):
            with self.subTest(text=ok):
                self.assertEqual(scan(ok), [])


if __name__ == "__main__":
    unittest.main()
