# Role Permission Schema (Phase 4)

Document control integrates with existing RBAC (`settings.Role`, `settings.RolePermission`) and extends it with scope controls.

## Core Permission Table

`settings_rolepermission`

- `id`
- `role_id -> settings_role.id`
- `module` (includes `documents`)
- `sub_module` (`documents.all`)
- `action` (`view`, `comment`, `upload_version`, `approve`, `archive`, `admin_override`, plus platform-wide actions)

Constraint:

- Unique: `(role_id, sub_module, action)`

## Document Scope Tables

`documents_documentrolescope`

- `id`
- `role_id -> settings_role.id` (one-to-one)
- `project_scope` (`all_projects` | `assigned_projects`)
- `business_unit_scope` (`all_business_units` | `assigned_business_units`)
- `allowed_confidentiality_levels` (JSON array from `public/internal/confidential/restricted`)
- `created_at`
- `updated_at`

`documents_documentprojectmembership`

- `id`
- `user_id -> auth_user.id`
- `project_id -> projects_project.id`
- `created_at`

Constraint:

- Unique: `(user_id, project_id)`

`documents_documentbusinessunitmembership`

- `id`
- `user_id -> auth_user.id`
- `division_id -> settings_division.id (nullable)`
- `department_id -> settings_department.id (nullable)`
- `created_at`

Constraint:

- Unique: `(user_id, division_id, department_id)`

Validation:

- At least one of `division_id` or `department_id` is required.
- If both are present, `department.division_id` must match `division_id`.

## Document Model Extensions

`documents_document` now includes:

- `business_unit_division_id -> settings_division.id (nullable)`
- `business_unit_department_id -> settings_department.id (nullable)`

Indexes:

- `(project_id, business_unit_division_id)`
- `(project_id, business_unit_department_id)`

## CRUD + Control Endpoints

- `GET/POST/PATCH/DELETE /api/documents/control/records/`
- `GET/POST/PATCH/DELETE /api/documents/control/versions/`
- `GET/POST/PATCH/DELETE /api/documents/control/approvals/`
- `GET/POST/PATCH/DELETE /api/documents/control/expiries/`
- `GET/POST/PATCH/DELETE /api/documents/control/comments/`
- `GET/POST/PATCH/DELETE /api/documents/control/access/role-scopes/`
- `GET/POST/PATCH/DELETE /api/documents/control/access/project-memberships/`
- `GET/POST/PATCH/DELETE /api/documents/control/access/business-unit-memberships/`

Action mappings are enforced by `HasRolePermission`, and query/write scope is enforced by `documents.access_control`.
