"""Licence handling is per file: the gate, the notices and the packed bundle's licence set."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from llmctl import check_licenses, gen_notices, pack_marketplace
from llmctl import provenance as prov

from .support import SKILLS, block, frontmatter, write

URL = "https://github.com/example/up/blob/main/spec.md"


def entry(key: str, license_: str | None, fidelity: str | None, took: str | None = None) -> str:
    fields = {"license": license_, "fidelity": fidelity, "took": took}
    return block(key, {"url": URL, **{k: v for k, v in fields.items() if v}})


class GateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def reference(self, body: str, **kwargs: str) -> check_licenses.Report:
        write(self.root, f"{SKILLS}/references/r.md", frontmatter(body, **kwargs))
        return check_licenses.check(self.root)

    def test_a_reference_copying_apache_material_must_declare_its_own_licence(self) -> None:
        body = entry("authoritativeSpec", "Apache-2.0", "largely-derived")
        (error,) = self.reference(body).errors
        self.assertIn("requires this file to be one of [Apache-2.0]", error[1])
        self.assertEqual(self.reference(body, license_="Apache-2.0").errors, [])

    def test_skill_md_licence_does_not_cover_a_sibling_reference(self) -> None:
        body = entry("authoritativeSpec", "Apache-2.0", "largely-derived")
        write(self.root, f"{SKILLS}/SKILL.md", frontmatter(body, license_="Apache-2.0", name="s"))
        report = self.reference(body)
        self.assertEqual([rel for rel, _ in report.errors], [f"{SKILLS}/references/r.md"])

    def test_a_copied_binding_source_is_judged_like_an_adaptation(self) -> None:
        # Authority is the key; copying is the fields. The gate must not care which key a
        # copied source sits under, so nobody has to duplicate it into the other.
        for license_, fidelity, declared in (
            ("MIT", "partly-derived", None),
            ("Apache-2.0", "largely-derived", None),
            ("Apache-2.0", "largely-derived", "Apache-2.0"),
            ("NONE", "partly-derived", None),
        ):
            outcomes = []
            for key in prov.PROVENANCE_KEYS:
                report = self.reference(
                    entry(key, license_, fidelity), **({"license_": declared} if declared else {})
                )
                outcomes.append([message.replace(key, "KEY") for _, message in report.errors])
            self.assertEqual(outcomes[0], outcomes[1], (license_, fidelity, declared))

    def test_took_on_a_binding_source_must_state_its_fidelity(self) -> None:
        # `took` says something was borrowed; the binding default says nothing was. The
        # gate does not guess which from the prose, and a recorded licence does not decide it.
        for license_ in (None, "MIT"):
            report = self.reference(entry("authoritativeSpec", license_, None, "The limits table."))
            self.assertEqual(report.warnings, [], license_)
            (error,) = report.errors
            self.assertIn("`fidelity` is not", error[1])
        # An empty `fidelity:` is not a stated one.
        empty = block("authoritativeSpec", {"url": URL, "took": "The limits table."})
        (error,) = self.reference(empty + "\n        fidelity:").errors
        self.assertIn("`fidelity` is not", error[1])

    def test_a_binding_source_that_records_no_borrowing_needs_no_fidelity(self) -> None:
        for body in (
            block("authoritativeSpec", URL),
            entry("authoritativeSpec", None, None),
            entry("authoritativeSpec", "MIT", None),
        ):
            report = self.reference(body)
            self.assertEqual((report.errors, report.warnings), ([], []), body)

    def test_took_with_a_stated_fidelity_is_judged_by_that_fidelity(self) -> None:
        took = "The limits table."
        for body in (
            entry("authoritativeSpec", None, "inspiration-only", took),
            entry("authoritativeSpec", None, "structural-echo", took),
            entry("authoritativeSpec", "MIT", "partly-derived", took),
        ):
            report = self.reference(body)
            self.assertEqual((report.errors, report.warnings), ([], []), body)
        (error,) = self.reference(entry("authoritativeSpec", None, "partly-derived", took)).errors
        self.assertIn("the upstream `license:` is required", error[1])

    def test_an_adaptation_keeps_its_whole_file_default_whatever_took_says(self) -> None:
        (error,) = self.reference(entry("adaptedFrom", None, None, "The tiers.")).errors
        self.assertIn("fidelity `largely-derived` copies expression", error[1])
        report = self.reference(entry("adaptedFrom", "MIT", None, "The tiers."))
        self.assertEqual((report.errors, report.warnings), ([], []))

    def test_a_block_the_parser_does_not_read_fails_the_gate(self) -> None:
        report = self.reference(block("authoritativeSpec", URL), under="provenance")
        self.assertEqual(report.records[0].entries, ())
        (error,) = report.errors
        self.assertEqual(error[0], f"{SKILLS}/references/r.md")
        self.assertIn("`metadata.provenance`", error[1])

    def test_a_misspelt_licence_fails_the_gate_and_is_not_read_as_one(self) -> None:
        body = block("adaptedFrom", {"url": URL, "licence": "MIT", "fidelity": "partly-derived"})
        report = self.reference(body)
        self.assertEqual([e.url for e in report.tracked], [URL])
        (field, required) = [message for _, message in report.errors]
        self.assertIn("`licence`", field)
        self.assertNotIn("parses to nothing", field)
        self.assertIn("the upstream `license:` is required", required)


class BundleTest(unittest.TestCase):
    """A packed bundle is judged file by file, references, prompts and instructions included."""

    def setUp(self) -> None:
        self.bundle = Path(self.enterContext(tempfile.TemporaryDirectory()))
        write(
            self.bundle, "skills/s/SKILL.md", frontmatter(block("authoritativeSpec", URL), name="s")
        )
        copied = {
            "skills/s/references/r.md": "Apache-2.0",
            "commands/c.md": "MPL-2.0",
            "instructions/i.instructions.md": "GPL-3.0",
        }
        for rel, spdx in copied.items():
            body = entry("adaptedFrom", spdx, "largely-derived")
            write(self.bundle, rel, frontmatter(body, license_=spdx))

    def test_provenance_on_every_packed_type_reaches_the_notices(self) -> None:
        files = gen_notices.bundle_provenance(str(self.bundle))
        ack: dict = {}
        _, exceptions = gen_notices.bundle_rows({"deps": [], "files": files}, {}, ack)
        self.assertEqual(
            sorted(row[0] for row in exceptions),
            ["commands/c.md", "instructions/i.instructions.md", "skills/s/references/r.md"],
        )
        # The bare binding URL in SKILL.md is credited, not noticed.
        self.assertEqual([url for _, url in ack.values()], [URL])

    def test_an_adaptation_with_no_recorded_copyright_holder_fails_the_pack_gate(self) -> None:
        files = gen_notices.bundle_provenance(str(self.bundle))
        bundle = {"name": "b", "deps": [], "files": files}
        bare = gen_notices.render([bundle], {})
        self.assertEqual(gen_notices.unrecorded(bare), ["example/up"])
        held = {"github.com/example/up": {"spdx": "Apache-2.0", "holder": "Copyright Example"}}
        self.assertEqual(gen_notices.unrecorded(gen_notices.render([bundle], held)), [])

    def test_each_files_own_licence_decides_which_texts_the_bundle_ships(self) -> None:
        needed = pack_marketplace.licenses_needed(self.bundle, set())
        self.assertEqual({"Apache-2.0", "MPL-2.0", "GPL-3.0"} - set(needed), set())


if __name__ == "__main__":
    unittest.main()
