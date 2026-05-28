from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)

from .asset_workflows import derive_maintenance_due_date
from .models import AssetComponent, PredictiveMaintenanceAlert, PredictiveMaintenanceRule, PreventiveSchedule, WorkOrder

SLA_HOURS_BY_PRIORITY = {
    WorkOrder.Priority.LOW: 72,
    WorkOrder.Priority.MEDIUM: 24,
    WorkOrder.Priority.HIGH: 8,
    WorkOrder.Priority.CRITICAL: 4,
    WorkOrder.Priority.URGENT: 4,
}

OPEN_WORK_ORDER_STATUSES = {
    WorkOrder.Status.OPEN,
    WorkOrder.Status.ASSIGNED,
    WorkOrder.Status.IN_PROGRESS,
    WorkOrder.Status.ON_HOLD,
}


def work_order_sla_hours_for(priority: str) -> int:
    return SLA_HOURS_BY_PRIORITY.get(priority, SLA_HOURS_BY_PRIORITY[WorkOrder.Priority.MEDIUM])


def work_order_sla_status_for(work_order: WorkOrder, *, now: datetime | None = None) -> str:
    current_time = now or timezone.now()
    today = timezone.localdate()
    if work_order.status == WorkOrder.Status.VERIFIED:
        return "verified"
    if work_order.status == WorkOrder.Status.COMPLETED:
        if work_order.sla_due_at and work_order.completed_date:
            completed_at = timezone.make_aware(
                datetime.combine(work_order.completed_date, datetime.max.time())
            )
            return "breached" if completed_at > work_order.sla_due_at else "met"
        if work_order.due_date and work_order.completed_date:
            return "breached" if work_order.completed_date > work_order.due_date else "met"
        return "completed"
    if work_order.status not in OPEN_WORK_ORDER_STATUSES:
        return "inactive"
    if work_order.sla_due_at:
        if current_time > work_order.sla_due_at:
            return "overdue"
        if current_time + timedelta(hours=4) >= work_order.sla_due_at:
            return "at_risk"
        return "on_track"
    if work_order.due_date:
        if work_order.due_date < today:
            return "overdue"
        if work_order.due_date <= today + timedelta(days=1):
            return "at_risk"
    return "on_track"


def _build_context_values(*, property_obj=None, facility=None, facility_space=None, asset_component=None, unit=None):
    resolved_property = property_obj
    resolved_facility = facility
    resolved_space = facility_space
    resolved_unit = unit

    if asset_component is not None:
        resolved_property = asset_component.property
        if asset_component.facility_id:
            resolved_facility = asset_component.facility
        if asset_component.facility_space_id:
            resolved_space = asset_component.facility_space
        if asset_component.unit_id:
            resolved_unit = asset_component.unit

    if facility_space is not None:
        resolved_space = facility_space
        resolved_facility = facility_space.facility
        resolved_property = facility_space.facility.property
        resolved_unit = facility_space.unit

    if facility is not None:
        resolved_facility = facility
        resolved_property = facility.property

    if unit is not None and resolved_unit is None:
        resolved_unit = unit
    if unit is not None and resolved_property is None:
        resolved_property = unit.property

    return {
        "property": resolved_property,
        "facility": resolved_facility,
        "facility_space": resolved_space,
        "unit": resolved_unit,
    }


def _validate_context_values(*, property_obj=None, facility=None, facility_space=None, asset_component=None, unit=None):
    errors: dict[str, str] = {}

    if facility and property_obj and facility.property_id != property_obj.id:
        errors["facility"] = "Selected facility does not belong to the selected property."

    if facility_space:
        if facility and facility_space.facility_id != facility.id:
            errors["facility_space"] = "Selected room / space does not belong to the selected facility."
        if property_obj and facility_space.facility.property_id != property_obj.id:
            errors["facility_space"] = "Selected room / space does not belong to the selected property."

    if unit and property_obj and unit.property_id != property_obj.id:
        errors["unit"] = "Selected unit does not belong to the selected property."

    if asset_component:
        if property_obj and asset_component.property_id != property_obj.id:
            errors["asset_component"] = "Selected asset does not belong to the selected property."
        if facility and asset_component.facility_id and asset_component.facility_id != facility.id:
            errors["asset_component"] = "Selected asset does not belong to the selected facility."
        if facility_space and asset_component.facility_space_id and asset_component.facility_space_id != facility_space.id:
            errors["asset_component"] = "Selected asset does not belong to the selected room / space."

    if errors:
        raise ValidationError(errors)


def normalize_work_order_payload(attrs: dict, *, instance: WorkOrder | None = None) -> dict:
    data = dict(attrs)
    property_obj = data.get("property", getattr(instance, "property", None))
    facility = data.get("facility", getattr(instance, "facility", None))
    facility_space = data.get("facility_space", getattr(instance, "facility_space", None))
    asset_component = data.get("asset_component", getattr(instance, "asset_component", None))
    unit = data.get("unit", getattr(instance, "unit", None))

    _validate_context_values(
        property_obj=property_obj,
        facility=facility,
        facility_space=facility_space,
        asset_component=asset_component,
        unit=unit,
    )

    resolved = _build_context_values(
        property_obj=property_obj,
        facility=facility,
        facility_space=facility_space,
        asset_component=asset_component,
        unit=unit,
    )
    if resolved["property"] is None:
        raise ValidationError({"property": "Provide a property directly or via facility, room / space, or asset."})

    data.update(resolved)

    priority = data.get("priority", getattr(instance, "priority", WorkOrder.Priority.MEDIUM))
    if not data.get("sla_target_hours") and not getattr(instance, "sla_target_hours", None):
        data["sla_target_hours"] = work_order_sla_hours_for(priority)

    now = timezone.now()
    if not data.get("sla_due_at") and not getattr(instance, "sla_due_at", None):
        data["sla_due_at"] = now + timedelta(hours=int(data.get("sla_target_hours") or work_order_sla_hours_for(priority)))

    if not data.get("due_date") and not getattr(instance, "due_date", None):
        sla_due_at = data.get("sla_due_at") or getattr(instance, "sla_due_at", None)
        if sla_due_at is not None:
            data["due_date"] = timezone.localtime(sla_due_at).date()

    status_value = data.get("status", getattr(instance, "status", WorkOrder.Status.OPEN))
    assigned_to = (data.get("assigned_to", getattr(instance, "assigned_to", "")) or "").strip()
    if assigned_to and status_value == WorkOrder.Status.OPEN:
        status_value = WorkOrder.Status.ASSIGNED
        data["status"] = status_value

    if status_value == WorkOrder.Status.IN_PROGRESS and not data.get("started_at") and not getattr(instance, "started_at", None):
        data["started_at"] = now

    if status_value in {WorkOrder.Status.COMPLETED, WorkOrder.Status.VERIFIED}:
        if not data.get("completed_date") and not getattr(instance, "completed_date", None):
            data["completed_date"] = timezone.localdate()
    if status_value == WorkOrder.Status.VERIFIED:
        if not data.get("verified_at") and not getattr(instance, "verified_at", None):
            data["verified_at"] = now

    return data


def normalize_preventive_schedule_payload(attrs: dict, *, instance: PreventiveSchedule | None = None) -> dict:
    data = dict(attrs)
    property_obj = data.get("property", getattr(instance, "property", None))
    facility = data.get("facility", getattr(instance, "facility", None))
    facility_space = data.get("facility_space", getattr(instance, "facility_space", None))
    asset_component = data.get("asset_component", getattr(instance, "asset_component", None))

    _validate_context_values(
        property_obj=property_obj,
        facility=facility,
        facility_space=facility_space,
        asset_component=asset_component,
    )
    resolved = _build_context_values(
        property_obj=property_obj,
        facility=facility,
        facility_space=facility_space,
        asset_component=asset_component,
    )
    if resolved["property"] is None:
        raise ValidationError({"property": "Provide a property directly or via facility, room / space, or asset."})
    data.update({key: value for key, value in resolved.items() if key != "unit"})

    if data.get("asset_component") and not data.get("title"):
        data["title"] = f"{data['asset_component'].component_id} preventive maintenance"

    if not data.get("sla_target_hours") and not getattr(instance, "sla_target_hours", None):
        priority = data.get("priority", getattr(instance, "priority", WorkOrder.Priority.MEDIUM))
        data["sla_target_hours"] = work_order_sla_hours_for(priority)

    if not data.get("next_due_date") and not getattr(instance, "next_due_date", None):
        asset = data.get("asset_component")
        if asset and asset.maintenance_next_due_date:
            data["next_due_date"] = asset.maintenance_next_due_date
        elif asset and asset.maintenance_frequency:
            data["next_due_date"] = derive_maintenance_due_date(
                frequency=asset.maintenance_frequency,
                commissioned_date=asset.commissioned_date,
                installation_date=asset.installation_date,
            )

    if data.get("last_completed_date") and not data.get("next_due_date"):
        frequency = data.get("frequency", getattr(instance, "frequency", ""))
        next_due_date = derive_maintenance_due_date(
            frequency=frequency,
            commissioned_date=data["last_completed_date"],
            installation_date=None,
            today=data["last_completed_date"],
        )
        if next_due_date is not None:
            data["next_due_date"] = next_due_date

    return data


def normalize_predictive_rule_payload(attrs: dict, *, instance: PredictiveMaintenanceRule | None = None) -> dict:
    data = dict(attrs)
    property_obj = data.get("property", getattr(instance, "property", None))
    facility = data.get("facility", getattr(instance, "facility", None))
    facility_space = data.get("facility_space", getattr(instance, "facility_space", None))
    asset_component = data.get("asset_component", getattr(instance, "asset_component", None))

    _validate_context_values(
        property_obj=property_obj,
        facility=facility,
        facility_space=facility_space,
        asset_component=asset_component,
    )
    resolved = _build_context_values(
        property_obj=property_obj,
        facility=facility,
        facility_space=facility_space,
        asset_component=asset_component,
    )
    if resolved["property"] is None:
        raise ValidationError({"property": "Provide a property directly or via facility, room / space, or asset."})
    data.update({key: value for key, value in resolved.items() if key != "unit"})

    if (
        data.get("runtime_hours_threshold") is None
        and data.get("cycle_threshold") is None
        and not data.get("alert_on_offline")
        and not data.get("alert_on_fault")
    ):
        raise ValidationError(
            {
                "non_field_errors": [
                    "Configure at least one predictive trigger: runtime hours, cycle count, offline alert, or fault alert."
                ]
            }
        )

    if not data.get("sla_target_hours") and not getattr(instance, "sla_target_hours", None):
        priority = data.get("priority", getattr(instance, "priority", WorkOrder.Priority.HIGH))
        data["sla_target_hours"] = work_order_sla_hours_for(priority)

    return data


def advance_preventive_schedule(schedule: PreventiveSchedule, *, completion_date: date | None = None) -> PreventiveSchedule:
    completion = completion_date or timezone.localdate()
    next_due_date = derive_maintenance_due_date(
        frequency=schedule.frequency,
        commissioned_date=completion,
        installation_date=None,
        today=completion,
    )
    dirty_fields: list[str] = []
    if schedule.last_completed_date != completion:
        schedule.last_completed_date = completion
        dirty_fields.append("last_completed_date")
    if next_due_date and schedule.next_due_date != next_due_date:
        schedule.next_due_date = next_due_date
        dirty_fields.append("next_due_date")
    if schedule.status != PreventiveSchedule.Status.ACTIVE:
        schedule.status = PreventiveSchedule.Status.ACTIVE
        dirty_fields.append("status")
    if dirty_fields:
        schedule.save(update_fields=dirty_fields + ["updated_at"])
    return schedule


def sync_follow_on_workflows_for_work_order(work_order_id: int) -> None:
    work_order = (
        WorkOrder.objects.select_related("preventive_schedule")
        .prefetch_related("predictive_alerts")
        .get(pk=work_order_id)
    )
    if work_order.preventive_schedule_id and work_order.status in {
        WorkOrder.Status.COMPLETED,
        WorkOrder.Status.VERIFIED,
    }:
        schedule = work_order.preventive_schedule
        advance_preventive_schedule(
            schedule,
            completion_date=work_order.completed_date,
        )

        try:
            from apps.accounts.models import UserProfile
            from apps.notifications.services import Notification, dispatch_workflow_notification

            org = work_order.organization
            admins = [
                p.user
                for p in UserProfile.objects.filter(
                    organization=org, role="admin", user__is_active=True
                ).select_related("user")
            ]
            if admins:
                dispatch_workflow_notification(
                    organization=org,
                    event_key="preventive_schedule_advanced",
                    recipients=admins,
                    fallback_title=f"Preventive Schedule Advanced — {schedule.title[:50]}",
                    fallback_message=(
                        f"Preventive maintenance schedule '{schedule.title}' has been "
                        f"automatically advanced following the completion of work order "
                        f"{getattr(work_order, 'wo_number', work_order.pk)}. "
                        f"Next due date: {schedule.next_due_date}."
                    ),
                    fallback_category=Notification.Category.SYSTEM,
                )
        except Exception:
            logger.debug("Preventive schedule notification skipped", exc_info=True)

    alerts_resolved = 0
    if work_order.status in {WorkOrder.Status.COMPLETED, WorkOrder.Status.VERIFIED}:
        alerts_resolved = work_order.predictive_alerts.filter(
            status__in=[
                PredictiveMaintenanceAlert.Status.OPEN,
                PredictiveMaintenanceAlert.Status.ACKNOWLEDGED,
                PredictiveMaintenanceAlert.Status.WORK_ORDER_CREATED,
            ]
        ).update(
            status=PredictiveMaintenanceAlert.Status.RESOLVED,
            resolved_at=timezone.now(),
            updated_at=timezone.now(),
        )

    if alerts_resolved > 0:
        try:
            from apps.accounts.models import UserProfile
            from apps.notifications.services import Notification, dispatch_workflow_notification

            org = work_order.organization
            admins = [
                p.user
                for p in UserProfile.objects.filter(
                    organization=org, role="admin", user__is_active=True
                ).select_related("user")
            ]
            if admins:
                dispatch_workflow_notification(
                    organization=org,
                    event_key="predictive_alerts_resolved",
                    recipients=admins,
                    fallback_title=f"Predictive Alerts Resolved — {getattr(work_order, 'wo_number', work_order.pk)}",
                    fallback_message=(
                        f"{alerts_resolved} predictive maintenance alert(s) have been automatically "
                        f"resolved following the completion of work order "
                        f"{getattr(work_order, 'wo_number', work_order.pk)}."
                    ),
                    fallback_category=Notification.Category.SYSTEM,
                )
        except Exception:
            logger.debug("Predictive alert resolution notification skipped", exc_info=True)


def _schedule_generation_date(schedule: PreventiveSchedule) -> date:
    return schedule.next_due_date - timedelta(days=int(schedule.generate_days_before or 0))


def generate_due_preventive_work_orders(organization, *, today: date | None = None) -> dict[str, int]:
    current_day = today or timezone.localdate()
    created = 0
    skipped = 0

    schedules = PreventiveSchedule.objects.filter(
        organization=organization,
        status=PreventiveSchedule.Status.ACTIVE,
        auto_create_work_orders=True,
    ).select_related(
        "property",
        "facility",
        "facility_space",
        "facility_space__unit",
        "asset_component",
        "vendor",
    )

    for schedule in schedules:
        if _schedule_generation_date(schedule) > current_day:
            skipped += 1
            continue
        if schedule.last_generated_date == schedule.next_due_date:
            skipped += 1
            continue
        if WorkOrder.objects.filter(
            organization=organization,
            preventive_schedule=schedule,
            status__in=OPEN_WORK_ORDER_STATUSES,
        ).exists():
            skipped += 1
            continue

        payload = normalize_work_order_payload(
            {
                "property": schedule.property,
                "facility": schedule.facility,
                "facility_space": schedule.facility_space,
                "asset_component": schedule.asset_component,
                "vendor": schedule.vendor,
                "title": schedule.title,
                "description": schedule.description or f"Preventive maintenance due for {schedule.title}.",
                "maintenance_mode": WorkOrder.MaintenanceMode.PREVENTIVE,
                "category": schedule.category,
                "priority": schedule.priority,
                "status": WorkOrder.Status.OPEN,
                "assigned_to": schedule.assigned_to,
                "due_date": schedule.next_due_date,
                "sla_target_hours": schedule.sla_target_hours,
                "notes": "Auto-generated from preventive maintenance schedule.",
                "preventive_schedule": schedule,
            }
        )
        work_order = WorkOrder.objects.create(
            organization=organization,
            **payload,
        )
        schedule.last_work_order = work_order
        schedule.last_generated_date = schedule.next_due_date
        schedule.save(update_fields=["last_work_order", "last_generated_date", "updated_at"])
        created += 1

    return {"created": created, "skipped": skipped}


def _rule_trigger_rows(rule: PredictiveMaintenanceRule) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    asset = rule.asset_component
    if asset and rule.alert_on_offline and asset.iot_status == AssetComponent.IoTStatus.OFFLINE:
        rows.append(
            {
                "trigger_type": PredictiveMaintenanceAlert.TriggerType.IOT_OFFLINE,
                "message": f"IoT device for {asset.name} is currently offline.",
                "iot_status": asset.iot_status,
            }
        )
    if asset and rule.alert_on_fault and asset.iot_status == AssetComponent.IoTStatus.FAULT:
        rows.append(
            {
                "trigger_type": PredictiveMaintenanceAlert.TriggerType.IOT_FAULT,
                "message": f"IoT device for {asset.name} reported a fault state.",
                "iot_status": asset.iot_status,
            }
        )
    if rule.runtime_hours_threshold is not None and rule.runtime_hours_reading is not None and rule.runtime_hours_reading >= rule.runtime_hours_threshold:
        rows.append(
            {
                "trigger_type": PredictiveMaintenanceAlert.TriggerType.RUNTIME_HOURS,
                "message": (
                    f"Runtime reading {rule.runtime_hours_reading}h exceeded the threshold "
                    f"of {rule.runtime_hours_threshold}h."
                ),
                "runtime_hours_reading": rule.runtime_hours_reading,
            }
        )
    if rule.cycle_threshold is not None and rule.cycle_reading is not None and rule.cycle_reading >= rule.cycle_threshold:
        rows.append(
            {
                "trigger_type": PredictiveMaintenanceAlert.TriggerType.CYCLE_COUNT,
                "message": (
                    f"Cycle reading {rule.cycle_reading} exceeded the threshold "
                    f"of {rule.cycle_threshold}."
                ),
                "cycle_reading": rule.cycle_reading,
            }
        )
    return rows


def evaluate_predictive_rules(organization, *, rule_ids: list[int] | None = None) -> dict[str, int]:
    created_alerts = 0
    created_work_orders = 0
    skipped = 0
    now = timezone.now()

    rules = PredictiveMaintenanceRule.objects.filter(
        organization=organization,
        is_active=True,
    ).select_related(
        "property",
        "facility",
        "facility_space",
        "facility_space__unit",
        "asset_component",
    )
    if rule_ids:
        rules = rules.filter(id__in=rule_ids)

    for rule in rules:
        trigger_rows = _rule_trigger_rows(rule)
        rule.last_evaluated_at = now
        if not trigger_rows:
            rule.save(update_fields=["last_evaluated_at", "updated_at"])
            skipped += 1
            continue

        for trigger in trigger_rows:
            if PredictiveMaintenanceAlert.objects.filter(
                organization=organization,
                rule=rule,
                trigger_type=trigger["trigger_type"],
                status__in=[
                    PredictiveMaintenanceAlert.Status.OPEN,
                    PredictiveMaintenanceAlert.Status.ACKNOWLEDGED,
                    PredictiveMaintenanceAlert.Status.WORK_ORDER_CREATED,
                ],
            ).exists():
                skipped += 1
                continue

            alert = PredictiveMaintenanceAlert.objects.create(
                organization=organization,
                rule=rule,
                property=rule.property,
                facility=rule.facility,
                facility_space=rule.facility_space,
                asset_component=rule.asset_component,
                title=f"{rule.title} alert",
                message=str(trigger["message"]),
                priority=rule.priority,
                trigger_type=str(trigger["trigger_type"]),
                runtime_hours_reading=trigger.get("runtime_hours_reading"),
                cycle_reading=trigger.get("cycle_reading"),
                iot_status=str(trigger.get("iot_status") or ""),
            )
            created_alerts += 1

            if rule.auto_create_work_order:
                payload = normalize_work_order_payload(
                    {
                        "property": rule.property,
                        "facility": rule.facility,
                        "facility_space": rule.facility_space,
                        "asset_component": rule.asset_component,
                        "title": f"Predictive maintenance - {rule.title}",
                        "description": str(trigger["message"]),
                        "maintenance_mode": WorkOrder.MaintenanceMode.PREDICTIVE,
                        "category": (
                            rule.asset_component.category
                            if rule.asset_component and rule.asset_component.category in {choice for choice, _ in WorkOrder.Category.choices}
                            else WorkOrder.Category.GENERAL
                        ),
                        "priority": rule.priority,
                        "status": WorkOrder.Status.OPEN,
                        "assigned_to": rule.assigned_to,
                        "sla_target_hours": rule.sla_target_hours,
                        "notes": "Auto-created from predictive maintenance evaluation.",
                    }
                )
                work_order = WorkOrder.objects.create(
                    organization=organization,
                    **payload,
                )
                alert.work_order = work_order
                alert.status = PredictiveMaintenanceAlert.Status.WORK_ORDER_CREATED
                alert.save(update_fields=["work_order", "status", "updated_at"])
                created_work_orders += 1

        rule.last_triggered_at = now
        rule.save(update_fields=["last_evaluated_at", "last_triggered_at", "updated_at"])

    return {
        "created_alerts": created_alerts,
        "created_work_orders": created_work_orders,
        "skipped": skipped,
    }


def run_maintenance_automation(organization, *, rule_ids: list[int] | None = None) -> dict[str, int]:
    with transaction.atomic():
        preventive_result = generate_due_preventive_work_orders(organization)
        predictive_result = evaluate_predictive_rules(organization, rule_ids=rule_ids)
    return {
        "preventive_work_orders_created": preventive_result["created"],
        "preventive_work_orders_skipped": preventive_result["skipped"],
        "predictive_alerts_created": predictive_result["created_alerts"],
        "predictive_work_orders_created": predictive_result["created_work_orders"],
        "predictive_rules_skipped": predictive_result["skipped"],
    }
