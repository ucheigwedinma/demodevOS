from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("settings", "0070_templateactivity_tasktemplate_activity"),
    ]

    operations = [
        migrations.AddField(model_name="tasktemplate", name="standard_duration_hours", field=models.DecimalField(blank=True, decimal_places=1, help_text="Standard duration in hours.", max_digits=7, null=True)),
        migrations.AddField(model_name="tasktemplate", name="complexity", field=models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], default="medium", max_length=10)),
        migrations.AddField(model_name="tasktemplate", name="category", field=models.CharField(blank=True, help_text="Task category: electrical, civil, logistics, legal_permits, mechanical, finishing, etc.", max_length=50)),
        migrations.AddField(model_name="tasktemplate", name="crew_size", field=models.PositiveIntegerField(blank=True, help_text="Recommended crew size.", null=True)),
        migrations.AddField(model_name="tasktemplate", name="estimated_labor_cost", field=models.DecimalField(blank=True, decimal_places=2, help_text="Base labor cost estimate.", max_digits=12, null=True)),
        migrations.AddField(model_name="tasktemplate", name="output_unit", field=models.CharField(blank=True, help_text="Unit of measure for progress: m², m³, linear m, units, kg.", max_length=50)),
        migrations.AddField(model_name="tasktemplate", name="equipment_type", field=models.CharField(blank=True, help_text="Required equipment types, comma-separated.", max_length=255)),
        migrations.AddField(model_name="tasktemplate", name="is_milestone", field=models.BooleanField(default=False, help_text="Mark as a project milestone checkpoint.")),
        migrations.AddField(model_name="tasktemplate", name="status", field=models.CharField(choices=[("draft", "Draft"), ("active", "Active"), ("archived", "Archived")], default="active", max_length=10)),
        migrations.AddField(model_name="tasktemplate", name="required_materials", field=models.JSONField(blank=True, default=list, help_text='[{"item","quantity","unit","essential"}]')),
        migrations.AddField(model_name="tasktemplate", name="required_ppe", field=models.JSONField(blank=True, default=list, help_text='["Hard Hat","Insulated Gloves",...]')),
        migrations.AddField(model_name="tasktemplate", name="quality_gates", field=models.JSONField(blank=True, default=list, help_text='[{"check","is_required"}]')),
        migrations.AddField(model_name="tasktemplate", name="photo_requirements", field=models.JSONField(blank=True, default=list, help_text='[{"description","is_mandatory"}]')),
        migrations.AddField(model_name="tasktemplate", name="sop_markdown", field=models.TextField(blank=True, help_text="Markdown-supported standard operating procedure.")),
    ]
