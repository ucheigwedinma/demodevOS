from django.core.management.base import BaseCommand

from apps.settings.seed_suites import (
    SuiteRunContext,
    build_demo_suite,
    describe_steps,
    filter_steps,
    resolve_target_organization_ids,
    run_suite,
)


class Command(BaseCommand):
    help = (
        "Run the demo seed suite, with optional core bootstrap, operational "
        "commands, and workflow runs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            dest="organization_ids",
            action="append",
            type=int,
            help="Limit organization-aware steps to the provided organization id. Repeat for multiple.",
        )
        parser.add_argument(
            "--skip-core",
            action="store_true",
            help="Skip the core non-demo setup steps and run only the demo-specific seeds.",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Re-seed demo-aware steps from a clean slate where supported.",
        )
        parser.add_argument(
            "--include-ops",
            action="store_true",
            help="Also run operational maintenance commands after seeding.",
        )
        parser.add_argument(
            "--include-workflows",
            action="store_true",
            help="Also run synchronous workflow/task automation after seeding.",
        )
        parser.add_argument(
            "--step",
            dest="steps",
            action="append",
            help="Run only a specific step key. Repeat to run multiple steps in order.",
        )
        parser.add_argument(
            "--list",
            dest="list_steps",
            action="store_true",
            help="List available step keys and exit.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would run without executing commands or workflows.",
        )
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continue running the remaining steps after a failure, but still exit non-zero at the end.",
        )

    def handle(self, *args, **options):
        steps = build_demo_suite(
            include_core=not options["skip_core"],
            include_ops=options["include_ops"],
            include_workflows=options["include_workflows"],
        )

        if options["list_steps"]:
            self.stdout.write("Available demo suite steps:")
            for line in describe_steps(steps):
                self.stdout.write(f"  {line}")
            return

        selected = filter_steps(steps, options.get("steps"))
        organization_ids = resolve_target_organization_ids(options.get("organization_ids"))
        context = SuiteRunContext(
            organization_ids=organization_ids,
            flush=options["flush"],
            dry_run=options["dry_run"],
            continue_on_error=options["continue_on_error"],
            stdout=self.stdout,
            stderr=self.stderr,
        )

        run_suite(
            suite_name="seed_demo_suite",
            steps=selected,
            context=context,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_demo_suite completed successfully ({len(selected)} step(s))."
            )
        )
