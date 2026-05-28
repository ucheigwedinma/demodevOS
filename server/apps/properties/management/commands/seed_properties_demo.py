"""
Seed realistic demo data for the Properties module.

Usage:
    python manage.py seed_properties_demo                          # seed all orgs
    python manage.py seed_properties_demo --organization-id 1      # seed one org
    python manage.py seed_properties_demo --flush                  # delete demo data only
    python manage.py seed_properties_demo --reseed                 # flush + re-seed
    python manage.py seed_properties_demo --flush --organization-id 1
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import Organization
from apps.properties.models import (
    AssetComponent,
    Inspection,
    MaintenanceVendor,
    PreventiveSchedule,
    Property,
    PropertyInventory,
    PropertyInventoryEvent,
    PropertyOwnership,
    PropertyValuation,
    ServiceRequest,
    Unit,
    WorkOrder,
)

DEMO_MARKER = "[demo-seed]"

# ---------------------------------------------------------------------------
# Hardcoded realistic data
# ---------------------------------------------------------------------------

PROPERTY_DATA = [
    {
        "name": "Admiralty Towers",
        "property_type": "building",
        "classification": "owned",
        "address": "14A Admiralty Way, Lekki Phase 1, Lagos",
        "gps_latitude": Decimal("6.4378500"),
        "gps_longitude": Decimal("3.4709800"),
        "plot_number": "LKI/2018/0447",
        "total_area_sqft": Decimal("48500.00"),
        "acquisition_price": Decimal("2850000000.00"),
        "current_value": Decimal("3650000000.00"),
        "units": [
            ("A101", 1, 1850, 3, 3, 95000000),
            ("A102", 1, 1620, 2, 2, 78000000),
            ("A201", 2, 2100, 3, 3, 115000000),
            ("A202", 2, 1850, 3, 2, 98000000),
            ("A301", 3, 2400, 4, 4, 145000000),
            ("A302", 3, 1620, 2, 2, 82000000),
            ("PH01", 4, 3200, 4, 5, 250000000),
        ],
    },
    {
        "name": "Eko Pearl Residence",
        "property_type": "estate",
        "classification": "owned",
        "address": "Eko Atlantic City, Victoria Island, Lagos",
        "gps_latitude": Decimal("6.4155300"),
        "gps_longitude": Decimal("3.4095600"),
        "plot_number": "EAC/2020/0012",
        "total_area_sqft": Decimal("125000.00"),
        "acquisition_price": Decimal("8500000000.00"),
        "current_value": Decimal("12400000000.00"),
        "units": [
            ("EP-A1", 0, 4500, 5, 6, 380000000),
            ("EP-A2", 0, 3800, 4, 5, 310000000),
            ("EP-B1", 0, 4200, 5, 5, 350000000),
            ("EP-B2", 0, 3600, 4, 4, 290000000),
            ("EP-C1", 0, 5200, 6, 7, 450000000),
        ],
    },
    {
        "name": "Victoria Heights",
        "property_type": "building",
        "classification": "owned",
        "address": "Plot 1672, Akin Adesola Street, Victoria Island, Lagos",
        "gps_latitude": Decimal("6.4281600"),
        "gps_longitude": Decimal("3.4219400"),
        "plot_number": "VI/2017/0891",
        "total_area_sqft": Decimal("32000.00"),
        "acquisition_price": Decimal("1950000000.00"),
        "current_value": Decimal("2800000000.00"),
        "units": [
            ("VH-G01", 0, 980, None, None, 35000000),
            ("VH-G02", 0, 1200, None, None, 42000000),
            ("VH-101", 1, 2200, 3, 3, 120000000),
            ("VH-201", 2, 2200, 3, 3, 128000000),
            ("VH-301", 3, 2400, 4, 3, 145000000),
            ("VH-401", 4, 2800, 4, 4, 185000000),
        ],
    },
    {
        "name": "Maitama Business Hub",
        "property_type": "mixed",
        "classification": "owned",
        "address": "Plot 289, Aguiyi Ironsi Street, Maitama, Abuja",
        "gps_latitude": Decimal("9.0847300"),
        "gps_longitude": Decimal("7.4943600"),
        "plot_number": "ABJ/MAI/2019/0156",
        "total_area_sqft": Decimal("22000.00"),
        "acquisition_price": Decimal("1200000000.00"),
        "current_value": Decimal("1650000000.00"),
        "units": [
            ("MBH-G1", 0, 1800, None, None, 85000000),
            ("MBH-101", 1, 1400, None, None, 62000000),
            ("MBH-102", 1, 1200, None, None, 55000000),
            ("MBH-201", 2, 1600, None, None, 72000000),
            ("MBH-301", 3, 2000, 2, 2, 95000000),
        ],
    },
    {
        "name": "Palm View Estate",
        "property_type": "estate",
        "classification": "under_development",
        "address": "Osapa London Road, off Lekki-Epe Expressway, Lekki, Lagos",
        "gps_latitude": Decimal("6.4448900"),
        "gps_longitude": Decimal("3.5275100"),
        "plot_number": "LKI/2022/1203",
        "total_area_sqft": Decimal("180000.00"),
        "acquisition_price": Decimal("4200000000.00"),
        "current_value": Decimal("5100000000.00"),
        "units": [
            ("PV-01", 0, 3500, 4, 4, 180000000),
            ("PV-02", 0, 3200, 4, 4, 165000000),
            ("PV-03", 0, 4000, 5, 5, 220000000),
            ("PV-04", 0, 3500, 4, 4, 180000000),
            ("PV-05", 0, 2800, 3, 3, 145000000),
            ("PV-06", 0, 4500, 5, 5, 260000000),
        ],
    },
    {
        "name": "Wuse Commercial Complex",
        "property_type": "building",
        "classification": "lease",
        "address": "Plot 48, Aminu Kano Crescent, Wuse II, Abuja",
        "gps_latitude": Decimal("9.0628400"),
        "gps_longitude": Decimal("7.4785900"),
        "plot_number": "ABJ/WUS/2021/0078",
        "total_area_sqft": Decimal("18000.00"),
        "acquisition_price": Decimal("850000000.00"),
        "current_value": Decimal("1100000000.00"),
        "units": [
            ("WCC-G1", 0, 2400, None, None, 48000000),
            ("WCC-G2", 0, 1800, None, None, 38000000),
            ("WCC-101", 1, 3200, None, None, 58000000),
            ("WCC-201", 2, 3200, None, None, 62000000),
        ],
    },
    {
        "name": "Trans-Amadi Warehouse Park",
        "property_type": "warehouse",
        "classification": "owned",
        "address": "KM 8, Trans-Amadi Industrial Layout, Port Harcourt, Rivers State",
        "gps_latitude": Decimal("4.8062500"),
        "gps_longitude": Decimal("7.0336100"),
        "plot_number": "PH/TAI/2020/0034",
        "total_area_sqft": Decimal("65000.00"),
        "acquisition_price": Decimal("750000000.00"),
        "current_value": Decimal("920000000.00"),
        "units": [
            ("WH-A", 0, 15000, None, None, 180000000),
            ("WH-B", 0, 18000, None, None, 210000000),
            ("WH-C", 0, 12000, None, None, 150000000),
        ],
    },
    {
        "name": "Ikoyi Crescent Land",
        "property_type": "land",
        "classification": "owned",
        "address": "Plot 7, Alexander Avenue, Ikoyi, Lagos",
        "gps_latitude": Decimal("6.4518200"),
        "gps_longitude": Decimal("3.4367900"),
        "plot_number": "IKY/2023/0015",
        "total_area_sqft": Decimal("42000.00"),
        "acquisition_price": Decimal("5800000000.00"),
        "current_value": Decimal("6500000000.00"),
        "units": [],
    },
]

OWNERSHIP_DATA = [
    ("corporate", "Admiralty Properties Ltd", "LASG/TD/2018/44721"),
    ("joint_venture", "Eko Development JV Partners", "LASG/TD/2020/01284"),
    ("corporate", "Victoria Heights Development Co.", "LASG/TD/2017/89123"),
    ("corporate", "Maitama Commercial Ventures Ltd", "ABUJ/TD/2019/15634"),
    ("individual", "Chief Adewale Ogundimu", "LASG/TD/2022/12034"),
    ("corporate", "Wuse Leasing Corp.", "ABUJ/TD/2021/07812"),
    ("corporate", "Trans-Amadi Logistics Ltd", "RVSG/TD/2020/00345"),
    ("individual", "Engr. Bola Tinubu-Williams", "LASG/TD/2023/00152"),
]

VENDOR_DATA = [
    ("Zenith Plumbing Solutions", "Chinedu Okafor", "chinedu@zenithplumbing.ng", "+234 803 456 7890", "plumbing", Decimal("4.2"), Decimal("15000.00")),
    ("PowerGuard Electrical Ltd", "Amaka Eze", "amaka@powerguard.ng", "+234 812 345 6789", "electrical", Decimal("4.5"), Decimal("18000.00")),
    ("CoolTech HVAC Services", "Ibrahim Musa", "ibrahim@cooltech.ng", "+234 809 876 5432", "hvac", Decimal("3.8"), Decimal("22000.00")),
    ("SecureNet Systems", "Olufemi Adeyemi", "olufemi@securenet.ng", "+234 814 567 8901", "security", Decimal("4.0"), Decimal("12000.00")),
    ("PrimeClean Facility Services", "Grace Nwankwo", "grace@primeclean.ng", "+234 806 234 5678", "cleaning", Decimal("3.5"), Decimal("8000.00")),
    ("Apex Maintenance Ltd", "Tunde Bakare", "tunde@apexmaint.ng", "+234 810 678 9012", "general", Decimal("4.3"), Decimal("16000.00")),
    ("LiftMaster Elevators", "Kola Ajayi", "kola@liftmaster.ng", "+234 802 111 2233", "elevator", Decimal("4.7"), Decimal("35000.00")),
    ("GenPower Solutions", "Uche Nnamdi", "uche@genpower.ng", "+234 811 444 5566", "generator", Decimal("4.1"), Decimal("25000.00")),
]

ASSET_DATA = [
    ("500kVA Mikano Generator", "generator", "Mikano", "MK-500D", "Generator Room, Basement"),
    ("Passenger Elevator — Shaft A", "elevator", "Otis", "Gen2-3000", "Main Lobby"),
    ("Passenger Elevator — Shaft B", "elevator", "Otis", "Gen2-3000", "Rear Lobby"),
    ("Central Chiller Unit", "hvac", "Daikin", "VRV-IV-28HP", "Rooftop Plant Room"),
    ("Fire Alarm Control Panel", "fire_safety", "Honeywell", "FACP-4100", "Ground Floor Security"),
    ("Booster Pump Set", "water_systems", "Grundfos", "CR-32-6", "Pump Room, Basement"),
    ("CCTV System — 32 Channel", "security", "Hikvision", "DS-7732NI-K4", "Security Control Room"),
    ("Transformer — 1000kVA", "electrical", "ABB", "ONAN-1000", "Transformer Bay"),
    ("Split AC Unit — Office Block", "hvac", "LG", "S4-Q18KL3AB", "Various Floors"),
    ("Fire Suppression System", "fire_safety", "Kidde", "FM-200-400", "Server Room"),
    ("Water Treatment Plant", "water_systems", "WTP Nigeria", "RO-5000", "Treatment Room"),
    ("Cargo Elevator", "elevator", "Schindler", "S300", "Service Bay"),
    ("Emergency Generator 200kVA", "generator", "FG Wilson", "P200-3", "Generator House"),
    ("ATS Panel", "electrical", "Socomec", "ATyS-6e-800A", "Main Switchroom"),
    ("Package Unit AC", "hvac", "Carrier", "50XC-120", "Commercial Block"),
    ("Smoke Detection System", "fire_safety", "Notifier", "NFS2-3030", "All Floors"),
    ("Sump Pump", "water_systems", "Wilo", "TP-65E", "Basement"),
    ("Perimeter Fence Alarm", "security", "Optex", "AX-200TFR", "Perimeter"),
    ("UPS System 60kVA", "electrical", "APC", "Galaxy-VM-60", "Data Room"),
    ("Service Elevator", "elevator", "ThyssenKrupp", "Evolution-200", "Service Core"),
]

WORK_ORDER_DATA = [
    ("Leaking pipe in Unit A201 bathroom", "plumbing", "high", "open", 85000),
    ("Faulty elevator door mechanism — Shaft A", "elevator", "urgent", "assigned", 450000),
    ("Replace burnt-out transformer fuses", "electrical", "high", "in_progress", 120000),
    ("AC unit not cooling — Suite MBH-201", "hvac", "medium", "open", 65000),
    ("Security camera malfunction — Parking Level B1", "security", "medium", "completed", 35000),
    ("Generator auto-start failure", "generator", "urgent", "in_progress", 280000),
    ("Cracked tile replacement — lobby", "general", "low", "completed", 45000),
    ("Fire extinguisher annual recharge", "fire_safety", "medium", "completed", 180000),
    ("Blocked drainage in basement car park", "plumbing", "high", "assigned", 95000),
    ("Painting touch-up — stairwell floors 1-3", "painting", "low", "open", 120000),
    ("Water pump vibration — unusual noise", "water_systems", "medium", "on_hold", 150000),
    ("Landscaping — quarterly hedge trimming", "landscaping", "low", "completed", 75000),
    ("Intercom system fault — ground floor", "security", "medium", "open", 55000),
    ("HVAC filter replacement — all units", "hvac", "low", "cancelled", 320000),
    ("Roof waterproofing repair", "structural", "high", "in_progress", 580000),
]

PREVENTIVE_SCHEDULE_DATA = [
    ("Generator Monthly Load Test", "generator", "monthly", 45000, "active"),
    ("Elevator Quarterly Inspection", "elevator", "quarterly", 120000, "active"),
    ("HVAC Filter Replacement", "hvac", "quarterly", 85000, "active"),
    ("Fire System Annual Certification", "fire_safety", "annual", 350000, "active"),
    ("Pest Control Treatment", "general", "monthly", 25000, "active"),
    ("Water Tank Cleaning", "water_systems", "semi_annual", 65000, "active"),
    ("Painting — Common Areas", "painting", "annual", 450000, "paused"),
    ("Security System Check", "security", "monthly", 15000, "active"),
    ("Plumbing Inspection — All Floors", "plumbing", "semi_annual", 40000, "active"),
    ("Electrical Panel Thermal Imaging", "electrical", "annual", 180000, "active"),
]

INSPECTION_DATA = [
    ("Q1 2026 Routine Building Inspection", "routine", "completed", "pass", "low", "compliant"),
    ("Annual Fire Safety Certification", "fire_safety", "completed", "pass", "low", "compliant"),
    ("Elevator Certification — Shaft A", "elevator_certification", "completed", "conditional", "medium", "partially_compliant"),
    ("Structural Integrity Assessment", "structural_integrity", "completed", "pass", "low", "compliant"),
    ("Environmental Audit — Waste Management", "environmental_audit", "scheduled", "", "", "pending_review"),
    ("Post-Storm Damage Assessment", "post_incident", "completed", "fail", "high", "non_compliant"),
    ("Electrical Safety Inspection", "electrical", "in_progress", "", "", ""),
    ("Health & Safety Compliance Review", "health_safety", "scheduled", "", "", ""),
    ("Pre-Handover Inspection — Unit PV-03", "pre_handover", "scheduled", "", "", ""),
    ("Q2 2026 Routine Inspection", "routine", "scheduled", "", "", ""),
    ("Condition Survey — Parking Structure", "condition_survey", "completed", "conditional", "medium", "partially_compliant"),
    ("Annual Compliance Audit", "compliance", "completed", "pass", "low", "compliant"),
]

SERVICE_REQUEST_DATA = [
    ("AC not cooling properly", "hvac", "high", "open", "Funmi Adeboye"),
    ("Water leak from ceiling", "plumbing", "urgent", "acknowledged", "Mr. Okonkwo"),
    ("Parking gate not opening", "security", "medium", "in_progress", "Tenant — Unit A301"),
    ("Request for additional power outlet", "electrical", "low", "resolved", "Mrs. Bakare"),
    ("Broken window handle", "general", "low", "closed", "Aisha Mohammed"),
    ("Lift stuck between floors", "elevator", "urgent", "resolved", "Security Desk"),
    ("Noisy generator during night hours", "generator", "medium", "acknowledged", "Resident — PH01"),
    ("Pest sighting in common area", "general", "medium", "open", "Cleaning Staff"),
    ("Hot water not working", "plumbing", "high", "in_progress", "Tenant — VH-201"),
    ("Lobby lighting too dim", "electrical", "low", "open", "Reception"),
]

NIGERIAN_INSPECTORS = [
    "Engr. Adebayo Oluwatobi",
    "Engr. Chioma Nwosu",
    "Arch. Fatima Bello",
    "Engr. Emeka Obiora",
    "QS Yusuf Abdullahi",
    "Engr. Ngozi Okeke",
]

NIGERIAN_APPRAISERS = [
    "Knight Frank Nigeria",
    "Broll Property Group",
    "Cluttons LLP",
    "Ubosi Eleh + Co.",
    "Northcourt Real Estate",
    "Estate Intel",
]

REGISTRATION_AUTHORITIES = [
    "Lagos State Land Registry",
    "FCT Land Administration",
    "Rivers State Land Registry",
]


class Command(BaseCommand):
    help = "Seed realistic demo data for the Properties module."

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
            help="Delete previous demo-seeded data (without re-seeding).",
        )
        parser.add_argument(
            "--reseed",
            action="store_true",
            help="Flush existing demo data and then re-seed fresh data.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        org_ids = options.get("org_ids")
        flush = options.get("flush", False)
        reseed = options.get("reseed", False)

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

            random.seed(org.id + 7000)

            if flush or reseed:
                self._flush(org)

            if flush and not reseed:
                continue

            properties = self._seed_properties(org)
            units = self._seed_units(org, properties)
            self._seed_property_inventories(org, units)
            self._seed_ownerships(org, properties)
            vendors = self._seed_vendors(org)
            assets = self._seed_assets(org, properties, units)
            self._seed_work_orders(org, properties, units, vendors, assets)
            self._seed_preventive_schedules(org, properties, vendors, assets)
            self._seed_inspections(org, properties, units, assets)
            self._seed_service_requests(org, properties, units)
            self._seed_valuations(org, properties)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Done! Properties module populated for {org.name}: "
                    f"{len(properties)} properties, {len(units)} units, "
                    f"{len(vendors)} vendors, {len(assets)} assets."
                )
            )

    def _flush(self, org):
        self.stdout.write("Flushing previous Properties demo data ...")
        ServiceRequest.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()
        WorkOrder.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()
        Inspection.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()
        PreventiveSchedule.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()
        PropertyValuation.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()
        AssetComponent.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()
        MaintenanceVendor.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()
        PropertyOwnership.objects.filter(
            organization=org,
            property__description__icontains=DEMO_MARKER,
        ).delete()
        PropertyInventoryEvent.objects.filter(
            organization=org,
            notes__icontains=DEMO_MARKER,
        ).delete()
        PropertyInventory.objects.filter(
            organization=org,
            notes__icontains=DEMO_MARKER,
        ).delete()
        Unit.objects.filter(organization=org, property__description__icontains=DEMO_MARKER).delete()
        Property.objects.filter(organization=org, description__icontains=DEMO_MARKER).delete()
        self.stdout.write("  Flushed.")

    # ----- Properties -----

    def _seed_properties(self, org):
        today = date.today()
        properties = []
        for idx, p in enumerate(PROPERTY_DATA):
            acq_date = today - timedelta(days=random.randint(365, 2200))
            prop, _ = Property.objects.get_or_create(
                organization=org,
                name=p["name"],
                defaults={
                    "property_type": p["property_type"],
                    "classification": p["classification"],
                    "address": p["address"],
                    "description": f"{DEMO_MARKER} Demo property for dashboard testing",
                    "gps_latitude": p["gps_latitude"],
                    "gps_longitude": p["gps_longitude"],
                    "plot_number": p["plot_number"],
                    "acquisition_date": acq_date,
                    "acquisition_price": p["acquisition_price"],
                    "current_value": p["current_value"],
                    "total_area_sqft": p["total_area_sqft"],
                    "is_active": True,
                },
            )
            properties.append(prop)
        self.stdout.write(f"  {len(properties)} properties ready.")
        return properties

    # ----- Units -----

    def _seed_units(self, org, properties):
        statuses = ["available", "available", "available", "reserved", "sold", "leased"]
        all_units = []
        for prop, data in zip(properties, PROPERTY_DATA):
            for unit_num, floor, sqft, beds, baths, price in data["units"]:
                unit, _ = Unit.objects.get_or_create(
                    organization=org,
                    property=prop,
                    unit_number=unit_num,
                    defaults={
                        "floor": floor if floor else None,
                        "area_sqft": Decimal(str(sqft)),
                        "bedrooms": beds,
                        "bathrooms": baths,
                        "asking_price": Decimal(str(price)),
                        "status": random.choice(statuses),
                    },
                )
                all_units.append(unit)
        self.stdout.write(f"  {len(all_units)} units ready.")
        return all_units

    # ----- Property Inventory -----

    def _seed_property_inventories(self, org, units):
        """Create PropertyInventory records for each unit, mirroring unit status."""
        _UNIT_TO_INV = {
            "available": "available",
            "reserved": "reserved",
            "sold": "sold",
            "leased": "leased",
        }
        count = 0
        for unit in units:
            inv_status = _UNIT_TO_INV.get(unit.status, "available")
            inv, created = PropertyInventory.objects.get_or_create(
                organization=org,
                unit=unit,
                defaults={
                    "status": inv_status,
                    "list_price": unit.asking_price,
                    "allocated_to": f"Tenant — {unit.unit_number}" if inv_status == "leased" else (
                        f"Buyer — {unit.unit_number}" if inv_status == "sold" else ""
                    ),
                    "notes": f"{DEMO_MARKER} Auto-seeded inventory record",
                },
            )
            if created:
                PropertyInventoryEvent.objects.get_or_create(
                    organization=org,
                    inventory=inv,
                    event_type="listed",
                    defaults={
                        "from_status": "",
                        "to_status": inv_status,
                        "actor_name": "System (seed)",
                        "notes": f"{DEMO_MARKER} Initial listing event",
                    },
                )
            count += 1
        self.stdout.write(f"  {count} property inventory records ready.")

    # ----- Ownership -----

    def _seed_ownerships(self, org, properties):
        today = date.today()
        count = 0
        for prop, (structure, owner, deed) in zip(properties, OWNERSHIP_DATA):
            reg_auth = REGISTRATION_AUTHORITIES[0] if "LASG" in deed else (
                REGISTRATION_AUTHORITIES[1] if "ABUJ" in deed else REGISTRATION_AUTHORITIES[2]
            )
            PropertyOwnership.objects.get_or_create(
                organization=org,
                property=prop,
                legal_owner_name=owner,
                defaults={
                    "ownership_structure": structure,
                    "ownership_percentage": Decimal("100.00") if structure != "joint_venture" else Decimal("60.00"),
                    "title_deed_number": deed,
                    "registration_authority": reg_auth,
                    "date_of_registration": today - timedelta(days=random.randint(365, 2000)),
                },
            )
            count += 1
        self.stdout.write(f"  {count} ownership records ready.")

    # ----- Maintenance Vendors -----

    def _seed_vendors(self, org):
        vendors = []
        today = date.today()
        for name, contact, email, phone, spec, rating, rate in VENDOR_DATA:
            vendor, _ = MaintenanceVendor.objects.get_or_create(
                organization=org,
                name=name,
                defaults={
                    "contact_person": contact,
                    "email": email,
                    "phone": phone,
                    "specialization": spec,
                    "license_number": f"LIC-{random.randint(10000, 99999)}",
                    "license_expiry": today + timedelta(days=random.randint(90, 730)),
                    "insurance_expiry": today + timedelta(days=random.randint(60, 365)),
                    "rating": rating,
                    "hourly_rate": rate,
                    "is_active": True,
                    "notes": f"{DEMO_MARKER} Demo maintenance vendor",
                },
            )
            vendors.append(vendor)
        self.stdout.write(f"  {len(vendors)} maintenance vendors ready.")
        return vendors

    # ----- Asset Components -----

    def _seed_assets(self, org, properties, units):
        today = date.today()
        building_properties = [p for p in properties if p.property_type != "land"]
        assets = []
        existing_ids = set(AssetComponent.objects.values_list("component_id", flat=True))
        counter = 1

        for idx, (name, category, manufacturer, model, location) in enumerate(ASSET_DATA):
            prop = building_properties[idx % len(building_properties)]
            prop_units = [u for u in units if u.property_id == prop.id]

            component_id = f"AST-{org.id:02d}-{counter:04d}"
            while component_id in existing_ids:
                counter += 1
                component_id = f"AST-{org.id:02d}-{counter:04d}"

            asset, created = AssetComponent.objects.get_or_create(
                organization=org,
                property=prop,
                name=name,
                defaults={
                    "component_id": component_id,
                    "category": category,
                    "location_description": location,
                    "manufacturer": manufacturer,
                    "model_number": model,
                    "serial_number": f"SN-{random.randint(100000, 999999)}",
                    "installation_date": today - timedelta(days=random.randint(180, 1800)),
                    "warranty_expiry": today + timedelta(days=random.randint(-180, 730)),
                    "expected_useful_life_years": random.choice([5, 8, 10, 15, 20]),
                    "condition_rating": random.choice(["excellent", "good", "good", "good", "fair", "poor"]),
                    "last_inspection_date": today - timedelta(days=random.randint(7, 180)),
                    "unit": random.choice(prop_units) if prop_units and random.random() < 0.3 else None,
                    "is_active": True,
                    "notes": f"{DEMO_MARKER} Demo asset component",
                },
            )
            if created:
                existing_ids.add(component_id)
                counter += 1
            assets.append(asset)

        self.stdout.write(f"  {len(assets)} asset components ready.")
        return assets

    # ----- Work Orders -----

    def _seed_work_orders(self, org, properties, units, vendors, assets):
        today = date.today()
        building_properties = [p for p in properties if p.property_type != "land"]
        count = 0

        for title, category, priority, status, est_cost in WORK_ORDER_DATA:
            prop = random.choice(building_properties)
            prop_units = [u for u in units if u.property_id == prop.id]
            prop_assets = [a for a in assets if a.property_id == prop.id]
            matching_vendors = [v for v in vendors if v.specialization == category or v.specialization == "general"]

            reported_days_ago = random.randint(1, 90)
            due_days = reported_days_ago - random.randint(-30, 14)

            wo, created = WorkOrder.objects.get_or_create(
                organization=org,
                property=prop,
                title=title,
                defaults={
                    "description": f"{DEMO_MARKER} {title}",
                    "category": category,
                    "priority": priority,
                    "status": status,
                    "unit": random.choice(prop_units) if prop_units and random.random() < 0.5 else None,
                    "asset_component": random.choice(prop_assets) if prop_assets and random.random() < 0.4 else None,
                    "vendor": random.choice(matching_vendors) if matching_vendors else None,
                    "reported_by": random.choice(NIGERIAN_INSPECTORS),
                    "assigned_to": random.choice(NIGERIAN_INSPECTORS) if status != "open" else "",
                    "due_date": today - timedelta(days=due_days),
                    "estimated_cost": Decimal(str(est_cost)),
                    "actual_cost": Decimal(str(int(est_cost * random.uniform(0.8, 1.3)))) if status == "completed" else None,
                    "completed_date": today - timedelta(days=random.randint(1, 14)) if status == "completed" else None,
                    "notes": f"{DEMO_MARKER} Demo work order",
                },
            )
            count += 1

        self.stdout.write(f"  {count} work orders ready.")

    # ----- Preventive Schedules -----

    def _seed_preventive_schedules(self, org, properties, vendors, assets):
        today = date.today()
        building_properties = [p for p in properties if p.property_type != "land"]
        count = 0

        for title, category, frequency, est_cost, status in PREVENTIVE_SCHEDULE_DATA:
            prop = random.choice(building_properties)
            matching_vendors = [v for v in vendors if v.specialization == category or v.specialization == "general"]
            matching_assets = [a for a in assets if a.category == category]

            freq_days = {
                "daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30,
                "quarterly": 90, "semi_annual": 180, "annual": 365,
            }
            next_due = today + timedelta(days=random.randint(1, freq_days.get(frequency, 30)))
            last_done = today - timedelta(days=random.randint(1, freq_days.get(frequency, 30)))

            PreventiveSchedule.objects.get_or_create(
                organization=org,
                property=prop,
                title=title,
                defaults={
                    "description": f"{DEMO_MARKER} Recurring preventive maintenance",
                    "category": category,
                    "frequency": frequency,
                    "assigned_to": random.choice(NIGERIAN_INSPECTORS),
                    "next_due_date": next_due,
                    "last_completed_date": last_done if status == "active" else None,
                    "estimated_cost": Decimal(str(est_cost)),
                    "status": status,
                    "vendor": random.choice(matching_vendors) if matching_vendors else None,
                    "asset_component": random.choice(matching_assets) if matching_assets else None,
                    "notes": f"{DEMO_MARKER} Demo preventive schedule",
                },
            )
            count += 1

        self.stdout.write(f"  {count} preventive schedules ready.")

    # ----- Inspections -----

    def _seed_inspections(self, org, properties, units, assets):
        today = date.today()
        building_properties = [p for p in properties if p.property_type != "land"]
        count = 0

        for title, insp_type, status, rating, risk, compliance in INSPECTION_DATA:
            prop = random.choice(building_properties)
            prop_units = [u for u in units if u.property_id == prop.id]
            prop_assets = [a for a in assets if a.property_id == prop.id]

            sched_date = today - timedelta(days=random.randint(-60, 120))
            completed = sched_date + timedelta(days=random.randint(0, 5)) if status == "completed" else None

            Inspection.objects.get_or_create(
                organization=org,
                property=prop,
                title=title,
                defaults={
                    "inspection_type": insp_type,
                    "status": status,
                    "scheduled_date": sched_date,
                    "completed_date": completed,
                    "inspector": random.choice(NIGERIAN_INSPECTORS),
                    "findings": f"{DEMO_MARKER} Inspection findings for {title}" if status == "completed" else "",
                    "rating": rating,
                    "risk_level": risk,
                    "compliance_status": compliance,
                    "corrective_action_required": rating == "fail",
                    "follow_up_required": rating in ("fail", "conditional"),
                    "unit": random.choice(prop_units) if prop_units and "Unit" in title else None,
                    "asset_component": random.choice(prop_assets) if prop_assets and random.random() < 0.3 else None,
                    "notes": f"{DEMO_MARKER} Demo inspection record",
                },
            )
            count += 1

        self.stdout.write(f"  {count} inspections ready.")

    # ----- Service Requests -----

    def _seed_service_requests(self, org, properties, units):
        today = date.today()
        building_properties = [p for p in properties if p.property_type != "land"]
        count = 0

        for title, category, priority, status, requester in SERVICE_REQUEST_DATA:
            prop = random.choice(building_properties)
            prop_units = [u for u in units if u.property_id == prop.id]
            days_ago = random.randint(1, 60)

            ServiceRequest.objects.get_or_create(
                organization=org,
                property=prop,
                title=title,
                defaults={
                    "description": f"{DEMO_MARKER} {title} — reported by {requester}",
                    "category": category,
                    "priority": priority,
                    "status": status,
                    "requested_by": requester,
                    "assigned_to": random.choice(NIGERIAN_INSPECTORS) if status not in ("open",) else "",
                    "resolved_date": today - timedelta(days=random.randint(1, 7)) if status in ("resolved", "closed") else None,
                    "resolution_notes": f"{DEMO_MARKER} Issue resolved successfully" if status in ("resolved", "closed") else "",
                    "unit": random.choice(prop_units) if prop_units and random.random() < 0.6 else None,
                    "notes": f"{DEMO_MARKER} Demo service request",
                },
            )
            count += 1

        self.stdout.write(f"  {count} service requests ready.")

    # ----- Valuations -----

    def _seed_valuations(self, org, properties):
        today = date.today()
        count = 0

        for prop in properties:
            num_valuations = random.randint(1, 3)
            for i in range(num_valuations):
                val_date = today - timedelta(days=random.randint(30, 900) + i * 365)
                base_value = float(prop.current_value or prop.acquisition_price or 500000000)
                age_factor = 1 - (i * random.uniform(0.05, 0.15))
                val_amount = Decimal(str(int(base_value * age_factor)))

                val_types = ["appraisal", "internal", "market", "tax"]

                PropertyValuation.objects.get_or_create(
                    organization=org,
                    property=prop,
                    valuation_date=val_date,
                    defaults={
                        "value": val_amount,
                        "valuation_type": random.choice(val_types),
                        "appraiser": random.choice(NIGERIAN_APPRAISERS),
                        "notes": f"{DEMO_MARKER} Periodic property valuation",
                    },
                )
                count += 1

        self.stdout.write(f"  {count} valuations ready.")
