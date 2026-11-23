# OWL FINANCE 6.1 — configuration and verification

1. Back up Neon before deploying. Existing tables are not dropped or migrated by this patch.
2. In Render set `SECRET_KEY` to a persistent random secret, `DATABASE_URL`, `PUBLIC_BASE_URL` to the exact HTTPS site URL, and `KYC_ENCRYPTION_KEY` to a valid Fernet key. Keep an existing KYC key unchanged if records already exist; rotating it without re-encryption makes existing records unreadable.
3. Set `CASHFREE_ENV=production`, `CASHFREE_CLIENT_ID` (live client ID) and `CASHFREE_SECRET_KEY` (live secret). Ensure Cashfree has approved the merchant account and loan-repayment business use case. Never put credentials in Git.
4. In Cashfree production dashboard, configure signed webhooks at `https://YOUR-DOMAIN/webhooks/cashfree`. Configure payment success events. Production and sandbox secrets are different.
5. Test `/apply` with valid KYC key and all five required PDF/image uploads. Check that uploads persist across Render restarts; use persistent storage/object storage before live operation.
6. Admin → Loans offers filters and archive action for undisbursed offers. It deliberately does not permanently delete financial history.
7. Verify Cashfree live payment using a small authorized payment and confirm webhook signature, order amount, currency, and installment accounting; do not mark payments successful from redirect alone.
8. Important: `demo_active` legacy loans are NOT converted to real disbursements automatically. Verify disbursement and repayment history before treating them as production loans.
9. Security: public phone-only loan lookup should remain disabled for live borrower records unless borrower verification is added.

This release is source-level patched and syntax-checked, not end-to-end validated against live Cashfree or Neon.
