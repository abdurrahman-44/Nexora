# NEXORA ERP — Security Architecture & Operational Hardening

## 1. Authentication & Credential Security
- **Password Hashing**: Uses `Argon2id` (via ` argon2-cffi` / `passlib` with cryptographic salt and work-factor tuning) — plaintext passwords are never stored or logged.
- **Token Lifecycle**:
  - Short-lived JWT Access Tokens (`15–30 minutes`) signed with `HS256` / `RS256` secret.
  - Refresh Tokens are cryptographically random 256-bit tokens stored hashed (`SHA-256`) in the `refresh_tokens` table with `family_id` tracking and delivered via `HttpOnly; SameSite=Lax` cookies.
  - Reuse of a revoked refresh token triggers immediate revocation of the entire token family.
- **Brute-Force & Account Lockout Protection**:
  - Every login attempt is recorded in `login_attempts`.
  - Five consecutive failed attempts lock the user account for 15 minutes (`locked_until`).
- **Multi-Factor Authentication (MFA)**:
  - RFC 6238 TOTP (`pyotp`) setup and verification flow supported per user account.

## 2. Multi-Tenant & RBAC Enforcement
- **Server-Side Enforcement**: Every protected API route uses FastAPI security dependencies (`require_permissions([...])`) that validate both:
  1. Active membership in the requested `organization_id`.
  2. Effective permission grants across the user's assigned `roles`.
- **Separation of Duties**:
  - Creators of purchase requests, purchase orders, leave requests, and expenses cannot approve their own submissions (`HTTP 403 SELF_APPROVAL_FORBIDDEN`).
- **Confidential Data Masking**:
  - Employee salary and national ID fields are automatically redacted unless the requester holds `hr.confidential.view` or is an HR Manager / Admin.

## 3. Financial & Inventory Transaction Integrity
- **ACID Transactions**: All stock movements, goods receipts, invoice postings, and journal postings execute inside atomic database transactions.
- **Double-Entry Invariant**: `SUM(debit) == SUM(credit)` verified to `0.01` precision before any journal entry can be marked `POSTED`.
- **Negative Stock Prevention**: Stock issues, sales allocations, and outbound transfers lock/validate `quantity_available >= requested_qty` before deduction.
- **Idempotency**: Sensitive financial endpoints (`/api/v1/payments`, `/api/v1/finance/journal-entries`) honor `Idempotency-Key` to prevent duplicate payment or journal posting on network retries.

## 4. Backup & Disaster Recovery Procedure
1. **Automated PostgreSQL Backups**:
   ```bash
   docker compose exec postgres pg_dump -U nexora -Fc nexora_erp > backups/nexora_erp_$(date +%Y%m%d_%H%M%S).dump
   ```
2. **Point-in-Time Recovery / Restore**:
   ```bash
   docker compose exec -T postgres pg_restore -U nexora -d nexora_erp --clean < backups/nexora_erp_backup.dump
   ```
