"""The procedures that audit binding sources split the files between them exactly once.

The filters are written into two skills as shell commands. This reads them from the
skills, so a filter edited in one place and not the other fails here rather than
leaving a reference page unaudited, or audited by both.
"""

from __future__ import annotations

import re
import shlex
import unittest
from pathlib import Path

from llmctl import provenance as prov
from llmctl import workspace

from .support import ROOT

UPDATE_REPO = ROOT / ".apm/skills/meta-update-repo/SKILL.md"
REFRESH = ROOT / ".apm/skills/meta-refresh-steering/SKILL.md"
MODELS_DIR = ".apm/skills/meta-update-models/"  # audits its own sources; no flags involved
SPEC_COMMAND = "llmctl-check-updates"


def spec_commands(skill: Path) -> list[list[str]]:
    """Every `llmctl-check-updates ... --specs` command in a skill's shell blocks, split."""
    commands = []
    for block in re.findall(r"```bash\n(.*?)```", skill.read_text(encoding="utf-8"), re.DOTALL):
        words = shlex.split(block.replace("\\\n", " "))
        if SPEC_COMMAND in words and "--specs" in words:
            commands.append(words)
    return commands


def values(words: list[str], flag: str) -> list[str]:
    return [words[i + 1] for i, word in enumerate(words[:-1]) if word == flag]


class OwnershipTest(unittest.TestCase):
    def setUp(self) -> None:
        (phase_d,) = spec_commands(UPDATE_REPO)
        self.excludes = values(phase_d, "--exclude")
        self.includes = [v for words in spec_commands(REFRESH) for v in values(words, "--include")]

    def owners(self, rel: str) -> list[str]:
        owners = []
        if workspace.included(rel, "", self.excludes):
            owners.append("meta-update-repo")
        if any(workspace.included(rel, include) for include in self.includes):
            owners.append("meta-refresh-steering")
        if rel.startswith(MODELS_DIR):
            owners.append("meta-update-models")
        return owners

    def test_every_binding_file_in_this_repository_has_exactly_one_owner(self) -> None:
        binding = [
            Path(path).relative_to(ROOT).as_posix()
            for path in prov.iter_files(ROOT)
            if any(e.kind == prov.BINDING for e in prov.parse(path).entries)
        ]
        self.assertTrue(binding)
        for rel in binding:
            self.assertEqual(len(self.owners(rel)), 1, f"{rel}: {self.owners(rel)}")

    def test_references_go_with_their_skill(self) -> None:
        steering = "packages/baseline/.apm/skills/meta-steering"
        harness = "packages/baseline/.apm/skills/meta-harness"
        for skill in (steering, harness):
            for leaf in ("SKILL.md", "references/anything.md"):
                self.assertEqual(self.owners(f"{skill}/{leaf}"), ["meta-refresh-steering"], leaf)
        self.assertEqual(self.owners(f"{MODELS_DIR}SKILL.md"), ["meta-update-models"])
        self.assertEqual(self.owners(f"{MODELS_DIR}references/anything.md"), ["meta-update-models"])


if __name__ == "__main__":
    unittest.main()
