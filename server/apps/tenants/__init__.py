"""Residential tenants & leasing.

This app models the people who *occupy units* — lease holders, buyers, and
their related lease agreements, payments, complaints, and inspections.

It is NOT the SaaS multi-tenancy app. Platform-level tenancy (i.e. the
customer organizations paying for DeveloperOS) is modelled by
``apps.accounts.Organization`` and enforced via ``OrganizationMiddleware``.

If you find yourself reaching for "tenant" and meaning "the customer org",
you want ``Organization``. If you mean "the person leasing unit 14B", you
want the models here.
"""
