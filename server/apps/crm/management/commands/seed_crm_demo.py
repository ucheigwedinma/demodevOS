"""
Seed realistic demo data for the CRM dashboard.

Usage:
    python manage.py seed_crm_demo
    python manage.py seed_crm_demo --flush
    python manage.py seed_crm_demo --leads 96
    python manage.py seed_crm_demo --organization-id 2
    python manage.py seed_crm_demo --organization-id 1 --organization-id 2 --flush
"""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import Organization, UserProfile
from apps.crm.models import (
    Broker,
    BrokerCommissionEarning,
    BrokerTier,
    Campaign,
    CommunicationLog,
    FollowUpRule,
    FollowUpTask,
    Lead,
    LeadActivity,
    LeadSource,
    ReservationEvent,
    UnitReservation,
)
from apps.projects.models import Project
from apps.properties.models import Property, Unit

DEMO_MARKER = "[demo-seed]"
DEFAULT_LEAD_COUNT = 84

SOURCE_DATA = [
    "Website",
    "Referral",
    "Walk-in",
    "Property Listing Portals",
    "Social Campaign",
    "Broker Network",
]

TIER_DATA = [
    {
        "name": "Titanium",
        "min_deals": 20,
        "min_revenue": Decimal("50000000"),
        "commission_multiplier": Decimal("1.35"),
        "bonus_pct": Decimal("4.50"),
        "color": "#5b21b6",
        "sort_order": 1,
    },
    {
        "name": "Platinum",
        "min_deals": 12,
        "min_revenue": Decimal("24000000"),
        "commission_multiplier": Decimal("1.20"),
        "bonus_pct": Decimal("3.00"),
        "color": "#6d28d9",
        "sort_order": 2,
    },
    {
        "name": "Gold",
        "min_deals": 6,
        "min_revenue": Decimal("12000000"),
        "commission_multiplier": Decimal("1.10"),
        "bonus_pct": Decimal("2.00"),
        "color": "#7c3aed",
        "sort_order": 3,
    },
    {
        "name": "Silver",
        "min_deals": 2,
        "min_revenue": Decimal("5000000"),
        "commission_multiplier": Decimal("1.00"),
        "bonus_pct": Decimal("0.75"),
        "color": "#8b5cf6",
        "sort_order": 4,
    },
]

BROKER_DATA = [
    ("Amara Yusuf", "Aurora Realty", "+2348031001001"),
    ("David Ekanem", "Nexa Homes", "+2348031001002"),
    ("Rita Nnaji", "Axis Prime", "+2348031001003"),
    ("Seyi Bello", "BlueRock Estates", "+2348031001004"),
    ("Mariam Ahmed", "Vertex Properties", "+2348031001005"),
    ("Emeka Ude", "Seven Oaks", "+2348031001006"),
    ("Joy Otu", "Landmark Residential", "+2348031001007"),
    ("Femi Bassey", "Apex Brokerage", "+2348031001008"),
]

FIRST_NAMES = [
    "Amina", "Jide", "Tari", "Kunle", "Ife", "Tobi", "Chidera", "Yemi", "Laila", "Ire",
    "Bola", "Ada", "Musa", "Kemi", "Obi", "Nora", "Sadiq", "Ayo", "Binta", "Dami",
]

LAST_NAMES = [
    "Adeyemi", "Okafor", "Balogun", "Danjuma", "Umeh", "Ojo", "Nwachukwu", "Salami", "Aliyu", "Popoola",
    "Nwosu", "Bamidele", "Onuoha", "Akinola", "Chukwu", "Ibrahim", "Adebayo", "Abiola", "Uzor", "Lawal",
]


class Command(BaseCommand):
    help = "Seed demo CRM data for the CRM dashboard."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previously seeded CRM demo rows before seeding.",
        )
        parser.add_argument(
            "--leads",
            type=int,
            default=DEFAULT_LEAD_COUNT,
            help="Number of demo leads to generate (default: 84).",
        )
        parser.add_argument(
            "--organization-id",
            dest="organization_ids",
            action="append",
            type=int,
            help=(
                "Target a specific organization id. "
                "Repeat the flag to seed multiple organizations. "
                "If omitted, all organizations are seeded."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        organization_ids = options.get("organization_ids") or []
        org_qs = Organization.objects.order_by("id")
        if organization_ids:
            org_qs = org_qs.filter(id__in=organization_ids)
        orgs = list(org_qs)

        if not orgs:
            self.stderr.write(self.style.ERROR("No Organization found. Create one first."))
            return

        if organization_ids:
            found_ids = {org.id for org in orgs}
            missing_ids = [org_id for org_id in organization_ids if org_id not in found_ids]
            if missing_ids:
                self.stderr.write(
                    self.style.WARNING(
                        f"Skipping unknown organization ids: {', '.join(str(v) for v in missing_ids)}"
                    )
                )

        lead_target = max(24, int(options["leads"] or DEFAULT_LEAD_COUNT))
        org_summaries: list[dict[str, int | str]] = []

        for org in orgs:
            random.seed(20260308 + org.id)

            actor = self._resolve_actor(org)

            if options["flush"]:
                self._flush(org)

            self.stdout.write(
                f"Seeding CRM demo data for org: {org} (leads={lead_target}) ..."
            )

            sources = self._seed_sources(org)
            tiers = self._seed_tiers(org)
            brokers = self._seed_brokers(org, tiers)
            leads = self._seed_leads(org, actor, sources, brokers, lead_target)

            communication_count = self._seed_communications(org, actor, leads)
            rules = self._seed_follow_up_rules(org)
            follow_up_task_count = self._seed_follow_up_tasks(leads, rules, actor)
            campaign_count = self._seed_campaigns(org, actor)
            commission_count = self._seed_commissions(leads)
            reservation_count = self._seed_reservations(org, actor, leads)

            org_summaries.append(
                {
                    "org_id": org.id,
                    "org_name": org.name,
                    "lead_count": len(leads),
                    "broker_count": len(brokers),
                    "communication_count": communication_count,
                    "follow_up_task_count": follow_up_task_count,
                    "campaign_count": campaign_count,
                    "commission_count": commission_count,
                    "reservation_count": reservation_count,
                }
            )
            self.stdout.write(
                self.style.SUCCESS(
                    "Done! CRM dashboard is now populated with demo data "
                    f"for {org.name} ({len(leads)} leads, {reservation_count} reservations)."
                )
            )

        if len(org_summaries) > 1:
            total_leads = sum(int(row["lead_count"]) for row in org_summaries)
            total_brokers = sum(int(row["broker_count"]) for row in org_summaries)
            total_communications = sum(int(row["communication_count"]) for row in org_summaries)
            total_tasks = sum(int(row["follow_up_task_count"]) for row in org_summaries)
            total_campaigns = sum(int(row["campaign_count"]) for row in org_summaries)
            total_commissions = sum(int(row["commission_count"]) for row in org_summaries)
            total_reservations = sum(int(row["reservation_count"]) for row in org_summaries)
            self.stdout.write(
                self.style.SUCCESS(
                    "Cross-org CRM seeding complete: "
                    f"{len(org_summaries)} orgs, "
                    f"{total_leads} leads, "
                    f"{total_brokers} brokers, "
                    f"{total_communications} communications, "
                    f"{total_tasks} follow-up tasks, "
                    f"{total_campaigns} campaigns, "
                    f"{total_commissions} commissions, "
                    f"{total_reservations} reservations."
                )
            )

    def _resolve_actor(self, org):
        org_profile = (
            UserProfile.objects.select_related("user")
            .filter(organization=org)
            .order_by("user_id")
            .first()
        )
        if org_profile and org_profile.user:
            return org_profile.user

        user_model = get_user_model()
        user = user_model.objects.order_by("id").first()
        if not user:
            user = user_model.objects.create_user(
                username="crm.demo.user",
                email="crm.demo.user@example.com",
                password="demo12345",
                first_name="CRM",
                last_name="Demo",
            )

        profile, _ = UserProfile.objects.get_or_create(user=user)
        update_fields: list[str] = []
        if profile.organization_id != org.id:
            profile.organization = org
            update_fields.append("organization")
        if profile.role != "admin":
            profile.role = "admin"
            update_fields.append("role")
        if update_fields:
            profile.save(update_fields=update_fields)

        return user

    def _flush(self, org):
        self.stdout.write("Flushing previous CRM demo data ...")

        ReservationEvent.objects.filter(
            reservation__organization=org,
        ).filter(
            Q(notes__icontains=DEMO_MARKER)
            | Q(reservation__notes__icontains=DEMO_MARKER)
        ).delete()
        UnitReservation.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()

        BrokerCommissionEarning.objects.filter(
            broker__organization=org,
            notes__icontains=DEMO_MARKER,
        ).delete()
        FollowUpTask.objects.filter(
            rule__organization=org,
            notes__icontains=DEMO_MARKER,
        ).delete()
        CommunicationLog.objects.filter(
            organization=org,
            summary__icontains=DEMO_MARKER,
        ).delete()
        Campaign.objects.filter(organization=org, description__icontains=DEMO_MARKER).delete()
        FollowUpRule.objects.filter(organization=org, description__icontains=DEMO_MARKER).delete()

        Lead.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()
        Broker.objects.filter(organization=org, notes__icontains=DEMO_MARKER).delete()
        BrokerTier.objects.filter(organization=org, benefits__icontains=DEMO_MARKER).delete()
        LeadSource.objects.filter(organization=org, description__icontains=DEMO_MARKER).delete()

        Unit.objects.filter(organization=org, unit_number__startswith="CRM-D-").delete()
        Property.objects.filter(organization=org, name__icontains=DEMO_MARKER).delete()
        Project.objects.filter(organization=org, name__icontains=DEMO_MARKER).delete()

        self.stdout.write("  Flushed.")

    def _seed_sources(self, org):
        sources = []
        for index, name in enumerate(SOURCE_DATA, start=1):
            source, _ = LeadSource.objects.get_or_create(
                organization=org,
                name=name,
                defaults={
                    "code": f"SRC-{index:02d}",
                    "description": f"{DEMO_MARKER} CRM demo lead source",
                    "sort_order": index,
                    "is_active": True,
                },
            )
            sources.append(source)
        self.stdout.write(f"  {len(sources)} lead sources ready.")
        return sources

    def _seed_tiers(self, org):
        tiers = []
        for row in TIER_DATA:
            tier, _ = BrokerTier.objects.get_or_create(
                organization=org,
                name=row["name"],
                defaults={
                    "code": row["name"].upper(),
                    "min_deals": row["min_deals"],
                    "min_revenue": row["min_revenue"],
                    "commission_multiplier": row["commission_multiplier"],
                    "bonus_pct": row["bonus_pct"],
                    "evaluation_period_months": 12,
                    "benefits": f"{DEMO_MARKER} Tiered referral advantages",
                    "color": row["color"],
                    "sort_order": row["sort_order"],
                    "is_active": True,
                },
            )
            tiers.append(tier)
        self.stdout.write(f"  {len(tiers)} broker tiers ready.")
        return tiers

    def _seed_brokers(self, org, tiers):
        brokers = []
        for idx, (name, company, phone) in enumerate(BROKER_DATA, start=1):
            broker, _ = Broker.objects.get_or_create(
                organization=org,
                name=name,
                defaults={
                    "company": company,
                    "license_number": f"BRK-{idx:04d}",
                    "email": f"broker{idx}@demo-crm.com",
                    "phone": phone,
                    "commission_rate": Decimal(str(round(random.uniform(1.8, 3.2), 2))),
                    "tier": random.choice(tiers),
                    "status": Broker.Status.ACTIVE,
                    "notes": f"{DEMO_MARKER} CRM demo broker",
                },
            )
            brokers.append(broker)
        self.stdout.write(f"  {len(brokers)} brokers ready.")
        return brokers

    def _seed_leads(self, org, actor, sources, brokers, lead_target):
        leads = []
        today = timezone.localdate()
        stage_choices = [
            Lead.PipelineStage.INQUIRY,
            Lead.PipelineStage.QUALIFIED,
            Lead.PipelineStage.SITE_VISIT,
            Lead.PipelineStage.OFFER_MADE,
            Lead.PipelineStage.RESERVATION,
            Lead.PipelineStage.SPA_ISSUED,
        ]

        active_cutoff = int(lead_target * 0.68)
        won_cutoff = int(lead_target * 0.88)

        for i in range(lead_target):
            first_name = FIRST_NAMES[i % len(FIRST_NAMES)]
            last_name = LAST_NAMES[(i * 3) % len(LAST_NAMES)]
            email = f"crm.demo.lead.{i + 1:03d}@example.com"

            if i < active_cutoff:
                status = Lead.Status.ACTIVE
                stage = random.choice(stage_choices)
                lost_reason = ""
                close_date = None
                score_low, score_high = 48, 96
            elif i < won_cutoff:
                status = Lead.Status.WON
                stage = Lead.PipelineStage.CLOSED
                lost_reason = ""
                close_date = today - timedelta(days=random.randint(3, 80))
                score_low, score_high = 76, 99
            else:
                status = Lead.Status.LOST
                stage = random.choice(
                    [
                        Lead.PipelineStage.QUALIFIED,
                        Lead.PipelineStage.SITE_VISIT,
                        Lead.PipelineStage.OFFER_MADE,
                        Lead.PipelineStage.RESERVATION,
                    ]
                )
                lost_reason = random.choice(
                    [
                        "Pricing sensitivity",
                        "Preferred another location",
                        "Financing delay",
                        "Timeline mismatch",
                    ]
                )
                close_date = today - timedelta(days=random.randint(2, 45))
                score_low, score_high = 35, 74

            inquiry_date = today - timedelta(days=random.randint(12, 220))
            budget_min = random.randint(450_000, 2_200_000)
            budget_max = budget_min + random.randint(100_000, 1_400_000)
            assigned_to = actor if random.random() < 0.72 else None

            lead, created = Lead.objects.get_or_create(
                organization=org,
                email=email,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "phone": f"+234801{random.randint(1000000, 9999999)}",
                    "company": random.choice(["", "Prime Holdings", "Vertex Capital", "Nova Industrial"]),
                    "pipeline_stage": stage,
                    "status": status,
                    "priority": random.choice([Lead.Priority.MEDIUM, Lead.Priority.HIGH]),
                    "lead_type": random.choice([Lead.LeadType.BUYER, Lead.LeadType.INVESTOR]),
                    "source": random.choice(sources),
                    "broker": random.choice(brokers) if random.random() < 0.86 else None,
                    "budget_min": Decimal(str(budget_min)),
                    "budget_max": Decimal(str(budget_max)),
                    "payment_capability": random.choice(
                        [
                            Lead.PaymentCapability.CASH,
                            Lead.PaymentCapability.MORTGAGE,
                            Lead.PaymentCapability.INSTALLMENT,
                            Lead.PaymentCapability.MIXED,
                        ]
                    ),
                    "assigned_to": assigned_to,
                    "inquiry_date": inquiry_date,
                    "qualified_date": inquiry_date + timedelta(days=random.randint(2, 14))
                    if stage
                    in {
                        Lead.PipelineStage.QUALIFIED,
                        Lead.PipelineStage.SITE_VISIT,
                        Lead.PipelineStage.OFFER_MADE,
                        Lead.PipelineStage.RESERVATION,
                        Lead.PipelineStage.SPA_ISSUED,
                        Lead.PipelineStage.CLOSED,
                    }
                    else None,
                    "site_visit_date": inquiry_date + timedelta(days=random.randint(12, 26))
                    if stage
                    in {
                        Lead.PipelineStage.SITE_VISIT,
                        Lead.PipelineStage.OFFER_MADE,
                        Lead.PipelineStage.RESERVATION,
                        Lead.PipelineStage.SPA_ISSUED,
                        Lead.PipelineStage.CLOSED,
                    }
                    else None,
                    "offer_date": inquiry_date + timedelta(days=random.randint(18, 38))
                    if stage
                    in {
                        Lead.PipelineStage.OFFER_MADE,
                        Lead.PipelineStage.RESERVATION,
                        Lead.PipelineStage.SPA_ISSUED,
                        Lead.PipelineStage.CLOSED,
                    }
                    else None,
                    "reservation_date": inquiry_date + timedelta(days=random.randint(24, 50))
                    if stage
                    in {
                        Lead.PipelineStage.RESERVATION,
                        Lead.PipelineStage.SPA_ISSUED,
                        Lead.PipelineStage.CLOSED,
                    }
                    else None,
                    "spa_issued_date": inquiry_date + timedelta(days=random.randint(35, 70))
                    if stage in {Lead.PipelineStage.SPA_ISSUED, Lead.PipelineStage.CLOSED}
                    else None,
                    "closed_date": close_date,
                    "lost_reason": lost_reason,
                    "score": random.randint(score_low, score_high),
                    "notes": f"{DEMO_MARKER} CRM pipeline seed",
                },
            )

            if created:
                created_at = timezone.make_aware(
                    datetime.combine(
                        inquiry_date + timedelta(days=random.randint(0, 4)),
                        datetime.min.time(),
                    )
                ) + timedelta(hours=random.randint(8, 18), minutes=random.randint(0, 59))
                Lead.objects.filter(pk=lead.pk).update(
                    created_at=created_at,
                    updated_at=created_at + timedelta(days=random.randint(1, 60)),
                )
                lead.created_at = created_at

            leads.append(lead)

        self.stdout.write(f"  {len(leads)} leads ready.")
        return leads

    def _seed_communications(self, org, actor, leads):
        total = 0
        channels = [
            CommunicationLog.Channel.EMAIL,
            CommunicationLog.Channel.PHONE,
            CommunicationLog.Channel.WHATSAPP,
            CommunicationLog.Channel.SMS,
        ]
        statuses = [
            CommunicationLog.Status.SENT,
            CommunicationLog.Status.DELIVERED,
            CommunicationLog.Status.READ,
            CommunicationLog.Status.RECEIVED,
        ]

        for lead in random.sample(leads, k=min(len(leads), 56)):
            interactions = random.randint(1, 3)
            for _ in range(interactions):
                days_ago = random.randint(0, 88)
                communicated_at = timezone.now() - timedelta(
                    days=days_ago,
                    hours=random.randint(0, 20),
                    minutes=random.randint(0, 59),
                )
                channel = random.choice(channels)
                direction = (
                    CommunicationLog.Direction.INBOUND
                    if random.random() < 0.28
                    else CommunicationLog.Direction.OUTBOUND
                )
                CommunicationLog.objects.create(
                    organization=org,
                    lead=lead,
                    channel=channel,
                    direction=direction,
                    status=random.choice(statuses),
                    subject=f"{DEMO_MARKER} Follow-up touchpoint",
                    summary=f"{DEMO_MARKER} {channel} engagement logged for dashboard analytics.",
                    from_address="sales@demo-crm.com",
                    to_address=lead.email or lead.phone,
                    performed_by=actor,
                    communicated_at=communicated_at,
                )
                total += 1

        self.stdout.write(f"  {total} communication logs created.")
        return total

    def _seed_follow_up_rules(self, org):
        rules_data = [
            (
                "Inquiry First Response",
                Lead.PipelineStage.INQUIRY,
                24,
                LeadActivity.ActivityType.CALL,
            ),
            (
                "Post Visit Check-in",
                Lead.PipelineStage.SITE_VISIT,
                18,
                LeadActivity.ActivityType.FOLLOW_UP,
            ),
            (
                "Offer Progress Nudge",
                Lead.PipelineStage.OFFER_MADE,
                36,
                LeadActivity.ActivityType.EMAIL,
            ),
        ]

        rules = []
        for name, stage, hours, activity in rules_data:
            rule, _ = FollowUpRule.objects.get_or_create(
                organization=org,
                name=name,
                defaults={
                    "description": f"{DEMO_MARKER} SLA follow-up rule",
                    "trigger_stage": stage,
                    "follow_up_within_hours": hours,
                    "required_activity_type": activity,
                    "auto_assign_to_owner": True,
                    "is_active": True,
                },
            )
            rules.append(rule)

        self.stdout.write(f"  {len(rules)} follow-up rules ready.")
        return rules

    def _seed_follow_up_tasks(self, leads, rules, actor):
        active_leads = [lead for lead in leads if lead.status == Lead.Status.ACTIVE]
        sample = random.sample(active_leads, k=min(len(active_leads), 42))

        created_count = 0
        for lead in sample:
            rule = random.choice(rules)
            due_at = timezone.now() + timedelta(hours=random.randint(-30, 72))

            status_roll = random.random()
            if status_roll < 0.12:
                status = FollowUpTask.Status.COMPLETED
            elif status_roll < 0.23:
                status = FollowUpTask.Status.BREACHED
            elif status_roll < 0.48:
                status = FollowUpTask.Status.IN_PROGRESS
            else:
                status = FollowUpTask.Status.PENDING

            task = FollowUpTask.objects.create(
                rule=rule,
                lead=lead,
                assigned_to=lead.assigned_to or actor,
                status=status,
                due_at=due_at,
                completed_at=timezone.now() - timedelta(hours=random.randint(1, 18))
                if status == FollowUpTask.Status.COMPLETED
                else None,
                breached_at=timezone.now() - timedelta(hours=random.randint(1, 20))
                if status == FollowUpTask.Status.BREACHED
                else None,
                notes=f"{DEMO_MARKER} Auto-generated follow-up task",
            )
            created_count += 1

            if status == FollowUpTask.Status.COMPLETED:
                task.save(update_fields=["completed_at", "updated_at"])

        self.stdout.write(f"  {created_count} follow-up tasks created.")
        return created_count

    def _seed_campaigns(self, org, actor):
        now = timezone.now()
        campaigns_data = [
            {
                "name": "VIP Buyer Re-Engagement",
                "campaign_type": Campaign.CampaignType.EMAIL_BLAST,
                "channel": CommunicationLog.Channel.EMAIL,
                "status": Campaign.Status.RUNNING,
                "scheduled_at": now - timedelta(days=2),
                "started_at": now - timedelta(days=1, hours=6),
            },
            {
                "name": "Site Visit Reminder Wave",
                "campaign_type": Campaign.CampaignType.WHATSAPP_CAMPAIGN,
                "channel": CommunicationLog.Channel.WHATSAPP,
                "status": Campaign.Status.SCHEDULED,
                "scheduled_at": now + timedelta(days=1),
                "started_at": None,
            },
            {
                "name": "Offer Closure Push",
                "campaign_type": Campaign.CampaignType.FOLLOW_UP,
                "channel": CommunicationLog.Channel.SMS,
                "status": Campaign.Status.DRAFT,
                "scheduled_at": None,
                "started_at": None,
            },
        ]

        count = 0
        for payload in campaigns_data:
            campaign, created = Campaign.objects.get_or_create(
                organization=org,
                name=payload["name"],
                defaults={
                    "description": f"{DEMO_MARKER} CRM campaign demo",
                    "campaign_type": payload["campaign_type"],
                    "status": payload["status"],
                    "channel": payload["channel"],
                    "subject": payload["name"],
                    "body": "Seeded campaign body for dashboard analytics.",
                    "scheduled_at": payload["scheduled_at"],
                    "started_at": payload["started_at"],
                    "created_by": actor,
                    "total_recipients": random.randint(25, 110),
                    "sent_count": random.randint(20, 105),
                    "delivered_count": random.randint(18, 98),
                    "opened_count": random.randint(8, 67),
                    "clicked_count": random.randint(4, 28),
                    "failed_count": random.randint(0, 7),
                },
            )
            if created:
                count += 1

        self.stdout.write(f"  {count} campaigns created.")
        return count

    def _seed_commissions(self, leads):
        won_leads = [lead for lead in leads if lead.status == Lead.Status.WON and lead.broker_id]
        sample = won_leads[: min(len(won_leads), 24)]

        created = 0
        for lead in sample:
            deal_value = lead.budget_max or lead.budget_min or Decimal("1000000")
            rate = lead.broker.commission_rate or Decimal("2.50")
            base = (Decimal(deal_value) * Decimal(rate) / Decimal("100")).quantize(Decimal("0.01"))
            multiplier = lead.broker.tier.commission_multiplier if lead.broker and lead.broker.tier else Decimal("1.00")
            bonus_pct = lead.broker.tier.bonus_pct if lead.broker and lead.broker.tier else Decimal("0")
            bonus = (base * bonus_pct / Decimal("100")).quantize(Decimal("0.01"))
            total = (base * multiplier + bonus).quantize(Decimal("0.01"))

            status = random.choice(
                [
                    BrokerCommissionEarning.Status.PAID,
                    BrokerCommissionEarning.Status.APPROVED,
                    BrokerCommissionEarning.Status.PENDING,
                ]
            )
            created_at = timezone.make_aware(
                datetime.combine(lead.closed_date or date.today(), datetime.min.time())
            ) + timedelta(hours=random.randint(8, 17), minutes=random.randint(0, 55))

            earning = BrokerCommissionEarning.objects.create(
                broker=lead.broker,
                lead=lead,
                project=None,
                deal_value=Decimal(deal_value),
                commission_rate=Decimal(rate),
                base_commission=base,
                tier_multiplier=multiplier,
                bonus_amount=bonus,
                total_commission=total,
                trigger_stage="closed",
                triggered_at=created_at,
                status=status,
                paid_at=created_at + timedelta(days=4) if status == BrokerCommissionEarning.Status.PAID else None,
                notes=f"{DEMO_MARKER} Seeded broker commission",
            )
            BrokerCommissionEarning.objects.filter(pk=earning.pk).update(created_at=created_at)
            created += 1

        self.stdout.write(f"  {created} broker commission earnings created.")
        return created

    def _seed_reservations(self, org, actor, leads):
        project = Project.objects.filter(organization=org).order_by("id").first()
        if project is None:
            project = Project.objects.create(
                organization=org,
                name=f"CRM Demo Project {DEMO_MARKER}",
                description="CRM seeded project for reservation analytics.",
            )

        property_obj = Property.objects.filter(organization=org).order_by("id").first()
        if property_obj is None:
            property_obj = Property.objects.create(
                organization=org,
                name=f"CRM Demo Residences {DEMO_MARKER}",
                property_type=Property.PropertyType.ESTATE,
                classification=Property.Classification.UNDER_DEVELOPMENT,
                address="10 Demo Crescent, Victoria Island, Lagos",
                description="CRM seeded property for reservation analytics.",
                is_active=True,
            )

        units = []
        for idx in range(1, 7):
            unit, _ = Unit.objects.get_or_create(
                organization=org,
                property=property_obj,
                unit_number=f"CRM-D-{idx:02d}",
                defaults={
                    "floor": 4 + idx,
                    "area_sqft": Decimal(str(980 + idx * 45)),
                    "bedrooms": 2 + (idx % 2),
                    "bathrooms": 2,
                    "asking_price": Decimal(str(850000 + idx * 180000)),
                    "status": Unit.UnitStatus.AVAILABLE,
                },
            )
            units.append(unit)

        candidate_leads = [
            lead for lead in leads if lead.status in {Lead.Status.ACTIVE, Lead.Status.WON}
        ]
        if not candidate_leads:
            return 0

        reservation_rows = [
            (UnitReservation.Status.HOLD, Unit.UnitStatus.RESERVED, 7),
            (UnitReservation.Status.PAYMENT_PENDING, Unit.UnitStatus.RESERVED, 6),
            (UnitReservation.Status.CONVERTED, Unit.UnitStatus.SOLD, 20),
            (UnitReservation.Status.CONVERTED, Unit.UnitStatus.SOLD, 33),
            (UnitReservation.Status.CANCELLED, Unit.UnitStatus.AVAILABLE, 14),
        ]

        created = 0
        for idx, (reservation_status, unit_status, days_ago) in enumerate(reservation_rows):
            lead = candidate_leads[idx % len(candidate_leads)]
            unit = units[idx % len(units)]

            total_price = unit.asking_price or Decimal(str(900000 + idx * 100000))
            hold_expires_at = timezone.now() + timedelta(hours=24 - idx * 3)
            reservation = UnitReservation.objects.create(
                organization=org,
                lead=lead,
                unit=unit,
                project=project,
                status=reservation_status,
                total_price=total_price,
                deposit_amount=(Decimal(total_price) * Decimal("0.10")).quantize(Decimal("0.01")),
                reservation_fee=(Decimal(total_price) * Decimal("0.02")).quantize(Decimal("0.01")),
                hold_expires_at=hold_expires_at,
                payment_deadline=hold_expires_at + timedelta(days=3),
                reservation_date=timezone.localdate() - timedelta(days=days_ago),
                confirmation_date=timezone.now() - timedelta(days=max(1, days_ago - 1)),
                performed_by=actor,
                notes=f"{DEMO_MARKER} CRM reservation seed",
            )

            unit.status = unit_status
            unit.save(update_fields=["status", "updated_at"])

            ReservationEvent.objects.create(
                reservation=reservation,
                event_type=ReservationEvent.EventType.HOLD_PLACED,
                performed_by=actor,
                notes=f"{DEMO_MARKER} Reservation lifecycle event",
                metadata={
                    "seeded": True,
                    "status": reservation_status,
                },
            )
            created += 1

        self.stdout.write(f"  {created} reservation records created.")
        return created
