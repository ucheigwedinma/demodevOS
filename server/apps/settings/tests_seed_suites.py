import ast
from io import StringIO
from pathlib import Path
from unittest.mock import ANY, call, patch

from django.core.management import call_command
from django.test import SimpleTestCase

from apps.settings.seed_suites import (
    SUITE_GUARD_COMMAND_PREFIXES,
    SUITE_GUARD_IGNORED_COMMANDS,
    registered_suite_command_names,
    registered_suite_workflow_task_names,
)


class SeedSuiteCommandTests(SimpleTestCase):
    @patch(
        "apps.settings.management.commands.seed_demo_suite.resolve_target_organization_ids",
        return_value=[4],
    )
    @patch("apps.settings.seed_suites.call_command")
    def test_demo_suite_flush_reseeds_properties(self, mocked_call_command, _mocked_orgs):
        output = StringIO()

        call_command(
            "seed_demo_suite",
            skip_core=True,
            flush=True,
            organization_ids=[4],
            stdout=output,
            stderr=output,
        )

        mocked_call_command.assert_any_call(
            "seed_properties_demo",
            stdout=ANY,
            stderr=ANY,
            org_ids=[4],
            reseed=True,
        )

    def test_platform_suite_lists_optional_steps(self):
        output = StringIO()

        call_command(
            "seed_platform_suite",
            include_ops=True,
            include_workflows=True,
            list_steps=True,
            stdout=output,
        )

        rendered = output.getvalue()
        self.assertIn("platform_editions", rendered)
        self.assertIn("documents_compliance_monitor", rendered)
        self.assertIn("maintenance_workflows", rendered)

    @patch(
        "apps.settings.management.commands.seed_platform_suite.resolve_target_organization_ids",
        return_value=[3, 5],
    )
    @patch("apps.settings.seed_suites.call_command")
    def test_platform_suite_runs_selected_seed_step(
        self,
        mocked_call_command,
        _mocked_orgs,
    ):
        output = StringIO()

        call_command(
            "seed_platform_suite",
            steps=["seed_rbac"],
            organization_ids=[3, 5],
            stdout=output,
            stderr=output,
        )

        self.assertEqual(
            mocked_call_command.call_args_list,
            [
                call("seed_rbac", stdout=ANY, stderr=ANY, org=3),
                call("seed_rbac", stdout=ANY, stderr=ANY, org=5),
            ],
        )


class SeedSuiteRegistryGuardTests(SimpleTestCase):
    def test_all_suite_candidate_management_commands_are_registered(self):
        discovered = self._discover_guarded_management_commands()
        registered = registered_suite_command_names()

        missing = sorted(discovered - registered)
        unexpected = sorted(registered - discovered)

        self.assertEqual(
            missing,
            [],
            msg=(
                "Suite registry is missing management command(s): "
                + ", ".join(missing)
                + ". Add them to server/apps/settings/seed_suites.py or ignore them explicitly "
                "if they are intentionally covered by a wrapper command."
            ),
        )
        self.assertEqual(
            unexpected,
            [],
            msg=(
                "Suite registry contains command(s) that are no longer discoverable: "
                + ", ".join(unexpected)
            ),
        )

    def test_all_scheduled_workflow_tasks_are_registered(self):
        discovered = self._discover_guarded_workflow_tasks()
        registered = registered_suite_workflow_task_names()

        missing = sorted(discovered - registered)
        unexpected = sorted(registered - discovered)

        self.assertEqual(
            missing,
            [],
            msg=(
                "Suite registry is missing scheduled workflow task(s): "
                + ", ".join(missing)
                + ". Add them to WORKFLOW_STEPS in server/apps/settings/seed_suites.py."
            ),
        )
        self.assertEqual(
            unexpected,
            [],
            msg=(
                "Suite registry contains workflow task(s) that are no longer discoverable: "
                + ", ".join(unexpected)
            ),
        )

    def _discover_guarded_management_commands(self) -> set[str]:
        apps_root = Path(__file__).resolve().parents[1]
        discovered: set[str] = set()

        for path in apps_root.glob("**/management/commands/*.py"):
            command_name = path.stem
            if command_name == "__init__":
                continue
            if command_name in SUITE_GUARD_IGNORED_COMMANDS:
                continue
            if command_name.startswith(SUITE_GUARD_COMMAND_PREFIXES):
                discovered.add(command_name)

        return discovered

    def _discover_guarded_workflow_tasks(self) -> set[str]:
        apps_root = Path(__file__).resolve().parents[1]
        discovered: set[str] = set()

        for path in apps_root.glob("**/tasks.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    if node.name.startswith("run_scheduled_") and node.name.endswith("_workflows"):
                        discovered.add(node.name)

        return discovered
