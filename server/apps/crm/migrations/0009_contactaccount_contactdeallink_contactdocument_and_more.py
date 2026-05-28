# Compatibility shim for a duplicate 0009 migration name.
#
# The Contact & Account tables are created in:
#   0009_contact_account_management
# This migration intentionally does not perform any schema operations.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("crm", "0009_contact_account_management"),
    ]

    operations = []
