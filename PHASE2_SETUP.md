# OWL FINANCE Phase 2 — Sandbox demonstration

This is a demonstration build, NOT production lending software.

## Deployment
1. Back up your GitHub repository and Neon database first.
2. Upload the contents of this folder to the existing repository root. Keep DATABASE_URL and SECRET_KEY unchanged.
3. On Render set CASHFREE_APP_ID and CASHFREE_SECRET_KEY to Cashfree SANDBOX credentials, CASHFREE_ENV=sandbox, PUBLIC_BASE_URL=https://owl-finance-1-0.onrender.com. Never commit secrets.
4. Redeploy and check logs.
5. Configure Cashfree sandbox webhook URL: https://owl-finance-1-0.onrender.com/webhooks/cashfree (note the plural webhooks). Subscribe to payment success events.
6. Register test customer, create and approve test loan, customer accepts, admin clicks Simulate Disbursement, customer clicks Pay Now, complete Cashfree sandbox checkout, verify signed webhook and installment payment status.

## Notes
- Simulate Disbursement never invokes a bank or payout API. It creates installment rows in Neon and a demo audit entry.
- This build explicitly rejects Cashfree production mode.
- Never enter real Aadhaar, PAN, bank data or real KYC documents in the demo.
- If a sandbox checkout fails, inspect Render logs and Cashfree sandbox event delivery; this package cannot guarantee Cashfree account configuration, merchant domain approval, or network reachability.
- This build reuses the existing SQLAlchemy tables; no SQL migration is required for the simulated disbursement flow.
- Previously accepted loans can be simulated once; a second attempt is rejected.
- The original project has not been independently security-audited. Do not use for real lending or collections.
