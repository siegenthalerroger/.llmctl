"""The shared parser: the defaults it applies and how a block fails loudly."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from llmctl import check_frontmatter
from llmctl import provenance as prov

from .support import SKILLS, block, frontmatter, write

URL = "https://github.com/example/up/blob/main/a.md"


class ProvenanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def entries(self, body: str) -> list[prov.Entry]:
        path = write(self.root, f"{SKILLS}/SKILL.md", frontmatter(body))
        return list(prov.parse(path).entries)

    def test_fidelity_defaults_depend_on_the_key(self) -> None:
        # A bare adaptedFrom URL is a whole-file derivation; a bare authoritativeSpec URL, or
        # an object under it that states no fidelity, is a citation that attaches no terms.
        adapted = self.entries(block("adaptedFrom", URL))
        cited = self.entries(block("authoritativeSpec", URL))
        unstated = self.entries(block("authoritativeSpec", {"url": URL, "took": "The limits."}))
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
