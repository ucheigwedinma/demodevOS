# App Test Case Catalog

## 1. Purpose and Scope

This catalog defines extensive test coverage for the platform across:

- Authentication and identity lifecycle
- Layered access control (7 layers)
- Core business modules (properties, projects, finance, procurement, CRM, documents, partners, settings, workflows)
- Security, auditability, resilience, and performance
- UI responsiveness and accessibility

This is designed for:

- Manual QA execution
- UAT checklists
- Automation backlog seeding (API, integration, end-to-end)

## 2. Environments

- `DEV`: rapid verification, feature branch checks
- `STAGING`: regression, UAT, integration with external providers
- `PRE-PROD`: release candidate smoke + performance sanity

## 3. Test Data Baseline

Create baseline entities before execution:

- 1 organization with enterprise tier
- 12 users across roles (`super-admin`, `system-admin`, `finance-controller`, `procurement-officer`, `manager`, `staff`, `auditor`, `external-consultant`, `board-viewer`, partner users)
- 2 departments, 2 divisions
- 3 projects, 8 properties, 20 units
- 15 finance records (bills/invoices/payments), 6 procurement records, 10 CRM leads
- 3 workflow templates with at least 5 steps each
- Access policy records including MFA + IP rules

## 4. Priority Legend

- `P0`: release blocking, security/compliance critical
- `P1`: high business impact
- `P2`: medium impact
- `P3`: low impact / UX polish

## 5. Test Cases

### A. Authentication and Identity Layer

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| AUTH-001 | P0 | Register user with valid data | New email | Submit `/signup` with valid payload | Account created, verification flow triggered |
| AUTH-002 | P0 | Register with duplicate email | Existing user email | Submit signup form | Validation error shown, no duplicate user |
| AUTH-003 | P0 | Register with weak password | Password policy enabled | Submit weak password | Password rejected with policy message |
| AUTH-004 | P0 | Login with valid credentials and MFA required | User has MFA required | Login then submit OTP | Access/refresh token issued only after valid OTP |
| AUTH-005 | P0 | Login with invalid password | Existing user | Submit wrong password | Request rejected, no token issued |
| AUTH-006 | P0 | Login suspended user | User status suspended | Submit valid credentials | Login denied with suspension message |
| AUTH-007 | P0 | OTP retry limit enforcement | OTP session exists | Submit invalid OTP repeatedly | Session blocked after limit, re-login required |
| AUTH-008 | P1 | Forgot password flow success | Existing user email | Request reset then submit new password | Password reset succeeds, old password invalid |
| AUTH-009 | P1 | Forgot password for unknown email | Unknown email | Submit forgot-password | Generic success response, no enumeration leak |
| AUTH-010 | P1 | Email verification token invalid | Invalid token | Verify email endpoint | Proper invalid/expired token response |
| AUTH-011 | P1 | OAuth login callback valid | OAuth provider configured | Complete OAuth flow | User authenticated and tokens/session returned |
| AUTH-012 | P1 | OAuth callback tampered state | OAuth state mismatch | Complete callback with bad state | Authentication blocked |
| AUTH-013 | P1 | Turnstile protection on login/register | Turnstile required | Omit/forge token | Request rejected |
| AUTH-014 | P1 | Service account key creation | IAM admin role | Create service account and API key | Key returned once, hash stored only |
| AUTH-015 | P1 | Revoke API key | Existing active key | Revoke key endpoint | Key becomes unusable immediately |
| AUTH-016 | P2 | Invitation acceptance with metadata | Pending invitation exists | Accept invite | Profile seeded with role/department/job title |
| AUTH-017 | P2 | Complete onboarding state update | New user | Complete onboarding endpoint | Flags updated and persisted |
| AUTH-018 | P2 | Complete tour state update | Authenticated user | Call complete-tour | Tour status updated |
| AUTH-019 | P2 | Session with expired refresh token | Expired refresh token | Refresh endpoint | Token refresh denied |
| AUTH-020 | P0 | Identity status checks for all identity types | Users with identity_type variants | Login and access protected endpoints | Access follows identity status and assignment rules |

### B. Role Layer, Permission Layer, Module Access Layer

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| IAM-001 | P0 | Role without permission cannot access endpoint | User assigned limited role | Call endpoint requiring missing permission | `403` denied |
| IAM-002 | P0 | Role with permission can access endpoint | Role has matching permission | Call endpoint | Allowed response |
| IAM-003 | P0 | Admin bypass for role checks still respects module toggle | Org admin user, module disabled | Access disabled module | Access denied due to module disabled |
| IAM-004 | P1 | Permission inheritance consistency (`RolePermission`) | Role has permission rows | List user permissions | Returned permission set is complete and correct |
| IAM-005 | P1 | Module activation disables all sub-module access | Module deactivated | Access any submodule endpoint | All denied |
| IAM-006 | P1 | Tier/module mismatch handling | Lower subscription tier org | Enable premium module and access | Denied/ignored based on tier policy |
| IAM-007 | P1 | Role assignment change takes effect immediately | User role changed | Re-test endpoint | New access policy applied immediately |
| IAM-008 | P1 | Permission matrix update propagates | Role permissions edited | Retry endpoint access | Behavior matches updated matrix |
| IAM-009 | P2 | Missing `rbac_sub_module` on a protected view | Misconfigured view | Access endpoint | Denied by default |
| IAM-010 | P1 | Direct permission fallback rows (`permission is null`) | Legacy role_permission rows | Access endpoint | Evaluation works correctly |
| IAM-011 | P2 | Role slug uniqueness per organization | Existing slug | Create duplicate role slug | Validation error |
| IAM-012 | P2 | Permission catalog uniqueness (`sub_module`, `action`) | Existing pair | Create duplicate permission | Duplicate blocked |
| IAM-013 | P1 | API returns accurate permission registry | Authenticated settings role | Fetch permission-registry | Registry matches server defaults |
| IAM-014 | P1 | Unauthorized user cannot list IAM users | Non-IAM role user | Call `/api/iam/users/` | Access denied |
| IAM-015 | P0 | Privilege escalation attempt via crafted payload | Low-priv user | Try assigning high role via unauthorized endpoint | Operation blocked and audited |

### C. Data Scope Layer

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| DS-001 | P0 | `self` scope limits IAM users list | User with self scope | List IAM users | Only own profile returned |
| DS-002 | P0 | `department` scope on IAM users | User with department scope | List IAM users | Only department users returned |
| DS-003 | P0 | `organization` scope on IAM users | User with org scope | List IAM users | Full org users returned |
| DS-004 | P1 | User-specific scope override supersedes role scope | Role scope dept + user scope self | Query data | User override applied |
| DS-005 | P1 | Scoped project visibility with project assignments | `project` scope user | List projects | Only assigned/related projects returned |
| DS-006 | P1 | Department scope for projects | User in department | List projects | Projects linked via department tasks visible |
| DS-007 | P1 | No scope assignments fallback behavior | User with no explicit rows | List scoped resource | Backward-compatible default applied as configured |
| DS-008 | P1 | Cross-module scope isolation | Scope granted for IAM only | Access projects | Projects still restricted per projects scope |
| DS-009 | P2 | Duplicate scope assignment blocked | Existing assignment | Create duplicate | Unique constraint enforced |
| DS-010 | P1 | Seeded role scope defaults created | Run seed command | Verify role_scopes rows | Defaults created for expected roles/modules |
| DS-011 | P2 | Reset seed behavior converges duplicates | Seed with reset | Inspect rows | Duplicate/divergent rows cleaned |
| DS-012 | P0 | Object fetch by ID obeys scope | User lacks scope on target object | Retrieve object directly | Not found/forbidden, no leakage |

### D. Process Authority Layer (Workflow Authority)

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| PA-001 | P0 | Only authorized actor can decide workflow step | Pending step assigned to role/user | Unauthorized user attempts decision | Decision blocked |
| PA-002 | P0 | Process authority mapping allows role-based approval | `process_authority` mapped role | Role user decides step | Approval accepted |
| PA-003 | P0 | Direct approver user can approve | Step has approver_user | Assigned user decides | Approval accepted |
| PA-004 | P0 | Delegated approver can approve within validity window | Active delegation exists | Delegate decides step | Approval accepted, acting_on_behalf_of populated |
| PA-005 | P0 | Delegation expired cannot be used | Expired delegation | Delegate decides step | Denied |
| PA-006 | P1 | RACI authority type filtering | Step has consulted/informed entries only | Attempt decision | Decision blocked unless responsible/accountable exists |
| PA-007 | P1 | My Approvals includes process-authority discoverable steps | User has process authority | Call `my-approvals` | Relevant steps included |
| PA-008 | P1 | My Approvals excludes unrelated steps | No authority mapping | Call `my-approvals` | Step absent |
| PA-009 | P1 | Workflow condition branch resolution | Template has condition step | Submit object crossing threshold | Correct branch steps instantiated |
| PA-010 | P1 | Parallel step behavior | Parallel execution mode step | Approve one parallel approver only | Workflow waits for all required decisions |
| PA-011 | P1 | Rejection terminates workflow | Pending approval workflow | Submit rejection decision | Workflow state moves to rejected |
| PA-012 | P1 | Cancellation marks pending steps skipped | In-progress workflow | Cancel workflow | Remaining pending steps skipped, instance cancelled |
| PA-013 | P1 | SLA breach escalation marker | Overdue pending step | Run SLA breach task | Step marked escalated/breached and audit logged |
| PA-014 | P2 | Process authority seed command completeness | Run seed command | Validate `workflow_roles`, `workflow_steps`, `approvers`, `process_authority` | Rows created as expected |
| PA-015 | P0 | Approval policy + template selection correctness | Multiple policies with thresholds | Submit objects across thresholds | Matching template selected by priority/range |

### E. Contextual Access Layer (Conditional Policies)

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| CP-001 | P0 | Finance approval requires MFA | Policy enabled (`require_mfa`) | Finance role approves with MFA off | Denied with policy reason |
| CP-002 | P0 | Finance approval passes when MFA enabled | Same as above | Finance role approves with MFA on | Allowed |
| CP-003 | P1 | IP restriction policy blocks unknown IP | CIDR policy configured | Request from non-whitelisted IP | Denied |
| CP-004 | P1 | IP restriction policy allows office network | CIDR policy configured | Request from whitelisted IP | Allowed |
| CP-005 | P1 | Time-window policy enforces hours | Time restriction configured | Request outside allowed hours | Denied |
| CP-006 | P1 | Device trust policy enforcement | Require corporate device policy | Request without trusted header | Denied |
| CP-007 | P1 | Country/location restriction | Location policy configured | Request from blocked country | Denied |
| CP-008 | P1 | Action-scoped policy applies only to target action | Policy action=approve | Perform view action | Not blocked by approve policy |
| CP-009 | P1 | Module-scoped policy isolation | Policy module=finance | Access projects endpoint | Policy not incorrectly applied |
| CP-010 | P2 | Multiple matching policies deterministic by priority | 2 matching policies | Execute request | Lower priority number evaluated first |
| CP-011 | P2 | Policy with empty conditions behavior | Policy with no conditions and deny action | Request match | Denied always within scope |
| CP-012 | P1 | Policy condition operator handling (`in`, `not_in`, `between`) | Matching policies created | Execute matching/non-matching requests | Correct allow/deny outcomes |
| CP-013 | P2 | Safe behavior before migrations applied | Run app before policy tables exist | Request protected endpoint | No crash; fallback behavior stable |
| CP-014 | P2 | Seed access policy command creates defaults | Run `seed_access_policies` | Inspect tables | Default policy/conditions/actions exist |
| CP-015 | P0 | Contextual check enforced in workflow decision path | Workflow approval endpoint | Attempt decision violating policy | Decision denied |

### F. Properties and Portfolio

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| PROP-001 | P1 | Create property with required fields | Authorized user | Submit create property | Property persisted |
| PROP-002 | P1 | Update property segmentation/classification | Existing property | Update classification fields | Changes saved and retrievable |
| PROP-003 | P1 | Upload property image/document | Existing property | Upload file | File linked and retrievable |
| PROP-004 | P1 | Property valuation entry creation | Property exists | Add valuation | Valuation appears in property history |
| PROP-005 | P2 | Property compliance status transitions | Property with inspections | Update compliance flags | Valid transitions enforced |
| PROP-006 | P1 | Unauthorized delete blocked | Non-privileged user | Attempt delete property | Denied |
| PROP-007 | P2 | Filter and search property lists | Dataset exists | Apply filters/search | Correct subset returned |
| PROP-008 | P2 | Property detail load performance | 100+ properties | Open detail page | Acceptable response/render timing |

### G. Projects

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| PROJ-001 | P1 | Create project and default phases | Authorized project role | Create project | Project + expected phase defaults exist |
| PROJ-002 | P1 | Add milestone with gate requirements | Project exists | Add milestone requiring approval | Milestone saved with rules |
| PROJ-003 | P1 | Task assignment and comment flow | Task exists | Assign task, add comment | Assignment and comments recorded |
| PROJ-004 | P1 | Risk register CRUD | Project exists | Create/update risk entry | Risk entry saved and visible |
| PROJ-005 | P1 | Variation order lifecycle | Variation feature enabled | Create -> approve/reject variation | Status transitions valid and auditable |
| PROJ-006 | P1 | Field operation report submission | Project exists | Submit daily site report with photos | Report stored with attachments |
| PROJ-007 | P2 | Stage-gate enforcement blocks completion | Gate checklist incomplete | Attempt phase completion | Completion blocked with clear error |
| PROJ-008 | P2 | Budget vs cost linkage to finance | Project + finance records | Post project costs | Costs reflected in project summaries |
| PROJ-009 | P1 | Project list scope filtering | Scoped user | List projects | Scoped subset only |
| PROJ-010 | P2 | Project templates apply consistently | Template exists | Create project from template | Template phases/checkpoints copied |

### H. Finance

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| FIN-001 | P0 | Create bill with valid line items | Finance role | Create bill + lines | Totals calculated correctly |
| FIN-002 | P1 | Bill total recalculates after line update/delete | Existing bill | Update/delete line | Header totals updated |
| FIN-003 | P0 | Submit bill for approval creates workflow instance | Draft bill exists | Submit approval | Workflow instance created once |
| FIN-004 | P0 | Duplicate active workflow submission blocked | Active workflow exists | Submit again | Request rejected |
| FIN-005 | P1 | Invoice create/edit/delete permissions | Invoice role variants | CRUD attempts per role | Enforced per permissions |
| FIN-006 | P1 | Budget create and approval flow | Budget draft exists | Submit and approve budget | Status and audit updates correct |
| FIN-007 | P1 | Journal posting validates balancing entries | Journal draft exists | Post unbalanced then balanced entries | Unbalanced rejected, balanced accepted |
| FIN-008 | P1 | Payments update related balances | Invoice/bill exists | Record payment | Outstanding balance reduced accurately |
| FIN-009 | P1 | Trial balance report correctness | Ledger entries exist | Generate trial balance | Debits equal credits |
| FIN-010 | P1 | General ledger filter correctness | Data with date ranges | Query by account/date | Expected entries only |
| FIN-011 | P2 | SPV entity creation and linking | SPV module enabled | Create SPV and attach plan | SPV saved and linked |
| FIN-012 | P2 | Payment plan/installment schedule integrity | Plan inputs valid | Generate installments | Schedule totals match principal |
| FIN-013 | P1 | Customer CRUD with role restrictions | Finance role matrix | Perform customer operations | Permission-accurate behavior |
| FIN-014 | P1 | Investor records and project investor linking | Investor module enabled | Link investor to project | Linkage persisted correctly |
| FIN-015 | P2 | Export endpoints security and data correctness | Export permission role | Export report | Valid export content, unauthorized denied |
| FIN-016 | P1 | Finance dashboard endpoints availability | Auth user | Fetch finance overview APIs | Stable response structure |
| FIN-017 | P0 | Contextual policy on finance approve action | Policy active | Approve without MFA/trusted context | Denied |
| FIN-018 | P2 | Large dataset pagination correctness | 500+ finance rows | Paginate list endpoints | No duplicates/missing rows across pages |

### I. Procurement

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| PROC-001 | P1 | Vendor CRUD operations | Procurement role | Create/update vendor | Vendor persisted with expected fields |
| PROC-002 | P1 | Requisition lifecycle | Requisition draft | Submit/approve/reject | Valid status transitions |
| PROC-003 | P1 | Purchase order from approved requisition | Approved requisition | Create PO | PO linked to requisition |
| PROC-004 | P1 | Goods receipt updates PO fulfillment | Existing PO | Create goods receipt | Quantities and status updated |
| PROC-005 | P1 | RFQ create and vendor comparison flow | Vendors exist | Create RFQ + responses + comparison | Comparison data accurate |
| PROC-006 | P2 | Tender comparison decision auditability | Tender records | Decide winner | Decision logged with actor/time |
| PROC-007 | P1 | Role restriction on approve actions | Non-approver role | Attempt approval | Denied |
| PROC-008 | P2 | Procurement-to-inventory sync behavior | Sync command available | Receive goods then sync | Inventory reflects receipts |
| PROC-009 | P2 | Pagination and ordering reliability | 100+ rows | Sort/filter procurement lists | Correct deterministic order |
| PROC-010 | P1 | Procurement workflow escalation path | SLA setup exists | Simulate overdue approvals | Escalation state and notifications triggered |

### J. CRM

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| CRM-001 | P1 | Lead CRUD and status transitions | CRM role | Create and update lead statuses | Valid progression and timestamps |
| CRM-002 | P1 | Lead archival flow | Existing lead | Archive lead with reason | Lead excluded from active list |
| CRM-003 | P1 | Reservation creation from lead | Lead and unit available | Create reservation | Reservation linked correctly |
| CRM-004 | P1 | Reservation hold expiration job | Hold with expiry | Run expiration command | Expired holds updated automatically |
| CRM-005 | P2 | Campaign creation and recipient handling | Contacts available | Create campaign and recipients | Recipients linked and visible |
| CRM-006 | P2 | Communication log completeness | Existing lead/customer | Log communication | Entry contains actor, channel, timestamp |
| CRM-007 | P1 | Broker commission structure and earning calc | Broker + sale data | Compute commission | Values match defined rules |
| CRM-008 | P1 | Access scope on CRM lists | Scoped role/user | List leads/reservations | Only permitted records returned |

### K. Documents and Governance

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| DOC-001 | P0 | Upload document and create initial version | Authorized role | Upload file + metadata | Document and version created |
| DOC-002 | P1 | Upload new version with audit continuity | Existing document | Upload version | Version increments and audit event logged |
| DOC-003 | P1 | Confidentiality label enforcement | Restricted label configured | Access document as low-priv role | Access denied |
| DOC-004 | P1 | Submit document workflow and decision | Workflow template exists | Submit and decide steps | State transitions and audit logs correct |
| DOC-005 | P1 | Digital signature request lifecycle | Provider configured | Send, complete, cancel signature flows | Status updates and audit events accurate |
| DOC-006 | P2 | OCR extraction job output shape | OCR feature enabled | Run OCR on scanned doc | Parsed fields stored and queryable |
| DOC-007 | P2 | Retention/expiry monitor behavior | Expiring docs exist | Run compliance monitor | Expected reminders/flags generated |
| DOC-008 | P1 | Full-text search relevance and permissions | Indexed docs exist | Search by term | Relevant docs returned, unauthorized hidden |
| DOC-009 | P1 | Download/share events audited with IP | Request context present | Download/share document | Audit includes actor/time/IP |
| DOC-010 | P2 | Archive/supersede/delete policy enforcement | Document in various states | Attempt state changes | Only allowed transitions succeed |

### L. Partner-Agnostic Portal

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| PART-001 | P0 | Create onboarding case per partner type | Template exists | Create client/contractor/investor case | Cases created with proper template mapping |
| PART-002 | P1 | Stage progression and SLA tracking | Case with stages | Move stage statuses | Timeline and SLA state updated |
| PART-003 | P1 | Submit case for review gate | Required stages complete/incomplete | Submit in both states | Allowed only when requirements met |
| PART-004 | P0 | ERP entity creation from approved case | Approved case | Trigger create ERP entity | Correct target entity created and linked |
| PART-005 | P0 | Entitlement provisioning | Approved case | Add entitlement rows | Entitlements saved with scope boundaries |
| PART-006 | P0 | Grant portal access eligibility checks | Case lacks ERP/entitlement then has both | Grant access attempts | Block until eligible, then grant succeeds |
| PART-007 | P1 | Approval recording with role labels | Case in review | Record approval/rejection | Approval records stored and visible |
| PART-008 | P1 | Audit timeline event completeness | Case lifecycle events executed | Fetch timeline | Events include actor, event type, payload |
| PART-009 | P1 | Source lead linkage and archival behavior | Case linked to lead | Convert/archive flow | Link integrity maintained |
| PART-010 | P1 | Partner type specific module rendering | Partner users exist | Login as each partner type | UI shows correct scoped modules |
| PART-011 | P0 | Data partitioning by project/SPV/contract | Multiple partner entitlements | Access cross-project records | Data leakage prevented |
| PART-012 | P1 | Portal legal acceptance capture | Legal docs pending | Accept terms | Acceptance record stored with timestamp |
| PART-013 | P2 | Notifications for case milestones | Notification channels configured | Trigger stage and approval events | Correct recipients and templates used |
| PART-014 | P2 | Search/filter in partner case list | Large partner dataset | Apply filters | Results match filter criteria |
| PART-015 | P0 | Partner cannot elevate own entitlements | Partner user role | Attempt privilege escalation | Denied and logged |

### M. Notifications, Audit, and Compliance

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| COMP-001 | P0 | Audit logs are immutable | Existing audit event | Attempt update/delete | Operation blocked |
| COMP-002 | P1 | Notification channel toggles respected | Email/SMS/in-app config set | Trigger notifications | Only enabled channels dispatch |
| COMP-003 | P1 | Template fallback behavior | Missing custom template | Trigger event | System template used |
| COMP-004 | P1 | Escalation matrix auto-escalation | Rule configured | Simulate no-response threshold | Escalation tier advances correctly |
| COMP-005 | P2 | Board notification cooldown | Board notification enabled | Trigger repeated critical events | Cooldown enforced |
| COMP-006 | P1 | Security settings validation (CIDR, country code) | Settings endpoint access | Submit invalid values | Validation errors returned |
| COMP-007 | P1 | Compliance report export permissions | Non-export role and export role | Export attempts | Only authorized export succeeds |
| COMP-008 | P1 | Failed login and security alert visibility | Security events generated | Query audit/security endpoints | Events visible to authorized auditors/admins |

### N. API and Integration Robustness

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| API-001 | P0 | Unauthorized request to protected endpoint | No token | Call protected API | `401` response |
| API-002 | P1 | Invalid pagination parameters handled | Authenticated request | Send invalid page/page_size | Safe defaults or validation errors |
| API-003 | P1 | Filtering by invalid enum values | Endpoint with filters | Send invalid value | Validation error, no server crash |
| API-004 | P1 | Concurrent update conflict handling | Same record open in two sessions | Submit conflicting updates | Deterministic last-write or conflict strategy applied |
| API-005 | P1 | Idempotency for repeated actions where applicable | Submit endpoint called twice rapidly | Repeat call | No duplicate side effects |
| API-006 | P2 | Webhook signature validation | Webhook endpoint enabled | Send invalid signature | Request rejected |
| API-007 | P2 | External provider outage resilience | Simulate provider timeout | Trigger integration action | Error surfaced gracefully and logged |
| API-008 | P2 | Media file missing scenario | Broken media path exists | Fetch object/media | Graceful fallback, no app crash |
| API-009 | P1 | Response schema stability for critical endpoints | API contract documented | Run schema checks | Response fields unchanged or versioned |
| API-010 | P1 | Rate limiting for sensitive auth routes | Throttle configured | Burst login/OTP attempts | Throttle enforced |

### O. UI, Accessibility, and UX Regression

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| UI-001 | P1 | All primary pages render on desktop and mobile | Authenticated session | Visit major routes | No layout breakage |
| UI-002 | P1 | Role-based menu visibility | Multiple role accounts | Login with each role | Navigation reflects role/module access |
| UI-003 | P2 | Form validation messages are clear and actionable | Invalid inputs | Submit forms | Error messages tied to fields |
| UI-004 | P2 | Loading/empty/error states present on data pages | Simulate API states | Visit list/detail pages | States are visible and consistent |
| UI-005 | P1 | Keyboard-only navigation works on critical flows | Browser with keyboard nav | Navigate login, approvals, partner actions | Reachable focus order and operable controls |
| UI-006 | P1 | Accessibility labels for icon-only buttons | Pages with icon buttons | Run a11y pass and manual screen reader check | Buttons have text/aria-label/title |
| UI-007 | P2 | Manifest and PWA assets resolve correctly | Static assets configured | Load app manifest and icons | Correct files served for light/dark variants |
| UI-008 | P2 | Theme and preference persistence | User preferences set | Change theme/preferences and reload | Preferences persist across sessions |

### P. Performance, Reliability, and Recovery

| ID | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---|---|---|---|
| PERF-001 | P1 | IAM users list performance at scale | 5k users in org | Query list with filters | Response within SLO, stable memory usage |
| PERF-002 | P1 | Workflow approvals throughput | 1k pending workflow steps | Load my-approvals and decide actions | Acceptable response times |
| PERF-003 | P1 | Finance report generation under load | Large ledger dataset | Generate report concurrently | No timeouts/data corruption |
| PERF-004 | P2 | Documents search latency with index growth | 50k docs indexed | Run common search queries | Latency remains acceptable |
| PERF-005 | P1 | Celery tasks recover after worker restart | Tasks queued | Restart worker mid-run | Tasks resume or retry safely |
| PERF-006 | P1 | Database migration safety on non-empty DB | Staging snapshot | Apply migrations | No data loss, migration succeeds |
| PERF-007 | P2 | Backup and restore integrity | Backup settings configured | Simulate restore in staging | Restored data usable and complete |
| PERF-008 | P2 | Notification fan-out reliability | High notification event volume | Trigger fan-out events | Delivery attempts and failure handling logged |

## 6. Minimum Release Gate (Recommended)

A release candidate should not ship unless:

- All `P0` test cases pass
- At least 95% of `P1` cases pass with no unresolved security defects
- No open critical/high vulnerabilities in auth, IAM, workflow approval, or data scope
- Migration dry-run completed in staging snapshot
- Audit logging verified for privileged operations

## 7. Automation Backlog Mapping

Prioritize automation in this order:

1. API tests for `AUTH-*`, `IAM-*`, `DS-*`, `PA-*`, `CP-*` (`P0/P1`)
2. End-to-end tests for onboarding, finance approval, procurement approval, partner entitlement
3. Regression tests for documents and reporting flows
4. Performance smoke tests for high-volume list/report endpoints

