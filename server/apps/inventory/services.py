from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from django.db.models import Max, Sum
from django.utils.text import slugify

from .models import (
    InventoryItem,
    InventoryStock,
    InventoryTransaction,
    ProcurementItemMapping,
    Warehouse,
)

INBOUND_TRANSACTION_TYPES = {
    InventoryTransaction.TransactionType.RECEIPT,
    InventoryTransaction.TransactionType.ADJUSTMENT_IN,
    InventoryTransaction.TransactionType.TRANSFER_IN,
}

OUTBOUND_TRANSACTION_TYPES = {
    InventoryTransaction.TransactionType.ISSUE,
    InventoryTransaction.TransactionType.ADJUSTMENT_OUT,
    InventoryTransaction.TransactionType.TRANSFER_OUT,
}


def _unique_warehouse_code(base_code: str) -> str:
    candidate = base_code
    suffix = 1
    while Warehouse.objects.filter(code=candidate).exists():
        suffix += 1
        candidate = f"{base_code}-{suffix}"
    return candidate


def get_or_create_default_warehouse(project=None) -> Warehouse:
    """Resolve destination warehouse for sync/manual operations."""
    if project is not None:
        warehouse = Warehouse.objects.filter(project=project, is_active=True).first()
        if warehouse:
            return warehouse

        code = _unique_warehouse_code(f"PRJ-{project.id:03d}-WH")
        return Warehouse.objects.create(
            code=code,
            name=f"{project.name} Site Store",
            project=project,
            is_active=True,
            is_default=False,
        )

    warehouse = Warehouse.objects.filter(is_default=True, is_active=True).first()
    if warehouse:
        return warehouse

    warehouse = Warehouse.objects.filter(is_active=True).first()
    if warehouse:
        if Warehouse.objects.filter(is_default=True).exclude(pk=warehouse.pk).exists():
            return warehouse
        warehouse.is_default = True
        warehouse.save(update_fields=["is_default", "updated_at"])
        return warehouse

    return Warehouse.objects.create(
        code="MAIN-001",
        name="Main Warehouse",
        location="HQ",
        is_active=True,
        is_default=True,
    )


def _generate_item_sku_from_description(description: str) -> str:
    token = slugify(description or "")[:24].upper()
    if not token:
        token = "ITEM"

    base = f"MAT-{token}"
    candidate = base
    suffix = 1
    while InventoryItem.objects.filter(sku=candidate).exists():
        suffix += 1
        candidate = f"{base}-{suffix}"
    return candidate


def ensure_item_for_po_item(po_item) -> InventoryItem:
    """Get or create an inventory item linked to a PO line item."""
    mapping = ProcurementItemMapping.objects.filter(po_item=po_item).select_related(
        "inventory_item"
    ).first()
    if mapping:
        return mapping.inventory_item

    existing = InventoryItem.objects.filter(
        name__iexact=po_item.description.strip(),
        unit_of_measure__iexact=po_item.unit_of_measure.strip(),
    ).first()

    if existing is None:
        existing = InventoryItem.objects.create(
            sku=_generate_item_sku_from_description(po_item.description),
            name=po_item.description.strip() or f"PO Item {po_item.id}",
            category=InventoryItem.Category.CONSUMABLE,
            unit_of_measure=po_item.unit_of_measure or "ea",
            default_unit_cost=po_item.unit_price or Decimal("0.00"),
            preferred_vendor=po_item.purchase_order.vendor,
        )

    ProcurementItemMapping.objects.get_or_create(
        po_item=po_item,
        defaults={"inventory_item": existing},
    )
    return existing


def recalculate_stock(item_id: int, warehouse_id: int) -> InventoryStock:
    """Rebuild stock snapshot from movement history."""
    txns = InventoryTransaction.objects.filter(item_id=item_id, warehouse_id=warehouse_id)

    inbound_qty = txns.filter(
        transaction_type__in=INBOUND_TRANSACTION_TYPES
    ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")
    outbound_qty = txns.filter(
        transaction_type__in=OUTBOUND_TRANSACTION_TYPES
    ).aggregate(total=Sum("quantity"))["total"] or Decimal("0")

    inbound_value = txns.filter(
        transaction_type__in=INBOUND_TRANSACTION_TYPES
    ).aggregate(total=Sum("total_cost"))["total"] or Decimal("0.00")

    last_timestamp = txns.aggregate(last=Max("created_at"))["last"]

    stock, _ = InventoryStock.objects.get_or_create(
        item_id=item_id,
        warehouse_id=warehouse_id,
    )
    stock.quantity_on_hand = inbound_qty - outbound_qty
    stock.average_unit_cost = (
        inbound_value / inbound_qty if inbound_qty > 0 else Decimal("0.00")
    )
    if stock.quantity_reserved > stock.quantity_on_hand:
        stock.quantity_reserved = max(Decimal("0"), stock.quantity_on_hand)
    stock.last_transaction_at = last_timestamp
    stock.save(
        update_fields=[
            "quantity_on_hand",
            "quantity_reserved",
            "average_unit_cost",
            "last_transaction_at",
            "updated_at",
        ]
    )
    return stock


def sync_goods_receipt_item(grn_item, performed_by=None):
    """Upsert inventory receipt transaction from a GRN line item."""
    accepted_qty = grn_item.quantity_accepted or Decimal("0")
    if accepted_qty <= 0:
        delete_goods_receipt_item_transaction(grn_item.id)
        return None

    item = ensure_item_for_po_item(grn_item.po_item)
    purchase_order = grn_item.goods_receipt.purchase_order
    warehouse = get_or_create_default_warehouse(project=purchase_order.project)
    unit_cost = grn_item.po_item.unit_price or Decimal("0.00")

    defaults = {
        "warehouse": warehouse,
        "item": item,
        "project": purchase_order.project,
        "purchase_order": purchase_order,
        "goods_receipt": grn_item.goods_receipt,
        "quantity": accepted_qty,
        "unit_cost": unit_cost,
        "total_cost": accepted_qty * unit_cost,
        "transaction_date": grn_item.goods_receipt.received_date,
        "source_module": "procurement",
        "source_reference": f"grn-item:{grn_item.id}",
        "performed_by": performed_by,
        "notes": grn_item.notes or "",
    }

    transaction, created = InventoryTransaction.objects.get_or_create(
        goods_receipt_item=grn_item,
        transaction_type=InventoryTransaction.TransactionType.RECEIPT,
        defaults=defaults,
    )
    if not created:
        for key, value in defaults.items():
            setattr(transaction, key, value)
        transaction.save()

    recalculate_stock(item.id, warehouse.id)
    return transaction


def delete_goods_receipt_item_transaction(goods_receipt_item_id: int):
    """Remove inventory movement synced from a deleted/zeroed GRN line."""
    txns = list(
        InventoryTransaction.objects.filter(
            goods_receipt_item_id=goods_receipt_item_id,
            transaction_type=InventoryTransaction.TransactionType.RECEIPT,
        )
    )
    if not txns:
        return

    pairs: set[tuple[int, int]] = {(tx.item_id, tx.warehouse_id) for tx in txns}
    InventoryTransaction.objects.filter(id__in=[tx.id for tx in txns]).delete()

    for item_id, warehouse_id in pairs:
        recalculate_stock(item_id, warehouse_id)


def bulk_sync_goods_receipt_items(items: Iterable) -> int:
    """Backfill helper to hydrate inventory movements from historic GRN data."""
    count = 0
    for item in items:
        sync_goods_receipt_item(item)
        count += 1
    return count


def _extract_inventory_sku(reference_number: str) -> str:
    raw = (reference_number or "").strip()
    if not raw:
        return ""
    upper = raw.upper()
    if "SKU:" in upper:
        idx = upper.index("SKU:")
        raw = raw[idx + 4 :].strip()
    if "|" in raw:
        raw = raw.split("|", 1)[0].strip()
    return raw


def delete_project_cost_transaction(cost_entry_id: int):
    """Remove inventory movement generated from a project cost entry."""
    source_reference = f"cost-entry:{cost_entry_id}"
    txns = list(
        InventoryTransaction.objects.filter(
            source_module="projects_cost",
            source_reference=source_reference,
            transaction_type=InventoryTransaction.TransactionType.ISSUE,
        )
    )
    if not txns:
        return

    pairs: set[tuple[int, int]] = {(tx.item_id, tx.warehouse_id) for tx in txns}
    InventoryTransaction.objects.filter(id__in=[tx.id for tx in txns]).delete()
    for item_id, warehouse_id in pairs:
        recalculate_stock(item_id, warehouse_id)


def sync_project_cost_entry(cost_entry, performed_by=None):
    """
    Sync project material cost entries into inventory issue transactions.

    Mapping rule:
    - category must be `materials`
    - `reference_number` should contain item SKU (plain or `SKU:<sku>`)
    """
    if cost_entry.category != "materials":
        delete_project_cost_transaction(cost_entry.id)
        return None

    sku = _extract_inventory_sku(cost_entry.reference_number)
    if not sku:
        delete_project_cost_transaction(cost_entry.id)
        return None

    item = InventoryItem.objects.filter(sku__iexact=sku).first()
    if not item:
        return None

    source_reference = f"cost-entry:{cost_entry.id}"
    warehouse = get_or_create_default_warehouse(project=cost_entry.phase.project)
    total_cost = cost_entry.amount or Decimal("0.00")

    defaults = {
        "warehouse": warehouse,
        "item": item,
        "project": cost_entry.phase.project,
        "transaction_type": InventoryTransaction.TransactionType.ISSUE,
        "quantity": Decimal("1.000"),
        "unit_cost": total_cost,
        "total_cost": total_cost,
        "transaction_date": cost_entry.date,
        "source_module": "projects_cost",
        "source_reference": source_reference,
        "notes": cost_entry.description or "",
        "performed_by": performed_by,
    }

    tx, created = InventoryTransaction.objects.get_or_create(
        source_module="projects_cost",
        source_reference=source_reference,
        transaction_type=InventoryTransaction.TransactionType.ISSUE,
        defaults=defaults,
    )
    if not created:
        for key, value in defaults.items():
            setattr(tx, key, value)
        tx.save()

    recalculate_stock(item.id, warehouse.id)
    return tx
