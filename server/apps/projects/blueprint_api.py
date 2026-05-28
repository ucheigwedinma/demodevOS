"""
Blueprint API — serializers and viewsets for the Project Planner.

Provides full CRUD for blueprints and their children (phases, activities,
tasks, dependencies, scenarios), plus actions for seeding from templates
and committing to create a live project.
"""

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.mixins import OrgScopedMixin
from apps.settings.permissions import HasRolePermission

from .blueprint_models import (
    BlueprintActivity,
    BlueprintDependency,
    BlueprintPhase,
    BlueprintScenario,
    BlueprintTask,
    ProjectBlueprint,
)

# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

class BlueprintTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlueprintTask
        fields = "__all__"
        read_only_fields = ("id", "activity")


class BlueprintActivitySerializer(serializers.ModelSerializer):
    tasks = BlueprintTaskSerializer(many=True, read_only=True)

    class Meta:
        model = BlueprintActivity
        fields = [
            "id", "phase", "name", "description", "sort_order",
            "wbs_code", "estimated_duration_days", "estimated_effort_hours",
            "tasks",
        ]
        read_only_fields = ("id",)


class BlueprintPhaseSerializer(serializers.ModelSerializer):
    activities = BlueprintActivitySerializer(many=True, read_only=True)

    class Meta:
        model = BlueprintPhase
        fields = [
            "id", "blueprint", "name", "description", "sort_order",
            "duration_days", "weight", "planned_budget",
            "activities",
        ]
        read_only_fields = ("id", "blueprint")


class BlueprintDependencySerializer(serializers.ModelSerializer):
    from_node_id = serializers.CharField(read_only=True)
    to_node_id = serializers.CharField(read_only=True)

    class Meta:
        model = BlueprintDependency
        fields = "__all__"
        read_only_fields = ("id",)


class BlueprintScenarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlueprintScenario
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class BlueprintListSerializer(serializers.ModelSerializer):
    phase_count = serializers.IntegerField(read_only=True)
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ProjectBlueprint
        fields = [
            "id", "name", "description", "status", "status_display",
            "source_template", "project",
            "projected_duration_days", "projected_total_cost",
            "phase_count", "created_by", "created_by_name",
            "created_at", "updated_at",
        ]

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return ""


class BlueprintDetailSerializer(serializers.ModelSerializer):
    phases = BlueprintPhaseSerializer(many=True, read_only=True)
    dependencies = BlueprintDependencySerializer(many=True, read_only=True)
    scenarios = BlueprintScenarioSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectBlueprint
        fields = "__all__"
        read_only_fields = ("id", "project", "created_by", "created_at", "updated_at")

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.email
        return ""


class BlueprintWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectBlueprint
        exclude = ("organization", "project", "created_by")


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------

class BlueprintViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Full CRUD for project blueprints."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"
    queryset = ProjectBlueprint.objects.all()
    search_fields = ["name", "description"]
    filterset_fields = ["status"]
    ordering = ["-updated_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            from django.db.models import Count
            qs = qs.annotate(phase_count=Count("phases"))
        elif self.action == "retrieve":
            qs = qs.prefetch_related(
                "phases__activities__tasks",
                "dependencies",
                "scenarios",
            )
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return BlueprintListSerializer
        if self.action in ("create", "update", "partial_update"):
            return BlueprintWriteSerializer
        return BlueprintDetailSerializer

    def perform_create(self, serializer):
        serializer.save(
            organization=self._resolve_request_org(),
            created_by=self.request.user if self.request.user.is_authenticated else None,
        )

    @action(detail=True, methods=["post"], url_path="seed-from-template")
    def seed_from_template(self, request, **_kwargs):
        """Seed this blueprint's WBS from a project template."""
        blueprint = self.get_object()
        template_id = request.data.get("template_id")
        if not template_id:
            return Response({"detail": "template_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        summary = _seed_blueprint_from_template(blueprint, template_id)
        return Response(summary)

    @action(detail=False, methods=["post"], url_path="generate-from-boq")
    def generate_from_boq(self, request, **_kwargs):
        """Route B: Auto-generate a blueprint from a single BOM."""
        bom_id = request.data.get("bom_id")
        if not bom_id:
            return Response({"detail": "bom_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        from apps.inventory.models import BillOfMaterials
        try:
            bom = BillOfMaterials.objects.get(pk=bom_id, organization=self._resolve_request_org())
        except BillOfMaterials.DoesNotExist:
            return Response({"detail": "BOM not found."}, status=status.HTTP_404_NOT_FOUND)

        from apps.inventory.boq_planning_engine import generate_blueprint_from_boq
        try:
            blueprint, summary = generate_blueprint_from_boq(bom, user=request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "blueprint_id": blueprint.id,
            "blueprint_name": blueprint.name,
            **summary,
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="merge-from-boqs")
    def merge_from_boqs(self, request, **_kwargs):
        """13C: Merge multiple BOMs (Structural + MEP + Architectural) into one blueprint."""
        org = self._resolve_request_org()

        # Check org setting
        from apps.settings.models import ProjectGovernanceSettings
        governance = ProjectGovernanceSettings.objects.filter(organization=org).first()
        if not governance or not governance.allow_multi_boq_merge:
            return Response(
                {"detail": "Multi-BOQ merge is not enabled for this organization. Enable it in Project Settings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        bom_ids = request.data.get("bom_ids", [])
        blueprint_name = request.data.get("name", "").strip()
        if not bom_ids or len(bom_ids) < 2:
            return Response({"detail": "At least 2 bom_ids are required."}, status=status.HTTP_400_BAD_REQUEST)

        from apps.inventory.models import BillOfMaterials
        boms = list(BillOfMaterials.objects.filter(pk__in=bom_ids, organization=org))
        if len(boms) != len(bom_ids):
            return Response({"detail": "One or more BOMs not found."}, status=status.HTTP_404_NOT_FOUND)

        from apps.inventory.boq_planning_engine import generate_blueprint_from_boq
        from .blueprint_models import BlueprintPhase

        # Generate from first BOM as the base
        try:
            blueprint, total_summary = generate_blueprint_from_boq(boms[0], user=request.user)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # Merge remaining BOMs into the same blueprint
        for bom in boms[1:]:
            try:
                temp_bp, summary = generate_blueprint_from_boq(bom, user=request.user)
                # Move phases from temp blueprint to the main one
                max_sort = BlueprintPhase.objects.filter(blueprint=blueprint).count()
                for phase in BlueprintPhase.objects.filter(blueprint=temp_bp):
                    phase.blueprint = blueprint
                    phase.sort_order = max_sort
                    max_sort += 1
                    phase.save(update_fields=["blueprint", "sort_order"])
                temp_bp.delete()

                # Accumulate summary
                for key in ["phases_created", "activities_created", "tasks_created", "dependencies_created", "items_processed"]:
                    total_summary[key] = total_summary.get(key, 0) + summary.get(key, 0)
                total_summary.setdefault("unmapped_categories", []).extend(summary.get("unmapped_categories", []))
            except Exception:
                pass  # Skip failing BOMs, continue with others

        # Update blueprint name
        if blueprint_name:
            blueprint.name = blueprint_name
        else:
            bom_names = ", ".join(b.name for b in boms)
            blueprint.name = f"Merged Plan — {bom_names[:80]}"
        blueprint.description = f"Auto-merged from {len(boms)} BOMs: {', '.join(b.bom_number for b in boms)}."
        blueprint.save(update_fields=["name", "description"])

        return Response({
            "blueprint_id": blueprint.id,
            "blueprint_name": blueprint.name,
            "boms_merged": len(boms),
            **total_summary,
        }, status=status.HTTP_201_CREATED)

        return Response({
            "blueprint_id": blueprint.id,
            "blueprint_name": blueprint.name,
            **summary,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="save-as-template")
    def save_as_template(self, request, **_kwargs):
        """Save the blueprint's WBS structure as a reusable project template."""
        blueprint = self.get_object()
        name = request.data.get("name", "").strip()
        template_type = request.data.get("template_type", "residential")
        if not name:
            return Response(
                {"detail": "name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.settings.models import (
            ProjectTemplate,
            TemplateActivity,
            TemplatePhase,
            TaskTemplate,
        )

        org = self._resolve_request_org()

        if ProjectTemplate.objects.filter(organization=org, name=name).exists():
            return Response(
                {"detail": f'A template named "{name}" already exists.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template = ProjectTemplate.objects.create(
            organization=org,
            name=name,
            template_type=template_type,
            description=blueprint.description,
            is_active=True,
            is_system=False,
        )

        for bp_phase in blueprint.phases.order_by("sort_order"):
            phase = TemplatePhase.objects.create(
                template=template,
                name=bp_phase.name,
                description=bp_phase.description,
                sort_order=bp_phase.sort_order,
                duration_days=bp_phase.duration_days,
                weight=bp_phase.weight,
            )
            for bp_activity in bp_phase.activities.order_by("sort_order"):
                activity = TemplateActivity.objects.create(
                    phase=phase,
                    name=bp_activity.name,
                    description=bp_activity.description,
                    sort_order=bp_activity.sort_order,
                    wbs_code=bp_activity.wbs_code,
                    estimated_duration_days=bp_activity.estimated_duration_days,
                    estimated_effort_hours=bp_activity.estimated_effort_hours,
                )
                for bp_task in bp_activity.tasks.order_by("sort_order"):
                    # Ensure unique task name
                    task_name = bp_task.name
                    if TaskTemplate.objects.filter(name=task_name).exists():
                        task_name = f"{task_name} ({template.name})"
                    TaskTemplate.objects.create(
                        activity=activity,
                        name=task_name,
                        description=bp_task.description,
                        sort_order=bp_task.sort_order,
                        reference_code=bp_task.reference_code,
                        assigned_role=bp_task.assigned_role,
                        priority=bp_task.priority,
                        estimated_effort_hours=bp_task.estimated_effort_hours,
                        standard_duration_hours=bp_task.standard_duration_hours,
                        crew_size=bp_task.crew_size,
                    )

        return Response({
            "template_id": template.id,
            "name": template.name,
            "phases": blueprint.phases.count(),
            "activities": sum(
                p.activities.count() for p in blueprint.phases.all()
            ),
        })

    @action(detail=True, methods=["post"], url_path="commit")
    def commit(self, request, **_kwargs):
        """Commit the blueprint and create a live project from it."""
        blueprint = self.get_object()
        if blueprint.status == ProjectBlueprint.Status.COMMITTED:
            return Response({"detail": "Blueprint is already committed."}, status=status.HTTP_400_BAD_REQUEST)

        from .template_instantiation import instantiate_project_from_blueprint

        result = instantiate_project_from_blueprint(blueprint, request.user)
        return Response(result)


class BlueprintPhaseViewSet(viewsets.ModelViewSet):
    """CRUD for phases within a blueprint."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"

    def get_queryset(self):
        return BlueprintPhase.objects.filter(
            blueprint_id=self.kwargs.get("blueprint_pk"),
        ).prefetch_related("activities__tasks").order_by("sort_order")

    def get_serializer_class(self):
        return BlueprintPhaseSerializer

    def perform_create(self, serializer):
        serializer.save(blueprint_id=self.kwargs["blueprint_pk"])


class BlueprintActivityViewSet(viewsets.ModelViewSet):
    """CRUD for activities within a blueprint phase."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"

    def get_queryset(self):
        return BlueprintActivity.objects.filter(
            phase_id=self.kwargs.get("phase_pk"),
        ).prefetch_related("tasks").order_by("sort_order")

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            class WriteSerializer(serializers.ModelSerializer):
                class Meta:
                    model = BlueprintActivity
                    fields = ["name", "description", "sort_order", "wbs_code", "estimated_duration_days", "estimated_effort_hours"]
            return WriteSerializer
        return BlueprintActivitySerializer

    def perform_create(self, serializer):
        serializer.save(phase_id=self.kwargs["phase_pk"])


class BlueprintTaskViewSet(viewsets.ModelViewSet):
    """CRUD for tasks within a blueprint activity."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"

    def get_queryset(self):
        return BlueprintTask.objects.filter(
            activity_id=self.kwargs.get("activity_pk"),
        ).order_by("sort_order")

    def get_serializer_class(self):
        return BlueprintTaskSerializer

    def perform_create(self, serializer):
        serializer.save(activity_id=self.kwargs["activity_pk"])


class BlueprintDependencyViewSet(viewsets.ModelViewSet):
    """CRUD for dependencies within a blueprint."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"

    def get_queryset(self):
        return BlueprintDependency.objects.filter(
            blueprint_id=self.kwargs.get("blueprint_pk"),
        ).select_related("from_activity", "from_task", "to_activity", "to_task")

    def get_serializer_class(self):
        return BlueprintDependencySerializer

    def perform_create(self, serializer):
        serializer.save(blueprint_id=self.kwargs["blueprint_pk"])


class BlueprintScenarioViewSet(viewsets.ModelViewSet):
    """CRUD for scenarios within a blueprint."""

    permission_classes = [IsAuthenticated, HasRolePermission]
    rbac_sub_module = "projects.projects"

    def get_queryset(self):
        return BlueprintScenario.objects.filter(
            blueprint_id=self.kwargs.get("blueprint_pk"),
        ).order_by("-is_baseline", "-created_at")

    def get_serializer_class(self):
        return BlueprintScenarioSerializer

    def perform_create(self, serializer):
        serializer.save(blueprint_id=self.kwargs["blueprint_pk"])

    @action(detail=True, methods=["post"], url_path="commit-baseline")
    def commit_baseline(self, _request, **kwargs):
        scenario = self.get_object()
        blueprint_pk = kwargs.get("blueprint_pk") or self.kwargs.get("blueprint_pk")
        BlueprintScenario.objects.filter(
            blueprint_id=blueprint_pk, is_baseline=True,
        ).exclude(pk=scenario.pk).update(is_baseline=False)
        scenario.is_baseline = True
        scenario.save(update_fields=["is_baseline", "updated_at"])
        return Response({"detail": f"'{scenario.name}' is now the baseline."})


# ---------------------------------------------------------------------------
# Seed from template
# ---------------------------------------------------------------------------

def _seed_blueprint_from_template(blueprint, template_id):
    """Copy template structure into a blueprint."""
    from apps.settings.models import ProjectTemplate

    template = ProjectTemplate.objects.prefetch_related(
        "phases__activities__task_templates",
        "phases__milestones",
        "dependencies",
    ).get(pk=template_id)

    blueprint.source_template = template
    blueprint.save(update_fields=["source_template", "updated_at"])

    # Clear existing data
    blueprint.phases.all().delete()
    blueprint.dependencies.all().delete()

    activity_map = {}  # template_activity_id → BlueprintActivity

    for tmpl_phase in template.phases.order_by("sort_order"):
        phase = BlueprintPhase.objects.create(
            blueprint=blueprint,
            name=tmpl_phase.name,
            description=tmpl_phase.description,
            sort_order=tmpl_phase.sort_order,
            duration_days=tmpl_phase.duration_days,
            weight=tmpl_phase.weight,
        )

        for tmpl_act in tmpl_phase.activities.order_by("sort_order"):
            activity = BlueprintActivity.objects.create(
                phase=phase,
                name=tmpl_act.name,
                description=tmpl_act.description,
                sort_order=tmpl_act.sort_order,
                wbs_code=tmpl_act.wbs_code,
                estimated_duration_days=tmpl_act.estimated_duration_days,
                estimated_effort_hours=tmpl_act.estimated_effort_hours,
            )
            activity_map[tmpl_act.id] = activity

            for tmpl_task in tmpl_act.task_templates.order_by("sort_order"):
                BlueprintTask.objects.create(
                    activity=activity,
                    name=tmpl_task.name,
                    description=tmpl_task.description,
                    sort_order=tmpl_task.sort_order,
                    reference_code=tmpl_task.reference_code,
                    assigned_role=tmpl_task.assigned_role,
                    priority=tmpl_task.priority,
                    standard_duration_hours=getattr(tmpl_task, "standard_duration_hours", None),
                    estimated_effort_hours=tmpl_task.estimated_effort_hours,
                    crew_size=getattr(tmpl_task, "crew_size", None),
                    estimated_labor_cost=getattr(tmpl_task, "estimated_labor_cost", None),
                    output_unit=getattr(tmpl_task, "output_unit", ""),
                    equipment_type=getattr(tmpl_task, "equipment_type", ""),
                    category=getattr(tmpl_task, "category", ""),
                    is_milestone=getattr(tmpl_task, "is_milestone", False),
                    complexity=getattr(tmpl_task, "complexity", "medium"),
                    required_materials=getattr(tmpl_task, "required_materials", []),
                    required_ppe=getattr(tmpl_task, "required_ppe", []),
                    quality_gates=getattr(tmpl_task, "quality_gates", []),
                    photo_requirements=getattr(tmpl_task, "photo_requirements", []),
                    sop_markdown=getattr(tmpl_task, "sop_markdown", ""),
                    source_task_template=tmpl_task,
                )

    # Copy dependencies
    for tmpl_dep in template.dependencies.all():
        from_act = activity_map.get(tmpl_dep.from_activity_id) if tmpl_dep.from_activity_id else None
        to_act = activity_map.get(tmpl_dep.to_activity_id) if tmpl_dep.to_activity_id else None
        if from_act and to_act:
            BlueprintDependency.objects.create(
                blueprint=blueprint,
                from_activity=from_act,
                to_activity=to_act,
                dependency_type=tmpl_dep.dependency_type,
                lag_hours=tmpl_dep.lag_hours,
                strength=tmpl_dep.strength,
                risk_impact=tmpl_dep.risk_impact,
                notes=tmpl_dep.notes,
            )

    # Copy schedule settings if available
    try:
        from apps.settings.models import TemplateScheduleSettings
        sched = TemplateScheduleSettings.objects.filter(template=template).first()
        if sched:
            for field in ["work_days", "shift_start", "shift_end", "hours_per_day",
                         "public_holidays", "custom_holidays", "rainy_season_buffer_enabled",
                         "rainy_season_buffer_pct", "rainy_season_months", "outdoor_task_categories",
                         "duration_scalar_pct", "resource_roles", "travel_buffer_hours"]:
                setattr(blueprint, field, getattr(sched, field))
            blueprint.save()
    except Exception:
        pass

    phase_count = blueprint.phases.count()
    return {
        "seeded": True,
        "phases": phase_count,
        "activities": BlueprintActivity.objects.filter(phase__blueprint=blueprint).count(),
        "tasks": BlueprintTask.objects.filter(activity__phase__blueprint=blueprint).count(),
        "dependencies": blueprint.dependencies.count(),
    }
