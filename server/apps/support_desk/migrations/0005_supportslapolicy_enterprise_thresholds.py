from django.db import migrations


class Migration(migrations.Migration):
    """
    Merge placeholder for branch compatibility.

    The actual enterprise SLA field changes are defined in:
    0005_supportslapolicy_agent_notify_threshold_percent_and_more
    """

    dependencies = [
        ("support_desk", "0005_supportslapolicy_agent_notify_threshold_percent_and_more"),
    ]

    operations = []
