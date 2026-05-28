# Project Governance Settings

Real estate–specific configuration for project templates, stage-gate rules, and risk frameworks.

---

## Overview

Project Governance Settings provide structured templates and controls for managing real estate development projects from feasibility through handover. This includes pre-defined project templates, stage-gate approval checkpoints, and risk assessment frameworks.

---

## 1. Project Templates

### 1.1 Available Template Types

Four pre-defined templates for different real estate project types:

#### Residential Template
- **Phases**: Feasibility & Site Acquisition → Design & Planning → Pre-Sales & Marketing → Construction → Handover & Closeout
- **Duration**: ~24 months total
- **Key Features**:
  - Pre-sales tracking milestones (30%, 50%)
  - Building permit workflow
  - Unit delivery checklist

#### Mixed-Use Template
- **Phases**: Feasibility & Acquisition → Design & Permitting → Pre-Sales & Leasing → Construction → Handover & Stabilization
- **Duration**: ~27 months total
- **Key Features**:
  - Combined residential and commercial workflows
  - Tenant leasing and unit sales tracking
  - Separate stabilization phase

#### Commercial Template
- **Phases**: Feasibility & Acquisition → Design & Permitting → Tenant Leasing → Construction → Commissioning & Handover
- **Duration**: ~28 months total
- **Key Features**:
  - Tenant leasing focus
  - Commissioning phase for MEP systems
  - Certificate of Occupancy requirements

#### Infrastructure Template
- **Phases**: Feasibility & Planning → Design & Approvals → Site Development → Completion & Handover
- **Duration**: ~19 months total
- **Key Features**:
  - Land development focus
  - Utilities and site improvements
  - Minimal building construction

### 1.2 Template Components

Each template pre-defines:
- **Milestones**: Key checkpoints within phases
- **Phases**: Sequential project stages with duration and weight
- **Required Documentation**: Permits, contracts, plans, reports, certificates
- **Compliance Checkpoints**: Regulatory requirements and references

---

## 2. Stage-Gate Rules

### 2.1 Available Stage Gates

Five approval gates that projects must pass through:

#### Feasibility Approval Gate
**When**: Before proceeding from feasibility to design

**Requirements**:
- ✓ Market study completed and approved
- ✓ Site due diligence completed (environmental, title, zoning)
- ✓ Financial feasibility analysis shows positive returns
- ✓ Board/Investment Committee approval obtained
- ✓ Purchase agreement signed or land secured

#### Design Freeze Gate
**When**: Before freezing design and starting procurement

**Requirements**:
- ✓ Detailed design approved by all stakeholders
- ✓ Building permit submitted or approved
- ✓ Construction budget finalized
- ✓ Value engineering completed
- ✓ Design complies with all building codes and regulations

#### Pre-Sales Approval Gate
**When**: Before construction start (Residential projects only)

**Requirements**:
- ✓ Minimum 30% pre-sales achieved
- ✓ Sales contracts legally binding
- ✓ Construction financing committed
- ✓ Escrow accounts established

#### Construction Start Gate
**When**: Before commencing construction

**Requirements**:
- ✓ Building permit obtained
- ✓ General contractor agreement signed
- ✓ Insurance certificates in place (builder's risk, liability)
- ✓ Construction financing drawn down
- ✓ Site mobilization plan approved
- ✓ Safety plan submitted and approved

#### Handover Approval Gate
**When**: Before project handover and closeout

**Requirements**:
- ✓ Certificate of Occupancy obtained
- ✓ All final inspections passed
- ✓ Punch list items completed
- ✓ As-built drawings delivered
- ✓ Warranty documents provided
- ✓ Final lien releases obtained from all contractors

### 2.2 Stage-Gate Enforcement

Control whether stage-gate rules are enforced via:
- `stage_gate_enforcement_enabled` — Enable/disable gate enforcement
- `require_template_selection` — Require template selection for new projects
- `risk_assessment_mandatory` — Require risk assessment for projects

---

## 3. Risk Framework

### 3.1 Risk Categories

Ten pre-defined risk categories organized by type:

#### Financial Risks
- **Cost Overrun Risk**: Budget overruns, material cost escalation
- **Financing Risk**: Loan covenant breaches, funding gaps

#### Regulatory Risks
- **Regulatory Approval Risk**: Permit delays, zoning changes

#### Construction Risks
- **Construction Delay Risk**: Schedule overruns, contractor delays
- **Quality Defect Risk**: Construction defects, material failures

#### Market Risks
- **Market Risk**: Demand fluctuations, pricing pressures

#### Operational Risks
- **Safety Incident Risk**: Worker injuries, OSHA violations

#### Environmental Risks
- **Environmental Compliance Risk**: Environmental violations, contamination

#### Legal Risks
- **Legal & Title Risk**: Ownership disputes, easement issues

#### Technical Risks
- **Design Change Risk**: Late design changes, rework

### 3.2 Risk Scoring Matrix

Configurable matrix for calculating risk scores:

**Likelihood Levels**:
- Very Low (1)
- Low (2)
- Medium (3)
- High (4)
- Very High (5)

**Impact Levels**:
- Very Low (1)
- Low (2)
- Medium (3)
- High (4)
- Very High (5)

**Risk Score Thresholds**:
- Low: ≤ 5
- Medium: 6–10
- High: 11–15
- Critical: > 15

### 3.3 Mitigation Assignment Rules

Auto-assignment rules for risk mitigation based on severity:

- **Assign to Role**: Route high-severity risks to specific roles
- **Escalation Required**: Flag critical risks for immediate escalation
- **Response Time**: SLA for risk response (in hours)

---

## 4. API Endpoints

### Project Governance Settings
```
GET    /api/settings/project-governance/
PATCH  /api/settings/project-governance/
```

### Project Templates
```
GET    /api/settings/project-templates/
POST   /api/settings/project-templates/
GET    /api/settings/project-templates/{id}/
PATCH  /api/settings/project-templates/{id}/
DELETE /api/settings/project-templates/{id}/
```

### Stage-Gate Rules
```
GET    /api/settings/stage-gate-rules/
POST   /api/settings/stage-gate-rules/
GET    /api/settings/stage-gate-rules/{id}/
PATCH  /api/settings/stage-gate-rules/{id}/
DELETE /api/settings/stage-gate-rules/{id}/
```

### Risk Categories
```
GET    /api/settings/risk-categories/
POST   /api/settings/risk-categories/
GET    /api/settings/risk-categories/{id}/
PATCH  /api/settings/risk-categories/{id}/
DELETE /api/settings/risk-categories/{id}/
```

### Risk Score Matrix
```
GET    /api/settings/risk-score-matrix/
PATCH  /api/settings/risk-score-matrix/
```

### Risk Mitigation Rules
```
GET    /api/settings/risk-mitigation-rules/
POST   /api/settings/risk-mitigation-rules/
GET    /api/settings/risk-mitigation-rules/{id}/
PATCH  /api/settings/risk-mitigation-rules/{id}/
DELETE /api/settings/risk-mitigation-rules/{id}/
```

---

## 5. Database Models

### Core Models

- **ProjectGovernanceSettings** — Singleton settings per organization
- **ProjectTemplate** — Template definitions (residential, mixed-use, commercial, infrastructure)
- **TemplatePhase** — Phases within a template
- **TemplateMilestone** — Milestones within a phase
- **TemplateRequiredDocument** — Required documents per phase
- **TemplateComplianceCheckpoint** — Compliance checkpoints per phase
- **StageGateRule** — Stage-gate approval rules
- **StageGateChecklistItem** — Checklist items per gate
- **RiskCategory** — Risk category definitions
- **RiskScoreMatrix** — Likelihood × Impact scoring matrix
- **RiskMitigationRule** — Auto-assignment rules for risk mitigation

---

## 6. Usage Example

### Creating a New Residential Project

When creating a new project using the Residential template:

1. **Template Applied**:
   - 5 phases auto-created
   - 15+ milestones pre-defined
   - Required documents list populated
   - Compliance checkpoints assigned

2. **Stage Gates Enforced**:
   - Feasibility gate blocks design phase until checklist complete
   - Pre-sales gate requires 30% sales before construction
   - Construction start gate requires permits and financing

3. **Risk Assessment**:
   - 10 risk categories available for assessment
   - Risk scores calculated via matrix (Likelihood × Impact)
   - Mitigation auto-assigned to appropriate roles

---

## 7. Benefits

✓ **Standardization**: Consistent project structure across all developments
✓ **Compliance**: Built-in regulatory checkpoints and documentation requirements
✓ **Risk Management**: Structured risk identification and mitigation
✓ **Governance**: Stage-gate controls prevent premature phase transitions
✓ **Efficiency**: Pre-defined templates reduce project setup time
✓ **Auditability**: Clear documentation trail for compliance and reporting

---

## 8. Customization

Organizations can:
- Create custom templates for unique project types
- Modify existing templates (non-system templates only)
- Add/remove stage-gate rules
- Define custom risk categories
- Adjust risk scoring thresholds
- Set up role-based mitigation routing

---

## 9. Related Documentation

- [Project Models](../project-models.md) — Project, Phase, Milestone schemas
- [Role-Based Permissions](role-permission-schema.md) — Access control for governance settings
- [Workflow Engine](../workflow/workflow-configuration-engine.md) — Approval workflows for stage gates
