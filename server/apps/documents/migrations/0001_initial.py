from django.db import migrations, models


def seed_phase_one_data(apps, schema_editor):
    DocumentGovernanceCharter = apps.get_model("documents", "DocumentGovernanceCharter")
    DocumentDomain = apps.get_model("documents", "DocumentDomain")
    ControlledVocabularyTerm = apps.get_model("documents", "ControlledVocabularyTerm")

    DocumentGovernanceCharter.objects.get_or_create(
        title="Document Governance Charter",
        version="v1.0",
        defaults={
            "status": "active",
            "purpose": (
                "Establish governance baseline for a centralized document repository "
                "covering land acquisition, development, sales, and handover workflows."
            ),
            "repository_scope": "formal_only",
            "external_portal_access": "read_only",
            "includes_digital_signature_v1": False,
            "scope_notes": (
                "Phase 1 scope controls formal records only. Site photos remain in project "
                "evidence stores until future governance expansion."
            ),
            "approved_by": "Document Governance Working Group",
        },
    )

    domain_rows = [
        (
            "land_title",
            "Land & Title",
            "Core records that prove ownership, interests, and encumbrances.",
            1,
        ),
        (
            "regulatory_statutory",
            "Regulatory & Statutory",
            "Approvals, permits, and statutory submissions required by regulators.",
            2,
        ),
        (
            "design_engineering",
            "Design & Engineering",
            "Design packages, calculations, revisions, and issue-for-construction artifacts.",
            3,
        ),
        (
            "construction_vendor",
            "Construction & Vendor",
            "Commercial and execution documents governing contractor and supplier work.",
            4,
        ),
        (
            "sales_client",
            "Sales & Client",
            "Sales contracts, customer-facing commitments, and handover records.",
            5,
        ),
        (
            "finance_commercial",
            "Finance & Commercial",
            "Financial and commercial records that support audit, payment, and due diligence.",
            6,
        ),
    ]

    domain_map = {}
    for code, name, description, sort_order in domain_rows:
        domain, _ = DocumentDomain.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "description": description,
                "sort_order": sort_order,
                "is_active": True,
            },
        )
        domain_map[code] = domain

    vocabulary_rows = [
        (
            "land_title",
            "Deed of Assignment",
            "deed_of_assignment",
            "Transfer instrument assigning legal interest in land.",
            "Upload signed and stamped executed copy as controlled master.",
            "Assignment Deed",
            True,
            1,
        ),
        (
            "land_title",
            "Certificate of Occupancy",
            "certificate_of_occupancy",
            "Government-issued title certificate confirming rights of occupancy.",
            "Track issuance date and linked parcel identifier.",
            "C of O",
            True,
            2,
        ),
        (
            "land_title",
            "Survey Plan",
            "survey_plan",
            "Licensed survey defining coordinates and physical boundaries.",
            "Store signed PDF plus source CAD where available.",
            "Survey",
            True,
            3,
        ),
        (
            "regulatory_statutory",
            "Development Permit",
            "development_permit",
            "Authority approval granting permission to commence development.",
            "Capture permit number, issuing authority, and expiry date.",
            "Building Approval",
            True,
            1,
        ),
        (
            "regulatory_statutory",
            "Environmental Impact Approval",
            "environmental_impact_approval",
            "Regulatory clearance for environmental impact obligations.",
            "Attach submission pack and final determination letter.",
            "EIA Approval",
            False,
            2,
        ),
        (
            "regulatory_statutory",
            "Compliance Certificate",
            "compliance_certificate",
            "Evidence that statutory or code compliance requirements were met.",
            "Document validity dates and inspection references.",
            "Statutory Certificate",
            False,
            3,
        ),
        (
            "design_engineering",
            "Issue for Construction Drawing",
            "ifc_drawing",
            "Approved drawing set released for construction execution.",
            "Maintain revision history and superseded versions.",
            "IFC Drawing",
            True,
            1,
        ),
        (
            "design_engineering",
            "As-Built Drawing",
            "as_built_drawing",
            "Final drawing reflecting actual built conditions.",
            "Link to completion milestone and handover package.",
            "Record Drawing",
            False,
            2,
        ),
        (
            "design_engineering",
            "Design Revision",
            "design_revision",
            "Formal change to previously issued design documents.",
            "Reference prior revision and approval authority.",
            "Revision Notice",
            True,
            3,
        ),
        (
            "construction_vendor",
            "Contract Agreement",
            "contract_agreement",
            "Executed agreement defining scope, timelines, and obligations.",
            "Use signed final version as authoritative contract record.",
            "Works Contract",
            True,
            1,
        ),
        (
            "construction_vendor",
            "Variation Order",
            "variation_order",
            "Approved scope or value change against baseline contract.",
            "Include pricing rationale and impacted milestones.",
            "Change Order",
            False,
            2,
        ),
        (
            "construction_vendor",
            "Material Approval",
            "material_approval",
            "Approval record for submitted materials and specifications.",
            "Attach submittal, technical review, and final decision.",
            "Submittal Approval",
            False,
            3,
        ),
        (
            "sales_client",
            "Offer Letter",
            "offer_letter",
            "Commercial offer issued to prospective buyer.",
            "Track validity window and pricing assumptions.",
            "Sales Offer",
            True,
            1,
        ),
        (
            "sales_client",
            "Sales Agreement",
            "sales_agreement",
            "Binding purchase agreement with buyer and transaction terms.",
            "Control approved template and capture executed final copy.",
            "SPA",
            True,
            2,
        ),
        (
            "sales_client",
            "Handover Pack",
            "handover_pack",
            "Bundle of documents delivered at possession handover.",
            "Include snag closeout, warranties, and utility records.",
            "Closeout Pack",
            False,
            3,
        ),
        (
            "finance_commercial",
            "Payment Certificate",
            "payment_certificate",
            "Certified valuation authorizing stage payment.",
            "Reference related contract, milestone, and valuation period.",
            "Interim Certificate",
            True,
            1,
        ),
        (
            "finance_commercial",
            "Invoice",
            "invoice",
            "Commercial invoice requesting payment for goods or services.",
            "Store tax-compliant final issued version.",
            "Tax Invoice",
            True,
            2,
        ),
        (
            "finance_commercial",
            "Tax Clearance",
            "tax_clearance",
            "Official confirmation of fulfilled tax obligations.",
            "Track validity date and issuing authority.",
            "Tax Certificate",
            False,
            3,
        ),
    ]

    for (
        domain_code,
        term,
        term_key,
        definition,
        usage_guidance,
        synonyms,
        is_required,
        sort_order,
    ) in vocabulary_rows:
        ControlledVocabularyTerm.objects.update_or_create(
            domain=domain_map[domain_code],
            term_key=term_key,
            defaults={
                "term": term,
                "definition": definition,
                "usage_guidance": usage_guidance,
                "synonyms": synonyms,
                "status": "active",
                "is_required": is_required,
                "sort_order": sort_order,
            },
        )


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DocumentDomain",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "code",
                    models.CharField(
                        choices=[
                            ("land_title", "Land & Title"),
                            ("regulatory_statutory", "Regulatory & Statutory"),
                            ("design_engineering", "Design & Engineering"),
                            ("construction_vendor", "Construction & Vendor"),
                            ("sales_client", "Sales & Client"),
                            ("finance_commercial", "Finance & Commercial"),
                        ],
                        max_length=40,
                        unique=True,
                    ),
                ),
                ("name", models.CharField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="DocumentGovernanceCharter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(default="Document Governance Charter", max_length=255)),
                ("version", models.CharField(default="v1.0", max_length=30)),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Draft"), ("active", "Active"), ("superseded", "Superseded")],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("purpose", models.TextField(blank=True)),
                (
                    "repository_scope",
                    models.CharField(
                        choices=[
                            ("formal_only", "Formal Documents Only"),
                            ("formal_and_site_photos", "Formal Documents + Site Photos"),
                        ],
                        default="formal_only",
                        help_text="Defines whether site photos are governed in this repository.",
                        max_length=40,
                    ),
                ),
                (
                    "external_portal_access",
                    models.CharField(
                        choices=[
                            ("not_included", "Not Included"),
                            ("read_only", "Read-Only External Access"),
                            ("collaboration", "External Collaboration"),
                        ],
                        default="not_included",
                        help_text="Defines if external parties can access repository records in v1.",
                        max_length=20,
                    ),
                ),
                (
                    "includes_digital_signature_v1",
                    models.BooleanField(
                        default=False,
                        help_text="Whether digital signature is in Phase 1 scope.",
                    ),
                ),
                ("scope_notes", models.TextField(blank=True)),
                ("approved_by", models.CharField(blank=True, max_length=255)),
                ("approved_at", models.DateField(blank=True, null=True)),
                ("review_due_at", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-updated_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="ControlledVocabularyTerm",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("term", models.CharField(max_length=120)),
                (
                    "term_key",
                    models.SlugField(
                        help_text="Machine-readable key used in metadata mappings and automations.",
                        max_length=120,
                    ),
                ),
                ("definition", models.TextField()),
                ("usage_guidance", models.TextField(blank=True)),
                ("synonyms", models.CharField(blank=True, max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("deprecated", "Deprecated")],
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "is_required",
                    models.BooleanField(
                        default=False,
                        help_text="Required terms should be enforced in document metadata validation.",
                    ),
                ),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "domain",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="vocabulary_terms", to="documents.documentdomain"),
                ),
            ],
            options={
                "ordering": ["domain__sort_order", "sort_order", "term"],
            },
        ),
        migrations.AddConstraint(
            model_name="controlledvocabularyterm",
            constraint=models.UniqueConstraint(fields=("domain", "term"), name="documents_unique_domain_term"),
        ),
        migrations.AddConstraint(
            model_name="controlledvocabularyterm",
            constraint=models.UniqueConstraint(fields=("domain", "term_key"), name="documents_unique_domain_term_key"),
        ),
        migrations.RunPython(seed_phase_one_data, migrations.RunPython.noop),
    ]
