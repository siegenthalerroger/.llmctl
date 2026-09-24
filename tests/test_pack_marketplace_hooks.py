"""Regression fixtures for APM hook projection into native marketplace plugins."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from llmctl.pack_marketplace import (
    PackError,
    normalize_plugin_hooks,
    relocate_manifest,
    write_codex_manifest,
)


class PluginHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="llmctl hook tests ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bundle = self.root / "bundle"
        self.bundle.mkdir()
        self.script = self.bundle / "skills/example/scripts/check.py"
        self.script.parent.mkdir(parents=True)
        self.script.write_text('print("checked")\n', encoding="utf-8")
        (self.bundle / "plugin.json").write_text(
            json.dumps({"name": "example", "version": "1.0.0"}), encoding="utf-8"
        )
        relocate_manifest(self.bundle)

    def write_hooks(self, command: str) -> None:
        self.hooks = {
            "description": "Keep metadata untouched",
            "hooks": {
                "PostToolUse": [
                    {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": command}]}
                ],
                "Stop": [{"hooks": [{"type": "command", "command": command}]}],
            },
        }
        (self.bundle / "hooks.json").write_text(json.dumps(self.hooks), encoding="utf-8")

    def command(self) -> str:
        data = json.loads((self.bundle / "hooks.json").read_text(encoding="utf-8"))
        return data["hooks"]["Stop"][0]["hooks"][0]["command"]

    def test_paths_and_both_manifests_survive_relocation(self) -> None:
        command = (
            f'"{sys.executable}"  '
            '"${CLAUDE_PLUGIN_ROOT}/.apm/skills/example/scripts/check.py" --hook'
        )
        self.write_hooks(command)
        normalize_plugin_hooks(self.bundle)
        write_codex_manifest(self.bundle, "productivity")
        self.assertEqual(self.command(), command.replace("/.apm/skills/", "/skills/"))
        for directory in (".claude-plugin", ".codex-plugin"):
            manifest = json.loads(
                (self.bundle / directory / "plugin.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["hooks"], "./hooks.json")
        relocated = self.root / "relocated plugin with spaces"
        shutil.move(self.bundle, relocated)
        environment = os.environ.copy()
        environment["CLAUDE_PLUGIN_ROOT"] = str(relocated)
        environment["PLUGIN_ROOT"] = str(relocated)
        command = json.loads((relocated / "hooks.json").read_text(encoding="utf-8"))["hooks"][
            "Stop"
        ][0]["hooks"][0]["command"]
        result = subprocess.run(
            ["sh", "-c", command],
            cwd=self.root,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout, "checked\n")

    def test_root_alias_and_quoted_spaces(self) -> None:
        path = self.script.with_name("check with spaces.py")
        self.script.rename(path)
        self.write_hooks(
            'python3 "${PLUGIN_ROOT}/.apm/skills/example/scripts/check with spaces.py"'
        )
        normalize_plugin_hooks(self.bundle)
        self.assertEqual(
            self.command(), 'python3 "${PLUGIN_ROOT}/skills/example/scripts/check with spaces.py"'
        )

    def test_native_path_and_unrelated_command_bytes_preserved(self) -> None:
        for command in (
            'python3 "${PLUGIN_ROOT}/skills/example/scripts/check.py"',
            'python3 --script="${PLUGIN_ROOT}/scripts/native.py"',
            "uvx --from git+https://github.com/example/tools@main validate "
            '--repo "${CLAUDE_PROJECT_DIR}" --hook',
            'printf "%s" "ordinary .apm/skills/example text"',
        ):
            with self.subTest(command=command):
                self.write_hooks(command)
                normalize_plugin_hooks(self.bundle)
                self.assertEqual(self.command(), command)

    def test_idempotent(self) -> None:
        self.write_hooks('python3 "${CLAUDE_PLUGIN_ROOT}/.apm/skills/example/scripts/check.py"')
        normalize_plugin_hooks(self.bundle)
        before = (self.bundle / "hooks.json").read_bytes()
        normalize_plugin_hooks(self.bundle)
        self.assertEqual((self.bundle / "hooks.json").read_bytes(), before)

    def test_invalid_paths_fail_without_partial_writes(self) -> None:
        for path in (
            ".apm/skills/missing.py",
            ".apm/hooks/missing.py",
            ".apm/skills/../../outside.py",
            ".apm/skills/example/$RUNTIME.py",
            ".apm/skills/example/*.py",
            ".apm/skills//example/scripts/check.py",
        ):
            with self.subTest(path=path):
                self.write_hooks(f'python3 "${{PLUGIN_ROOT}}/{path}"')
                before = (self.bundle / "hooks.json").read_bytes()
                with self.assertRaises(PackError):
                    normalize_plugin_hooks(self.bundle)
                self.assertEqual((self.bundle / "hooks.json").read_bytes(), before)

    def test_ambiguous_shell_arguments_fail(self) -> None:
        for command in (
            'python3 "${PLUGIN_ROOT}"/.apm/skills/example/scripts/check.py',
            'python3 --script="${PLUGIN_ROOT}/.apm/skills/example/scripts/check.py"',
            "python3 '${PLUGIN_ROOT}/.apm/skills/example/scripts/check.py'",
            'python3 "${PLUGIN_ROOT}/.apm/skills/example/scripts/check.py',
        ):
            with self.subTest(command=command):
                self.write_hooks(command)
                with self.assertRaises(PackError):
                    normalize_plugin_hooks(self.bundle)

    def test_symlink_escape_fails(self) -> None:
        outside = self.root / "outside.py"
        outside.write_text("pass\n", encoding="utf-8")
        self.script.unlink()
        self.script.symlink_to(outside)
        self.write_hooks('python3 "${PLUGIN_ROOT}/.apm/skills/example/scripts/check.py"')
        with self.assertRaises(PackError):
            normalize_plugin_hooks(self.bundle)

    def test_conflicting_manifest_fails(self) -> None:
        self.write_hooks("echo check")
        path = self.bundle / ".claude-plugin/plugin.json"
        path.write_text(json.dumps({"name": "example", "hooks": {"Stop": []}}), encoding="utf-8")
        with self.assertRaisesRegex(PackError, "conflict"):
            normalize_plugin_hooks(self.bundle)

    def test_non_hook_plugin_unchanged(self) -> None:
        path = self.bundle / ".claude-plugin/plugin.json"
        before = path.read_bytes()
        normalize_plugin_hooks(self.bundle)
        write_codex_manifest(self.bundle, "productivity")
        self.assertEqual(path.read_bytes(), before)
        self.assertNotIn(
            "hooks",
            json.loads((self.bundle / ".codex-plugin/plugin.json").read_text(encoding="utf-8")),
        )

    def test_flat_platform_commands_only(self) -> None:
        self.write_hooks("echo check")
        self.hooks["hooks"]["PostToolUse"] = [
            {
                "bash": 'python3 "${PLUGIN_ROOT}/.apm/skills/example/scripts/check.py"',
                "description": ".apm/skills unchanged",
            }
        ]
        path = self.bundle / "hooks.json"
        path.write_text(json.dumps(self.hooks), encoding="utf-8")
        normalize_plugin_hooks(self.bundle)
        entry = json.loads(path.read_text(encoding="utf-8"))["hooks"]["PostToolUse"][0]
        self.assertEqual(entry["bash"], 'python3 "${PLUGIN_ROOT}/skills/example/scripts/check.py"')
        self.assertEqual(entry["description"], ".apm/skills unchanged")


if __name__ == "__main__":
    unittest.main()
