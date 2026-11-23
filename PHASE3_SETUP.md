# OWL FINANCE Phase 3 — sandbox update

## New features
- Public home page and mobile-number lookup with SMS OTP verification, no account login required after OTP.
- Guest access lasts 10 minutes and permits Cashfree sandbox installment payments.
- Customer foreclosure request and admin approval/rejection with preliminary demo amount (remaining scheduled installments, not a legally valid payoff quote). No automatic one-click foreclosure settlement.
- Full PAN, Aadhaar and bank account entry encrypted at rest using Fernet. Last four characters remain in the original application table.

## Render environment variables
- `KYC_ENCRYPTION_KEY`: REQUIRED for full KYC fields. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Store privately; losing this key makes encrypted records unreadable.
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`: REQUIRED for SMS OTP. Twilio SMS delivery to India may require registration, sender compliance and account approval. No fallback OTP is exposed in logs.
- Keep `DATABASE_URL`, `SECRET_KEY`, `CASHFREE_APP_ID`, `CASHFREE_SECRET_KEY`, `CASHFREE_ENV=sandbox`, `PUBLIC_BASE_URL`.

## Database
Flask `db.create_all()` creates the three new tables `sensitive_kyc`, `guest_otp`, `foreclosure`. No destructive SQL migration is needed because original tables are unchanged. Check in Neon SQL Editor:
```sql
SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;
```

## Limitations and safety
- **Sandbox only**. Simulated disbursement and Cashfree test payments; do not use actual customer KYC.
- OTP is required. Phone-only disclosure would be unsafe. Twilio credentials and approved SMS delivery are needed for the guest flow to work.
- Foreclosure is request/review only; approved quotes are not automatically payable as a single Cashfree settlement. The existing EMI payment flow still works.
- Preliminary foreclosure amount uses remaining scheduled installments; it is not a legally correct principal + accrued interest calculation.
- For production: use compliant identity verification, private object storage, rate limits across workers, consent/retention policies, secure admin access, migration tooling, comprehensive testing and regulatory review.
