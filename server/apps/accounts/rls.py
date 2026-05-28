from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from django.db import DEFAULT_DB_ALIAS, connections
from django.utils.connection import ConnectionDoesNotExist

RLS_ORG_SETTING = "app.current_organization_id"
RLS_BYPASS_SETTING = "app.bypass_rls"
RLS_POLICY_NAME = "org_tenant_isolation"

_ORG_TABLE_DISCOVERY_SQL = """
SELECT DISTINCT
    n.nspname AS schema_name,
    c.relname AS table_name
FROM pg_constraint con
JOIN pg_class c
    ON c.oid = con.conrelid
JOIN pg_namespace n
    ON n.oid = c.relnamespace
JOIN pg_class cref
    ON cref.oid = con.confrelid
JOIN pg_namespace nref
    ON nref.oid = cref.relnamespace
JOIN pg_attribute a
    ON a.attrelid = con.conrelid
   AND a.attnum = ANY(con.conkey)
WHERE con.contype = 'f'
  AND c.relkind IN ('r', 'p')
  AND a.attname = 'organization_id'
  AND n.nspname = 'public'
  AND nref.nspname = 'public'
  AND cref.relname = 'accounts_organization'
ORDER BY n.nspname, c.relname
"""


def _is_postgres(using: str = DEFAULT_DB_ALIAS) -> bool:
    try:
        return connections[using].vendor == "postgresql"
    except ConnectionDoesNotExist:
        return False


def set_rls_context(
    organization_id: int | None,
    *,
    bypass: bool,
    using: str = DEFAULT_DB_ALIAS,
) -> None:
    """Set PostgreSQL session vars used by tenant RLS policies."""
    if not _is_postgres(using):
        return
    org_value = "" if organization_id is None else str(organization_id)
    bypass_value = "on" if bypass else "off"
    connection = connections[using]
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [RLS_ORG_SETTING, org_value],
        )
        cursor.execute(
            "SELECT set_config(%s, %s, false)",
            [RLS_BYPASS_SETTING, bypass_value],
        )


def reset_rls_context(
    *,
    using: str = DEFAULT_DB_ALIAS,
    bypass: bool = True,
) -> None:
    """
    Reset RLS context for a connection.

    Defaulting bypass to True keeps management commands and background workers
    functional unless they opt into strict tenant context explicitly.
    """
    set_rls_context(None, bypass=bypass, using=using)


@contextmanager
def rls_context(
    organization_id: int | None,
    *,
    bypass: bool,
    using: str = DEFAULT_DB_ALIAS,
):
    """
    Apply RLS session context for a block and reset afterwards.

    Useful for Celery tasks and management commands.
    """
    set_rls_context(organization_id, bypass=bypass, using=using)
    try:
        yield
    finally:
        reset_rls_context(using=using, bypass=True)


def iter_organization_ids(*, using: str = DEFAULT_DB_ALIAS) -> Iterator[int]:
    """
    Yield organization ids for background fan-out processing.

    Uses ORM so callers can share this in tasks/commands without raw SQL.
    """
    from apps.accounts.models import Organization

    queryset = Organization.objects.using(using).order_by("id").values_list("id", flat=True)
    yield from queryset.iterator()


def discover_org_scoped_tables(using: str = DEFAULT_DB_ALIAS) -> list[tuple[str, str]]:
    """Return (schema, table) pairs that carry organization foreign keys."""
    if not _is_postgres(using):
        return []
    connection = connections[using]
    with connection.cursor() as cursor:
        cursor.execute(_ORG_TABLE_DISCOVERY_SQL)
        return [(row[0], row[1]) for row in cursor.fetchall()]


def sync_org_rls_policies(using: str = DEFAULT_DB_ALIAS) -> int:
    """Enable FORCE RLS and upsert the org-isolation policy on org-scoped tables."""
    if not _is_postgres(using):
        return 0
    connection = connections[using]
    quote = connection.ops.quote_name
    org_guard = (
        "("
        f"COALESCE(current_setting('{RLS_BYPASS_SETTING}', true), 'off') IN ('on','true','1')"
        " OR organization_id IS NULL"
        f" OR organization_id = NULLIF(current_setting('{RLS_ORG_SETTING}', true), '')::bigint"
        ")"
    )
    tables = discover_org_scoped_tables(using=using)
    with connection.cursor() as cursor:
        for schema_name, table_name in tables:
            qualified_table = f"{quote(schema_name)}.{quote(table_name)}"
            policy_name = quote(RLS_POLICY_NAME)
            cursor.execute(f"ALTER TABLE {qualified_table} ENABLE ROW LEVEL SECURITY")
            cursor.execute(f"ALTER TABLE {qualified_table} FORCE ROW LEVEL SECURITY")
            cursor.execute(f"DROP POLICY IF EXISTS {policy_name} ON {qualified_table}")
            cursor.execute(
                f"CREATE POLICY {policy_name} ON {qualified_table} "
                f"USING {org_guard} "
                f"WITH CHECK {org_guard}"
            )
    return len(tables)


def disable_org_rls_policies(using: str = DEFAULT_DB_ALIAS) -> int:
    """Drop the org-isolation policy and disable RLS where that policy exists."""
    if not _is_postgres(using):
        return 0
    connection = connections[using]
    quote = connection.ops.quote_name
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT schemaname, tablename
            FROM pg_policies
            WHERE policyname = %s
            ORDER BY schemaname, tablename
            """,
            [RLS_POLICY_NAME],
        )
        tables = [(row[0], row[1]) for row in cursor.fetchall()]
        for schema_name, table_name in tables:
            qualified_table = f"{quote(schema_name)}.{quote(table_name)}"
            policy_name = quote(RLS_POLICY_NAME)
            cursor.execute(f"ALTER TABLE {qualified_table} NO FORCE ROW LEVEL SECURITY")
            cursor.execute(f"DROP POLICY IF EXISTS {policy_name} ON {qualified_table}")
            cursor.execute(f"ALTER TABLE {qualified_table} DISABLE ROW LEVEL SECURITY")
    return len(tables)
