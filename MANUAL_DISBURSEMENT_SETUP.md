# OWL FINANCE — manual disbursement update

## What changed
- Admin can record a completed external UPI or bank transfer, with date and unique UTR/reference.
- The application does **not** send funds, verify the bank transfer, or provide a bank payout API. The admin is responsible for independent bank reconciliation.
- After recording, the loan becomes `active` and monthly installments are generated from the recorded transfer date.
- Cashfree remains **sandbox-only**; checkout explicitly discloses test mode.
- The site has a more professional presentation without general-purpose demo banners.
- Public phone-number-only loan lookup is **disabled by default** to protect actual borrowers. It can be used only in a closed test environment with fictional customers by setting `PUBLIC_PHONE_LOOKUP_ENABLED=true`. Do not enable on a public real-borrower site without verification.

## Deployment
1. Back up Neon and GitHub.
2. Upload files to your existing repository and redeploy Render.
3. The new `disbursement_record` table is created by `db.create_all()` on startup. Check Neon SQL Editor with `SELECT * FROM disbursement_record LIMIT 5;`.
4. Keep `CASHFREE_ENV=sandbox`, and configure `CASHFREE_APP_ID`, `CASHFREE_SECRET_KEY`, `PUBLIC_BASE_URL`.
5. Set `PUBLIC_PHONE_LOOKUP_ENABLED=false` for public deployments.
6. On an accepted loan, admin enters method, UTR/reference, date and confirms that a transfer was made externally.

## Important limits
- A manually entered UTR is **not proof** that funds arrived; reconcile against your bank statement.
- Existing `demo_active` loans remain accessible for compatibility. No old rows are deleted.
- The foreclosure estimate is **not** a final payoff or closure.
- Cashfree test payments do not constitute real collections.
- This update does not implement legally sufficient borrower agreements, KFS/APR, a secure public borrower verification system, or production-ready Aadhaar compliance.
- A lending permit should be checked for scope, limits, expiry and operating area before accepting live borrowers.
