# OWL FINANCE — by OWL STORE

Flask / Neon PostgreSQL / Render starter for manual KYC and individually configured loan offers. **PRE-LAUNCH / SANDBOX ONLY**. This is not a production-ready regulated lending product.

## Local run

1. `python -m venv .venv` and activate it.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`; set `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `DATABASE_URL` (SQLite fallback is for local demos only).
4. `python app.py`
5. Open http://127.0.0.1:5000. The admin is bootstrapped from environment variables on first startup. Register customers separately.

## Deploy

1. Push project files to a **private GitHub repository** (never commit `.env` or KYC uploads).
2. In Neon create a PostgreSQL database and copy the pooled connection string. Set `DATABASE_URL` to `postgresql+psycopg://...` (SSL required).
3. In Render create a Blueprint from `render.yaml`, set all secret environment variables, including `PUBLIC_BASE_URL`.
4. Persistent private storage is required for uploads. The Render disk in this blueprint may require a paid plan and cannot be shared across instances. **Single instance only** with this storage implementation. For production, replace local uploads with encrypted private object storage and malware scanning.
5. Configure Cashfree sandbox credentials and webhook URL `https://YOUR_DOMAIN/webhooks/cashfree` for payment events. Test verified signatures and retries. Do not enable live payments before Cashfree approves the use case.

## Important limitations / required hardening

- Real disbursement is disabled by default and cannot occur until `LIVE_LENDING_ENABLED=true`. **Do not enable until the lending entity's legal permissions, required disclosures, agreements and payment-flow compliance have been independently reviewed.**
- No actual funds disbursement integration is included; admin records an externally completed disbursement only.
- KYC uploads and manual reviews are implemented, but this is **not a certified KYC/AML system**. Only masked Aadhaar is requested. Do not upload full unmasked Aadhaar. Implement consent tracking, document retention/deletion policies, encryption at rest, access monitoring and secure storage before real use.
- PAN, Aadhaar and bank details are **last-four-only** in this starter. Full collection requires a purpose-limited, compliant secure verification flow.
- Loan offer acceptance is a sandbox click, **not a legally binding e-sign or complete KFS/loan agreement workflow**.
- Interest is per-loan: monthly or annual; flat or reducing. Calculator is illustrative, excludes APR, fees, taxes, late fees and statutory disclosures. Decimal rounding is simplified.
- Cashfree webhook signature is verified and success is applied idempotently per order. Before production, implement payment reconciliation against Cashfree's Get Order/Get Payments API, stronger duplicate payment safeguards across multiple orders for the same installment, event logging, refunds, chargebacks and out-of-order handling.
- Add migration tooling (Alembic/Flask-Migrate), email/phone OTP verification, password reset, rate limiting, MFA for admins, permissions separation, CSRF and security tests, stronger server-side file validation/antivirus, object storage, consent logs, support and grievance workflows, operational alerts, backup/restore and monitoring.
- The database schema is created automatically with `db.create_all()` for first-time demos; it does not migrate existing tables.
- Render disk and Neon should be provisioned in compatible regions with secure networking and appropriate data-residency review.

## Proprietor

Soumitra Karmakar — OWL STORE (sole proprietorship), Gopalnagar, Pandua, Hooghly, West Bengal, India 712152.

## Enhanced sandbox release
This archive includes the corrected admin bootstrap, customer directory, payment activity view, portfolio summary and CSV export. It is designed to replace the files in your existing GitHub repository while preserving the Neon schema. `db.create_all()` creates missing tables but is not a migration tool. Back up Neon before deploying.

### Existing Render deployment
Upload the archive contents (not the outer directory) into your repository. Keep the current DATABASE_URL, SECRET_KEY and existing admin login. Existing admin passwords are NOT reset by changes to ADMIN_PASSWORD. Use `CASHFREE_APP_ID` and `CASHFREE_SECRET_KEY` for Cashfree sandbox, not CLIENT_ID/CLIENT_SECRET. Configure persistent KYC storage. The included render.yaml defines a disk which may require a paid Render plan; don't collect real documents without durable private storage.

### Operational security / limitations
**Sandbox-only by design.** `LIVE_LENDING_ENABLED` cannot activate disbursement in this release. Do not collect real Aadhaar/PAN or bank documents, do not lend real money, and do not use live Cashfree. This is a functional testing foundation, NOT a complete production lending service. Before production: legal/licensing review; compliant agreements and KFS/APR; full identity verification, consent and privacy workflows; object storage with malware scanning and encryption; MFA, rate limiting, password resets, email verification; schema migrations; comprehensive automated tests; proper accounting, loan servicing and payment reconciliation.
