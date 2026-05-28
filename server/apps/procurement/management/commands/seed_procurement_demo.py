"""
Seed realistic demo data for the Procurement module.

Usage:
    python manage.py seed_procurement_demo
    python manage.py seed_procurement_demo --flush
    python manage.py seed_procurement_demo --organization-id 1
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Organization
from apps.procurement.models import (
    GoodsReceipt,
    GoodsReceiptItem,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseRequisition,
    PurchaseRequisitionItem,
    RequestForQuotation,
    RequestForQuotationQuote,
    Vendor,
)

DEMO_MARKER = "[demo-seed]"

# ---------------------------------------------------------------------------
# Hardcoded realistic data
# ---------------------------------------------------------------------------

VENDOR_DATA = [
    {
        "name": "Dangote Cement Plc",
        "contact_person": "Engr. Bola Adewale",
        "email": "procurement@dangotecement.com.ng",
        "phone": "+234 803 700 1001",
        "category": "materials",
        "performance_rating": Decimal("4.60"),
        "delivery_timeliness_score": Decimal("92.50"),
        "price_competitiveness": "high",
        "compliance_status": "compliant",
        "address": "1 Alfred Rewane Road, Ikoyi, Lagos",
        "tax_id": "TIN-DAN-20180044",
    },
    {
        "name": "Julius Berger Nigeria Plc",
        "contact_person": "Dipl.-Ing. Klaus Weber",
        "email": "tenders@juliusberger.com.ng",
        "phone": "+234 809 111 2233",
        "category": "contractor",
        "performance_rating": Decimal("4.80"),
        "delivery_timeliness_score": Decimal("96.00"),
        "price_competitiveness": "premium",
        "compliance_status": "compliant",
        "address": "10 Shettima Munguno Crescent, Utako, Abuja",
        "tax_id": "TIN-JBN-20150012",
    },
    {
        "name": "BuildMate Construction Ltd",
        "contact_person": "Chukwuemeka Obi",
        "email": "info@buildmateng.com",
        "phone": "+234 812 345 6789",
        "category": "contractor",
        "performance_rating": Decimal("3.90"),
        "delivery_timeliness_score": Decimal("78.30"),
        "price_competitiveness": "average",
        "compliance_status": "compliant",
        "address": "42 Awolowo Road, Ikoyi, Lagos",
        "tax_id": "TIN-BML-20200087",
    },
    {
        "name": "SteelPro Industries",
        "contact_person": "Ibrahim Yakubu",
        "email": "sales@steelprong.com",
        "phone": "+234 806 234 5678",
        "category": "materials",
        "performance_rating": Decimal("3.50"),
        "delivery_timeliness_score": Decimal("71.20"),
        "price_competitiveness": "low",
        "compliance_status": "pending_review",
        "address": "KM 12 Lagos-Ibadan Expressway, Ogun State",
        "tax_id": "TIN-SPI-20210134",
    },
    {
        "name": "AlphaGlass Industries Ltd",
        "contact_person": "Ngozi Emenike",
        "email": "orders@alphaglass.ng",
        "phone": "+234 814 567 8901",
        "category": "materials",
        "performance_rating": Decimal("4.20"),
        "delivery_timeliness_score": Decimal("85.00"),
        "price_competitiveness": "average",
        "compliance_status": "compliant",
        "address": "Agbara Industrial Estate, Ogun State",
        "tax_id": "TIN-AGI-20190056",
    },
    {
        "name": "Arbico Construction Ltd",
        "contact_person": "Tunde Bakare",
        "email": "tenders@arbicoplc.com",
        "phone": "+234 802 111 2233",
        "category": "contractor",
        "performance_rating": Decimal("4.10"),
        "delivery_timeliness_score": Decimal("82.40"),
        "price_competitiveness": "average",
        "compliance_status": "compliant",
        "address": "3 Akin Adesola Street, Victoria Island, Lagos",
        "tax_id": "TIN-ARB-20170023",
    },
    {
        "name": "Lafarge Africa Plc",
        "contact_person": "Amaka Nwankwo",
        "email": "procurement@lafarge.com.ng",
        "phone": "+234 810 678 9012",
        "category": "materials",
        "performance_rating": Decimal("4.40"),
        "delivery_timeliness_score": Decimal("89.10"),
        "price_competitiveness": "high",
        "compliance_status": "compliant",
        "address": "27B Gerrard Road, Ikoyi, Lagos",
        "tax_id": "TIN-LAF-20160009",
    },
    {
        "name": "QuickFix Electrical Services",
        "contact_person": "Kola Ajayi",
        "email": "info@quickfixng.com",
        "phone": "+234 811 444 5566",
        "category": "contractor",
        "performance_rating": Decimal("2.80"),
        "delivery_timeliness_score": Decimal("58.70"),
        "price_competitiveness": "low",
        "compliance_status": "non_compliant",
        "address": "15 Apapa Road, Ebute Metta, Lagos",
        "tax_id": "TIN-QFE-20220198",
        "is_blacklisted": True,
        "blacklist_reason": "Repeated delivery failures and poor quality workmanship on VI Commercial project",
    },
    {
        "name": "Greenfield Interiors Ltd",
        "contact_person": "Adaeze Okwu",
        "email": "projects@greenfieldng.com",
        "phone": "+234 809 876 5432",
        "category": "contractor",
        "performance_rating": Decimal("4.30"),
        "delivery_timeliness_score": Decimal("87.60"),
        "price_competitiveness": "average",
        "compliance_status": "compliant",
        "address": "Plot 22, Admiralty Way, Lekki Phase 1, Lagos",
        "tax_id": "TIN-GFI-20210067",
    },
    {
        "name": "PrimeStar Consulting Engineers",
        "contact_person": "Engr. Fatima Bello",
        "email": "consulting@primestarng.com",
        "phone": "+234 803 456 7890",
        "category": "consultant",
        "performance_rating": Decimal("4.50"),
        "delivery_timeliness_score": Decimal("91.30"),
        "price_competitiveness": "premium",
        "compliance_status": "compliant",
        "address": "7 Maitama Sule Street, Maitama, Abuja",
        "tax_id": "TIN-PSC-20180045",
    },
]

# (title, priority, status, requester, items: list of (desc, qty, uom, unit_price))
REQUISITION_DATA = [
    (
        "Portland Cement — Phase 3 Foundation",
        "high",
        "approved",
        "Engr. Adebayo Oluwatobi",
        [
            ("Portland Cement 42.5R — 50kg bags", 500, "bag", 8500),
            ("Sharp Sand — 20-ton load", 8, "ton", 35000),
            ("Granite 19mm — 30-ton load", 12, "ton", 42000),
        ],
    ),
    (
        "Structural Steel Reinforcement — Block B",
        "high",
        "approved",
        "Engr. Emeka Obiora",
        [
            ("Deformed Steel Bars Y16mm — 12m length", 800, "pcs", 4200),
            ("Deformed Steel Bars Y12mm — 12m length", 1200, "pcs", 2800),
            ("Binding Wire 1.2mm — 25kg coil", 20, "coil", 18000),
        ],
    ),
    (
        "Aluminium Windows — Tower A",
        "medium",
        "approved",
        "Arch. Fatima Bello",
        [
            ("Casement Window 1200x1500mm — powder coated", 48, "unit", 85000),
            ("Fixed Panel 900x1200mm — tinted", 24, "unit", 62000),
            ("Sliding Door 2100x2400mm — double glazed", 12, "unit", 185000),
        ],
    ),
    (
        "MEP Supplies — HVAC Installation",
        "medium",
        "submitted",
        "Engr. Chioma Nwosu",
        [
            ("Split AC Unit 2.5HP — LG", 36, "unit", 350000),
            ("Copper Pipe 3/4 inch — 15m roll", 20, "roll", 28000),
            ("AC Condenser Bracket — heavy duty", 36, "pcs", 8500),
            ("Refrigerant R410A — 11.3kg cylinder", 12, "cyl", 45000),
        ],
    ),
    (
        "Painting Materials — Common Areas",
        "low",
        "draft",
        "QS Yusuf Abdullahi",
        [
            ("Emulsion Paint — Dulux White 20L", 30, "bucket", 32000),
            ("Undercoat Primer — 20L", 15, "bucket", 18000),
            ("Roller Set — 9 inch professional", 20, "set", 4500),
        ],
    ),
    (
        "Plumbing Fittings — Block C",
        "medium",
        "approved",
        "Engr. Ngozi Okeke",
        [
            ("PPR Pipe 25mm — 4m length", 200, "pcs", 1800),
            ("PPR Elbow 25mm", 100, "pcs", 350),
            ("WC Suite — close-coupled ceramic", 24, "set", 65000),
            ("Wash Hand Basin — pedestal type", 24, "set", 38000),
        ],
    ),
    (
        "Electrical Cabling — Distribution",
        "urgent",
        "ordered",
        "Engr. Adebayo Oluwatobi",
        [
            ("Armoured Cable 4x16mm — per metre", 500, "m", 4200),
            ("PVC Cable 2.5mm single core — 100m roll", 40, "roll", 12500),
            ("Distribution Board — 12-way MCB", 8, "unit", 45000),
            ("MCB 32A — single pole", 48, "pcs", 3200),
        ],
    ),
    (
        "Tiling Materials — Lobby & Corridors",
        "low",
        "submitted",
        "Arch. Fatima Bello",
        [
            ("Porcelain Floor Tile 600x600mm — polished", 400, "sqm", 12500),
            ("Tile Adhesive — 25kg bag", 60, "bag", 4800),
            ("Grout — 5kg bag", 30, "bag", 2800),
        ],
    ),
]

NIGERIAN_STAFF = [
    "Engr. Adebayo Oluwatobi",
    "Engr. Chioma Nwosu",
    "Arch. Fatima Bello",
    "Engr. Emeka Obiora",
    "QS Yusuf Abdullahi",
    "Engr. Ngozi Okeke",
    "Mr. Tunde Bakare",
    "Mrs. Adaeze Okwu",
]


class Command(BaseCommand):
    help = "Seed realistic demo data for the Procurement module."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization-id",
            type=int,
            action="append",
            default=None,
            dest="org_ids",
            help="Seed only for specific organization(s). Omit to seed for all.",
        )
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previous demo-seeded data before re-seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        org_ids = options.get("org_ids")
        flush = options.get("flush", False)

        if org_ids:
            orgs = Organization.objects.filter(id__in=org_ids)
        else:
            orgs = Organization.objects.all()

        if not orgs.exists():
            self.stderr.write(self.style.ERROR("No organizations found."))
            return

        for org in orgs:
            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Organization: {org.name} (id={org.id})")
            self.stdout.write(f"{'='*60}")

            random.seed(org.id + 8000)

            if flush:
                self._flush(org)

            vendors = self._seed_vendors(org)
            requisitions = self._seed_requisitions(org)
            purchase_orders = self._seed_purchase_orders(org, vendors, requisitions)
            self._seed_goods_receipts(org, purchase_orders)
            self._seed_rfqs(org, vendors, requisitions)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Done! Procurement module populated for {org.name}: "
                    f"{len(vendors)} vendors, {len(requisitions)} PRs, "
                    f"{len(purchase_orders)} POs."
                )
            )

    def _flush(self, org):
        self.stdout.write("Flushing previous Procurement demo data ...")
        # Delete in reverse dependency order
        GoodsReceiptItem.objects.filter(
            goods_receipt__organization=org,
            goods_receipt__notes__icontains=DEMO_MARKER,
        ).delete()
        GoodsReceipt.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()
        RequestForQuotationQuote.objects.filter(
            organization=org, notes__icontains=DEMO_MARKER
        ).delete()
        RequestForQuotation.objects.filter(
            organization=org, notes__icontains=DEMO_MARKER
        ).delete()
        PurchaseOrderItem.objects.filter(
            purchase_order__organization=org,
            purchase_order__notes__icontains=DEMO_MARKER,
        ).delete()
        PurchaseOrder.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()
        PurchaseRequisitionItem.objects.filter(
            requisition__organization=org,
            requisition__notes__icontains=DEMO_MARKER,
        ).delete()
        PurchaseRequisition.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()
        Vendor.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()
        self.stdout.write("  Flushed.")

    # ----- Vendors -----

    def _seed_vendors(self, org):
        today = date.today()
        vendors = []
        for data in VENDOR_DATA:
            vendor, _ = Vendor.objects.get_or_create(
                organization=org,
                name=data["name"],
                defaults={
                    "contact_person": data["contact_person"],
                    "email": data["email"],
                    "phone": data["phone"],
                    "address": data["address"],
                    "tax_id": data["tax_id"],
                    "category": data["category"],
                    "performance_rating": data["performance_rating"],
                    "delivery_timeliness_score": data["delivery_timeliness_score"],
                    "price_competitiveness": data["price_competitiveness"],
                    "compliance_status": data["compliance_status"],
                    "is_blacklisted": data.get("is_blacklisted", False),
                    "blacklist_reason": data.get("blacklist_reason", ""),
                    "bank_name": random.choice(["First Bank", "GTBank", "Zenith Bank", "Access Bank", "UBA"]),
                    "bank_account_number": f"{random.randint(1000000000, 9999999999)}",
                    "bank_branch": random.choice(["Victoria Island", "Ikoyi", "Lekki", "Ikeja", "Maitama"]),
                    "is_active": not data.get("is_blacklisted", False),
                    "notes": f"{DEMO_MARKER} Demo procurement vendor",
                },
            )
            vendors.append(vendor)
        self.stdout.write(f"  {len(vendors)} vendors ready.")
        return vendors

    # ----- Purchase Requisitions -----

    def _seed_requisitions(self, org):
        today = date.today()
        requisitions = []

        for title, priority, status, requester, items in REQUISITION_DATA:
            req, created = PurchaseRequisition.objects.get_or_create(
                organization=org,
                title=title,
                defaults={
                    "status": status,
                    "requester": requester,
                    "priority": priority,
                    "required_date": today + timedelta(days=random.randint(7, 60)),
                    "justification": f"{DEMO_MARKER} Required for ongoing construction works",
                    "approved_by": random.choice(NIGERIAN_STAFF) if status in ("approved", "ordered") else "",
                    "approved_date": today - timedelta(days=random.randint(1, 14)) if status in ("approved", "ordered") else None,
                    "notes": f"{DEMO_MARKER} Demo purchase requisition",
                },
            )
            if created:
                total = Decimal("0")
                for idx, (desc, qty, uom, price) in enumerate(items):
                    PurchaseRequisitionItem.objects.create(
                        requisition=req,
                        description=desc,
                        quantity=Decimal(str(qty)),
                        unit_of_measure=uom,
                        estimated_unit_price=Decimal(str(price)),
                        sort_order=idx,
                    )
                    total += Decimal(str(qty)) * Decimal(str(price))
                req.estimated_total = total
                req.save(update_fields=["estimated_total"])
            requisitions.append(req)

        self.stdout.write(f"  {len(requisitions)} purchase requisitions ready.")
        return requisitions

    # ----- Purchase Orders -----

    def _seed_purchase_orders(self, org, vendors, requisitions):
        today = date.today()
        # Create POs for approved/ordered requisitions
        approved_reqs = [r for r in requisitions if r.status in ("approved", "ordered")]
        active_vendors = [v for v in vendors if v.is_active and not v.is_blacklisted]
        po_statuses = ["approved", "issued", "issued", "partially_received", "received"]

        purchase_orders = []
        for req in approved_reqs:
            vendor = random.choice(active_vendors)
            status = random.choice(po_statuses)
            issue_date = today - timedelta(days=random.randint(3, 30))

            po, created = PurchaseOrder.objects.get_or_create(
                organization=org,
                requisition=req,
                defaults={
                    "vendor": vendor,
                    "status": status,
                    "issue_date": issue_date,
                    "expected_delivery_date": issue_date + timedelta(days=random.randint(7, 45)),
                    "delivery_address": "Project Site — Lekki Phase 1, Lagos",
                    "payment_terms": random.choice([
                        "30 days net", "50% advance, 50% on delivery",
                        "60 days net", "Letter of Credit",
                    ]),
                    "approved_by": random.choice(NIGERIAN_STAFF),
                    "approved_date": issue_date - timedelta(days=random.randint(1, 5)),
                    "notes": f"{DEMO_MARKER} Demo purchase order",
                },
            )
            if created:
                # Create PO items from requisition items
                subtotal = Decimal("0")
                for idx, pri in enumerate(req.items.all()):
                    markup = Decimal(str(random.uniform(0.95, 1.15)))
                    unit_price = (pri.estimated_unit_price * markup).quantize(Decimal("0.01"))
                    PurchaseOrderItem.objects.create(
                        purchase_order=po,
                        description=pri.description,
                        quantity=pri.quantity,
                        unit_of_measure=pri.unit_of_measure,
                        unit_price=unit_price,
                        sort_order=idx,
                    )
                    subtotal += pri.quantity * unit_price

                tax = (subtotal * Decimal("0.075")).quantize(Decimal("0.01"))
                po.subtotal = subtotal
                po.tax_amount = tax
                po.total_amount = subtotal + tax
                po.save(update_fields=["subtotal", "tax_amount", "total_amount"])
            purchase_orders.append(po)

        self.stdout.write(f"  {len(purchase_orders)} purchase orders ready.")
        return purchase_orders

    # ----- Goods Receipts -----

    def _seed_goods_receipts(self, org, purchase_orders):
        today = date.today()
        # Create GRNs for POs that are partially_received or received
        receivable_pos = [
            po for po in purchase_orders
            if po.status in ("partially_received", "received")
        ]
        count = 0

        for po in receivable_pos:
            grn_status = "accepted" if po.status == "received" else random.choice(["inspected", "partially_accepted"])
            grn, created = GoodsReceipt.objects.get_or_create(
                organization=org,
                purchase_order=po,
                defaults={
                    "status": grn_status,
                    "received_date": today - timedelta(days=random.randint(1, 14)),
                    "received_by": random.choice(NIGERIAN_STAFF),
                    "delivery_note_number": f"DN-{random.randint(10000, 99999)}",
                    "inspection_notes": f"{DEMO_MARKER} Materials inspected on delivery",
                    "notes": f"{DEMO_MARKER} Demo goods receipt",
                },
            )
            if created:
                for poi in po.items.all():
                    if po.status == "received":
                        qty_received = poi.quantity
                        qty_accepted = poi.quantity
                        qty_rejected = Decimal("0")
                    else:
                        pct = Decimal(str(random.uniform(0.5, 0.9)))
                        qty_received = (poi.quantity * pct).quantize(Decimal("1"))
                        reject_pct = Decimal(str(random.uniform(0, 0.05)))
                        qty_rejected = (qty_received * reject_pct).quantize(Decimal("1"))
                        qty_accepted = qty_received - qty_rejected

                    GoodsReceiptItem.objects.create(
                        goods_receipt=grn,
                        po_item=poi,
                        quantity_received=qty_received,
                        quantity_accepted=qty_accepted,
                        quantity_rejected=qty_rejected,
                        rejection_reason="Minor damage during transit" if qty_rejected > 0 else "",
                        notes=f"{DEMO_MARKER}",
                    )
            count += 1

        self.stdout.write(f"  {count} goods receipts ready.")

    # ----- RFQs -----

    def _seed_rfqs(self, org, vendors, requisitions):
        today = date.today()
        active_vendors = [v for v in vendors if v.is_active and not v.is_blacklisted]

        rfq_data = [
            ("Structural Steel Supply — Phase 3", "closed", Decimal("42000000")),
            ("HVAC Package — Tower A & B", "evaluation", Decimal("85000000")),
            ("Aluminium Cladding — Exterior Facade", "issued", Decimal("120000000")),
            ("MEP Subcontract — Block C", "approved", Decimal("250000000")),
            ("Interior Finishing — Show Units", "draft", Decimal("18000000")),
        ]

        count = 0
        for title, status, est_value in rfq_data:
            # Link to a requisition if one matches
            linked_req = None
            if requisitions and random.random() < 0.4:
                linked_req = random.choice(requisitions)

            selected_vendor = None
            if status in ("approved", "closed"):
                selected_vendor = random.choice(active_vendors)

            rfq, created = RequestForQuotation.objects.get_or_create(
                organization=org,
                title=title,
                defaults={
                    "status": status,
                    "requisition": linked_req,
                    "issue_date": today - timedelta(days=random.randint(7, 60)),
                    "submission_deadline": today + timedelta(days=random.randint(-14, 30)),
                    "estimated_value": est_value,
                    "selected_vendor": selected_vendor,
                    "selection_notes": f"{DEMO_MARKER} Vendor selected based on best value" if selected_vendor else "",
                    "notes": f"{DEMO_MARKER} Demo RFQ for tender evaluation",
                },
            )
            if created and status in ("evaluation", "approved", "closed"):
                # Create vendor quotes
                num_quotes = random.randint(3, min(5, len(active_vendors)))
                quote_vendors = random.sample(active_vendors, num_quotes)

                for qv in quote_vendors:
                    variance = Decimal(str(random.uniform(0.85, 1.25)))
                    quoted = (est_value * variance).quantize(Decimal("0.01"))
                    is_winner = (qv == selected_vendor) if selected_vendor else False

                    RequestForQuotationQuote.objects.create(
                        organization=org,
                        rfq=rfq,
                        vendor=qv,
                        quote_date=today - timedelta(days=random.randint(3, 30)),
                        validity_date=today + timedelta(days=random.randint(30, 90)),
                        quoted_amount=quoted,
                        delivery_days=random.randint(14, 90),
                        warranty_terms=random.choice([
                            "12 months defects liability",
                            "24 months warranty",
                            "6 months parts & labour",
                        ]),
                        payment_terms=random.choice([
                            "30 days net", "50% advance, 50% on completion",
                            "Progress-based milestones",
                        ]),
                        compliance_score=Decimal(str(random.uniform(60, 98))).quantize(Decimal("0.01")),
                        technical_score=Decimal(str(random.uniform(55, 95))).quantize(Decimal("0.01")),
                        commercial_score=Decimal(str(random.uniform(50, 92))).quantize(Decimal("0.01")),
                        status="winner" if is_winner else random.choice(["shortlisted", "pending", "rejected"]),
                        notes=f"{DEMO_MARKER} Demo RFQ quote",
                    )
            count += 1

        self.stdout.write(f"  {count} RFQs ready.")
