## Run locally

1. Run `cp .env.example .env` and fill env vars.

2. Run following commands.

```bash
docker compose up
# Initialize Postgre (only once)
docker exec -i airflow_postgres psql -U airflow -d automation-jp-procurement < sql/setup_db.sql
```

Access httP://localhost:3031.
