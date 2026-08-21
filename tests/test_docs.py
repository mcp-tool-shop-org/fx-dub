"""Contract presence — the documents an agent session is required to be able to find.

AGENTS.md names a reading order and the repo's operating rules depend on those
files existing where they are named. Two of the rules are mechanically
checkable and are checked here:

* AGENTS.md must point at the project database (``kb/fxdub.db``), because that
  is step 2 of the reading order.
* Every brief must name its paste target on line 1 (operating rule 3) — an
  unlabelled brief lands in the wrong session, which has already happened.
"""

from __future__ import annotations

import glob
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AGENTS_MD = os.path.join(REPO_ROOT, "AGENTS.md")
KB_README = os.path.join(REPO_ROOT, "kb", "README.md")
DISPATCH = os.path.join(REPO_ROOT, "docs", "design", "2026-08-21-fxdub-v1.dispatch.md")
DISPATCH_VERIFY = os.path.join(REPO_ROOT, "docs", "design", "2026-08-21-fxdub-v1.dispatch.verify.md")
BRIEFS_GLOB = os.path.join(REPO_ROOT, "docs", "briefs", "*.md")

PASTE_TARGET_MARKER = "PASTE TARGET"


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


class ContractFilePresenceTests(unittest.TestCase):
    def test_required_documents_exist(self):
        for label, path in (
            ("AGENTS.md", AGENTS_MD),
            ("kb/README.md", KB_README),
            ("v1 dispatch", DISPATCH),
            ("v1 dispatch verification", DISPATCH_VERIFY),
        ):
            with self.subTest(document=label):
                self.assertTrue(os.path.isfile(path), path)
                self.assertGreater(os.path.getsize(path), 0, "{0} is empty".format(path))

    def test_agents_md_points_at_the_database(self):
        self.assertIn(
            "kb/fxdub.db", _read(AGENTS_MD),
            "AGENTS.md no longer names kb/fxdub.db — step 2 of the reading order is broken")

    def test_agents_md_points_at_the_dispatch_and_the_graph_archive(self):
        text = _read(AGENTS_MD)
        for reference in (
            "docs/design/2026-08-21-fxdub-v1.dispatch.md",
            "workflows/comfy-cloud/as-built/README.md",
        ):
            with self.subTest(reference=reference):
                self.assertIn(reference, text)


class BriefContractTests(unittest.TestCase):
    def setUp(self):
        self.briefs = sorted(glob.glob(BRIEFS_GLOB))

    def test_briefs_exist(self):
        self.assertTrue(self.briefs, "no briefs found at docs/briefs/*.md")

    def test_every_brief_names_its_paste_target_on_line_one(self):
        for path in self.briefs:
            with self.subTest(brief=os.path.basename(path)):
                with open(path, "r", encoding="utf-8") as fh:
                    first_line = fh.readline()
                self.assertIn(
                    PASTE_TARGET_MARKER, first_line,
                    "line 1 of {0} does not name a paste target: {1!r}".format(
                        os.path.basename(path), first_line.strip()[:120]))


if __name__ == "__main__":
    unittest.main()
