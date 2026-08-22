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
BRIEFS_DIR = os.path.join(REPO_ROOT, "docs", "briefs")
# Two kinds of document live here and they have OPPOSITE contracts.
# A *-brief.md is outbound: the Director pastes it into the in-app agent thread by hand,
# so line 1 must name its paste target (an unlabelled paste has already landed in the
# wrong session once — see AGENTS.md rule 3).
# A *-verification.md is advisor-side: our measured record of what the agent's reply
# actually turned out to be. It must NEVER carry a paste target, because it must never
# be pasted anywhere.
# A *-reply.md is INBOUND: the in-app agent's own words, preserved as testimony.
# It must never carry a paste target either -- relaying an agent's reply back to it is
# meaningless -- and, because a reply can be WRONG and has been, it must be readable
# as testimony rather than as instruction. Round 11's reply recommended dropping voice
# cloning entirely; cloning works, and a future session finding that file unmarked
# would delete a working route.
BRIEFS_GLOB = os.path.join(BRIEFS_DIR, "*-brief.md")
RECORDS_GLOB = os.path.join(BRIEFS_DIR, "*-verification.md")
REPLIES_GLOB = os.path.join(BRIEFS_DIR, "*-reply.md")
ALL_BRIEF_DOCS_GLOB = os.path.join(BRIEFS_DIR, "*.md")

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
        """Steps 3 and 4 of the reading order must still be reachable from AGENTS.md.

        Matched on the distinctive path fragment rather than a whole markdown
        link, so re-formatting a link does not fail this — only dropping the
        reference does.
        """
        text = _read(AGENTS_MD)
        for reference in (
            "2026-08-21-fxdub-v1.dispatch.md",
            "workflows/comfy-cloud/as-built",
        ):
            with self.subTest(reference=reference):
                self.assertIn(reference, text)


class BriefContractTests(unittest.TestCase):
    def setUp(self):
        self.briefs = sorted(glob.glob(BRIEFS_GLOB))

    def test_briefs_exist(self):
        self.assertTrue(self.briefs, "no briefs found at docs/briefs/*-brief.md")

    def test_every_doc_in_briefs_declares_which_kind_it_is(self):
        """No unclassified file may sit in docs/briefs/ escaping both contracts.

        Without this, the paste-target gate is trivially bypassed by naming a
        file anything else — which is exactly how a *-verification.md landed
        here unchecked and turned the suite red instead of the document.
        """
        classified = (set(glob.glob(BRIEFS_GLOB))
                      | set(glob.glob(RECORDS_GLOB))
                      | set(glob.glob(REPLIES_GLOB)))
        for path in sorted(glob.glob(ALL_BRIEF_DOCS_GLOB)):
            with self.subTest(doc=os.path.basename(path)):
                self.assertIn(
                    path, classified,
                    "{0} is not a *-brief.md, *-verification.md or *-reply.md, so "
                    "no contract applies to it. Name it for what it is.".format(
                        os.path.basename(path)))

    def test_agent_replies_never_name_a_paste_target(self):
        """An inbound reply is testimony, not something to relay.

        Pasting an agent's own reply back into its thread is meaningless, and a
        paste-target header would invite exactly that.
        """
        for path in sorted(glob.glob(REPLIES_GLOB)):
            with self.subTest(doc=os.path.basename(path)):
                head = _read(path).lstrip().splitlines()[:3]
                self.assertNotIn(
                    PASTE_TARGET_MARKER, "\n".join(head),
                    "{0} is an agent reply and must not name a paste target.".format(
                        os.path.basename(path)))

    def test_every_agent_reply_is_paired_with_a_verification(self):
        """A reply archived without our measured account of it is a trap.

        Round 11's reply stated a false impossibility and recommended dropping a
        working capability. Unpaired, it reads as fact. The verification record
        is what makes it readable as testimony.
        """
        for path in sorted(glob.glob(REPLIES_GLOB)):
            with self.subTest(doc=os.path.basename(path)):
                expected = path.replace("-reply.md", "-verification.md")
                self.assertTrue(
                    os.path.exists(expected),
                    "{0} has no matching -verification.md. An agent reply must "
                    "never be archived without our measured account of it.".format(
                        os.path.basename(path)))

    def test_verification_records_never_name_a_paste_target(self):
        """The inverse contract, so the distinction is enforced both ways.

        A verification record is our measured account of what an agent reply
        turned out to be — several of them say the agent was right and we were
        wrong. Pasting one into the agent thread would feed our own reasoning
        back to the party we are checking. It must never look pasteable.
        """
        records = sorted(glob.glob(RECORDS_GLOB))
        self.assertTrue(records, "no verification records found — this gate is vacuous")
        for path in records:
            with self.subTest(record=os.path.basename(path)):
                with open(path, "r", encoding="utf-8") as fh:
                    head = fh.read(400)
                self.assertNotIn(
                    PASTE_TARGET_MARKER, head,
                    "{0} names a paste target — verification records are "
                    "advisor-side and must never be pasted.".format(
                        os.path.basename(path)))

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
