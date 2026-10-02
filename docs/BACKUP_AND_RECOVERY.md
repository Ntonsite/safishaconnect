# SafishaCon — Backup and Recovery

PostgreSQL holds **all** SafishaCon business state: bookings, price snapshots, assignments, payments, settlements, reviews, the audit log and job state. There is no other store to back up. File uploads don't exist yet; when they arrive, their object-storage bucket needs versioning and its own lifecycle policy.

**Objectives for the pilot:**

| | Target | How |
|---|---|---|
| RPO (data we can lose) | ≤ 5 minutes | Point-in-time recovery from continuous WAL archiving |
| RTO (time to restore service) | ≤ 2 hours | Documented restore and redeploy (below), rehearsed quarterly |

## 1. Automated backups

### Recommended: managed PostgreSQL

Use a managed service: AWS RDS/Aurora, Google Cloud SQL, Azure Database for PostgreSQL, DigitalOcean, Aiven, Neon or Supabase. Enable:

1. **Automated daily snapshots** with **point-in-time recovery** (WAL archiving). Retention: **14 days** for the pilot (most providers allow 7–35).
2. **A weekly logical dump to separate storage**, in a different account, provider or region from the database. This protects against account compromise, accidental deletion of the instance together with its snapshots, and provider-level incidents:

```bash
# Run from a scheduled job (e.g. a cron container or CI schedule) with a read-only role.
pg_dump --format=custom --no-owner --no-acl \
  --file="safishacon-$(date +%Y%m%d).dump" "$DATABASE_URL"
# encrypt + upload, e.g. age/gpg then aws s3 cp / rclone; keep 8 weekly + 12 monthly
```

3. **Encryption:** at rest (the provider's default) and in transit (`sslmode=require` in `DATABASE_URL`).
4. **Deletion protection** on the instance.

### Self-hosted PostgreSQL (e.g. the docker compose `db` service on a VM)

The compose volume `pgdata` is **not** a backup. A volume dies with its disk. Add:

- **Continuous archiving and base backups** with `pgBackRest` or `WAL-G`, pushing to object storage (S3, Backblaze B2, Wasabi):
  - full backup weekly;
  - differential backups daily;
  - WAL archived continuously (`archive_timeout = 60`).
- The same weekly `pg_dump` described above.
- Monitoring that alerts when the most recent backup or archived WAL segment is older than 24 hours or 15 minutes respectively.

## 2. Retention

| Copy | Retention |
|---|---|
| PITR window (snapshots + WAL) | 14 days |
| Weekly logical dumps | 8 weeks |
| Monthly logical dumps (first of the month) | 12 months |
| Yearly (end of financial year) | 7 years, for financial records (confirm against Tanzanian tax/TRA requirements) |

**Personal data:** backups contain customer names, phone numbers and addresses. Restrict access to backup storage, encrypt the dumps, and honour deletion requests on the next retention cycle.

## 3. Restore procedures

### A. Point-in-time recovery (accidental delete, bad data fix, bad migration)

1. **Freeze writes.**
   - Scale `api` and `worker` to 0, or put nginx into maintenance mode.
   - Record the incident time (UTC) and the last known-good moment.
2. **Restore** the instance to a **new** database at the timestamp just before the incident (the provider's console or CLI). With pgBackRest: `pgbackrest --stanza=safisha --type=time --target="2026-10-02 09:14:00+00" restore`.
3. **Verify** the restored copy before switching (see §5 checks).
4. **Switch** `DATABASE_URL` to the restored instance and start `api` (it runs `alembic upgrade head`; this is a no-op if the schema is current), then `worker`.
5. **Reconcile** anything that happened between the restore point and the freeze. Cash confirmations and settlements done offline must be re-entered from the provider and admin records. The audit log in the *old* database (kept read-only) shows what was lost.

### B. Full loss (instance deleted or region down)

1. Create a new PostgreSQL 16 instance.
2. Restore the latest snapshot. If snapshots are unavailable, restore the latest logical dump:

```bash
createdb safishacon
pg_restore --no-owner --no-acl --jobs=4 --dbname="$DATABASE_URL" safishacon-YYYYMMDD.dump
```

3. Enable `pg_stat_statements` and create the application role with least privilege.
4. Deploy `api` (migrations run on start under an advisory lock), then `worker` and `web`.
5. Run the §5 checks, then re-open traffic.

## 4. Migrations and backups

- **Take a snapshot immediately before every production migration.** Migrations are reversible (`alembic downgrade`), but a snapshot is the safety net for data-changing steps. Example: migration `0002` cancels duplicate open assignments before adding a unique index.
- Test each migration against a recent production-sized copy first. Migration `0002` took 6.6 s on a 150k-booking copy.
- Prefer expand/contract migrations (add the column, backfill, switch code, drop later), so the previous app version keeps working during rollbacks.
- Restoring a dump from an older schema works: start the API and Alembic upgrades it. Restoring a *newer* schema into older code doesn't. Deploy the matching code version.

## 5. Recovery testing (quarterly, and after any backup-tooling change)

1. Restore the latest backup into a scratch instance (never production).
2. Run the checks:

```sql
SELECT count(*) FROM bookings;                         -- compare with the production dashboard
SELECT max(created_at) FROM bookings;                  -- within the RPO of the restore target
SELECT count(*) FROM bookings WHERE commission_amount + provider_earning <> total_amount;  -- must be 0
SELECT booking_id FROM provider_assignments
 WHERE status IN ('OFFERED','ACCEPTED') GROUP BY booking_id HAVING count(*) > 1;           -- must be empty
SELECT version_num FROM alembic_version;               -- matches the deployed code
```

3. Start an API container against it (`ENVIRONMENT=production`, private network). Check `/health/ready`, sign in as an admin and open a closed booking and its settlement.
4. Record the time taken (actual RTO) and the data age (actual RPO) in the operations log. Fix whatever made it slow.

## 6. Responsibilities

| Task | Owner | Frequency |
|---|---|---|
| Check backup and alert status | On-call engineer | Weekly |
| Off-platform logical dump | Automated | Weekly |
| Restore rehearsal | Engineering lead | Quarterly |
| Review retention and access to backup storage | Engineering lead + operations | Every 6 months |
