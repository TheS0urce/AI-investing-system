# Alpaca Paper Verification - 2026-05-22

## Result

- Status: `ALPACA-PAPER-ACCOUNT-OK`
- Broker provider: `alpaca`
- Broker mode: `paper`
- Live routing enabled: `false`
- Account status: `ACTIVE`
- Currency: `USD`
- Buying power: `200000`
- Cash: `100000`
- Portfolio value: `100000`
- Pattern day trader: `false`
- Account number: masked only, ending in `MARJ`

## Commands Used

```bash
.venv/bin/python scripts/alpaca_env_sanity.py
.venv/bin/python scripts/check_alpaca_paper_account.py
```

## Security Notes

- No API key or secret is stored in this file.
- Paper credentials are stored locally in `.env`, which is git-ignored.
- Live broker routing remains disabled.
- The account check is read-only and does not submit orders.

## Stage Decision

- GO: read-only Alpaca paper account verification.
- NO-GO: paper order submission until a paper-only adapter and tests are implemented.
- NO-GO: live order routing.
