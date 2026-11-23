# OWL FINANCE repair

1. Set `KYC_ENCRYPTION_KEY` in Render Environment to a Fernet key generated locally with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Do not change an existing key used to encrypt stored KYC data. Keep a secure backup. Redeploy.
2. Upload all files in this package to the existing repository, preserving the `templates/` folder. No destructive database migration is required.
3. Loan cancellation is available for offered/accepted loans in the admin loan view; this retains financial history.
4. Approving foreclosure is not payment. After verifying receipt externally, the admin can enter the full outstanding scheduled amount and bank reference to record settlement and close the loan. The system rejects partial amounts and does not initiate transfers.
5. Do not use the manual full-schedule settlement for negotiated discounts or fee waivers without a proper accounting workflow.
6. Test using non-production customer records before deploying.
