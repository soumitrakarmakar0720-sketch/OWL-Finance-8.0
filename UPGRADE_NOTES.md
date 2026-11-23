# OWL FINANCE — source-based repair package

This update was made from the uploaded manual-disbursement ZIP. It has passed Python syntax compilation and Jinja template parsing, but **has not been deployed or tested against your Neon or Cashfree accounts**.

## Changes
- Validate Fernet KYC key before inserting application records; report a friendly configuration error rather than a 500 for invalid keys. Keep the original key for existing encrypted records.
- Add admin-only full KYC review (decrypt on demand and audit access). Sensitive records remain encrypted at rest.
- Add admin staff account creation and admin/staff customer account creation. Staff cannot approve loans, disburse, or view sensitive KYC in this version.
- Add admin-created loan offers, still requiring KYC verification, customer acceptance, and independently completed manual transfer before activation.
- Add admin cancellation of undisbursed loans with audit trail. No hard delete.
- Cashfree sandbox: checkout auto-opens, keeps manual retry button, logs API failures to Render logs, and preserves verified webhook processing.

## Deployment
1. Backup Neon and GitHub, and keep the current KYC_ENCRYPTION_KEY if it was ever used successfully.
2. Upload the files to your existing repository, redeploy Render.
3. Set CASHFREE_ENV=sandbox, CASHFREE_APP_ID and CASHFREE_SECRET_KEY to **sandbox** credentials, and PUBLIC_BASE_URL to the exact https origin of your Render app.
4. Verify the Cashfree merchant account has this checkout domain configured/allowlisted as required by Cashfree, and webhook points to /webhooks/cashfree.
5. Test sandbox order creation and inspect Render logs for `Cashfree sandbox order creation failed` if checkout does not open. Never post API keys in screenshots.
6. Generate a valid Fernet key with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Only set a new key if existing records do not depend on an older one.

## Important
- Cashfree sandbox is not live collections. Real money transfer is NOT performed by this app.
- Uploaded KYC files are stored in the configured UPLOAD_DIR; Render's ephemeral filesystem is not durable. Configure persistent, access-controlled storage before relying on production document retention.
- Public phone-only lookup must not expose real borrowers' financial information without adequate authentication; keep it disabled for real borrower data.
- Review role permissions, secure sessions, backups, privacy compliance, and webhook reconciliation before production use.
- Do not represent `demo_active` historical records as real disbursements. Only `disbursement_record` entries represent admin-recorded external transfers.
