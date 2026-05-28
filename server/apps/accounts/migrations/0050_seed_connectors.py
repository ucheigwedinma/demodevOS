"""Seed the Connector catalogue with a starting set of common
third-party integrations. Idempotent — safe to re-run."""

from django.db import migrations


SEED = [
    # slug, name, vendor, category, description
    ("slack", "Slack", "Slack Technologies", "communication",
     "Send notifications and approval prompts to Slack channels."),
    ("microsoft-teams", "Microsoft Teams", "Microsoft", "communication",
     "Surface platform alerts in Teams channels and DMs."),
    ("notion", "Notion", "Notion Labs", "storage",
     "Sync project pages and meeting notes to a Notion workspace."),
    ("zapier", "Zapier", "Zapier Inc.", "automation",
     "Trigger Zaps from any DeveloperOS event; consume Zap webhooks."),
    ("make", "Make (Integromat)", "Celonis", "automation",
     "Visual automation across hundreds of apps."),
    ("google-drive", "Google Drive", "Google", "storage",
     "Mirror documents and exports to a shared Drive folder."),
    ("dropbox", "Dropbox", "Dropbox Inc.", "storage",
     "Mirror documents to a Dropbox team folder."),
    ("hubspot", "HubSpot", "HubSpot", "analytics",
     "Bidirectional sync of leads and deals with HubSpot CRM."),
    ("salesforce", "Salesforce", "Salesforce", "analytics",
     "Bidirectional sync of accounts and opportunities."),
    ("stripe", "Stripe", "Stripe Inc.", "finance",
     "Bidirectional sync of invoices, payments, and customers."),
    ("github", "GitHub", "GitHub Inc.", "development",
     "Open issues from project tasks; reflect commit activity."),
    ("gitlab", "GitLab", "GitLab Inc.", "development",
     "Same as GitHub but for GitLab-hosted repositories."),
]


def seed_connectors(apps, schema_editor):
    Connector = apps.get_model("accounts", "Connector")
    for slug, name, vendor, category, description in SEED:
        Connector.objects.get_or_create(
            slug=slug,
            defaults={
                "name": name,
                "vendor": vendor,
                "category": category,
                "description": description,
                "is_available": True,
            },
        )


def unseed_connectors(apps, schema_editor):
    Connector = apps.get_model("accounts", "Connector")
    Connector.objects.filter(slug__in=[s[0] for s in SEED]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0049_connector_webhook_webhookdelivery_applicationtoken_and_more"),
    ]
    operations = [
        migrations.RunPython(seed_connectors, reverse_code=unseed_connectors),
    ]
