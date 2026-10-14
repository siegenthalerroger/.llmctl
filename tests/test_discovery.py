"""What the drift audit finds, and what it recommends once it finds it."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from llmctl import check_updates as cu
from llmctl import provenance as prov

from .support import ROOT, SKILLS, FakeGitHub, block, commit_all, frontmatter, write

GH = "https://github.com/example/up/blob/main/a.md"
OPTIONS = cu.Options(change_details=False, max_change_commits=5, allow_no_local_commit=False)


class DiscoveryTest(unittest.TestCase):
    def test_reference_pages_are_audited_and_installed_copies_are_not(self) -> None:
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        skill = block("authoritativeSpec", f"{GH}1") + "\n"
        skill += block("adaptedFrom", {"url": f"{GH}2", "took": "The tiers."})
        write(root, f"{SKILLS}/SKILL.md", frontmatter(skill, name="s"))
        spec = {"url": f"{GH}3", "license": "MIT", "fidelity": "partly-derived"}
        write(root, f"{SKILLS}/references/spec.md", frontmatter(block("authoritativeSpec", spec)))
        write(root, f"{SKILLS}/references/borrowed.md", frontmatter(block("adaptedFrom", f"{GH}4")))
        write(
            root, "packages/p/apm_modules/up/SKILL.md", frontmatter(block("adaptedFrom", f"{GH}5"))
        )
        write(root, "README.md", frontmatter(block("adaptedFrom", f"{GH}6")))

        found = {
            kind: {(r["file"], r["source"]): r for r in cu.tracked_entries(root, kind)}
            for kind in prov.PROVENANCE_KEYS
        }
        self.assertEqual(
            set(found["authoritativeSpec"]),
            {(f"{SKILLS}/SKILL.md", f"{GH}1"), (f"{SKILLS}/references/spec.md", f"{GH}3")},
        )
        self.assertEqual(
            set(found["adaptedFrom"]),
            {(f"{SKILLS}/SKILL.md", f"{GH}2"), (f"{SKILLS}/references/borrowed.md", f"{GH}4")},
        )
        row = found["authoritativeSpec"][(f"{SKILLS}/references/spec.md", f"{GH}3")]
        self.assertEqual(row["kind"], "authoritativeSpec")

    def test_every_provenance_bearing_file_in_this_repository_is_audited(self) -> None:
        # The audit once skipped everything that was not a primitive, which hid a
        # near-verbatim copy of a specification from drift review.
        declared = {
            Path(p).relative_to(ROOT).as_posix()
            for p in prov.iter_files(ROOT)
            if prov.parse(p).entries
        }
        audited = {
            r["file"] for kind in prov.PROVENANCE_KEYS for r in cu.tracked_entries(ROOT, kind)
        }
        self.assertEqual(declared - audited, set())


def item(kind: str, took: str = "") -> cu.Item:
    return {
        "file": f"{SKILLS}/references/r.md",
        "kind": kind,
        "source": GH,
        "took": took,
        "license": "",
        "fidelity": "",
    }


class RecommendationTest(unittest.TestCase):
    """A binding source is assessed in full; `took` is not consulted for either key."""

    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write(self.root, f"{SKILLS}/references/r.md", "# local\n")
        commit_all(self.root, "2026-01-01T00:00:00+00:00")
        self.client = FakeGitHub("2026-06-01T00:00:00+00:00")

    def test_binding_source_is_assessed_in_full_whatever_took_says(self) -> None:
        for took in ("", "The limits table.", "The general approach."):
            row = cu.audit_spec(item("authoritativeSpec", took), self.root, self.client, OPTIONS)
            self.assertEqual(row["status"], "update_available")
            self.assertEqual(row["recommendation"], "assess_all_normative_content", took)

    def test_binding_source_on_a_plain_web_page_gets_the_same_recommendation(self) -> None:
        # Not a GitHub URL: dated by Last-Modified instead, through a separate branch.
        page = SimpleNamespace(
            status_code=200, headers={"Last-Modified": "Mon, 01 Jun 2026 00:00:00 GMT"}
        )
        row = {
            **item("authoritativeSpec", "The limits table."),
            "source": "https://example.com/spec",
        }
        with mock.patch.object(cu, "probe", return_value=page):
            result = cu.audit_spec(row, self.root, self.client, OPTIONS)
        self.assertEqual(result["status"], "update_available")
        self.assertEqual(result["recommendation"], "assess_all_normative_content")

    def test_adapted_source_is_still_merged_and_took_does_not_change_the_row(self) -> None:
        plain = cu.audit_adapted(item("adaptedFrom"), self.root, self.client, OPTIONS)
        scoped = cu.audit_adapted(
            item("adaptedFrom", "The tiers."), self.root, self.client, OPTIONS
        )
        for row in (plain, scoped):
            self.assertEqual(row["recommendation"], "review_and_merge_from_upstream")
        self.assertEqual(plain["status"], scoped["status"])

    def test_bootstrap_keeps_the_same_split(self) -> None:
        never_committed = Path(self.enterContext(tempfile.TemporaryDirectory()))
        options = cu.Options(False, 5, allow_no_local_commit=True)
        for kind, expected in (
            ("authoritativeSpec", "bootstrap_assess_all_normative_content"),
            ("adaptedFrom", "bootstrap_review_and_merge_from_upstream"),
        ):
            row = cu.audit_adapted(item(kind), never_committed, self.client, options)
            self.assertEqual(row["recommendation"], expected)


if __name__ == "__main__":
    unittest.main()
