"""The shared parser: the defaults it applies and how a block fails loudly."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from llmctl import check_frontmatter
from llmctl import provenance as prov

from .support import SKILLS, block, frontmatter, nest, write

URL = "https://github.com/example/up/blob/main/a.md"
FIELDS = ("url", "license", "fidelity", "took")


class ProvenanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def record(self, body: str, **kwargs: str) -> prov.Record:
        return prov.parse(write(self.root, f"{SKILLS}/SKILL.md", frontmatter(body, **kwargs)))

    def entries(self, body: str) -> list[prov.Entry]:
        return list(self.record(body).entries)

    def test_fidelity_defaults_depend_on_the_key(self) -> None:
        # A bare adaptedFrom URL is a whole-file derivation; a bare authoritativeSpec URL, or
        # an object under it that states no fidelity, is a citation that attaches no terms.
        adapted = self.entries(block("adaptedFrom", URL))
        cited = self.entries(block("authoritativeSpec", URL))
        unstated = self.entries(block("authoritativeSpec", {"url": URL, "license": "MIT"}))
        self.assertEqual(prov.effective_fidelity(adapted[0]), "largely-derived")
        self.assertEqual(prov.effective_fidelity(cited[0]), "inspiration-only")
        self.assertEqual(prov.effective_fidelity(unstated[0]), "inspiration-only")

    def test_a_block_that_tracks_nothing_is_reported_not_dropped(self) -> None:
        for body, problem in (
            (block("adaptedFrom", {"license": "MIT"}), "has an entry with no url"),
            ("    authoritativeSpec: []", "yields no entries"),
        ):
            path = write(self.root, f"{SKILLS}/SKILL.md", frontmatter(body))
            record = prov.parse(path)
            self.assertEqual(record.entries, (), body)
            self.assertTrue(any(problem in message for message in record.malformed), body)

    def test_a_block_outside_metadata_provenance_is_reported_and_not_read(self) -> None:
        # The convention has one location. Every other placement used to parse to nothing
        # and say nothing, so the file dropped out of the gate, the notices and the audit.
        for under, key, where in (
            ("provenance", "adaptedFrom", "provenance"),
            ("Provenance", "adaptedFrom", "Provenance"),
            ("", "adaptedFrom", "adaptedFrom"),
            ("", "authoritativeSpec", "authoritativeSpec"),
            ("metadata", "adaptedFrom", "metadata.adaptedFrom"),
            ("metadata", "authoritativeSpec", "metadata.authoritativeSpec"),
            ("metadata.Provenance", "adaptedFrom", "metadata.Provenance"),
            ("Metadata.provenance", "adaptedFrom", "Metadata"),
        ):
            record = self.record(block(key, URL), under=under)
            self.assertEqual(record.entries, (), where)
            self.assertEqual(len(record.malformed), 1, record.malformed)
            self.assertIn(f"`{where}`", record.malformed[0])
            self.assertIn("`metadata.provenance`", record.malformed[0])
        # The dotted path the docs name the field by, written as one literal key.
        record = self.record(f'metadata.provenance.adaptedFrom: "{URL}"', under="")
        self.assertEqual(record.entries, ())
        (problem,) = record.malformed
        self.assertIn("`metadata.provenance.adaptedFrom`", problem)

    def test_a_misplaced_block_is_reported_beside_a_nested_one(self) -> None:
        body = nest("provenance", block("adaptedFrom", URL))
        body += "\n" + nest("metadata.provenance", block("authoritativeSpec", URL))
        record = self.record(body, under="")
        # The stray block uses the other key, so an adaptedFrom entry would prove it was read.
        self.assertEqual([(e.kind, e.url) for e in record.entries], [("authoritativeSpec", URL)])
        (problem,) = record.malformed
        self.assertIn("`provenance`", problem)

    def test_a_file_with_nothing_misplaced_reports_nothing(self) -> None:
        for body, under in (
            (block("adaptedFrom", URL), "metadata.provenance"),
            ('modelProfile: {cost: "LOW"}', "metadata"),
            ("metadata:", ""),
            ("", ""),
        ):
            record = self.record(body, under=under, name="s", license_="MIT")
            self.assertEqual(record.malformed, (), body)

    def test_provenance_that_is_not_a_mapping_of_keys_is_reported(self) -> None:
        for body, under in (
            (f'provenance: "{URL}"', "metadata"),
            (f'provenance: ["{URL}"]', "metadata"),
            ("provenance:", "metadata"),
            ("provenance: {}", "metadata"),
            (f'metadata: ["{URL}"]', ""),
            (f'metadata: "{URL}"', ""),
        ):
            record = self.record(body, under=under)
            self.assertEqual(record.entries, (), body)
            self.assertEqual(len(record.malformed), 1, record.malformed)
            self.assertIn("`metadata", record.malformed[0])
            self.assertIn("not a mapping", record.malformed[0])

    def test_an_unknown_key_under_provenance_is_reported(self) -> None:
        for key in ("adapted_from", "adaptedfrom", "authoritative_spec", "license"):
            record = self.record(block("adaptedFrom", URL) + "\n" + block(key, URL))
            # The valid key beside it is still read; the near-miss is not read as the key
            # it resembles.
            self.assertEqual([e.kind for e in record.entries], ["adaptedFrom"], key)
            self.assertEqual(len(record.malformed), 1, record.malformed)
            for name in (key, *prov.PROVENANCE_KEYS):
                self.assertIn(name, record.malformed[0])

    def test_an_unknown_field_is_reported_and_its_entry_still_tracked(self) -> None:
        # The url is good, so the entry stays in the drift audit; the misspelt field is not
        # read as the one it resembles, so it cannot satisfy a licence requirement.
        for field, value in (("licence", "MIT"), ("fidelty", "partly-derived"), ("Took", "x")):
            record = self.record(block("adaptedFrom", {"url": URL, field: value}))
            self.assertEqual(record.entries, (prov.Entry(URL, "object", "adaptedFrom"),), field)
            self.assertEqual(len(record.malformed), 1, record.malformed)
            for name in (field, *FIELDS):
                self.assertIn(f"`{name}`", record.malformed[0])

    def test_a_field_that_is_not_a_string_is_ignored_and_reported(self) -> None:
        # str() of a list or a YAML 1.1 boolean reads as text; under a binding key it would
        # then claim a borrowing nobody recorded.
        for field, value in (("took", "[]"), ("took", "no"), ("license", "[MIT]")):
            body = nest("authoritativeSpec", f'- url: "{URL}"\n  {field}: {value}')
            (entry,) = self.record(body).entries
            self.assertIsNone(getattr(entry, field), (field, value))
            (problem,) = self.record(body).malformed
            self.assertIn(f"`{field}` is a", problem)
        record = self.record(nest("adaptedFrom", f'- url: ["{URL}"]'))
        self.assertEqual(record.entries, ())
        (problem,) = record.malformed
        self.assertIn("`url` is a list", problem)

    def test_a_misplaced_file_licence_is_reported_and_the_default_kept(self) -> None:
        for body, under, key in (
            ("license: MIT", "metadata", "metadata.license"),
            ("licence: MIT", "metadata", "metadata.licence"),
            ("licence: MIT", "", "licence"),
            ("License: MIT", "", "License"),
        ):
            record = self.record(body, under=under)
            self.assertEqual((record.declared, record.effective), (None, prov.DEFAULT_CONTENT))
            (problem,) = record.malformed
            self.assertIn(f"`{key}`", problem)
            self.assertIn("top-level `license`", problem)
        self.assertEqual(self.record("", under="", license_="MIT").malformed, ())

    def test_a_reference_page_needs_no_name_or_description(self) -> None:
        # Frontmatter validation is for primitives. A reference carrying only provenance and
        # a licence is neither validated nor an error.
        spec = block(
            "authoritativeSpec", {"url": URL, "license": "MIT", "fidelity": "partly-derived"}
        )
        write(self.root, f"{SKILLS}/SKILL.md", frontmatter(block("adaptedFrom", URL), name="s"))
        write(self.root, f"{SKILLS}/references/spec.md", frontmatter(spec, license_="MIT"))
        report = check_frontmatter.check(self.root)
        self.assertEqual((report.errors, report.files), ([], [f"{SKILLS}/SKILL.md"]))


if __name__ == "__main__":
    unittest.main()
