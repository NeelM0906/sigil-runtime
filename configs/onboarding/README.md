# User onboarding — Callagy Recovery

## Pre-created users

All users below are onboarded with the migration script. Default password
for all accounts is the shared team password — users should change it
after first login.

| Name | Email | Data migration |
|------|-------|---------------|
| Mark Winters | mark.winters@callagyrecovery.com | Supabase + Pinecone (recovery) |
| Danny Lopez | dannylopez@callagyrecovery.com | Supabase + Pinecone (recovery) |
| Eric Ranner | eric.ranner@callagyrecovery.com | Fresh account |
| Ramon Inoa | ramon.inoa@callagyrecovery.com | Fresh account |
| Fatima Espinar | fatima.espinar@callagyrecovery.com | Fresh account |
| Kaitlin Varner | kaitlin.varner@callagyrecovery.com | Fresh account |
| Laura Yeaw | laura.yeaw@callagyrecovery.com | Fresh account |

## Run onboarding
```bash
# Dry run first
PYTHONPATH=src python scripts/migrate_user_data.py \
  --config configs/onboarding/recovery-users.json \
  --runtime-home .runtime \
  --dry-run

# Execute
PYTHONPATH=src python scripts/migrate_user_data.py \
  --config configs/onboarding/recovery-users.json \
  --runtime-home .runtime
```

## New users after initial setup

New users self-register through the Mission Control login page.
No manual setup needed — tenant directories are created automatically.
