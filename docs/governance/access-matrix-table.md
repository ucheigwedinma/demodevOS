# Access Matrix Table (Phase 4)

This matrix defines the default `documents.all` permissions and scope posture seeded for system roles.

| Role | View | Comment | Upload Version | Approve | Archive | Admin Override | Project Scope | Business Unit Scope | Confidentiality Scope |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Developer Executive | Yes | Yes | Yes | Yes | Yes | Yes | All projects | All business units | Public, Internal, Confidential, Restricted |
| Project Director | Yes | Yes | Yes | Yes | Yes | No | Assigned projects | Assigned business units | Public, Internal, Confidential |
| Sales Manager | Yes | Yes | Yes | No | No | No | Assigned projects | Assigned business units | Public, Internal |
| Finance Controller | Yes | Yes | No | Yes | No | No | Assigned projects | Assigned business units | Public, Internal, Confidential |
| Procurement Officer | Yes | Yes | Yes | No | No | No | Assigned projects | Assigned business units | Public, Internal |
| Governance Officer | Yes | Yes | Yes | Yes | Yes | Yes | All projects | All business units | Public, Internal, Confidential, Restricted |
| Legal | Yes | Yes | Yes | Yes | Yes | Yes | All projects | All business units | Public, Internal, Confidential, Restricted |
| External Consultant | Yes | No | No | No | No | No | Assigned projects | Assigned business units | Public |
| Auditor | Yes | No | No | No | No | No | All projects | All business units | Public, Internal, Confidential |
| Board Viewer | Yes | No | No | No | No | No | All projects | All business units | Public, Internal |

## Seed Commands

```bash
python3 manage.py seed_rbac --reset-permissions
python3 manage.py seed_documents_phase4_access_scopes --reset
```
