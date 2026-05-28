from django.db import migrations

DEFAULT_ACCOUNTS = [
    ("1000", "Cash and Cash Equivalents", "asset", "current_asset"),
    ("1100", "Accounts Receivable", "asset", "current_asset"),
    ("1200", "Rent Receivable", "asset", "current_asset"),
    ("1300", "Prepaid Expenses", "asset", "current_asset"),
    ("1500", "Property & Equipment", "asset", "fixed_asset"),
    ("1510", "Land", "asset", "fixed_asset"),
    ("1520", "Buildings", "asset", "fixed_asset"),
    ("1530", "Accumulated Depreciation", "asset", "fixed_asset"),
    ("2000", "Accounts Payable", "liability", "current_liability"),
    ("2100", "Accrued Liabilities", "liability", "current_liability"),
    ("2200", "Security Deposits Held", "liability", "current_liability"),
    ("2500", "Mortgage Payable", "liability", "long_term_liability"),
    ("3000", "Owner's Equity", "equity", "owners_equity"),
    ("3100", "Retained Earnings", "equity", "retained_earnings"),
    ("4000", "Rental Income", "revenue", "operating_revenue"),
    ("4100", "Property Sales Revenue", "revenue", "operating_revenue"),
    ("4200", "Service Charges", "revenue", "operating_revenue"),
    ("4900", "Other Income", "revenue", "other_revenue"),
    ("5000", "Property Maintenance", "expense", "operating_expense"),
    ("5100", "Utilities", "expense", "operating_expense"),
    ("5200", "Insurance", "expense", "operating_expense"),
    ("5300", "Property Tax", "expense", "operating_expense"),
    ("5400", "Depreciation", "expense", "operating_expense"),
    ("5500", "Management Fees", "expense", "operating_expense"),
    ("5600", "Professional Fees", "expense", "operating_expense"),
    ("5700", "Marketing & Advertising", "expense", "operating_expense"),
    ("5800", "Administrative Expenses", "expense", "operating_expense"),
    ("5900", "Interest Expense", "expense", "other_expense"),
]


def seed_accounts(apps, schema_editor):
    Organization = apps.get_model("accounts", "Organization")
    Account = apps.get_model("finance", "Account")

    for org in Organization.objects.all():
        for code, name, account_type, sub_type in DEFAULT_ACCOUNTS:
            Account.objects.get_or_create(
                organization=org,
                code=code,
                defaults={
                    "name": name,
                    "account_type": account_type,
                    "sub_type": sub_type,
                    "is_system": True,
                    "is_active": True,
                },
            )


def unseed_accounts(apps, schema_editor):
    Account = apps.get_model("finance", "Account")
    Account.objects.filter(is_system=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("finance", "0006_account"),
    ]

    operations = [
        migrations.RunPython(seed_accounts, unseed_accounts),
    ]
