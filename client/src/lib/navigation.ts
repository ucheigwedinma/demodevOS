/**
 * Domain-based navigation data for the three-panel sidebar.
 *
 * Hierarchy: Domain → Section → SubItem
 * All sub-items remain under their existing parent sections.
 */

import type { NavDomain, NavDomainSection, NavSubItem } from "$lib/types";
import { supportDeskNavItems } from "$lib/supportDesk";

// ---------------------------------------------------------------------------
// Domain definitions (9 domains)
// ---------------------------------------------------------------------------

export const domains: NavDomain[] = [
  // ── 1. Dashboard ──────────────────────────────────────────────────────
  {
    key: "dashboard",
    label: "Dashboard",
    labelKey: "nav.dashboard",
    sections: [
      { key: "operations-hub", label: "Operations Hub", labelKey: "nav.section.operations_hub", href: "/", subItems: [] },
      { key: "executive-dashboard", label: "Executive Dashboard", labelKey: "nav.section.executive_dashboard", href: "/dashboard/executive", subItems: [] },
      { key: "portfolio-analysis", label: "Portfolio Analysis", labelKey: "nav.section.portfolio_analysis", href: "/dashboard/portfolio-analysis", subItems: [] },
      { key: "kpi-monitor", label: "KPI Monitor", labelKey: "nav.section.kpi_monitor", href: "/dashboard/kpi-monitor", subItems: [] },
      { key: "board-metrics", label: "Board Metrics", labelKey: "nav.section.board_metrics", href: "/dashboard/board-metrics", subItems: [] },
      { key: "risk-alerts", label: "Risk Alerts", labelKey: "nav.section.risk_alerts", href: "/dashboard/risk-alerts", subItems: [] },
      { key: "custom-dashboards", label: "Custom Dashboards", labelKey: "nav.section.custom_dashboards", href: "/dashboard/custom", subItems: [] },
    ],
  },

  // ── 2. Operations ─────────────────────────────────────────────────────
  {
    key: "operations",
    label: "Operations",
    labelKey: "nav.operations",
    sections: [
      {
        key: "crm",
        label: "CRM",
        labelKey: "nav.section.crm",
        href: "/crm",
        subItems: [
          { href: "/crm", label: "Dashboard", labelKey: "nav.item.crm", exact: true },
          { href: "/crm/leads", label: "Leads & Pipeline", labelKey: "nav.item.crm_leads" },
          { href: "/crm/opportunities", label: "Opportunity / Deal Management", labelKey: "nav.item.crm_opportunities" },
          { href: "/crm/property-matching", label: "Property Matching Engine", labelKey: "nav.item.crm_property_matching" },
          { href: "/crm/contacts", label: "Contact & Accounts", labelKey: "nav.item.crm_contacts" },
          { href: "/crm/reservations", label: "Reservations", labelKey: "nav.item.crm_reservations" },
          { href: "/crm/assessments", label: "Financial Pre-Assessment", labelKey: "nav.item.crm_assessments" },
          { href: "/crm/brokers", label: "Brokers & Partners", labelKey: "nav.item.crm_brokers" },
          { href: "/crm/activities-tasks", label: "Activities & Task Management", labelKey: "nav.item.crm_activities_tasks" },
          { href: "/crm/communications", label: "Communication Engine", labelKey: "nav.item.crm_communications" },
          { href: "/crm/campaigns", label: "Campaigns", labelKey: "nav.item.crm_campaigns" },
          { href: "/crm/analytics-reporting", label: "CRM Analytics & Reporting", labelKey: "nav.item.crm_analytics_reporting" },
        ],
      },
      {
        key: "facility-management",
        label: "Facility Management",
        labelKey: "nav.section.facility_management",
        href: "/facility-management",
        subItems: [
          { href: "/facility-management", label: "Dashboard", labelKey: "nav.item.facility_management", exact: true },
          { href: "/facility-management/registry", label: "Facility Registry", labelKey: "nav.item.facility_management_registry" },
          { href: "/facility-management/assets", label: "Asset Management", labelKey: "nav.item.facility_management_assets" },
          { href: "/facility-management/maintenance", label: "Maintenance Management", labelKey: "nav.item.facility_management_maintenance" },
          { href: "/facility-management/service-requests", label: "Service Requests & Bill Payments", labelKey: "nav.item.facility_management_service_requests" },
          { href: "/facility-management/space-occupancy", label: "Space & Occupancy Management", labelKey: "nav.item.facility_management_space_occupancy" },
          { href: "/facility-management/utilities", label: "Utilities & Energy Management", labelKey: "nav.item.facility_management_utilities" },
          { href: "/facility-management/documents", label: "Documents & Drawings", labelKey: "nav.item.facility_management_documents" },
          { href: "/facility-management/health-safety", label: "Health, Safety & Compliance", labelKey: "nav.item.facility_management_health_safety" },
        ],
      },
      {
        key: "tenants",
        label: "Tenants",
        labelKey: "nav.section.tenants",
        href: "/tenants",
        subItems: [
          { href: "/tenants", label: "Dashboard", labelKey: "nav.item.tenants", exact: true },
          { href: "/tenants/registry", label: "Tenant Registry", labelKey: "nav.item.tenants_registry" },
          { href: "/tenants/leases", label: "Lease Management", labelKey: "nav.item.tenants_leases" },
          { href: "/tenants/billing", label: "Billing & Charges", labelKey: "nav.item.tenants_billing" },
          { href: "/tenants/payments", label: "Payments & Collections", labelKey: "nav.item.tenants_payments" },
          { href: "/tenants/service-requests", label: "Service Requests", labelKey: "nav.item.tenants_service_requests" },
          { href: "/tenants/communications", label: "Communication & Engagement", labelKey: "nav.item.tenants_communications" },
          { href: "/tenants/documents", label: "Documents & Contracts", labelKey: "nav.item.tenants_documents" },
          { href: "/tenants/inspections", label: "Inspections & Move-In/Out", labelKey: "nav.item.tenants_inspections" },
          { href: "/tenants/complaints", label: "Complaints & Escalations", labelKey: "nav.item.tenants_complaints" },
          { href: "/tenants/reports", label: "Reports & Analytics", labelKey: "nav.item.tenants_reports" },
        ],
      },
    ],
  },

  // ── 3. Development ────────────────────────────────────────────────────
  {
    key: "development",
    label: "Development",
    labelKey: "nav.development",
    sections: [
      {
        key: "boq",
        label: "Bill of Quantities",
        labelKey: "nav.section.boq",
        href: "/boq",
        subItems: [
          { href: "/boq", label: "Overview", labelKey: "nav.item.boq", exact: true },
          { href: "/boq/builder", label: "BoQ Builder", labelKey: "nav.item.boq_builder" },
          { href: "/boq/master", label: "Master BoQ", labelKey: "nav.item.boq_master" },
          { href: "/boq/cost-estimates", label: "Cost Estimates", labelKey: "nav.item.boq_cost_estimates" },
          { href: "/boq/rate-library", label: "Rate Library", labelKey: "nav.item.boq_rate_library" },
          { href: "/boq/mapping", label: "BoQ Mapping", labelKey: "nav.item.boq_mapping" },
          { href: "/boq/category-mapping", label: "Category Mapping", labelKey: "nav.item.boq_category_mapping" },
          { href: "/boq/revisions", label: "Revisions", labelKey: "nav.item.boq_revisions" },
        ],
      },
      {
        key: "project-planning",
        label: "Planning & Library",
        labelKey: "nav.section.project_planning",
        href: "/projects/blueprints",
        subItems: [
          { href: "/projects/blueprints", label: "Blueprints", labelKey: "nav.item.projects_blueprints" },
          { href: "/project-planning", label: "Templates (WBS)", labelKey: "nav.item.project_planning", exact: true },
          { href: "/project-planning/task-templates", label: "Task Templates", labelKey: "nav.item.project_planning_task_templates" },
          { href: "/project-planning/dependencies", label: "Dependency Engine", labelKey: "nav.item.project_planning_dependencies" },
          { href: "/project-planning/scheduling", label: "Scheduling Engine", labelKey: "nav.item.project_planning_scheduling" },
          { href: "/project-planning/resources", label: "Resource Modeling", labelKey: "nav.item.project_planning_resources" },
          { href: "/project-planning/resource-optimization", label: "Resource Optimization", labelKey: "nav.item.project_planning_resource_optimization" },
          { href: "/project-planning/cost-projection", label: "Cost Projection", labelKey: "nav.item.project_planning_cost_projection" },
          { href: "/project-planning/scenarios", label: "Scenario Analysis", labelKey: "nav.item.project_planning_scenarios" },
        ],
      },
      {
        key: "projects",
        label: "Projects",
        labelKey: "nav.section.projects",
        href: "/projects",
        subItems: [
          { href: "/projects", label: "Projects Overview", labelKey: "nav.item.projects", exact: true },
          { href: "/projects/project-pipeline", label: "Project Pipeline", labelKey: "nav.item.projects_project_pipeline" },
          { href: "/projects/project-setup", label: "Project Kickoff", labelKey: "nav.item.projects_project_setup" },
          { href: "/projects/execution-stats", label: "Execution Stats", labelKey: "nav.item.projects_execution_stats" },
          { href: "/projects/feasibility-viability", label: "Feasibility & Viability", labelKey: "nav.item.projects_feasibility_viability" },
          { href: "/projects/land-acquisition", label: "Land Acquisition", labelKey: "nav.item.projects_land_acquisition" },
          { href: "/projects/approvals-permits", label: "Approvals & Permits", labelKey: "nav.item.projects_approvals_permits" },
          { href: "/projects/design-management", label: "Design Management", labelKey: "nav.item.projects_design_management" },
          { href: "/projects/development-budget", label: "Development Budget", labelKey: "nav.item.projects_development_budget" },
          { href: "/projects/budget-cost", label: "Budget & Cost", labelKey: "nav.item.projects_budget_cost" },
          { href: "/projects/financing", label: "Financing", labelKey: "nav.item.projects_financing" },
          { href: "/projects/development-schedule", label: "Development Schedule", labelKey: "nav.item.projects_development_schedule" },
          { href: "/projects/phases-milestones", label: "Phases & Milestones", labelKey: "nav.item.projects_phases_milestones" },
          { href: "/projects/milestones-stage-gates", label: "Stage Gate Reviews", labelKey: "nav.item.projects_milestones_stage_gates" },
          { href: "/projects/consultants-stakeholders", label: "Consultants & Stakeholders", labelKey: "nav.item.projects_consultants_stakeholders" },
          { href: "/projects/procurement-planning", label: "Procurement Planning", labelKey: "nav.item.projects_procurement_planning" },
          { href: "/projects/sales-revenue-forecast", label: "Sales & Revenue Forecast", labelKey: "nav.item.projects_sales_revenue_forecast" },
          { href: "/projects/risk-register", label: "Risk Register", labelKey: "nav.item.projects_risk_register" },
          { href: "/projects/document-control", label: "Document Control", labelKey: "nav.item.projects_document_control" },
          { href: "/projects/communications", label: "Communications", labelKey: "nav.item.projects_communications" },
          { href: "/projects/governance", label: "Governance", labelKey: "nav.item.projects_governance" },
          { href: "/projects/reports", label: "Reports", labelKey: "nav.item.projects_reports" },
          { href: "/projects/predictive-intelligence", label: "Predictive Intelligence", labelKey: "nav.item.projects_predictive_intelligence" },
          { href: "/projects/closeout", label: "Closeout", labelKey: "nav.item.projects_closeout" },
        ],
      },
      {
        key: "construction",
        label: "Construction",
        labelKey: "nav.section.construction",
        href: "/construction",
        subItems: [
          { href: "/construction/site-overview", label: "Site Overview", labelKey: "nav.item.construction_site_overview", exact: true },
          { href: "/construction/site-mobilization", label: "Site Mobilization", labelKey: "nav.item.construction_site_mobilization", exact: true },
          { href: "/construction/schedule", label: "Construction Schedule", labelKey: "nav.item.construction_schedule", exact: true },
          { href: "/projects/tasks", label: "Tasks & Work Packages", labelKey: "nav.item.projects_tasks", exact: true },
          { href: "/construction/contractor-management", label: "Contractor Management", labelKey: "nav.item.construction_contractor_management", exact: true },
          { href: "/construction/equipment", label: "Equipment & Machinery", labelKey: "nav.item.construction_equipment", exact: true },
          { href: "/projects/field-operations", label: "Field Operations", labelKey: "nav.item.projects_field_operations" },
          { href: "/construction/quality-control", label: "Quality Control", labelKey: "nav.item.construction_quality_control", exact: true },
          { href: "/construction/hse", label: "HSE", labelKey: "nav.item.construction_hse", exact: true },
          { href: "/projects/issues", label: "Issues", labelKey: "nav.item.projects_issues" },
          { href: "/projects/variations", label: "Variations", labelKey: "nav.item.projects_variations" },
          { href: "/construction/rfis", label: "RFIs", labelKey: "nav.item.construction_rfis", exact: true },
          { href: "/construction/site-instructions", label: "Site Instructions", labelKey: "nav.item.construction_site_instructions", exact: true },
          { href: "/construction/testing-commissioning", label: "Testing & Commissioning", labelKey: "nav.item.construction_testing_commissioning", exact: true },
          { href: "/construction/cost-control", label: "Cost Control", labelKey: "nav.item.construction_cost_control", exact: true },
          { href: "/construction/reports", label: "Reports", labelKey: "nav.item.construction_reports", exact: true },
        ],
      },
    ],
  },

  // ── 4. Supply Chain ───────────────────────────────────────────────────
  {
    key: "supply-chain",
    label: "Supply Chain",
    labelKey: "nav.supply_chain",
    sections: [
      {
        key: "procurement",
        label: "Procurement",
        labelKey: "nav.section.procurement",
        href: "/procurement",
        subItems: [
          { href: "/procurement", label: "Dashboard", labelKey: "nav.item.procurement", exact: true },
          { href: "/procurement/requisitions", label: "Requisitions (PR)", labelKey: "nav.item.procurement_requisitions" },
          { href: "/procurement/rfqs", label: "RFQs / Bidding", labelKey: "nav.item.procurement_rfqs" },
          { href: "/procurement/tender-comparisons", label: "Tender Comparisons", labelKey: "nav.item.procurement_tender_comparisons" },
          { href: "/procurement/vendor-selection", label: "Vendor Selection", labelKey: "nav.item.procurement_vendor_selection" },
          { href: "/procurement/purchase-orders", label: "Purchase Orders", labelKey: "nav.item.procurement_purchase_orders" },
          { href: "/procurement/vendors", label: "Vendors (Suppliers)", labelKey: "nav.item.procurement_vendors" },
          { href: "/procurement/contracts", label: "Contracts & Agreements", labelKey: "nav.item.procurement_contracts" },
          { href: "/procurement/delivery-tracking", label: "Delivery Tracking", labelKey: "nav.item.procurement_delivery_tracking" },
          { href: "/procurement/goods-receipts", label: "Goods Received Notes", labelKey: "nav.item.procurement_goods_receipts" },
          { href: "/procurement/invoice-matching", label: "Invoice Matching", labelKey: "nav.item.procurement_invoice_matching" },
          { href: "/procurement/approvals", label: "Approvals", labelKey: "nav.item.procurement_approvals" },
          { href: "/procurement/spend-analytics", label: "Spend Analytics", labelKey: "nav.item.procurement_spend_analytics" },
          { href: "/procurement/settings", label: "Settings", labelKey: "nav.item.procurement_settings" },
        ],
      },
      {
        key: "material-management",
        label: "Material Management",
        labelKey: "nav.section.material_management",
        href: "/material-management",
        subItems: [
          { href: "/material-management/master-database", label: "Material Master Database", labelKey: "nav.item.material_management_master_database" },
          { href: "/material-management/bills-of-materials", label: "Bills of Materials", labelKey: "nav.item.material_management_bills_of_materials" },
          { href: "/material-management/requisitions", label: "Material Requisition (Site)", labelKey: "nav.item.material_management_requisitions" },
          { href: "/material-management/procurement-integration", label: "Procurement Integration", labelKey: "nav.item.material_management_procurement_integration" },
          { href: "/material-management/goods-receipt", label: "Goods Receipt", labelKey: "nav.item.material_management_goods_receipt" },
          { href: "/material-management/issue-to-construction", label: "Issue to Construction", labelKey: "nav.item.material_management_issue_to_construction" },
          { href: "/material-management/consumption-tracking", label: "Consumption Tracking", labelKey: "nav.item.material_management_consumption_tracking" },
          { href: "/material-management/transfers", label: "Material Transfers", labelKey: "nav.item.material_management_transfers" },
          { href: "/material-management/returns", label: "Returns Management", labelKey: "nav.item.material_management_returns" },
        ],
      },
      {
        key: "inventory",
        label: "Inventory",
        labelKey: "nav.section.inventory",
        href: "/inventory",
        subItems: [
          { href: "/inventory", label: "Overview", labelKey: "nav.item.inventory", exact: true },
          { href: "/inventory/items", label: "Items", labelKey: "nav.item.inventory_items" },
          { href: "/inventory/stock", label: "Stock", labelKey: "nav.item.inventory_stock" },
          { href: "/inventory/movements", label: "Movements", labelKey: "nav.item.inventory_movements" },
          { href: "/inventory/warehouses", label: "Warehouses", labelKey: "nav.item.inventory_warehouses" },
        ],
      },
    ],
  },

  // ── 5. Assets ─────────────────────────────────────────────────────────
  {
    key: "assets",
    label: "Assets",
    labelKey: "nav.assets",
    sections: [
      {
        key: "properties",
        label: "Properties",
        labelKey: "nav.section.properties",
        href: "/properties",
        subItems: [
          { href: "/properties", label: "Property Registry", labelKey: "nav.item.properties", exact: true },
          { href: "/properties/segmentation", label: "Portfolio Segmentation", labelKey: "nav.item.properties_segmentation" },
          { href: "/properties/maintenance", label: "Facilities & Maintenance", labelKey: "nav.item.properties_maintenance" },
          { href: "/properties/compliance", label: "Compliance", labelKey: "nav.item.properties_compliance" },
          { href: "/properties/valuations", label: "Valuations", labelKey: "nav.item.properties_valuations" },
        ],
      },
      { key: "property-registry", label: "Property Registry", labelKey: "nav.section.property_registry", href: "/properties", subItems: [] },
    ],
  },

  // ── 6. People ─────────────────────────────────────────────────────────
  {
    key: "people",
    label: "People",
    labelKey: "nav.people",
    sections: [
      {
        key: "hr",
        label: "HR",
        labelKey: "nav.section.hr",
        href: "/hr",
        subItems: [
          {
            href: "/hr",
            label: "Organization Structure",
            labelKey: "nav.item.hr",
            matchPaths: ["/hr", "/hr/business-units", "/hr/departments", "/hr/teams", "/hr/positions", "/hr/reporting-lines", "/hr/budgeting", "/hr/vacancies"],
          },
          {
            href: "/hr/employees",
            label: "Employee Directory",
            labelKey: "nav.item.hr_employees",
            matchPaths: ["/hr/employees", "/hr/employment-history", "/hr/contact-info", "/hr/id-documents", "/hr/emergency-contacts", "/hr/compensation", "/hr/contracts", "/hr/attachments"],
          },
          {
            href: "/hr/requisitions",
            label: "Recruitment & Hiring",
            labelKey: "nav.item.hr_requisitions",
            matchPaths: ["/hr/requisitions", "/hr/job-listings", "/hr/candidates", "/hr/interviews", "/hr/evaluations", "/hr/offers", "/hr/hiring-workflow"],
          },
          {
            href: "/hr/onboarding-templates",
            label: "Onboarding",
            labelKey: "nav.item.hr_onboarding_templates",
            matchPaths: ["/hr/onboarding-templates", "/hr/onboarding-tasks", "/hr/document-collection", "/hr/equipment-allocation", "/hr/orientation-checklists", "/hr/probation-tracking"],
          },
          {
            href: "/hr/performance-goals",
            label: "Performance Management",
            labelKey: "nav.item.hr_performance_goals",
            matchPaths: ["/hr/performance-goals", "/hr/performance-reviews", "/hr/continuous-feedback", "/hr/manager-evaluations", "/hr/peer-reviews", "/hr/performance-improvement-plans"],
          },
          {
            href: "/hr/skills-matrix",
            label: "Skills & Capability",
            labelKey: "nav.item.hr_skills_matrix",
            matchPaths: ["/hr/skills-matrix", "/hr/certifications", "/hr/licenses", "/hr/competency-assessments", "/hr/training-records"],
          },
          {
            href: "/hr/training-courses",
            label: "Learning & Development",
            labelKey: "nav.item.hr_training_courses",
            matchPaths: ["/hr/training-courses", "/hr/training-plans", "/hr/course-enrollments", "/hr/learning-library", "/hr/training-completions", "/hr/certification-expiry-alerts"],
          },
          {
            href: "/hr/attendance-logs",
            label: "Attendance & Leave",
            labelKey: "nav.item.hr_attendance_logs",
            matchPaths: ["/hr/attendance-logs", "/hr/leave-requests", "/hr/leave-calendar", "/hr/leave-balances", "/hr/overtime-requests", "/hr/remote-work-logs"],
          },
          {
            href: "/hr/promotions",
            label: "Employee Lifecycle",
            labelKey: "nav.item.hr_promotions",
            matchPaths: ["/hr/promotions", "/hr/transfers", "/hr/role-changes", "/hr/disciplinary-records", "/hr/exit-management", "/hr/exit-interviews"],
          },
          {
            href: "/hr/headcount-analytics",
            label: "Workforce Analytics",
            labelKey: "nav.item.hr_headcount_analytics",
            matchPaths: ["/hr/headcount-analytics", "/hr/turnover-rate", "/hr/department-staffing", "/hr/hiring-funnel", "/hr/workforce-cost", "/hr/diversity-metrics"],
          },
          {
            href: "/hr/hr-policies",
            label: "Documents & Policies",
            labelKey: "nav.item.hr_hr_policies",
            matchPaths: ["/hr/hr-policies", "/hr/employee-handbook", "/hr/compliance-documents", "/hr/policy-acknowledgements", "/hr/document-templates"],
          },
        ],
      },
      {
        key: "payroll",
        label: "Payroll",
        labelKey: "nav.section.payroll",
        href: "/payroll",
        subItems: [
          { href: "/payroll", label: "Dashboard", labelKey: "nav.item.payroll", exact: true },
          { href: "/hr/payroll-processing", label: "Payroll Runs", labelKey: "nav.item.hr_payroll_processing" },
          { href: "/payroll/employee-payroll-profiles", label: "Employee Payroll Profiles", labelKey: "nav.item.payroll_employee_payroll_profiles" },
          { href: "/hr/salary-structures", label: "Salary Structures", labelKey: "nav.item.hr_salary_structures", exact: true },
          { href: "/hr/allowances", label: "Allowances", labelKey: "nav.item.hr_allowances" },
          { href: "/hr/deductions", label: "Earnings & Deductions", labelKey: "nav.item.hr_deductions" },
          { href: "/payroll/time-inputs", label: "Time & Inputs", labelKey: "nav.item.payroll_time_inputs" },
          { href: "/hr/bonuses", label: "Bonuses & Adjustments", labelKey: "nav.item.hr_bonuses" },
          { href: "/payroll/disbursements", label: "Disbursements", labelKey: "nav.item.payroll_disbursements" },
          { href: "/hr/payslips", label: "Payslips", labelKey: "nav.item.hr_payslips" },
          { href: "/hr/tax-records", label: "Tax Records", labelKey: "nav.item.hr_tax_records" },
          { href: "/payroll/reports", label: "Reports", labelKey: "nav.item.payroll_reports" },
          { href: "/payroll/accounting-integration", label: "Accounting Integration", labelKey: "nav.item.payroll_accounting_integration" },
          { href: "/payroll/audit-logs", label: "Audit Logs", labelKey: "nav.item.payroll_audit_logs" },
        ],
      },
      {
        key: "partners",
        label: "Partners",
        labelKey: "nav.section.partners",
        href: "/partners",
        subItems: [
          { href: "/partners", label: "Onboarding Hub", labelKey: "nav.item.partners", exact: true },
        ],
      },
    ],
  },

  // ── 7. Finance ────────────────────────────────────────────────────────
  {
    key: "finance",
    label: "Finance",
    labelKey: "nav.finance",
    sections: [
      { key: "finance-dashboard", label: "Finance Dashboard", labelKey: "nav.section.finance_dashboard", href: "/finance/dashboard", subItems: [] },
      { key: "budgets", label: "Budgets", labelKey: "nav.section.budgets", href: "/finance/budgets", subItems: [] },
      {
        key: "cost-tracking",
        label: "Cost Tracking",
        labelKey: "nav.section.cost_tracking",
        href: "/finance",
        subItems: [
          { href: "/finance", label: "Cost Tracker", labelKey: "nav.item.finance", exact: true },
          { href: "/finance/variance-analysis", label: "Variance Analysis", labelKey: "nav.item.finance_variance_analysis" },
          { href: "/finance/investors", label: "Investors", labelKey: "nav.item.finance_investors" },
          { href: "/finance/reports/trial-balance", label: "Trial Balance", labelKey: "nav.item.finance_reports_trial_balance" },
          { href: "/finance/spv", label: "SPV Entities", labelKey: "nav.item.finance_spv" },
          { href: "/finance/payment-plans", label: "Payment Plans", labelKey: "nav.item.finance_payment_plans" },
        ],
      },
      { key: "treasury", label: "Treasury", labelKey: "nav.section.treasury", href: "/treasury", subItems: [] },
    ],
  },

  // ── 8. Accounting ───────────────────────────────────────────────────
  {
    key: "accounting",
    label: "Accounting",
    labelKey: "nav.accounting",
    sections: [
      { key: "chart-of-accounts", label: "Chart of Accounts", labelKey: "nav.section.chart_of_accounts", href: "/finance/chart-of-accounts", subItems: [] },
      { key: "journal-entries", label: "Journal Entries", labelKey: "nav.section.journal_entries", href: "/finance/journals", subItems: [] },
      {
        key: "accounts-payable",
        label: "Accounts Payable",
        labelKey: "nav.section.accounts_payable",
        href: "/accounting/accounts-payable",
        subItems: [
          { href: "/finance/bills", label: "Bills", labelKey: "nav.item.finance_bills" },
          { href: "/finance/payment-vouchers", label: "Payment Vouchers", labelKey: "nav.item.finance_payment_vouchers" },
          { href: "/finance/payment-runs", label: "Payment Runs", labelKey: "nav.item.finance_payment_runs" },
          { href: "/finance/aging-report", label: "Aging Report", labelKey: "nav.item.finance_aging_report" },
        ],
      },
      {
        key: "accounts-receivable",
        label: "Accounts Receivable",
        labelKey: "nav.section.accounts_receivable",
        href: "/accounting/accounts-receivable",
        subItems: [
          { href: "/finance/invoices", label: "Invoices", labelKey: "nav.item.finance_invoices" },
          { href: "/finance/customers", label: "Customers", labelKey: "nav.item.finance_customers" },
          { href: "/finance/payment-receipts", label: "Payment Receipts", labelKey: "nav.item.finance_payment_receipts" },
        ],
      },
      {
        key: "banking",
        label: "Banking",
        labelKey: "nav.section.banking",
        href: "/finance/banking",
        subItems: [
          { href: "/finance/bank-accounts", label: "Bank Accounts", labelKey: "nav.item.finance_bank_accounts" },
          { href: "/finance/bank-transactions", label: "Bank Transactions", labelKey: "nav.item.finance_bank_transactions" },
          { href: "/finance/bank-reconciliation", label: "Reconciliation", labelKey: "nav.item.finance_bank_reconciliation" },
        ],
      },
      { key: "general-ledger", label: "General Ledger", labelKey: "nav.section.general_ledger", href: "/finance/reports/general-ledger", subItems: [] },
    ],
  },

  // ── 9. Governance ───────────────────────────────────────────────────── ─────────────────────────────────────────────────────
  {
    key: "governance",
    label: "Governance",
    labelKey: "nav.governance",
    sections: [
      {
        key: "contracts",
        label: "Contracts",
        labelKey: "nav.section.contracts",
        href: "/contracts",
        subItems: [
          { href: "/contracts", label: "Overview", labelKey: "nav.item.contracts", exact: true },
          { href: "/contracts/main-contracts", label: "Main Contracts", labelKey: "nav.item.contracts_main_contracts" },
          { href: "/contracts/subcontracts", label: "Subcontracts", labelKey: "nav.item.contracts_subcontracts" },
          { href: "/contracts/variation-orders", label: "Variation Orders", labelKey: "nav.item.contracts_variation_orders" },
          { href: "/contracts/payment-terms", label: "Payment Terms", labelKey: "nav.item.contracts_payment_terms" },
          { href: "/contracts/value-vs-executed", label: "Value vs Executed", labelKey: "nav.item.contracts_value_vs_executed" },
          { href: "/contracts/retention-tracking", label: "Retention Tracking", labelKey: "nav.item.contracts_retention_tracking" },
          { href: "/contracts/claims-management", label: "Claims Management", labelKey: "nav.item.contracts_claims_management" },
          { href: "/contracts/dispute-log", label: "Dispute Log", labelKey: "nav.item.contracts_dispute_log" },
        ],
      },
      {
        key: "documents",
        label: "Documents",
        labelKey: "nav.section.documents",
        href: "/documents",
        subItems: [
          { href: "/documents/dashboard", label: "Dashboard", labelKey: "nav.item.documents_dashboard", exact: true },
          { href: "/documents/repository", label: "Repository", labelKey: "nav.item.documents_repository", exact: true },
          { href: "/documents/ocr", label: "OCR Extraction", labelKey: "nav.item.documents_ocr" },
          { href: "/documents/signatures", label: "E-Signatures", labelKey: "nav.item.documents_signatures" },
          { href: "/documents/generator", label: "Document Generator", labelKey: "nav.item.documents_generator" },
        ],
      },
      { key: "compliance-governance", label: "Compliance", labelKey: "nav.section.compliance_governance", href: "/compliance", subItems: [] },
      { key: "permits", label: "Permits", labelKey: "nav.section.permits", href: "/permits", subItems: [] },
      { key: "audit-logs", label: "Audit Logs", labelKey: "nav.section.audit_logs", href: "/audit-logs", subItems: [] },
      { key: "risk-management", label: "Risk Management", labelKey: "nav.section.risk_management", href: "/risk-management", subItems: [] },
    ],
  },

  // ── 10. Workspace ──────────────────────────────────────────────────────
  {
    key: "workspace",
    label: "Workspace",
    labelKey: "nav.workspace",
    sections: [
      {
        key: "support-desk",
        label: "Support Desk",
        labelKey: "nav.section.support_desk",
        href: "/support-desk",
        subItems: supportDeskNavItems as NavSubItem[],
      },
      { key: "internal-tasks", label: "Internal Tasks", labelKey: "nav.section.internal_tasks", href: "/internal-tasks", subItems: [] },
      { key: "calendar", label: "Calendar", labelKey: "nav.section.calendar", href: "/calendar", subItems: [] },
      { key: "teams", label: "Teams", labelKey: "nav.section.teams", href: "/teams", subItems: [] },
    ],
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Flatten all sections from all domains into a single array (for CommandPalette). */
export function flattenSections(doms: NavDomain[]): NavDomainSection[] {
  return doms.flatMap((d) => d.sections);
}

/**
 * Resolve a nav item's display label, preferring the i18n translation if a
 * `labelKey` is set. Falls back to the English `label` when:
 *   - the item has no labelKey at all (incremental migration: not every
 *     entry needs to be translated immediately)
 *   - the labelKey is set but the active locale is missing that string
 *
 * Pass the i18n module's `t` function in so this helper stays a pure
 * function — easier to test, no hidden import-time coupling.
 */
export function navLabel(
  item: { label: string; labelKey?: string },
  t: (key: string) => string,
): string {
  if (!item.labelKey) return item.label;
  const translated = t(item.labelKey);
  // The store's t() returns the raw key when no translation matches; in
  // that case prefer the in-code English label so the UI never shows
  // "nav.dashboard" to a user.
  return translated === item.labelKey ? item.label : translated;
}

// ---------------------------------------------------------------------------
// Domain icon SVG paths (Panel 1 — 52px icon rail)
// ---------------------------------------------------------------------------

export function domainIconPath(key: string): string {
  const map: Record<string, string> = {
    dashboard:
      "M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25a2.25 2.25 0 0 1-2.25-2.25v-2.25Z",
    operations:
      "M19.5 12c0-1.232-.046-2.453-.138-3.662a4.006 4.006 0 0 0-3.7-3.7 48.678 48.678 0 0 0-7.324 0 4.006 4.006 0 0 0-3.7 3.7c-.017.22-.032.441-.046.662M19.5 12l3-3m-3 3-3-3m-12 3c0 1.232.046 2.453.138 3.662a4.006 4.006 0 0 0 3.7 3.7 48.656 48.656 0 0 0 7.324 0 4.006 4.006 0 0 0 3.7-3.7c.017-.22.032-.441.046-.662M4.5 12l3 3m-3-3-3 3",
    development:
      "M3.75 20.25h16.5M5.25 20.25V6.75l6.75-3 6.75 3v13.5M9 12.75h6M9 16.5h6",
    "supply-chain":
      "m21 7.5-9-5.25L3 7.5m18 0-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9",
    assets:
      "M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21",
    people:
      "M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z",
    finance:
      "M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z",
    accounting:
      "M15.75 15.75V18m-7.5-6.75h.008v.008H8.25v-.008Zm0 2.25h.008v.008H8.25V13.5Zm0 2.25h.008v.008H8.25v-.008Zm0 2.25h.008v.008H8.25V18Zm2.498-6.75h.007v.008h-.007v-.008Zm0 2.25h.007v.008h-.007V13.5Zm0 2.25h.007v.008h-.007v-.008Zm0 2.25h.007v.008h-.007V18Zm2.504-6.75h.008v.008h-.008v-.008Zm0 2.25h.008v.008h-.008V13.5Zm0 2.25h.008v.008h-.008v-.008Zm0 2.25h.008v.008h-.008V18Zm2.498-6.75h.008v.008h-.008v-.008Zm0 2.25h.008v.008h-.008V13.5ZM8.25 6h7.5v2.25h-7.5V6ZM12 2.25c-1.892 0-3.758.11-5.593.322C5.307 2.7 4.5 3.65 4.5 4.757V19.5a2.25 2.25 0 0 0 2.25 2.25h10.5a2.25 2.25 0 0 0 2.25-2.25V4.757c0-1.108-.806-2.057-1.907-2.185A48.507 48.507 0 0 0 12 2.25Z",
    governance:
      "M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z",
    workspace:
      "M3.75 4.5h16.5v6H3.75v-6Zm0 9h7.5v6H3.75v-6Zm10.5 0h6v6h-6v-6Z",
  };
  return map[key] ?? "M12 6v12m6-6H6";
}

// ---------------------------------------------------------------------------
// Sub-item icon SVG paths (Panel 3 — sub-items)
// Moved from +layout.svelte to keep the layout file focused on rendering.
// ---------------------------------------------------------------------------

export function subItemIconPath(href: string): string {
  const directMap: Record<string, string> = {
    "/": "M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25A2.25 2.25 0 0 1 8.25 10.5H6A2.25 2.25 0 0 1 3.75 8.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25a2.25 2.25 0 0 1-2.25-2.25v-2.25Z",
    "/dashboard/portfolio-analysis": "M3 3v18h18M7.5 15.75h3v3h-3v-3Zm4.5-5.25h3v8.25h-3V10.5Zm4.5-3h3v11.25h-3V7.5",
    "/dashboard/board-metrics": "M3 3v18h18M7.5 15.75h3v3h-3v-3Zm4.5-5.25h3v8.25h-3V10.5Zm4.5-3h3v11.25h-3V7.5Z",
    "/dashboard/custom": "M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25A2.25 2.25 0 0 1 8.25 10.5H6A2.25 2.25 0 0 1 3.75 8.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25a2.25 2.25 0 0 1-2.25-2.25v-2.25Z",
    "/projects": "M3.75 6.75h16.5m-16.5 5.25h16.5m-16.5 5.25h10.5",
    "/projects/execution-stats": "M3 3v18h18M7.5 14.25l3-3 2.25 2.25L17.25 9",
    "/projects/project-pipeline": "M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0-.5 1.5m.5-1.5h-9.5m0 0-.5 1.5",
    "/projects/project-setup": "M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28ZM15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
    "/projects/feasibility-viability": "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z",
    "/projects/land-acquisition": "M9 6.75V15m0-7.5a3 3 0 0 1 3-3h.75M9 15a3 3 0 0 0 3 3h.75m0-12A3 3 0 0 1 15.75 3H18A2.25 2.25 0 0 1 20.25 5.25v13.5A2.25 2.25 0 0 1 18 21h-2.25A3 3 0 0 1 12.75 18m0-12V3.375c0-.621-.504-1.125-1.125-1.125H8.25M12.75 18v2.625c0 .621-.504 1.125-1.125 1.125H8.25",
    "/projects/development-budget": "M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z",
    "/projects/financing": "M12 21v-8.25M15.75 21V11.25M8.25 21v-3.375c0-.621.504-1.125 1.125-1.125h1.5c.621 0 1.125.504 1.125 1.125V21m0-12.75V5.625c0-.621.504-1.125 1.125-1.125h1.5c.621 0 1.125.504 1.125 1.125v2.625m0 0V21m0-14.625h3.375c.621 0 1.125.504 1.125 1.125v8.25c0 .621-.504 1.125-1.125 1.125h-3.375",
    "/projects/development-schedule": "M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5m-9-6h.008v.008H12v-.008ZM12 15h.008v.008H12V15Zm0 2.25h.008v.008H12v-.008ZM9.75 15h.008v.008H9.75V15Zm0 2.25h.008v.008H9.75v-.008ZM7.5 15h.008v.008H7.5V15Zm0 2.25h.008v.008H7.5v-.008Zm6.75-4.5h.008v.008h-.008v-.008Zm0 2.25h.008v.008h-.008V15Zm0 2.25h.008v.008h-.008v-.008Zm2.25-4.5h.008v.008H16.5v-.008Zm0 2.25h.008v.008H16.5V15Z",
    "/projects/consultants-stakeholders": "M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z",
    "/projects/approvals-permits": "M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z",
    "/projects/design-management": "M9.53 16.122a3 3 0 0 0-5.78 1.128 2.25 2.25 0 0 1-2.4 2.245 4.5 4.5 0 0 0 8.4-2.245c0-.399-.078-.78-.22-1.128Zm0 0a15.998 15.998 0 0 0 3.388-1.62m-5.043-.025a15.994 15.994 0 0 1 1.622-3.395m3.42 3.42a15.995 15.995 0 0 0 4.764-4.648l3.876-5.814a1.151 1.151 0 0 0-1.597-1.597L14.146 6.32a15.996 15.996 0 0 0-4.649 4.763m3.42 3.42a6.776 6.776 0 0 0-3.42-3.42",
    "/projects/procurement-planning": "M15.75 10.5V6a3.75 3.75 0 1 0-7.5 0v4.5m11.356-1.993 1.263 12c.07.665-.45 1.243-1.119 1.243H4.25a1.125 1.125 0 0 1-1.12-1.243l1.264-12A1.125 1.125 0 0 1 5.513 7.5h12.974c.576 0 1.059.435 1.119 1.007ZM8.625 10.5a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm7.5 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z",
    "/projects/sales-revenue-forecast": "M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941",
    "/projects/governance": "M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418",
    "/projects/milestones-stage-gates": "M3 3v1.5M3 21v-6m0 0 2.77-.693a9 9 0 0 1 6.208.682l.108.054a9 9 0 0 0 6.086.71l3.114-.732a48.524 48.524 0 0 1-.005-10.499l-3.11.732a9 9 0 0 1-6.085-.711l-.108-.054a9 9 0 0 0-6.208-.682L3 4.5M3 15V4.5",
    "/projects/document-control": "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z",
    "/projects/communications": "M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z",
    "/projects/reports": "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z",
    "/projects/closeout": "M9 12.75 11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 0 1-1.043 3.296 3.745 3.745 0 0 1-3.296 1.043A3.745 3.745 0 0 1 12 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 0 1-3.296-1.043 3.745 3.745 0 0 1-1.043-3.296A3.745 3.745 0 0 1 3 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 0 1 1.043-3.296 3.746 3.746 0 0 1 3.296-1.043A3.746 3.746 0 0 1 12 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 0 1 3.296 1.043 3.746 3.746 0 0 1 1.043 3.296A3.745 3.745 0 0 1 21 12Z",
    "/projects/predictive-intelligence": "M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18",
    "/projects/phases-milestones": "M3.75 4.5h9.75a2.25 2.25 0 0 1 2.25 2.25v9.75m-12-9h9m-9 4.5h9m-9 4.5h4.5m3.75-5.25 2.25 2.25 3.75-4.5",
    "/projects/tasks": "M5.25 6.75h13.5m-13.5 4.5h8.25m-8.25 4.5h6m8.25-8.25 2.25 2.25 3.75-4.5",
    "/projects/budget-cost": "M3.75 4.5h16.5m-16.5 5.25h9.75m-9.75 5.25h6m7.5-3.75h3v7.5h-3zM14.25 9.75h3v9h-3zM8.25 12h3v6.75h-3z",
    "/projects/field-operations": "M3.75 7.5h16.5m-16.5 4.5h9.75m-9.75 4.5h7.5m7.5-9v9m0 0-2.25-2.25m2.25 2.25 2.25-2.25",
    "/projects/issues": "M12 9v3.75h3m6.75-.75a9.75 9.75 0 1 1-19.5 0 9.75 9.75 0 0 1 19.5 0ZM12 17.25h.008v.008H12v-.008Z",
    "/projects/variations": "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9ZM8.25 12h7.5M8.25 15.75h4.5",
    "/projects/risk-register": "M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z",
    "/projects/templates": "M4.5 5.25A2.25 2.25 0 0 1 6.75 3h10.5A2.25 2.25 0 0 1 19.5 5.25v13.5A2.25 2.25 0 0 1 17.25 21H6.75A2.25 2.25 0 0 1 4.5 18.75V5.25ZM8.25 7.5h7.5M8.25 11.25h7.5M8.25 15h4.5",
    "/projects/blueprints": "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25Z",
    "/project-planning": "M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5M8.25 3v18M15.75 3v18",
    "/project-planning/task-templates": "M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0 1 18 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3 1.5 1.5 3-3.75",
    "/project-planning/dependencies": "M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5",
    "/project-planning/scheduling": "M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5",
    "/project-planning/resources": "M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z",
    "/project-planning/cost-projection": "M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z",
    "/project-planning/scenarios": "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z",
    "/boq": "M3.75 5.25h16.5m-16.5 5.25h16.5m-16.5 5.25h16.5M8.25 3v18",
    "/boq/builder": "M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085",
    "/boq/master": "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25Z",
    "/boq/cost-estimates": "M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z",
    "/boq/rate-library": "M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25",
    "/boq/mapping": "M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5",
    "/boq/category-mapping": "M9.568 3H5.25A2.25 2.25 0 0 0 3 5.25v4.318c0 .597.237 1.17.659 1.591l9.581 9.581c.699.699 1.78.872 2.607.33a18.095 18.095 0 0 0 5.223-5.223c.542-.827.369-1.908-.33-2.607L11.16 3.66A2.25 2.25 0 0 0 9.568 3Z M6 6h.008v.008H6V6Z",
    "/boq/revisions": "M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182",
    "/construction/site-overview": "M3.75 20.25h16.5M5.25 20.25V6.75l6.75-3 6.75 3v13.5M9 12.75h6M9 16.5h6",
    "/construction/site-mobilization": "M3.75 20.25h16.5M4.5 6.75h15m-12 4.5h9m-9 4.5h6m6.75-9 2.25 2.25 3.75-4.5",
    "/construction/schedule": "M3.75 5.25h16.5M3.75 12h16.5M3.75 18.75h16.5M8.25 3.75v16.5M15.75 3.75v16.5",
    "/construction/contractor-management": "M18 18.75a3 3 0 0 0 3-3V15a6 6 0 0 0-6-6h-6a6 6 0 0 0-6 6v.75a3 3 0 0 0 3 3h12ZM15 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
    "/construction/equipment": "M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085",
    "/construction/quality-control": "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    "/construction/hse": "M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z",
    "/construction/rfis": "M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 5.25h.008v.008H12v-.008Z",
    "/construction/site-instructions": "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z",
    "/construction/testing-commissioning": "M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0 1 18 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3 1.5 1.5 3-3.75",
    "/construction/cost-control": "M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    "/construction/reports": "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z",
    "/properties": "M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21",
    "/properties/segmentation": "M10.5 6a7.5 7.5 0 1 0 7.5 7.5h-7.5V6ZM13.5 3.75a7.5 7.5 0 0 1 6.75 6.75h-6.75V3.75Z",
    "/properties/maintenance": "M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085",
    "/properties/compliance": "M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z",
    "/properties/valuations": "M2.25 18 9 11.25l4.306 4.306a11.95 11.95 0 0 1 5.814-5.518l2.74-1.22m0 0-5.94-2.281m5.94 2.28-2.28 5.941",
    "/facility-management": "M3.75 4.5h16.5v6H3.75v-6Zm0 9h7.5v6H3.75v-6Zm10.5 0h6v6h-6v-6Z",
    "/facility-management/registry": "M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21",
    "/facility-management/assets": "M4.5 7.5h15m-15 4.5h10.5m-10.5 4.5h7.5m7.5-9 1.5 1.5-4.5 4.5-2.25-2.25",
    "/facility-management/maintenance": "M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085",
    "/facility-management/service-requests": "M3.75 5.25h16.5A2.25 2.25 0 0 1 22.5 7.5v9A2.25 2.25 0 0 1 20.25 18.75H8.25L3 22.5V7.5a2.25 2.25 0 0 1 2.25-2.25Zm4.5 4.5h7.5m-7.5 3.75h4.5",
    "/facility-management/space-occupancy": "M4.5 6.75h15v10.5H4.5V6.75Zm3 3h9m-9 3.75h5.25m7.5 7.5h-15A2.25 2.25 0 0 1 3 18.75V5.25A2.25 2.25 0 0 1 5.25 3h13.5A2.25 2.25 0 0 1 21 5.25v13.5A2.25 2.25 0 0 1 18.75 21Z",
    "/facility-management/utilities": "M3 3v18h18M7.5 15.75h3v3h-3v-3Zm4.5-5.25h3v8.25h-3V10.5Zm4.5-3h3v11.25h-3V7.5",
    "/facility-management/documents": "M5.25 3.75h9l4.5 4.5v10.5A2.25 2.25 0 0 1 16.5 21h-11.25A2.25 2.25 0 0 1 3 18.75V6A2.25 2.25 0 0 1 5.25 3.75Zm2.25 6.75h9M7.5 14.25h9M7.5 18h6",
    "/facility-management/health-safety": "M12 3.75c2.93 2.44 5.756 3.75 8.25 3.75 0 8.516-5.304 12.87-8.25 13.95C9.054 20.37 3.75 16.016 3.75 7.5c2.494 0 5.32-1.31 8.25-3.75Zm-1.5 8.25 1.5 1.5 3.75-3.75",
    "/tenants": "M4.5 6.75A2.25 2.25 0 0 1 6.75 4.5h10.5A2.25 2.25 0 0 1 19.5 6.75v10.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 17.25V6.75Zm4.125 2.625a1.875 1.875 0 1 0 0 3.75 1.875 1.875 0 0 0 0-3.75Zm6.75.75h-3v1.5h3v-1.5Zm-6.75 5.25c-1.553 0-2.865.81-3.518 2.025h7.035c-.652-1.215-1.964-2.025-3.517-2.025Zm4.125 2.025H18v-1.5h-5.25v1.5Z",
    "/tenants/registry": "M6 4.5h9.75L19.5 8.25v11.25A2.25 2.25 0 0 1 17.25 21H6.75A2.25 2.25 0 0 1 4.5 18.75V6.75A2.25 2.25 0 0 1 6.75 4.5Zm2.25 5.25h7.5m-7.5 3.75h7.5m-7.5 3.75H12",
    "/tenants/lease-occupancy": "M4.5 5.25h15v13.5h-15V5.25Zm3 3h9m-9 3.75h9m-9 3.75h5.25M3 18.75V5.25A2.25 2.25 0 0 1 5.25 3h13.5A2.25 2.25 0 0 1 21 5.25v13.5A2.25 2.25 0 0 1 18.75 21H5.25A2.25 2.25 0 0 1 3 18.75Z",
    "/tenants/leases": "M4.5 5.25h15v13.5h-15V5.25Zm3 3h9m-9 3.75h9m-9 3.75h5.25M3 18.75V5.25A2.25 2.25 0 0 1 5.25 3h13.5A2.25 2.25 0 0 1 21 5.25v13.5A2.25 2.25 0 0 1 18.75 21H5.25A2.25 2.25 0 0 1 3 18.75Z",
    "/tenants/billing": "M3.75 6.75h16.5m-16.5 5.25h9.75m-9.75 5.25h6m7.5-6.75a2.25 2.25 0 1 1 0 4.5m-4.5-9v12",
    "/tenants/payments": "M12 6v12m0 0 3-3m-3 3-3-3m8.25-8.25h1.5A2.25 2.25 0 0 1 21 9v9a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 18V9a2.25 2.25 0 0 1 2.25-2.25h1.5",
    "/tenants/service-requests": "M3.75 5.25h16.5A2.25 2.25 0 0 1 22.5 7.5v9A2.25 2.25 0 0 1 20.25 18.75H8.25L3 22.5V7.5a2.25 2.25 0 0 1 2.25-2.25Zm4.5 4.5h7.5m-7.5 3.75h4.5",
    "/tenants/communications": "M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z",
    "/tenants/documents": "M5.25 3.75h9l4.5 4.5v10.5A2.25 2.25 0 0 1 16.5 21h-11.25A2.25 2.25 0 0 1 3 18.75V6A2.25 2.25 0 0 1 5.25 3.75Zm2.25 6.75h9M7.5 14.25h9M7.5 18h6",
    "/tenants/inspections": "M9 12.75 11.25 15 15 9.75m-8.25 9h10.5A2.25 2.25 0 0 0 19.5 17.25V6.75A2.25 2.25 0 0 0 17.25 4.5H6.75A2.25 2.25 0 0 0 4.5 6.75v10.5A2.25 2.25 0 0 0 6.75 19.5Z",
    "/tenants/complaints": "M12 9v3.75h3m6.75-.75a9.75 9.75 0 1 1-19.5 0 9.75 9.75 0 0 1 19.5 0ZM12 17.25h.008v.008H12v-.008Z",
    "/tenants/reports": "M3 3v18h18M7.5 15.75h3v3h-3v-3Zm4.5-5.25h3v8.25h-3V10.5Zm4.5-3h3v11.25h-3V7.5Z",
    "/documents/dashboard": "M3.75 12h16.5m-12 5.25h7.5m-7.5-10.5h7.5M5.25 3h13.5A2.25 2.25 0 0 1 21 5.25v13.5A2.25 2.25 0 0 1 18.75 21H5.25A2.25 2.25 0 0 1 3 18.75V5.25A2.25 2.25 0 0 1 5.25 3Z",
    "/documents/repository": "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z",
    "/documents/ocr": "M3.75 4.5h16.5v15H3.75v-15Zm3 3h3.75m-3.75 4.5h3.75m3.75-4.5h3.75m-3.75 4.5h3.75m-7.5 4.5h4.5",
    "/documents/signatures": "M16.5 7.5h2.25A2.25 2.25 0 0 1 21 9.75V18a2.25 2.25 0 0 1-2.25 2.25H9.75A2.25 2.25 0 0 1 7.5 18v-2.25m9-8.25-3-3m0 0-3 3m3-3V15m-9-6.75V6A2.25 2.25 0 0 1 6.75 3.75h8.25A2.25 2.25 0 0 1 17.25 6v2.25",
    "/documents/generator": "M4.5 4.5A2.25 2.25 0 0 1 6.75 2.25h7.5L19.5 7.5v12A2.25 2.25 0 0 1 17.25 21H6.75A2.25 2.25 0 0 1 4.5 18.75V4.5Zm3.75 6h7.5m-7.5 3.75h7.5m-7.5 3.75h4.5",
    "/procurement": "M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5",
    "/procurement/vendors": "M18 18.75a3 3 0 0 0 3-3V15a6 6 0 0 0-6-6h-6a6 6 0 0 0-6 6v.75a3 3 0 0 0 3 3h12ZM15 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
    "/procurement/requisitions": "M9 12.75h6m-6 3h6m-6-6h6M6.75 3h10.5A2.25 2.25 0 0 1 19.5 5.25v13.5A2.25 2.25 0 0 1 17.25 21H6.75A2.25 2.25 0 0 1 4.5 18.75V5.25A2.25 2.25 0 0 1 6.75 3Z",
    "/procurement/rfqs": "M3.75 4.5h16.5v15H3.75v-15Zm3 3h5.25m-5.25 3.75h10.5m-10.5 3.75h7.5",
    "/procurement/tender-comparisons": "M4.5 18V6m5.25 12V9m5.25 9v-6m5.25 6V4.5",
    "/procurement/vendor-selection": "M3.75 6.75h16.5m-16.5 4.5h10.5m-10.5 4.5h7.5m8.25-7.5 2.25 2.25 3.75-4.5",
    "/procurement/purchase-orders": "M2.25 3h1.386c.51 0 .955.343 1.086.837L5.25 6m0 0h13.5l-1.5 6H6.219m-.969-6 1.286 6m0 0h10.714M9 19.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Zm9 0a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0Z",
    "/procurement/delivery-tracking": "M3 3v18h18M6.75 15.75h3v3h-3v-3Zm4.5-5.25h3v8.25h-3V10.5Zm4.5-3h3v11.25h-3V7.5Z",
    "/procurement/goods-receipts": "M9 12.75 11.25 15l3.75-4.5m-8.25 9h10.5A2.25 2.25 0 0 0 19.5 17.25V6.75A2.25 2.25 0 0 0 17.25 4.5H6.75A2.25 2.25 0 0 0 4.5 6.75v10.5A2.25 2.25 0 0 0 6.75 19.5Z",
    "/material-management/master-database": "M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125v-3.75",
    "/material-management/bills-of-materials": "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15a2.25 2.25 0 0 1 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25Z",
    "/contracts": "M5.25 3.75h9l4.5 4.5v10.5A2.25 2.25 0 0 1 16.5 21h-11.25A2.25 2.25 0 0 1 3 18.75V6A2.25 2.25 0 0 1 5.25 3.75Zm2.25 6.75h9M7.5 14.25h9M7.5 18h6",
    "/contracts/main-contracts": "M4.5 4.5A2.25 2.25 0 0 1 6.75 2.25h7.5L19.5 7.5v12A2.25 2.25 0 0 1 17.25 21H6.75A2.25 2.25 0 0 1 4.5 18.75V4.5Zm3.75 6h7.5m-7.5 3.75h7.5m-7.5 3.75h4.5",
    "/contracts/subcontracts": "M3.75 6.75h16.5m-16.5 4.5h10.5m-10.5 4.5h7.5m8.25-7.5 2.25 2.25 3.75-4.5",
    "/contracts/variation-orders": "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9ZM8.25 12h7.5M8.25 15.75h4.5",
    "/contracts/payment-terms": "M4.5 6.75h15m-15 5.25h10.5m-10.5 5.25h6M15 10.5h4.5m-4.5 5.25h4.5",
    "/contracts/value-vs-executed": "M3 3v18h18M7.5 15.75h3v3h-3v-3Zm4.5-5.25h3v8.25h-3V10.5Zm4.5-3h3v11.25h-3V7.5Z",
    "/contracts/retention-tracking": "M12 8.25v4.5l3 1.5m6-2.25a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    "/contracts/claims-management": "M3.75 4.5h16.5v15H3.75v-15Zm3 3h10.5m-10.5 3.75h10.5m-10.5 3.75h7.5",
    "/contracts/dispute-log": "M12 9v3.75h3m6.75-.75a9.75 9.75 0 1 1-19.5 0 9.75 9.75 0 0 1 19.5 0ZM12 17.25h.008v.008H12v-.008Z",
    "/crm": "M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z",
    "/crm/leads": "M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z",
    "/crm/opportunities": "M2.25 12.75 11.204 3.795c.44-.44 1.152-.44 1.591 0l8.955 8.955M4.5 10.5v7.125c0 .621.504 1.125 1.125 1.125h3.75v-4.5c0-.621.504-1.125 1.125-1.125h3a1.125 1.125 0 0 1 1.125 1.125v4.5h3.75c.621 0 1.125-.504 1.125-1.125V10.5",
    "/crm/property-matching": "M3 3v18h18M6.75 15.75h3v3h-3v-3Zm4.5-4.5h3v7.5h-3v-7.5Zm4.5-3h3v10.5h-3V8.25",
    "/crm/reservations": "M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5",
    "/crm/contacts": "M15 9h3.75M15 12h3.75M15 15h3.75M4.5 19.5h15a2.25 2.25 0 0 0 2.25-2.25V6.75A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25v10.5A2.25 2.25 0 0 0 4.5 19.5Zm6-10.125a1.875 1.875 0 1 1-3.75 0 1.875 1.875 0 0 1 3.75 0Zm1.294 6.336a6.721 6.721 0 0 1-3.17.789 6.721 6.721 0 0 1-3.168-.789 3.376 3.376 0 0 1 6.338 0Z",
    "/crm/assessments": "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15a2.25 2.25 0 0 1 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25Z",
    "/crm/brokers": "M20.25 14.15v4.25c0 1.094-.787 2.036-1.872 2.18-2.087.277-4.216.42-6.378.42s-4.291-.143-6.378-.42c-1.085-.144-1.872-1.086-1.872-2.18v-4.25m16.5 0a2.18 2.18 0 0 0 .75-1.661V8.706c0-1.081-.768-2.015-1.837-2.175a48.114 48.114 0 0 0-3.413-.387m4.5 8.006c-.194.165-.42.295-.673.38A23.978 23.978 0 0 1 12 15.75c-2.648 0-5.195-.429-7.577-1.22a2.016 2.016 0 0 1-.673-.38m0 0A2.18 2.18 0 0 1 3 12.489V8.706c0-1.081.768-2.015 1.837-2.175a48.111 48.111 0 0 1 3.413-.387m7.5 0V5.25A2.25 2.25 0 0 0 13.5 3h-3a2.25 2.25 0 0 0-2.25 2.25v.894m7.5 0a48.667 48.667 0 0 0-7.5 0",
    "/crm/activities-tasks": "M9 12.75 11.25 15 15 9.75M21.75 12c0 5.385-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12 6.615 2.25 12 2.25 21.75 6.615 21.75 12Z",
    "/crm/communications": "M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z",
    "/crm/campaigns": "M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 1 1 0-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.51l-.657.38c-.551.32-1.26.119-1.527-.461a20.845 20.845 0 0 1-1.44-4.282m3.102.069a18.03 18.03 0 0 1-.59-4.59c0-1.586.205-3.124.59-4.59m0 9.18a23.848 23.848 0 0 1 8.835 2.535M10.34 6.66a23.847 23.847 0 0 0 8.835-2.535m0 0A23.74 23.74 0 0 0 18.795 3m.38 1.125a23.91 23.91 0 0 1 1.014 5.395m-1.014 8.855c-.118.38-.245.754-.38 1.125m.38-1.125a23.91 23.91 0 0 0 1.014-5.395m0-3.46c.495.413.811 1.035.811 1.73 0 .695-.316 1.317-.811 1.73m0-3.46a24.347 24.347 0 0 1 0 3.46",
    "/crm/analytics-reporting": "M3 3v18h18M7.5 15.75h3v3h-3v-3Zm4.5-5.25h3v8.25h-3V10.5Zm4.5-3h3v11.25h-3V7.5",
    "/support-desk": "M3.75 4.5h16.5v6H3.75v-6Zm0 9h7.5v6H3.75v-6Zm10.5 0h6v6h-6v-6Z",
    "/support-desk/tickets": "M4.5 7.5A2.25 2.25 0 0 1 6.75 5.25h10.5A2.25 2.25 0 0 1 19.5 7.5v2.25a1.5 1.5 0 0 0 0 3V15a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 15v-2.25a1.5 1.5 0 0 0 0-3V7.5Zm4.5 1.5h6M9 11.25h6",
    "/support-desk/requests": "M7.5 3.75h9A2.25 2.25 0 0 1 18.75 6v12A2.25 2.25 0 0 1 16.5 20.25h-9A2.25 2.25 0 0 1 5.25 18V6A2.25 2.25 0 0 1 7.5 3.75Zm2.25 4.5h4.5m-4.5 3.75h4.5m-4.5 3.75h3",
    "/support-desk/knowledge-base": "M12 6.75v13.5m0-13.5c-1.623-1.06-4.425-1.5-6.75-.75v11.25c2.325-.75 5.127-.31 6.75.75m0-11.25c1.623-1.06 4.425-1.5 6.75-.75v11.25c-2.325-.75-5.127-.31-6.75.75",
    "/support-desk/sla-escalations": "M12 6v6l3.75 2.25m5.25-2.25a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    "/support-desk/communication": "M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z",
    "/support-desk/automation": "M4.5 12h4.125m6.75 0H19.5M12 4.5v4.125m0 6.75V19.5m-4.243-4.243 2.917-2.917m2.652-2.652 2.917-2.917m-8.486 0 2.917 2.917m2.652 2.652 2.917 2.917",
    "/support-desk/reports": "M3 3v18h18M7.5 15.75h3v3h-3v-3Zm4.5-5.25h3v8.25h-3V10.5Zm4.5-3h3v11.25h-3V7.5Z",
    "/support-desk/configuration": "M4.5 6.75h15m-15 5.25h9.75m-9.75 5.25h12M3 6.75h.008v.008H3V6.75Zm0 5.25h.008v.008H3V12Zm0 5.25h.008v.008H3v-.008Z",
    "/partners": "M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244",
    "/payroll": "M3.75 21h16.5M5.25 18.75V8.25A2.25 2.25 0 0 1 7.5 6h9A2.25 2.25 0 0 1 18.75 8.25v10.5M8.25 10.5h7.5M8.25 14.25h4.5",
    "/payroll/employee-payroll-profiles": "M15 9h3.75M15 12h3.75M15 15h3.75M4.5 19.5h15a2.25 2.25 0 0 0 2.25-2.25V6.75A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25v10.5A2.25 2.25 0 0 0 4.5 19.5Zm6-10.125a1.875 1.875 0 1 1-3.75 0 1.875 1.875 0 0 1 3.75 0Zm1.294 6.336a6.721 6.721 0 0 1-3.17.789 6.721 6.721 0 0 1-3.168-.789 3.376 3.376 0 0 1 6.338 0Z",
    "/payroll/time-inputs": "M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    "/payroll/disbursements": "M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z",
    "/payroll/reports": "M3 3v18h18M7.5 15.75h3v3h-3v-3Zm4.5-5.25h3v8.25h-3V10.5Zm4.5-3h3v11.25h-3V7.5",
    "/payroll/accounting-integration": "M4.5 6.75h15m-15 5.25h15m-15 5.25h9M3 6.75h.008v.008H3V6.75Zm0 5.25h.008v.008H3V12Zm0 5.25h.008v.008H3v-.008Z",
    "/payroll/audit-logs": "M5.25 4.5h13.5A2.25 2.25 0 0 1 21 6.75v10.5A2.25 2.25 0 0 1 18.75 19.5H5.25A2.25 2.25 0 0 1 3 17.25V6.75A2.25 2.25 0 0 1 5.25 4.5Zm3 3.75h7.5m-7.5 3.75h7.5m-7.5 3.75h4.5",
    "/hr": "M3.75 21h16.5M4.5 3h15M5.25 3v18M18.75 3v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21",
    "/hr/employees": "M15 9h3.75M15 12h3.75M15 15h3.75M4.5 19.5h15a2.25 2.25 0 0 0 2.25-2.25V6.75A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25v10.5A2.25 2.25 0 0 0 4.5 19.5Zm6-10.125a1.875 1.875 0 1 1-3.75 0 1.875 1.875 0 0 1 3.75 0Zm1.294 6.336a6.721 6.721 0 0 1-3.17.789 6.721 6.721 0 0 1-3.168-.789 3.376 3.376 0 0 1 6.338 0Z",
    "/hr/requisitions": "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15a2.25 2.25 0 0 1 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25Z",
    "/hr/onboarding-templates": "M3.75 6.75h16.5m-16.5 4.5h10.5m-10.5 4.5h7.5m8.25-7.5 2.25 2.25 3.75-4.5",
    "/hr/performance-goals": "M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z",
    "/hr/skills-matrix": "M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342",
    "/hr/training-courses": "M4.26 10.147a60.438 60.438 0 0 0-.491 6.347A48.62 48.62 0 0 1 12 20.904a48.62 48.62 0 0 1 8.232-4.41 60.46 60.46 0 0 0-.491-6.347m-15.482 0a50.636 50.636 0 0 0-2.658-.813A59.906 59.906 0 0 1 12 3.493a59.903 59.903 0 0 1 10.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.717 50.717 0 0 1 12 13.489a50.702 50.702 0 0 1 7.74-3.342",
    "/hr/attendance-logs": "M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    "/hr/salary-structures": "M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    "/hr/payroll-processing": "M6.75 3v2.25M17.25 3v2.25M3.75 7.5h16.5M4.5 6h15A1.5 1.5 0 0 1 21 7.5v10.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18V7.5A1.5 1.5 0 0 1 4.5 6Zm4.5 8.25 1.5 1.5 3-3",
    "/hr/allowances": "M12 6v12m0-12 3 3m-3-3-3 3m8.25 8.25h1.5A2.25 2.25 0 0 1 21 19.5h-18a2.25 2.25 0 0 1 2.25-2.25h1.5",
    "/hr/deductions": "M12 18V6m0 12-3-3m3 3 3-3m-9.75-8.25h13.5A2.25 2.25 0 0 1 21 9v9a2.25 2.25 0 0 1-2.25 2.25H5.25A2.25 2.25 0 0 1 3 18V9a2.25 2.25 0 0 1 2.25-2.25Z",
    "/hr/bonuses": "M11.48 3.499a.562.562 0 0 1 1.04 0l2.125 5.111a.563.563 0 0 0 .475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 0 0-.182.557l1.285 5.385a.562.562 0 0 1-.84.61l-4.725-2.885a.562.562 0 0 0-.586 0L6.982 20.54a.562.562 0 0 1-.84-.61l1.285-5.386a.562.562 0 0 0-.182-.557l-4.204-3.602a.562.562 0 0 1 .321-.988l5.518-.442a.563.563 0 0 0 .475-.345L11.48 3.5Z",
    "/hr/payslips": "M7.5 3.75h6l4.5 4.5v10.5A2.25 2.25 0 0 1 15.75 21H7.5a2.25 2.25 0 0 1-2.25-2.25V6A2.25 2.25 0 0 1 7.5 3.75Zm0 6.75h9M7.5 14.25h6",
    "/hr/tax-records": "M12 3.75c2.93 2.44 5.756 3.75 8.25 3.75 0 8.516-5.304 12.87-8.25 13.95C9.054 20.37 3.75 16.016 3.75 7.5c2.494 0 5.32-1.31 8.25-3.75Zm-1.5 7.5h3m-3 3h3",
    "/hr/promotions": "M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5",
    "/hr/headcount-analytics": "M3 3v18h18M7.5 14.25l3-3 2.25 2.25L17.25 9",
    "/hr/hr-policies": "M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z",
    "/finance": "M2.25 18.75a60.07 60.07 0 0 1 19.5 0M3.75 15.75V4.5h16.5v11.25M12 9.75h.008v.008H12V9.75Z",
    "/finance/dashboard": "M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5M9 11.25v-2.25m3 2.25V8.25m3 3V6.75",
    "/finance/bills": "M6.75 3h10.5A2.25 2.25 0 0 1 19.5 5.25v13.5A2.25 2.25 0 0 1 17.25 21H6.75A2.25 2.25 0 0 1 4.5 18.75V5.25A2.25 2.25 0 0 1 6.75 3ZM8.25 7.5h7.5M8.25 11.25h7.5M8.25 15h4.5",
    "/finance/payment-vouchers": "M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15a2.25 2.25 0 0 1 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25Z",
    "/finance/payment-runs": "M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z",
    "/finance/aging-report": "M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z",
    "/accounting/accounts-payable": "M2.25 18.75a60.07 60.07 0 0 1 15.797 2.101c.727.198 1.453-.342 1.453-1.096V18.75M3.75 4.5v.75A.75.75 0 0 1 3 6h-.75m0 0v-.375c0-.621.504-1.125 1.125-1.125H20.25M2.25 6v9m18-10.5v.75c0 .414.336.75.75.75h.75m-1.5-1.5h.375c.621 0 1.125.504 1.125 1.125v9.75c0 .621-.504 1.125-1.125 1.125h-.375m1.5-1.5H21a.75.75 0 0 0-.75.75v.75m0 0H3.75m0 0h-.375a1.125 1.125 0 0 1-1.125-1.125V15m1.5 1.5v-.75A.75.75 0 0 0 3 15h-.75M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm3 0h.008v.008H18V10.5Zm-12 0h.008v.008H6V10.5Z",
    "/accounting/accounts-receivable": "M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    "/finance/payment-receipts": "M9 12.75 11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
    "/finance/banking": "M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6M3.75 9v.75A2.25 2.25 0 0 0 6 12h12a2.25 2.25 0 0 0 2.25-2.25V9M3.75 21h16.5",
    "/finance/bank-accounts": "M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6M3.75 9v.75A2.25 2.25 0 0 0 6 12h12a2.25 2.25 0 0 0 2.25-2.25V9M3.75 21h16.5",
    "/finance/bank-transactions": "M7.5 21 3 16.5m0 0L7.5 12M3 16.5h13.5m0-13.5L21 7.5m0 0L16.5 12M21 7.5H7.5",
    "/finance/bank-reconciliation": "M9 12.75 11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 0 1-1.043 3.296 3.745 3.745 0 0 1-3.296 1.043A3.745 3.745 0 0 1 12 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 0 1-3.296-1.043 3.745 3.745 0 0 1-1.043-3.296A3.745 3.745 0 0 1 3 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 0 1 1.043-3.296 3.746 3.746 0 0 1 3.296-1.043A3.746 3.746 0 0 1 12 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 0 1 3.296 1.043 3.746 3.746 0 0 1 1.043 3.296A3.745 3.745 0 0 1 21 12Z",
    "/finance/invoices": "M7.5 3.75h6l4.5 4.5v10.5A2.25 2.25 0 0 1 15.75 21H7.5a2.25 2.25 0 0 1-2.25-2.25V6A2.25 2.25 0 0 1 7.5 3.75Zm0 6.75h9M7.5 14.25h6",
    "/finance/customers": "M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.5 19.5a7.5 7.5 0 0 1 15 0",
    "/finance/investors": "M18 18.75a3 3 0 0 0 3-3V15a6 6 0 0 0-6-6h-6a6 6 0 0 0-6 6v.75a3 3 0 0 0 3 3h12ZM15 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
    "/finance/chart-of-accounts": "M4.5 6.75h15M4.5 12h15m-15 5.25h15",
    "/finance/journals": "m16.862 4.487 1.687 1.688a1.875 1.875 0 0 1 0 2.651l-8.086 8.087a4.5 4.5 0 0 1-1.897 1.13l-2.685.894.894-2.685a4.5 4.5 0 0 1 1.13-1.897l8.086-8.087a1.875 1.875 0 0 1 2.651 0ZM19.5 15v3.75A2.25 2.25 0 0 1 17.25 21H6.75A2.25 2.25 0 0 1 4.5 18.75V8.25A2.25 2.25 0 0 1 6.75 6h3.75",
    "/finance/reports/trial-balance": "M12 3v18m8.25-13.5H3.75m16.5 9H3.75M6 7.5V6a2.25 2.25 0 1 1 4.5 0v1.5m3 9V18a2.25 2.25 0 1 0 4.5 0v-1.5",
    "/finance/reports/general-ledger": "M4.5 4.5A2.25 2.25 0 0 1 6.75 2.25h10.5A2.25 2.25 0 0 1 19.5 4.5v15a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5v-15ZM8.25 7.5h7.5M8.25 11.25h7.5M8.25 15h4.5",
    "/finance/budgets": "M2.25 7.5h19.5m-18 0v10.5A2.25 2.25 0 0 0 6 20.25h12A2.25 2.25 0 0 0 20.25 18V7.5m-16.5 0V6A2.25 2.25 0 0 1 6 3.75h12A2.25 2.25 0 0 1 20.25 6v1.5",
    "/finance/variance-analysis": "M3 3v18h18M7.5 15.75h3v3h-3v-3Zm4.5-7.5h3v10.5h-3V8.25Zm4.5 3h3v7.5h-3v-7.5",
    "/finance/spv": "M3.75 21h16.5M5.25 21V4.5h13.5V21M9 8.25h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6h1.5m-1.5 3h1.5m-1.5 3h1.5M10.5 21v-3a1.5 1.5 0 0 1 3 0v3",
    "/finance/payment-plans": "M6.75 3v2.25M17.25 3v2.25M3.75 7.5h16.5M4.5 6h15A1.5 1.5 0 0 1 21 7.5v10.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18V7.5A1.5 1.5 0 0 1 4.5 6Zm4.5 8.25 1.5 1.5 3-3",
    "/inventory": "M3.75 3.75h16.5v16.5H3.75V3.75Zm4.5 4.5h7.5m-7.5 4.5h7.5m-7.5 4.5h4.5",
    "/inventory/items": "M4.5 6.75h15m-15 5.25h15m-15 5.25h9",
    "/inventory/stock": "M3.75 7.5h16.5m-16.5 4.5h16.5m-16.5 4.5h16.5",
    "/inventory/movements": "M3 3v18h18M7.5 15l3-3 2.25 2.25L17.25 9",
    "/inventory/warehouses": "M3.75 6.75h16.5v10.5H3.75V6.75Zm3 3h3m4.5 0h3m-10.5 3h3m4.5 0h3",
  };

  return directMap[href] ?? "M12 6v12m6-6H6";
}
