"""
Platform operations API — allows superusers to trigger management commands
from the console UI instead of SSH-ing into the server.
"""

import io

from django.core.management import call_command
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Whitelist of allowed management commands (prevents arbitrary code execution).
ALLOWED_COMMANDS = {
    "seed_demo_suite": "Seed the full demo suite",
    "seed_platform_editions": "Seed platform tier definitions",
    "seed_platform_suite": "Seed the platform/core suite with optional operations",
    "seed_platform_governance": "Seed event keys, email templates, workflows, access policies",
    "seed_rbac": "Seed default RBAC roles",
    "seed_master_data": "Seed master data entries",
    "seed_feature_flags": "Seed feature flag definitions",
    "seed_metrics_contract": "Seed KPI metric definitions",
    "seed_access_scopes": "Seed data scope definitions",
    "seed_access_policies": "Seed access control policies",
    "seed_risk_mitigation_rules": "Seed risk mitigation rules",
    "seed_status_badges": "Seed status badge definitions",
    "seed_project_templates": "Seed project templates",
    "dispatch_scheduled_reports": "Dispatch due scheduled reports",
}


class RunOperationView(APIView):
    """POST /api/platform/operations/run/  — trigger a management command by key."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_superuser:
            return Response(
                {"status": "error", "detail": "Superuser access required."},
                status=status.HTTP_403_FORBIDDEN,
            )

        command = request.data.get("command", "")
        if command not in ALLOWED_COMMANDS:
            return Response(
                {"status": "error", "detail": f"Unknown or disallowed command: {command}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            out = io.StringIO()
            call_command(command, stdout=out, stderr=out)
            output = out.getvalue()
            return Response({"status": "ok", "output": output or "Completed successfully."})
        except Exception as exc:
            return Response(
                {"status": "error", "detail": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
