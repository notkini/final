# Weldomat Machine Monitoring System

A lightweight industrial machine runtime monitoring system designed for Raspberry Pi deployment.

The system monitors machine operating states, records uptime and downtime events, calculates shift-wise efficiency, and provides a browser-based monitoring dashboard.

The project is designed for industrial runtime monitoring where a Raspberry Pi acquires machine state signals and stores operational data in PostgreSQL.

---

## System Architecture

```text
Machine / PLC Signal
        |
        v
Raspberry Pi GPIO
        |
        v
Python Monitoring Service
        |
        +--------------------+
        |                    |
        v                    v
 Local SQLite Queue      PostgreSQL
  Offline Buffer          Database
                              |
                              v
                        FastAPI Backend
                              |
                              v
                       Web Dashboard
```

The local SQLite queue temporarily stores machine events when PostgreSQL is unavailable.

Once the database connection is restored, queued events are automatically synchronized.

---

## Features

### Machine Monitoring

- Machine UP and DOWN state detection
- GPIO-based signal acquisition
- Simulation mode for development and testing
- Configurable GPIO pin
- Signal debounce handling
- Automatic machine event logging
- Machine heartbeat monitoring

### Multi-Machine Support

- Register multiple machines
- Unique machine codes
- Select an existing machine for monitoring
- Create and configure new machines
- Track monitor assignment history
- Maintain independent configuration for every machine

### Shift Monitoring

Each machine can have independently configured production shifts.

Example:

```text
Shift A    06:00 - 14:00
Shift B    14:00 - 20:00
Shift C    20:00 - 06:00
```

Overnight shifts are supported.

The monitoring service calculates:

- Shift uptime
- Shift downtime
- Shift efficiency
- Shift completion status

Efficiency is calculated as:

```text
Efficiency (%) = Uptime / (Uptime + Downtime) × 100
```

### Production Break Configuration

Optional production breaks can be configured for each machine:

- Breakfast
- Lunch
- Dinner

Only the break start time is configured.

Each break is assumed to have a fixed duration of one hour.

Example:

```text
Lunch Start: 13:00

Break Window:
13:00 - 14:00
```

During an active break, the dashboard can display the current break status.

### Offline Event Queue

Machine events are stored locally when PostgreSQL is unavailable.

```text
Machine Event
      |
      v
PostgreSQL Available?
      |
   +--+--+
   |     |
  YES    NO
   |     |
   v     v
Postgres SQLite Queue
           |
           v
    Automatic Sync
```

This prevents machine state events from being lost during temporary network or database failures.

---

## Web Interface

The application includes a FastAPI-based web interface.

### Dashboard

Displays current machine monitoring information including:

- Current machine
- Connection state
- Machine state
- Current shift
- Current shift uptime
- Current shift downtime
- Shift efficiency
- Shift performance table
- Machine event timeline
- Active production break

### 7-Day History

Displays machine performance for the previous seven days.

Includes:

- Weighted efficiency
- Total uptime
- Total downtime
- Runtime distribution
- Efficiency trend
- Daily performance
- Shift-level historical records

### Custom History

Allows historical data to be queried using:

- Machine
- From date
- To date
- Shift A
- Shift B
- Shift C

The page displays:

- Weighted efficiency
- Total uptime
- Total downtime
- Runtime distribution
- Shift runtime comparison
- Efficiency trend
- Historical shift records

### Machine Configuration

The configuration page allows the operator to:

- Select an existing machine
- Register a new machine
- Configure Shift A
- Configure Shift B
- Configure Shift C
- Configure breakfast timing
- Configure lunch timing
- Configure dinner timing
- Assign the monitor to a machine

Configuration is stored in PostgreSQL.

---

## Technology Stack

### Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic
- Uvicorn

### Database

- PostgreSQL
- SQLite offline queue

### Frontend

- HTML
- CSS
- JavaScript
- Chart.js

### Infrastructure

- Docker
- Docker Compose
- Raspberry Pi
- systemd

---

## Project Structure

```text
grafana-main/
│
├── app/
│   ├── api.py
│   ├── calculations.py
│   ├── config.py
│   ├── database.py
│   ├── db_health.py
│   ├── gpio_reader.py
│   ├── init_db.py
│   ├── logging_config.py
│   ├── models.py
│   ├── monitor.py
│   ├── offline_queue.py
│   └── shifts.py
│
├── alembic/
│   ├── versions/
│   │   ├── 0001_baseline.py
│   │   └── migrations...
│   │
│   └── env.py
│
├── web/
│   ├── templates/
│   │   ├── dashboard.html
│   │   ├── history.html
│   │   ├── custom_history.html
│   │   └── setup.html
│   │
│   └── static/
│       ├── css/
│       │   ├── dashboard.css
│       │   ├── history.css
│       │   ├── custom_history.css
│       │   └── setup.css
│       │
│       ├── js/
│       │   ├── dashboard.js
│       │   ├── history.js
│       │   ├── custom_history.js
│       │   └── setup.js
│       │
│       └── vendor/
│           └── chart.umd.min.js
│
├── scripts/
│   └── backup.sh
│
├── data/
│   └── offline_queue.db
│
├── logs/
│   └── monitor.log
│
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
├── pytest.ini
├── .env
├── .env.example
└── README.md
```

---

## Database Tables

### `machines`

Stores registered machines.

```text
id
machine_name
machine_code
is_active
created_at
```

### `machine_events`

Stores machine state changes.

```text
id
machine_id
state
event_time
source
event_key
created_at
```

Valid states:

```text
UP
DOWN
```

### `shift_config`

Stores machine-specific shift timings.

```text
id
machine_id
shift_name
start_time
end_time
updated_at
```

### `shift_performance`

Stores calculated shift performance.

```text
id
machine_id
shift_date
shift_name
up_seconds
down_seconds
efficiency_pct
is_final
last_updated
```

### `monitor_assignments`

Tracks which machine is assigned to the monitoring device.

```text
id
machine_id
assigned_at
unassigned_at
```

### `monitor_heartbeat`

Stores monitoring service heartbeat information.

```text
id
machine_id
last_beat
current_state
```

### `break_config`

Stores production break start times.

```text
id
machine_id
break_name
start_time
updated_at
```

Supported break names:

```text
BREAKFAST
LUNCH
DINNER
```

---

## Environment Configuration

Create a `.env` file in the project root.

Example:

```env
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=weldomat_monitor
POSTGRES_USER=weldomat
POSTGRES_PASSWORD=changeme

OFFLINE_QUEUE_PATH=data/offline_queue.db
OFFLINE_SYNC_INTERVAL_SECONDS=45

GPIO_PIN=17
DEBOUNCE_SECONDS=0.08
ACTIVE_HIGH=true

SIMULATION_MODE=true

RECALC_INTERVAL_SECONDS=45
HEARTBEAT_INTERVAL_SECONDS=15

LOG_DIR=logs
LOG_FILE=monitor.log
LOG_LEVEL=INFO
LOG_MAX_BYTES=5242880
```

Change database passwords before production deployment.

---

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd grafana-main
```

### 2. Create a Virtual Environment

Windows:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux or Raspberry Pi:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file.

Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Update the PostgreSQL password and required configuration values.

---

## Start PostgreSQL

Ensure Docker is running.

Start the containers:

```bash
docker compose up -d
```

Check container status:

```bash
docker compose ps
```

PostgreSQL should report a healthy status.

---

## Database Migration

Apply all Alembic migrations:

```bash
python -m alembic upgrade head
```

Verify the migration version:

```bash
python -m alembic current
```

---

## Start the Web Application

Run the FastAPI server:

```bash
python -m uvicorn app.api:app --host 0.0.0.0 --port 8000
```

Open the dashboard:

```text
http://127.0.0.1:8000
```

For Raspberry Pi network access:

```text
http://<raspberry-pi-ip>:8000
```

Available pages:

```text
/                  Dashboard
/history           7-Day History
/custom-history    Custom History
/setup             Machine Configuration
```

---

## Run the Monitoring Service

Activate the virtual environment and run:

```bash
python -m app.monitor
```

The monitoring service will:

1. Determine the assigned machine.
2. Read the GPIO or simulated machine signal.
3. Detect machine state changes.
4. Store events in PostgreSQL.
5. Queue events locally if PostgreSQL is unavailable.
6. Calculate shift performance.
7. Update the monitor heartbeat.
8. Synchronize offline events.

---

## Simulation Mode

Simulation mode can be enabled in `.env`.

```env
SIMULATION_MODE=true
```

Run:

```bash
python -m app.monitor
```

The application will generate simulated machine state changes.

For Raspberry Pi GPIO monitoring:

```env
SIMULATION_MODE=false
```

Ensure the configured GPIO pin is connected through appropriate signal isolation hardware.

---

## PostgreSQL Access

Open PostgreSQL inside Docker:

```bash
docker exec -it weldomat_postgres psql -U weldomat -d weldomat_monitor
```

List tables:

```sql
\dt
```

View machines:

```sql
SELECT *
FROM machines
ORDER BY id;
```

View machine events:

```sql
SELECT *
FROM machine_events
ORDER BY event_time DESC;
```

View shift performance:

```sql
SELECT *
FROM shift_performance
ORDER BY shift_date DESC, shift_name;
```

View monitor assignments:

```sql
SELECT *
FROM monitor_assignments
ORDER BY assigned_at DESC;
```

Exit PostgreSQL:

```sql
\q
```

---

## Raspberry Pi Deployment

The application is intended to run on a Raspberry Pi 4 Model B.

Recommended deployment:

```text
Raspberry Pi
│
├── Python Monitoring Service
├── FastAPI Web Application
├── SQLite Offline Queue
└── Docker PostgreSQL
```

The monitoring service and FastAPI server can be configured as `systemd` services to automatically start when the Raspberry Pi boots.

---

## Logging

Application logs are stored in:

```text
logs/monitor.log
```

The logging system supports rotating log files to prevent unlimited log growth.

The maximum log size is configured using:

```env
LOG_MAX_BYTES=5242880
```

---

## Data Reliability

The system uses several mechanisms to protect monitoring data:

- Unique event keys prevent duplicate machine events.
- SQLite provides offline event buffering.
- PostgreSQL stores persistent machine history.
- Alembic manages database schema changes.
- Monitor heartbeat records service availability.
- Monitor assignments preserve machine assignment history.

---

## Future Improvements

Possible future enhancements include:

- Operator authentication
- Role-based access control
- PLC communication through Modbus TCP
- Siemens S7 communication
- OEE calculation
- Planned downtime classification
- Downtime reason entry
- Production count monitoring
- Alarm history
- CSV and Excel report export
- Central monitoring of multiple Raspberry Pi devices
- Predictive maintenance analytics

---

## Purpose

This project provides a lightweight industrial machine runtime acquisition and monitoring solution.

It is designed to demonstrate:

- Industrial signal acquisition
- Machine state monitoring
- Time-series event storage
- Offline data buffering
- Shift-based production analytics
- Raspberry Pi edge computing
- PostgreSQL database integration
- Web-based industrial monitoring

---

## License

This project is intended for academic and internal development use.
