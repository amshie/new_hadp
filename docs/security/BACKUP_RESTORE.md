# Backup and restore

Status: implemented for the database (2026-10-14); the object store is not covered yet (see
**What is not covered**). Synthetic data only, as everything else in this repository: no
real patient data has been backed up, restored, or held by any of this.

## Targets

| Target                           | Value                                      | Held by                                                           |
| -------------------------------- | ------------------------------------------ | ----------------------------------------------------------------- |
| RPO (most data that can be lost) | 24 hours                                   | one backup a night (`scripts/backup.sh` under cron)               |
| RTO (time to be back)            | one business day                           | `scripts/restore.sh` into a new database, then `demo_stack.sh up` |
| Retention                        | 30 days                                    | a lifecycle rule on the bucket (not a script that deletes)        |
| Where                            | EU only (Hetzner Object Storage, Nürnberg) | the endpoint in `backup.env`; nothing leaves the EU               |
| Encryption                       | age, before the dump touches a disk        | the server holds the public half only                             |

These are the pilot's targets from `CLAUDE.md` ("RPO ≤ 24h, RTO ≤ 1 business day"). They
are validated by the restore test below, not estimated.

## How it works

`scripts/backup.sh` runs `pg_dump` (custom format, with grants and row-level-security
policies) and pipes it through `age` to one file, uploads that file to the bucket with
`curl --aws-sigv4`, reads the object back with `HEAD` and compares its size, and prints one
line: the object's name, its size and the start of its checksum. The plain dump exists in a
pipe only; the encrypted file lives in a directory of the run that is removed on exit. No
secret, value or name is printed. A non-zero exit is the whole failure signal, so cron's
mail (or the log it writes) is what to watch.

`scripts/restore.sh <name | latest>` downloads the object, decrypts it with the identity the
operator holds, and restores it with `pg_restore --exit-on-error` into a database that must
be **empty** — it refuses one with tables. It prints the schema revision and the row counts
of a few tables, so the result can be compared with the source. A restore never touches the
live database: it goes into a new one, and the operator switches when the counts are right.

Both read their settings from the environment, or from `$HADP_DEMO_HOME/backup.env`
(`/etc/hadp-demo/backup.env`) where that exists; `scripts/backup.sh` has the list.

## The key

The backup is encrypted to an [age](https://age-encryption.org) recipient. The server holds
the **recipient** (public) only, so a copy of the server, or of the bucket, yields nothing
readable. The **identity** (private) is made once, off the server, and kept in two places:
the founder's password manager and a sealed printed copy. It is put on a machine only for a
restore, and removed after.

```bash
age-keygen -o hadp-backup-identity.txt   # on a laptop, not the server
age-keygen -y hadp-backup-identity.txt   # -> age1…, the recipient for backup.env
```

Losing the identity means losing every backup. Rotating it means a new recipient in
`backup.env` and, until the old objects expire, keeping the old identity as well.

## On the demo server

Once, as root:

```bash
apt-get install -y age
install -m 600 /dev/null /etc/hadp-demo/backup.env
# then write into it: BACKUP_S3_ENDPOINT, BACKUP_S3_REGION, BACKUP_S3_BUCKET,
# BACKUP_S3_ACCESS_KEY_ID, BACKUP_S3_SECRET_ACCESS_KEY, BACKUP_AGE_RECIPIENT
/opt/hadp/scripts/backup.sh          # the first one, by hand: it must print one line
```

And a nightly run, at 03:17 server time, that keeps a log of the one line per night:

```cron
17 3 * * * /opt/hadp/scripts/backup.sh >> /var/log/hadp-backup.log 2>&1
```

The bucket: in Hetzner's console, Object Storage, a bucket in Nürnberg with a lifecycle
rule that expires objects after 30 days, and credentials made for this bucket only.

## The restore test

`.github/workflows/backup-restore.yml` runs the whole path every Monday, on every change to
the two scripts, and on demand: a seeded synthetic database is backed up into the S3 test
double with a key made for the run, restored into an empty database, and the restored
database must report the same schema revision, the same row counts and the same number of
row-level-security policies as the source. A failure there is a broken backup path, found
before it is needed.

On the server, a restore drill once a quarter, by hand: `scripts/restore.sh latest` into
`hadp_drill`, compare the counts with the live database, drop `hadp_drill`. Record the date
and the result in this file.

| Drill      | Result |
| ---------- | ------ |
| (none yet) |        |

## Restoring for real

1. Do not touch the live database. Create an empty one beside it:
   `docker exec -i <postgres> psql -U postgres -c "CREATE DATABASE hadp_restore"`.
2. Put the identity on the server for the duration: `BACKUP_AGE_IDENTITY=/root/identity.txt`.
3. `RESTORE_PG_CONTAINER=<postgres> RESTORE_PG_DATABASE=hadp_restore scripts/restore.sh latest`
   (or a named object, for a point before a known mistake).
4. Compare the counts it prints with what is expected. If right: stop the stack, rename the
   databases (`ALTER DATABASE hadp RENAME TO hadp_broken; ALTER DATABASE hadp_restore RENAME TO hadp`),
   start it (`scripts/demo_stack.sh up --no-build`).
5. Remove the identity from the server. Note the restore in the audit of operations.

## What is not covered

- **The object store.** On the demo server the source documents live in an in-memory test
  double and are gone with every restart already (`infra/docker/README.md`); the database
  keeps what was read from them. A deployment with a real object store needs the bucket
  itself backed up (versioning plus replication to a second EU bucket is the simplest), and
  this file extended before any real document is stored.
- **Point-in-time recovery.** One dump a night is the RPO; WAL archiving would narrow it and
  is not needed for a pilot.
- **Deletion completeness.** A backup holds what was deleted since it was made. The
  retention of 30 days is the longest a deleted record survives; the erasure process
  (`docs/notes/0012`) has to say so to the person who asked.
