# OWL FINANCE Phase 4 — no-OTP sandbox demo

## Changes
- Public homepage: find demo loans using only a 10-digit test mobile number. No OTP/Twilio configuration.
- Public installment page and Cashfree sandbox checkout; verified webhook continues to update the test installment.
- Public lookup deliberately does NOT expose KYC, PAN, Aadhaar, bank details, borrower identity, full loan contract, or foreclosure actions.
- Customer login still supports foreclosure requests; admin can review them.
- Existing tables and admin/customer workflows preserved. No schema migration required.

## Deploy
1. Back up GitHub and Neon. Upload the ZIP contents to your existing repository root and deploy.
2. Keep DATABASE_URL, SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD, KYC_ENCRYPTION_KEY and PUBLIC_BASE_URL.
3. Set CASHFREE_APP_ID, CASHFREE_SECRET_KEY to **sandbox** credentials; CASHFREE_ENV=sandbox.
4. Cashfree webhook: https://owl-finance-1-0.onrender.com/webhooks/cashfree (POST). Verify endpoint and webhook delivery.
5. Do not use real KYC or actual customer data in this demo. Public number-only lookup is not safe for real lending.
6. Cashfree checkout is dependent on valid sandbox credentials and merchant permissions. Webhook status updates must be tested end-to-end.
7. Existing Render KYC upload disk must remain private and persistent.

## Demo checklist
- Register fictional customer with fictional mobile number.
- Submit fictional KYC and loan application; admin verifies and offers loan.
- Accept offer, simulate disbursement; verify installments.
- Log out; homepage → Find demo loan → enter test mobile → open installment → Pay with Cashfree.
- Complete a supported Cashfree sandbox payment; verify webhook and paid amount in Neon.
- Log in as customer to request foreclosure; approve/reject as admin.

## Limitations
This is not production-ready: mobile-number-only lookup can be enumerated despite basic throttling; use real authentication/OTP before live data. Cashfree transactions remain test-only. Foreclosure approval is a demo quote, not automatic final settlement. Database initialization uses create_all, not migrations.
