"""A commit's scope has to name something it touched; `tests/` is tooling's."""

from __future__ import annotations

import unittest

from llmctl import commits


class ScopesTest(unittest.TestCase):
    def test_tests_belong_to_tooling(self) -> None:
        self.assertEqual(commits.scopes_for(["tests/test_provenance.py"]), {"tooling"})


if __name__ == "__main__":
    unittest.main()
