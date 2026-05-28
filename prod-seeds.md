# Production Seed Scripts

Run inside the server container:

```bash
docker compose -f docker-compose.hostinger.yml exec server python manage.py <command>
```

## Global Seeds (run once, shared by all orgs)

1. `seed_master_data`
2. `seed_status_badges`
3. `seed_platform_editions`
4. `seed_feature_flags`
5. `seed_project_templates`
6. `seed_partner_onboarding_templates`

## Org-Scoped Seeds (run per org with `--org <org_id>`)

7. `seed_rbac --org <org_id>`
8. `seed_access_scopes --org <org_id>`
9. `seed_access_policies --org <org_id>`
10. `seed_platform_governance --org <org_id>`
11. `seed_metrics_contract --org <org_id>`
12. `seed_risk_mitigation_rules --org <org_id>`
13. `seed_process_authority --org <org_id>`

## Document Control (org-scoped, run per org with `--org <org_id>`)

14. `seed_documents_phase1_charter --org <org_id>`
15. `seed_documents_phase1_domains --org <org_id>`
16. `seed_documents_phase1_vocabulary --org <org_id>`
17. `seed_documents_phase2_all --org <org_id>`
18. `seed_documents_phase4_access_scopes --org <org_id>`
19. `seed_documents_phase5_workflows --org <org_id>`

## Demo Data (optional — skip on production)
-org 2
- `seed_crm_demo`
- `seed_finance_demo`
- `seed_projects_demo`
- `seed_procurement_demo`
- `seed_partners_demo`
- `seed_properties_demo`
- `seed_support_desk`
- `seed_knowledge_base`
