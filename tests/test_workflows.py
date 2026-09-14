"""Trigger contracts for the GitHub Actions workflows.

CI minutes are finite, and the expensive failure here is silent: a workflow that
fires twice for one commit costs double and looks completely normal in the UI —
two green checks, nobody counts them.

It happened twice over in this repo, and neither was noticed until someone
grouped the run history by commit SHA (measured 2026-09-14):

* **push + pull_request on a PR branch.** An unrestricted ``push:`` trigger fires
  alongside ``pull_request:`` for the same commit.
* **main + tag at release time.** ``on.push`` with no ``branches`` filter also
  fires on a tag push, and the tag points at a commit that already ran on ``main``
  — so every release ran the whole matrix a second time. Four of the five
  duplicate pairs in the history were this one.

An attempt to fix the first in the ``concurrency`` group failed, and the failure
is instructive: ``github.head_ref`` is empty on a push, so the two events resolved
to different group names and nothing was cancelled. It could not have fixed the
second at all — those runs are minutes apart, and ``cancel-in-progress`` only
cancels something still running.

**The duplicate has to be removed at the trigger.** That is what these tests
check, and the parser below is deliberately shallow: it reads the ``on:`` block's
indentation and nothing cleverer. PyYAML is not in the test toolchain — CI
installs ``build`` and ``pillow`` only — so this parses by hand, the same way
``ZeroDependencyTests`` parses one field out of ``pyproject.toml`` rather than
taking a dependency on ``tomllib`` above the 3.10 floor.
"""

from __future__ import annotations

import glob
import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW_GLOB = os.path.join(REPO_ROOT, ".github", "workflows", "*.yml")

#: Triggers that fire automatically on a code change. A workflow reaching more
#: than one of these for the same commit is the defect this module exists for.
CODE_CHANGE_TRIGGERS = ("push", "pull_request")

#: Paths every ci run must stay gated on, per the org's Actions rules. Dropping
#: one silently widens the trigger, which is the same cost defect from the other
#: direction.
REQUIRED_CI_PATHS = ("pyproject.toml", "tools/**", "tests/**", "verify.sh",
                     ".github/workflows/**")


def parse_triggers(text):
    """Return ``{trigger: {sub_key: value}}`` for a workflow's top-level ``on:``.

    Shallow by design — indentation only, no YAML semantics. A value is kept as
    the raw string after the colon (``"[main]"``, ``""`` for a nested block), and
    list items under a sub-key are collected into ``sub_key + "[]"``.

    :raises ValueError: if the ``on:`` block is missing or uses the inline form
        (``on: [push]``). An unparseable workflow must FAIL these gates rather
        than skip them — a check that quietly finds nothing to check reads as a
        pass, which is the failure mode this repo keeps paying for.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("on:"):
            if line[3:].strip():
                raise ValueError(
                    "inline `on:` form is not parsed by this gate: {0!r}".format(line))
            start = i + 1
            break
    if start is None:
        raise ValueError("no top-level `on:` block")

    triggers = {}
    current = None
    current_sub = None
    for line in lines[start:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            break
        body = line.strip()
        if indent == 2 and body.endswith(":") or (indent == 2 and ":" in body):
            key, _, value = body.partition(":")
            current, current_sub = key.strip(), None
            triggers[current] = {}
            if value.strip():
                triggers[current]["__inline__"] = value.strip()
        elif indent == 4 and current is not None and ":" in body:
            key, _, value = body.partition(":")
            current_sub = key.strip()
            triggers[current][current_sub] = value.strip()
        elif body.startswith("-") and current is not None and current_sub is not None:
            triggers[current].setdefault(current_sub + "[]", []).append(
                body[1:].strip().strip("'\""))
    return triggers


def double_fire_problems(name, triggers):
    """Return the reasons this workflow can run more than once for one commit.

    Shared by the live gate and its own red-gate test, so the detector that is
    proven falsifiable is the same one that guards the repo.
    """
    problems = []
    push = triggers.get("push")
    if push is None:
        return problems

    branches = push.get("branches", "") or ""
    branch_items = push.get("branches[]", [])
    scoped = bool(branches.strip()) or bool(branch_items)

    if not scoped:
        problems.append(
            "{0}: `push` names no `branches`, so it also fires on TAG pushes — and a "
            "tag points at a commit that already ran on the default branch. Every "
            "release pays for the matrix twice.".format(name))
    if "pull_request" in triggers and not scoped:
        problems.append(
            "{0}: fires on both `push` (any branch) and `pull_request`, so a PR "
            "branch runs the whole matrix twice for one commit. Scope `push` to the "
            "default branch.".format(name))

    wildcards = {b for b in branch_items if "*" in b}
    wildcards |= {"*"} if "*" in branches else set()
    if "pull_request" in triggers and wildcards:
        problems.append(
            "{0}: `push.branches` matches every branch ({1}), which re-opens the "
            "push+pull_request double-fire.".format(name, sorted(wildcards)))
    return problems


def _read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


class WorkflowTriggerTests(unittest.TestCase):
    def setUp(self):
        self.workflows = sorted(glob.glob(WORKFLOW_GLOB))

    def test_workflows_exist(self):
        """Guard against the gate silently finding nothing to gate."""
        self.assertTrue(self.workflows, "no workflows found at .github/workflows/*.yml")

    def test_no_workflow_runs_twice_for_one_commit(self):
        for path in self.workflows:
            name = os.path.basename(path)
            with self.subTest(workflow=name):
                problems = double_fire_problems(name, parse_triggers(_read(path)))
                self.assertEqual([], problems, "\n".join(problems))

    def test_every_workflow_keeps_a_manual_fallback(self):
        """`workflow_dispatch` is required by the org rules — and load-bearing here.

        Scoping `push` to the default branch means a branch with no open PR gets
        no automatic run. The manual trigger is the accepted mitigation, so it is
        not optional.
        """
        for path in self.workflows:
            name = os.path.basename(path)
            with self.subTest(workflow=name):
                self.assertIn("workflow_dispatch", parse_triggers(_read(path)),
                              "{0} has no manual fallback".format(name))

    def test_ci_stays_paths_gated_on_both_triggers(self):
        """A trigger that loses its paths filter fires on every README typo."""
        triggers = parse_triggers(_read(os.path.join(REPO_ROOT, ".github", "workflows", "ci.yml")))
        for trigger in CODE_CHANGE_TRIGGERS:
            with self.subTest(trigger=trigger):
                paths = triggers[trigger].get("paths[]", [])
                self.assertTrue(paths, "ci.yml {0} lost its paths filter".format(trigger))
                for required in REQUIRED_CI_PATHS:
                    self.assertIn(required, paths)

    def test_ci_push_is_scoped_to_the_default_branch(self):
        """The specific fix, asserted directly so a revert is loud."""
        triggers = parse_triggers(_read(os.path.join(REPO_ROOT, ".github", "workflows", "ci.yml")))
        self.assertIn("main", triggers["push"].get("branches", ""))

    def test_no_workflow_uses_the_concurrency_form_that_does_not_collapse(self):
        """`head_ref || ref` was applied here as a double-fire fix and did not work.

        It resolves to `refs/heads/x` on a push and `x` on a pull_request, so the
        two events never share a group. Asserted as a NEGATIVE because that is
        what the evidence supports: the form was measured not to collapse (two
        full runs on 77cc70f, 2026-09-14). This does not assert that any
        particular replacement does collapse — the trigger filter is what this
        repo measured, and the group is belt-and-braces.
        """
        broken = "github.head_ref || github.ref }}"
        for path in self.workflows:
            with self.subTest(workflow=os.path.basename(path)):
                self.assertNotIn(
                    broken, _read(path),
                    "{0} uses the concurrency group form that was measured NOT to "
                    "collapse push and pull_request. Use the bare branch name on "
                    "both sides: github.event.pull_request.head.ref || "
                    "github.ref_name".format(os.path.basename(path)))


class DetectorFalsifiabilityTests(unittest.TestCase):
    """A detector that cannot go red is theater. Prove this one fires.

    The first fixture is the ci.yml that shipped at commit 5051536 — the real
    configuration these tests were written against, reproduced verbatim enough to
    be caught.
    """

    SHIPPED_BAD = """name: ci
on:
  push:
    paths:
      - 'tools/**'
  pull_request:
    paths:
      - 'tools/**'
  workflow_dispatch:
"""

    WILDCARD_BAD = """name: ci
on:
  push:
    branches: ['**']
    paths:
      - 'tools/**'
  pull_request:
    paths:
      - 'tools/**'
  workflow_dispatch:
"""

    FIXED = """name: ci
on:
  push:
    branches: [main]
    paths:
      - 'tools/**'
  pull_request:
    paths:
      - 'tools/**'
  workflow_dispatch:
"""

    def test_the_configuration_that_shipped_is_caught(self):
        problems = double_fire_problems("ci.yml", parse_triggers(self.SHIPPED_BAD))
        self.assertEqual(len(problems), 2, problems)
        self.assertIn("TAG pushes", problems[0])
        self.assertIn("twice for one commit", problems[1])

    def test_a_wildcard_branch_filter_is_caught(self):
        """`branches: ['**']` is scoped in form and unscoped in effect."""
        problems = double_fire_problems("ci.yml", parse_triggers(self.WILDCARD_BAD))
        self.assertTrue(problems)
        self.assertIn("every branch", problems[0])

    def test_the_fixed_configuration_passes(self):
        """The control. A detector that fires on the correct shape is noise."""
        self.assertEqual([], double_fire_problems("ci.yml", parse_triggers(self.FIXED)))

    def test_a_release_only_workflow_is_not_flagged(self):
        """release.yml has no push trigger at all and must not be dragged in."""
        text = "name: release\non:\n  release:\n    types: [published]\n  workflow_dispatch:\n"
        self.assertEqual([], double_fire_problems("release.yml", parse_triggers(text)))

    def test_an_unparseable_on_block_fails_loudly(self):
        for label, text in (("inline form", "name: x\non: [push]\n"),
                            ("missing block", "name: x\njobs:\n  a:\n    runs-on: ubuntu-latest\n")):
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    parse_triggers(text)


if __name__ == "__main__":
    unittest.main()
