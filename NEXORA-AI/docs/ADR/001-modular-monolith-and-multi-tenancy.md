# ADR-001: Modular Monolith Architecture, Double-Entry Core & Multi-Tenant Isolation

- **Status**: Accepted
- **Date**: 16 Nov 2026

## Context
NEXORA ERP spans 10 operational and intelligence domains (Organization, Auth/RBAC, HR, Inventory, Procurement, Sales, Finance/Accounting, Projects, Workflow Approvals, and AI/ML). Prematurely splitting these tightly coupled transactional domains into distributed microservices introduces distributed transaction hazards (e.g., partial failures between Inventory Goods Receipt and General Ledger Journal Posting).

## Decisions
1. **Modular Monolith Backend**: All operational domains run within a single well-layered FastAPI service (`app/api/v1`, `app/services`, `app/models`) sharing ACID database transactions in PostgreSQL, while asynchronous compute (forecasting, bulk reports, notifications) is offloaded to Celery + Redis workers.
2. **Strict Double-Entry Accounting Core**: All financial KPIs derive from `journal_entries` and `journal_lines` where `SUM(debit) == SUM(credit)` is enforced prior to posting.
3. **Database Dual-Compatibility for Local & Container Execution**:
   - Production & Docker Compose use **PostgreSQL 16** (`postgresql+psycopg://...`) with Row-Level Security policies.
   - When running directly on a host machine without Docker/PostgreSQL daemon running, the SQLAlchemy 2.x layer seamlessly supports local persistent relational file storage (`sqlite:///./nexora_erp.db` with foreign keys enforced `PRAGMA foreign_keys=ON`) so every feature, migration, seed script, and automated test suite can be verified locally and in Docker without any mock data.
