from collections import defaultdict
import re

from django.db import migrations, models


DOC_TYPE_CATEGORY_MAP = {
    "deed_of_assignment": "LND",
    "certificate_of_occupancy": "LND",
    "survey_plan": "LND",
    "development_permit": "REG",
    "environmental_impact_approval": "REG",
    "compliance_certificate": "REG",
    "ifc_drawing": "DES",
    "as_built_drawing": "DES",
    "design_revision": "DES",
    "contract_agreement": "CON",
    "variation_order": "CON",
    "material_approval": "CON",
    "offer_letter": "SAL",
    "sales_agreement": "SAL",
    "handover_pack": "SAL",
    "payment_certificate": "FIN",
    "invoice": "FIN",
    "tax_clearance": "FIN",
    "other": "GEN",
}

WORKFLOW_PHASE_NUMBERING_MAP = {
    "land_acquisition": "PH1",
    "design_approvals": "PH2",
    "construction": "PH3",
    "sales_leasing": "PH4",
    "handover_closeout": "PH5",
}


def _normalize_segment(raw, default):
    segment = re.sub(r"[^A-Z0-9]", "", (raw or "").upper())
    if not segment:
        return default
    return segment[:10]


def _project_segment(project_code, project_name):
    if project_code:
        return _normalize_segment(project_code, "GEN")
    if project_name:
        tokens = re.findall(r"[A-Za-z0-9]+", project_name.upper())
        if tokens:
            primary = tokens[0]
            if len(primary) >= 3:
                return primary[:3]
            return primary.ljust(3, "X")
    return "GEN"


def _build_document_number(project_segment, phase_segment, category_segment, sequence_number, revision_number):
    return f"{project_segment}-{phase_segment}-{category_segment}-{sequence_number:03d}-R{revision_number}"


def backfill_phase3_numbering(apps, schema_editor):
    DocumentType = apps.get_model("documents", "DocumentType")
    DocumentWorkflowPhase = apps.get_model("documents", "DocumentWorkflowPhase")
    Document = apps.get_model("documents", "Document")
    DocumentVersion = apps.get_model("documents", "DocumentVersion")

    for code, category_code in DOC_TYPE_CATEGORY_MAP.items():
        DocumentType.objects.filter(code=code).update(category_code=category_code)

    for code, numbering_code in WORKFLOW_PHASE_NUMBERING_MAP.items():
        DocumentWorkflowPhase.objects.filter(code=code).update(numbering_code=numbering_code)

    used_numbers = set()
    scope_counter = defaultdict(int)

    for document in (
        Document.objects
        .select_related("project", "phase", "document_type", "current_version")
        .order_by("id")
    ):
        project_name = document.project.name if document.project_id else ""
        project_segment = _project_segment(document.project_code, project_name)
        phase_segment = _normalize_segment(getattr(document.phase, "numbering_code", ""), "PH0")
        category_segment = _normalize_segment(getattr(document.document_type, "category_code", ""), "GEN")

        scope = (project_segment, phase_segment, category_segment)
        existing_seq = document.sequence_number if document.sequence_number and document.sequence_number > 0 else 0
        sequence_number = max(existing_seq, scope_counter[scope] + 1)

        revision_number = document.revision_number if document.revision_number is not None else 0
        if document.current_version_id:
            current_major = document.current_version.version_major
            revision_number = max(revision_number, current_major)
        elif revision_number == 0:
            latest_version = (
                DocumentVersion.objects
                .filter(document_id=document.id)
                .order_by("-version_major", "-version_minor", "-uploaded_at")
                .first()
            )
            if latest_version:
                revision_number = latest_version.version_major

        candidate = _build_document_number(
            project_segment=project_segment,
            phase_segment=phase_segment,
            category_segment=category_segment,
            sequence_number=sequence_number,
            revision_number=revision_number,
        )
        while candidate in used_numbers:
            sequence_number += 1
            candidate = _build_document_number(
                project_segment=project_segment,
                phase_segment=phase_segment,
                category_segment=category_segment,
                sequence_number=sequence_number,
                revision_number=revision_number,
            )

        scope_counter[scope] = sequence_number
        used_numbers.add(candidate)

        Document.objects.filter(id=document.id).update(
            project_code=project_segment,
            sequence_number=sequence_number,
            revision_number=revision_number,
            document_number=candidate,
        )


def noop_reverse(apps, schema_editor):
    # Intentionally no-op: numbering standard is forward-only.
    return


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0002_phase2_document_control_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="project_code",
            field=models.CharField(blank=True, help_text="Optional project numbering segment override (e.g., LUA).", max_length=10),
        ),
        migrations.AddField(
            model_name="document",
            name="revision_number",
            field=models.PositiveIntegerField(default=0, help_text="Current revision number represented as Rn."),
        ),
        migrations.AddField(
            model_name="document",
            name="sequence_number",
            field=models.PositiveIntegerField(default=0, help_text="Sequential number for PROJECT-PHASE-CATEGORY scope."),
        ),
        migrations.AddField(
            model_name="documenttype",
            name="category_code",
            field=models.CharField(default="GEN", help_text="Numbering category segment (e.g., REG, DES, CON).", max_length=10),
        ),
        migrations.AddField(
            model_name="documentworkflowphase",
            name="numbering_code",
            field=models.CharField(default="PH0", help_text="Numbering phase segment (e.g., PH1, PH2).", max_length=10),
        ),
        migrations.RunPython(backfill_phase3_numbering, noop_reverse),
    ]
