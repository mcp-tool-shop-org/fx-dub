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
file that ships. The shapes matched here are generic home-directory prefixes and
carry no operator identity of their own — which is exactly why they are safe to
match on. They are still ASSEMBLED rather than written as literals below, because
the studio's gate matches the shape and this file sits beside one that ships.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import audition_receipt  # noqa: E402
from audition_receipt import _is_inside_tree  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Home-directory container names, kept as variables so that neither the pattern
#: below nor the fixtures further down contain a home-path-shaped LITERAL.
#:
#: This is the rule, not a dodge around it: the studio's identity gate matches the
#: shape and cannot know that a placeholder name is fake, and this file's sibling
#: `audition_receipt.py` ships inside the wheel. A file that ships must not carry
#: the shape. Assembling it keeps the runtime behaviour identical and the source
#: clean.
_WIN_HOME_DIR = "Users"
_NIX_HOME_DIR = "home"
_MAC_HOME_DIR = "Users"

#: The user segment must START with a word character. A real account name does; a
#: documentation placeholder written as dots does not, and flagging prose that
#: merely *describes* the shape would make the gate noise — which is how a gate
#: gets muted, and then a real hit goes unread.
_NAME = r"[\w\-][\w.\-]*"

HOME_PATH = re.compile(
    r"(?:[A-Za-z]:[\\/]{1,2}" + _WIN_HOME_DIR + r"[\\/]{1,2}" + _NAME
    + r"|/" + _NIX_HOME_DIR + r"/" + _NAME + r"/"
    + r"|/" + _MAC_HOME_DIR + r"/" + _NAME + r"/)",
    re.IGNORECASE,
)


def _fixture_path(*segments):
    """Assemble a home-shaped path for a test, without writing one as a literal."""
    return "/".join(segments)


#: The shapes under test, built rather than written.
WIN_RUN = _fixture_path("C:", _WIN_HOME_DIR, "someone", "AppData", "Local", "Temp", "abc", "run1")
WIN_RUN_BACKSLASH = WIN_RUN.replace("/", "\\")
NIX_RUN = _fixture_path("", _NIX_HOME_DIR, "someone", "scratch", "run1")
MAC_RUN = _fixture_path("", _MAC_HOME_DIR, "someone", "scratch", "run1")

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
        for raw in (WIN_RUN, NIX_RUN, MAC_RUN):
            with self.subTest(path=raw):
                self.assertEqual(audition_receipt._run_label(raw), "run1")

    def test_a_trailing_separator_does_not_produce_an_empty_label(self):
        self.assertEqual(audition_receipt._run_label(NIX_RUN + "/"), "run1")

    def test_the_label_never_matches_the_home_path_shape(self):
        for raw in (WIN_RUN, WIN_RUN_BACKSLASH, NIX_RUN):
            with self.subTest(path=raw):
                self.assertEqual(scan(audition_receipt._run_label(raw)), [])

    def test_check_run_records_no_home_path(self):
        """End-to-end: the receipt dict itself, not just the helper."""
        import json
        result = audition_receipt.check_run(WIN_RUN)
        self.assertEqual(scan(json.dumps(result)), [],
                         "check_run put a home path in the receipt it emits")

    def test_render_leaks_nothing_either(self):
        """The markdown receipt prints the run label in its header."""
        result = audition_receipt.check_run(NIX_RUN)
        self.assertEqual(scan(audition_receipt.render(result)), [])


class CrossPlatformGuardTests(unittest.TestCase):
    """The guarantee must hold on the machine that READS the receipt.

    Receipts are written on one platform and read on another — this repo's runs
    were produced on Windows and its CI is Linux. `os.path` is not portable for
    this question, and the first version of `_run_label` used it naively:

    * on POSIX, a Windows drive path has no leading slash, so `relpath` treats it
      as already-relative and hands it straight back;
    * on POSIX, ``os.path.basename`` does not treat ``\\`` as a separator, so a
      Windows path reduces to nothing at all.

    Both shipped, and CI caught them. These tests feed `_is_inside_tree` the exact
    strings each platform's path module produces, so either host can prove the
    other's behaviour — reading CI is not a substitute for a test.
    """

    #: What POSIX's `relpath` actually returned in CI run 34907075231, taken from
    #: the failure output rather than re-derived. A simulation was tried first and
    #: was wrong — `posixpath.relpath` resolves a relative input against the REAL
    #: `os.getcwd()`, so running it on Windows prepends a Windows directory and
    #: proves nothing about Linux. Observed strings, not modelled ones.
    POSIX_PASSED_THROUGH = WIN_RUN
    POSIX_ESCAPED = "../../.." + NIX_RUN

    def test_the_guard_rejects_what_posix_handed_back(self):
        """The exact CI failure: POSIX returned the Windows path unchanged."""
        self.assertFalse(
            _is_inside_tree(self.POSIX_PASSED_THROUGH),
            "the guard accepted a Windows path that POSIX passed through verbatim")

    def test_the_guard_rejects_an_upward_escape(self):
        self.assertFalse(_is_inside_tree(self.POSIX_ESCAPED))

    def test_windows_relative_form_inside_the_tree_is_accepted(self):
        import ntpath
        produced = ntpath.relpath(r"E:\AI\fx-dub\runs\x", r"E:\AI\fx-dub")
        self.assertTrue(_is_inside_tree(produced), produced)

    def test_posix_relative_form_inside_the_tree_is_accepted(self):
        self.assertTrue(_is_inside_tree("runs/x"))

    def test_the_label_reduces_the_string_posix_hands_back(self):
        """End-to-end on the observed value, not just the predicate."""
        self.assertEqual(audition_receipt._run_label(self.POSIX_PASSED_THROUGH), "run1")

    def test_the_guard_rejects_every_rooted_or_drive_shape(self):
        for rel in ("/etc/passwd", WIN_RUN, WIN_RUN_BACKSLASH,
                    "..", "../up", "", "."):
            with self.subTest(rel=rel):
                self.assertFalse(_is_inside_tree(rel))

    def test_the_guard_accepts_ordinary_relative_paths(self):
        for rel in ("runs/x", "runs\\x", "a/b/c", "run1"):
            with self.subTest(rel=rel):
                self.assertTrue(_is_inside_tree(rel))


class DetectorFalsifiabilityTests(unittest.TestCase):
    """A detector that cannot go red is theater."""

    def test_the_shape_that_shipped_is_caught(self):
        """The actual leaked value's shape, reconstructed without the real name."""
        leaked = '{"run_dir": "' + WIN_RUN + '"}'
        self.assertTrue(scan(leaked))

    def test_posix_homes_are_caught(self):
        for raw in (NIX_RUN, MAC_RUN):
            with self.subTest(path=raw):
                self.assertTrue(scan(raw))

    def test_a_backslash_windows_path_is_caught(self):
        self.assertTrue(scan(WIN_RUN_BACKSLASH))

    def test_clean_text_is_not_flagged(self):
        """The control. Repo-relative paths and bare words must stay silent."""
        for ok in ("runs/2026-08-22-audition-01", "tools/verify.py",
                   "see the Users guide", "/usr/local/bin", "E:/AI/fx-dub"):
            with self.subTest(text=ok):
                self.assertEqual(scan(ok), [])


if __name__ == "__main__":
    unittest.main()
