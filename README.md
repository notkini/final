# Weldomat Monitor with Grafana

Architecture: Python monitor -> PostgreSQL -> Grafana.

## Removed
There is no frontend, API, Node-RED, or Excel report generator in this project.

## Setup
1. Copy `.env.example` to `.env` and set passwords.
2. Start PostgreSQL and Grafana:
```bash
docker compose up -d
```
3. Create database tables:
```bash
source .venv/bin/activate
alembic upgrade head
```
4. Run simulation:
```bash
python -m app.monitor
```

## Grafana
Open `http://192.168.50.2:3000`.
Login with the Grafana credentials from `.env`.

Add a PostgreSQL data source:
- Host: `postgres:5432`
- Database: `weldomat_monitor`
- User/password: values from `.env`
- TLS/SSL: disable

Use `grafana/sql/grafana_queries.sql` for panels.
