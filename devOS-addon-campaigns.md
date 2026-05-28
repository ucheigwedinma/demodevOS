# Add-On Upsell Campaign System

> Usage-based, automated campaigns that target users with personalised add-on
> prompts based on what they actually used during their trial.

---

## 1. How It Works

```
TRIAL (14 days)                         POST-TRIAL
 |                                        |
 |  User accesses CRM 23 times           |  "You used CRM 23 times during
 |  User accesses Tenants 0 times        |   your trial. Keep it for $75/mo."
 |  User accesses Facility Mgmt 4 times  |
 |                                        |  Shows CRM + Facility Mgmt
 |  Middleware logs every API request     |  Skips Tenants (never touched)
 |  by module to ModuleAccessLog         |
 v                                        v
```

**Three stages:**

1. **Track** -- lightweight middleware records module access per org during trial
2. **Analyse** -- on trial end, aggregate usage into a per-org add-on report
3. **Prompt** -- show in-app upsell + send email for add-ons the user actually used

---

## 2. Backend: Module Access Tracking

### New model: `ModuleAccessLog`

```
App:    apps/analytics/ (or apps/accounts/)
Table:  module_access_log

Fields:
  organization    FK -> Organization
  module_key      CharField (Module enum value)
  access_date     DateField (one row per org per module per day)
  access_count    IntegerField (incremented per API hit)
  created_at      DateTimeField (auto)

Unique constraint: (organization, module_key, access_date)
```

**Why per-day granularity?** Keeps the table small (max ~15 modules x 14 days = 210 rows per org per trial). Enough for "you used X 23 times" messaging without storing every request.

### Middleware: `ModuleAccessTrackingMiddleware`

Placed after `OrganizationMiddleware`. Only active for trialing orgs.

```python
class ModuleAccessTrackingMiddleware:
    """Track per-module API access for trialing organizations."""

    def __call__(self, request):
        response = self.get_response(request)

        # Only track for trialing orgs on successful API calls
        if (
            not getattr(request, "organization", None)
            or not request.path.startswith("/api/")
            or response.status_code >= 400
        ):
            return response

        sub = getattr(request.organization, "subscription", None)
        if not sub or sub.status != "trialing":
            return response

        # Resolve module from URL prefix
        module_key = resolve_module_from_path(request.path)
        if not module_key:
            return response

        # Async increment via cache + periodic flush to DB
        cache_key = f"mat:{request.organization.id}:{module_key}:{date.today()}"
        cache.incr(cache_key)  # Redis INCR, atomic

        return response
```

**Performance:** Uses Redis `INCR` (atomic, <1ms). A periodic Celery task flushes cache counters to `ModuleAccessLog` every 5 minutes.

### Celery task: `flush_module_access_counters`

```python
@app.task
def flush_module_access_counters():
    """Flush Redis module access counters to the database."""
    # Scan for mat:* keys, bulk upsert to ModuleAccessLog
    # Uses UPDATE ... ON CONFLICT (org, module, date) DO UPDATE SET count = count + N
```

### Celery task: `generate_trial_addon_report`

Runs daily. For orgs whose trial ended in the last 24h:

```python
@app.task
def generate_trial_addon_report():
    """Generate add-on usage reports for recently ended trials."""
    ended_trials = OrganizationSubscription.objects.filter(
        status="active",  # just transitioned from trialing
        trial_end__date=date.today() - timedelta(days=1),
    )
    for sub in ended_trials:
        org = sub.organization
        tier_modules = TIER_MODULE_MAP.get(org.subscription_tier, set())
        addon_usage = (
            ModuleAccessLog.objects
            .filter(organization=org)
            .exclude(module_key__in=tier_modules)
            .values("module_key")
            .annotate(total=Sum("access_count"))
            .order_by("-total")
        )
        if addon_usage:
            # Store report + trigger email + in-app prompt
            TrialAddonReport.objects.create(
                organization=org,
                report_data=[
                    {"module": r["module_key"], "access_count": r["total"]}
                    for r in addon_usage
                ],
            )
            send_addon_upsell_email.delay(org.id)
```

---

## 3. New model: `TrialAddonReport`

```
Fields:
  organization    FK -> Organization (unique)
  report_data     JSONField  # [{"module": "crm", "access_count": 23}, ...]
  dismissed       BooleanField (default False)
  created_at      DateTimeField
```

---

## 4. API Endpoints

### `GET /api/platform/trial-addon-report/`

Returns the add-on usage report for the current org (if one exists and hasn't been dismissed). Used by the frontend to show the upsell prompt.

```json
{
  "addons_used": [
    {
      "module_key": "crm",
      "module_name": "CRM",
      "access_count": 23,
      "monthly_price": "75.00",
      "description": "Customer relationship management for leads, deals, and client engagement."
    },
    {
      "module_key": "facility_management",
      "module_name": "Facility Management",
      "access_count": 4,
      "monthly_price": "100.00",
      "description": "Facility management module for building operations and maintenance."
    }
  ],
  "skipped": ["tenants"]
}
```

### `POST /api/platform/trial-addon-report/dismiss/`

Dismisses the prompt. Won't show again.

---

## 5. Frontend: In-App Upsell Prompt

After trial ends, on next login the dashboard shows a dismissible banner/modal.
Only appears if `TrialAddonReport` exists and hasn't been dismissed.

### Design

```
+--------------------------------------------------------------+
|  h-1 bg-neutral-900 accent bar                               |
|                                                               |
|  [icon]  Your trial included some premium features            |
|                                                               |
|  During your 14-day trial, you explored modules that          |
|  aren't part of your Growth plan. Keep the ones you loved.    |
|                                                               |
|  +----------------------------------------------------------+ |
|  |  CRM                           23 times used     $75/mo  | |
|  |  Customer relationship management...    [Add to Plan ->]  | |
|  +----------------------------------------------------------+ |
|  +----------------------------------------------------------+ |
|  |  Facility Management            4 times used     $100/mo | |
|  |  Building operations and...             [Add to Plan ->]  | |
|  +----------------------------------------------------------+ |
|                                                               |
|  [ Maybe Later ]                                              |
+--------------------------------------------------------------+
```

**Visual hierarchy:**
- Most-used add-on at top, highest contrast
- Usage count is social proof ("you used this 23 times")
- Price anchored next to the action
- "Maybe Later" dismisses (stores in `TrialAddonReport.dismissed`)

---

## 6. Email Campaign

Sent by Celery task `send_addon_upsell_email` via Zeptomail, 24h after trial ends.

### Subject lines (A/B test)

- A: "You used CRM 23 times -- keep it?"
- B: "Your Growth plan is active. Here's what you're missing."

### Email body

```
Hi {first_name},

Your 14-day trial just ended and your Growth plan is now active.

During your trial, you explored some add-on modules that aren't
included in Growth:

  CRM -- used 23 times                               $75/mo
  Facility Management -- used 4 times               $100/mo

These modules are available as add-ons to your current plan.
Add them anytime from Settings > Subscription.

[Add CRM to my plan ->]

Best,
The developerOS team
```

### Follow-up sequence

| Day | Trigger | Channel | Message |
|-----|---------|---------|---------|
| 0 | Trial ends | In-app prompt | Usage-based add-on upsell |
| 1 | 24h post-trial | Email | "You used CRM 23 times" |
| 7 | 7d post-trial | Email | "Your team's CRM data is still there" (if not purchased) |
| 14 | 14d post-trial | Email | "Last chance: add CRM before your trial data expires" |
| 30 | 30d post-trial | Email | Final reminder, then stop |

**Stop conditions:**
- User purchases the add-on -> remove from sequence
- User dismisses in-app prompt -> don't show again, but emails continue
- User unsubscribes from marketing -> stop emails, keep in-app

---

## 7. Implementation Order

| Step | What | Effort |
|------|------|--------|
| 1 | `ModuleAccessLog` model + migration | Small |
| 2 | `ModuleAccessTrackingMiddleware` + Redis counter | Medium |
| 3 | `flush_module_access_counters` Celery task | Small |
| 4 | `TrialAddonReport` model + `generate_trial_addon_report` task | Medium |
| 5 | `/api/platform/trial-addon-report/` endpoint | Small |
| 6 | Frontend upsell prompt component | Medium |
| 7 | `send_addon_upsell_email` Celery task + Zeptomail template | Medium |
| 8 | Follow-up email sequence (days 7, 14, 30) | Small |

---

## 8. Data Retention

- `ModuleAccessLog` rows are deleted 60 days after trial end (no longer needed)
- `TrialAddonReport` is kept indefinitely (small, useful for analytics)
- Email sequence state tracked via existing notification/email preferences system
