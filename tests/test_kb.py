"""The knowledge database — kb/build_db.py must produce a queryable fxdub.db.

``kb/fxdub.db`` is future-you's memory (AGENTS.md reads it second, right after
AGENTS.md itself). It is a *build artifact*: the seed data in ``kb/build_db.py``
is the source of truth and the script drops-and-recreates the file, so these
tests run the real script in a subprocess and then interrogate the result.

The working tree is left exactly as found — the pre-existing ``kb/fxdub.db``
bytes are restored in :func:`tearDownModule`.
"""

from __future__ import annotations

import contextlib
import os
import sqlite3
import subprocess
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_SCRIPT = os.path.join(REPO_ROOT, "kb", "build_db.py")
DB_PATH = os.path.join(REPO_ROOT, "kb", "fxdub.db")

TABLES = (
    "nodes", "models", "runs", "graphs", "threads",
    "traps", "decisions", "next_actions", "meta",
)
VIEWS = ("v_open_actions", "v_publishable", "v_measured_costs")

#: Floor, not target — the seeds grow every session; the gate is that a session
#: cannot silently delete the ledger.
MIN_ROWS = {
    "nodes": 35, "models": 10, "runs": 5, "graphs": 6,
    "traps": 14, "next_actions": 6,
    # threads gains a row per dialog round, so this is a floor like the rest.
    "threads": 4,
}
#: Fixed-cardinality: decisions A-J is the closed architecture lock. Adding one
#: means the dispatch changed, which must be deliberate — so this stays exact.
EXACT_ROWS = {"decisions": 10}

NODE_STATUSES = {"present", "reported", "absent", "unknown"}
CLASSES = {"A", "B"}

_ORIGINAL_DB = None
_FIRST_COUNTS = None


def _build():
    """Run kb/build_db.py exactly the way AGENTS.md documents it."""
    return subprocess.run(
        [sys.executable, os.path.join("kb", "build_db.py")],
        cwd=REPO_ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _counts():
    # contextlib.closing, NOT `with sqlite3.connect(...)`: the connection's own
    # context manager commits the transaction but leaves the handle open, and on
    # Windows that open handle makes build_db.py's os.remove(DB) fail with
    # WinError 32 on the next rebuild.
    with contextlib.closing(_connect()) as conn:
        return {t: conn.execute("SELECT COUNT(*) FROM " + t).fetchone()[0] for t in TABLES}


def setUpModule():
    global _ORIGINAL_DB, _FIRST_COUNTS
    if not os.path.exists(BUILD_SCRIPT):
        raise unittest.SkipTest("kb/build_db.py is missing")
    if os.path.exists(DB_PATH):
        with open(DB_PATH, "rb") as fh:
            _ORIGINAL_DB = fh.read()

    result = _build()
    if result.returncode != 0:
        raise AssertionError(
            "kb/build_db.py exited {0}\nstdout:\n{1}\nstderr:\n{2}".format(
                result.returncode, result.stdout, result.stderr)
        )
    if not os.path.exists(DB_PATH):
        raise AssertionError("kb/build_db.py ran clean but produced no {0}".format(DB_PATH))
    _FIRST_COUNTS = _counts()


def tearDownModule():
    """Restore the committed database bytes — tests must not dirty the tree."""
    if _ORIGINAL_DB is not None:
        with open(DB_PATH, "wb") as fh:
            fh.write(_ORIGINAL_DB)
    elif os.path.exists(DB_PATH):
        os.remove(DB_PATH)


class KnowledgeDbSchemaTests(unittest.TestCase):
    def setUp(self):
        self.conn = _connect()
        self.addCleanup(self.conn.close)

    def _names(self, kind):
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type=?", (kind,)
        ).fetchall()
        return {r["name"] for r in rows}

    def test_tables_exist(self):
        present = self._names("table")
        for table in TABLES:
            with self.subTest(table=table):
                self.assertIn(table, present)

    def test_fts_table_exists(self):
        self.assertIn("fts", self._names("table"))

    def test_views_exist(self):
        present = self._names("view")
        for view in VIEWS:
            with self.subTest(view=view):
                self.assertIn(view, present)

    def test_views_are_queryable(self):
        for view in VIEWS:
            with self.subTest(view=view):
                rows = self.conn.execute("SELECT * FROM " + view).fetchall()
                self.assertGreater(len(rows), 0, "{0} returned no rows".format(view))

    def test_meta_carries_schema_version_and_build_date(self):
        meta = {r["key"]: r["value"] for r in self.conn.execute("SELECT key, value FROM meta")}
        self.assertIn("schema_version", meta)
        self.assertIn("built_at", meta)
        self.assertTrue(meta["schema_version"], "schema_version is empty")
        # built_at is an ISO date (YYYY-MM-DD) — the 30-day freshness rule reads it.
        self.assertRegex(meta["built_at"], r"^\d{4}-\d{2}-\d{2}$")


class KnowledgeDbContentTests(unittest.TestCase):
    def setUp(self):
        self.conn = _connect()
        self.addCleanup(self.conn.close)

    def _count(self, table):
        return self.conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]

    def test_row_minimums(self):
        for table, minimum in sorted(MIN_ROWS.items()):
            with self.subTest(table=table):
                self.assertGreaterEqual(
                    self._count(table), minimum,
                    "{0} has fewer rows than the ledger floor".format(table))

    def test_exact_row_counts(self):
        for table, expected in sorted(EXACT_ROWS.items()):
            with self.subTest(table=table):
                self.assertEqual(self._count(table), expected)

    def test_decision_ids_are_the_locked_set(self):
        """Decisions A-J are the architecture lock — the real invariant behind the count."""
        ids = [r["id"] for r in self.conn.execute("SELECT id FROM decisions ORDER BY id")]
        self.assertEqual(list("ABCDEFGHIJ"), ids)

    def test_thread_rounds_are_contiguous(self):
        """The dialog thread is a numbered sequence; a gap means a round went missing.

        This replaces an exact row count: `threads` legitimately grows by one per
        round of the Comfy-Agent dialog, but it must never skip one.
        """
        rounds = [r["round"] for r in self.conn.execute("SELECT round FROM threads ORDER BY round")]
        self.assertEqual(list(range(1, len(rounds) + 1)), rounds)

    def test_every_thread_round_has_a_state(self):
        for row in self.conn.execute("SELECT round, direction, state FROM threads"):
            with self.subTest(round=row["round"]):
                self.assertTrue(row["state"], "round {0} has no state".format(row["round"]))
                self.assertTrue(row["direction"], "round {0} has no direction".format(row["round"]))

    def _tables_with_class_column(self):
        out = []
        for table in TABLES:
            cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(" + table + ")")}
            if "class" in cols:
                out.append(table)
        return out

    def test_every_class_column_is_A_or_B(self):
        tables = self._tables_with_class_column()
        self.assertTrue(tables, "no table carries a 'class' column — the A/B rule vanished")
        for table in tables:
            with self.subTest(table=table):
                values = {
                    r["class"] for r in
                    self.conn.execute("SELECT DISTINCT class FROM " + table)
                }
                self.assertTrue(
                    values <= CLASSES,
                    "{0}.class has non-A/B values: {1}".format(table, sorted(values - CLASSES)))

    def test_node_status_vocabulary(self):
        values = {r["status"] for r in self.conn.execute("SELECT DISTINCT status FROM nodes")}
        self.assertTrue(
            values <= NODE_STATUSES,
            "nodes.status has unexpected values: {0}".format(sorted(values - NODE_STATUSES)))

    def test_spot_check_chatterbox_demo_run_header(self):
        """The first e2e cloud ChatterBox measurement: 24 kHz MONO (decoded FLAC header)."""
        row = self.conn.execute(
            "SELECT sample_rate, channels FROM runs WHERE job_id=?",
            ("19c22524-a7b0-48ee-bb99-37e1651e8067",),
        ).fetchone()
        self.assertIsNotNone(row, "the ChatterBox demo run is missing from runs")
        self.assertEqual(row["sample_rate"], 24000)
        self.assertEqual(row["channels"], 1)

    def test_spot_check_ace15_model_is_commercially_clear(self):
        row = self.conn.execute(
            "SELECT commercial, license FROM models WHERE name=?",
            ("acestep_v1.5_xl_base_bf16.safetensors",),
        ).fetchone()
        self.assertIsNotNone(row, "the ACE-Step 1.5 XL base model is missing from models")
        self.assertEqual(row["commercial"], "yes")

    def test_run_ids_are_full_uuids_or_marked_partial(self):
        """House rule: full UUIDs in receipts. Anything short must say so in its id."""
        for row in self.conn.execute("SELECT job_id FROM runs"):
            job_id = row["job_id"]
            with self.subTest(job_id=job_id):
                self.assertTrue(
                    len(job_id) == 36 or "confirmation" in job_id,
                    "{0!r} is neither a full UUID nor flagged as a partial reference".format(job_id))


class KnowledgeDbSearchTests(unittest.TestCase):
    def setUp(self):
        self.conn = _connect()
        self.addCleanup(self.conn.close)

    def _match(self, expression):
        return self.conn.execute(
            "SELECT kind, name FROM fts WHERE fts MATCH ?", (expression,)
        ).fetchall()

    def test_fts_finds_chatterbox(self):
        rows = self._match("chatterbox")
        self.assertGreaterEqual(len(rows), 1, "FTS lost the ChatterBox rows")

    def test_fts_finds_the_clobber_incident(self):
        """The open_workflow clobber must be findable by full-text search.

        NOTE: the corpus word is "CLOBBERED" (graphs.notes), and FTS5's default
        unicode61 tokenizer emits the single token ``clobbered`` — so a bare
        ``MATCH 'clobber'`` is a legitimate 0-row query against this corpus.
        The prefix form is the correct query for the concept, so that is what is
        asserted here; the bare-token behaviour is pinned below so a future
        re-word of the seed cannot silently change it.
        """
        rows = self._match("clobber*")
        self.assertGreaterEqual(
            len(rows), 1,
            "FTS no longer surfaces the open_workflow clobber incident")

    def test_fts_clobber_prefix_and_exact_token_agree(self):
        prefix = self._match("clobber*")
        exact = self._match("clobbered")
        self.assertEqual(
            len(prefix), len(exact),
            "the clobber rows changed shape — re-check the seed wording in build_db.py")


class KnowledgeDbIdempotencyTests(unittest.TestCase):
    def test_rebuild_is_idempotent(self):
        """AGENTS.md advertises 'rebuild from seed (idempotent)'. Hold it to that."""
        result = _build()
        self.assertEqual(
            result.returncode, 0,
            "second build failed\nstdout:\n{0}\nstderr:\n{1}".format(result.stdout, result.stderr))
        self.assertEqual(_counts(), _FIRST_COUNTS, "row counts drifted across rebuilds")

    def test_rebuild_preserves_schema(self):
        _build()
        with contextlib.closing(_connect()) as conn:
            objects = {
                (r["type"], r["name"])
                for r in conn.execute("SELECT type, name FROM sqlite_master")
                if not r["name"].startswith("sqlite_")
            }
        for table in TABLES:
            self.assertIn(("table", table), objects)
        for view in VIEWS:
            self.assertIn(("view", view), objects)


if __name__ == "__main__":
    unittest.main()
