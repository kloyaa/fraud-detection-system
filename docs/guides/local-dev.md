# Local Development Guide

Everything you need to run the full RAS stack locally.

**Prerequisites:** Docker Desktop, `make`, Python 3.12+, Node.js 20+, pnpm 9+.

---

## Quick Start

```bash
cp .env.example .env
make dev
```

Services start at:

| Service | URL | Credentials |
|---|---|---|
| Backend API | http://localhost:8000 | — |
| Swagger UI | http://localhost:8000/docs | — |
| Frontend | http://localhost:3000 | analyst@ras.dev / analyst123 |
| Keycloak Admin | http://localhost:8080 | admin / admin |
| Vault UI | http://localhost:8200/ui | token: `dev-root-token` |
| Kafka | localhost:9094 | — |
| Cassandra | localhost:9042 | — |
| PostgreSQL | localhost:5432 | postgres / postgres |
| Redis | localhost:6379 | — |

```bash
make docker-logs      # follow app logs
make docker-down      # stop everything
```

---

## Kafka

**Local broker:** confluentinc/cp-kafka 7.6.1, KRaft mode (no Zookeeper), single node. Confluent CP image aligns with Confluent Cloud (staging/prod).

### Connect from the host (tests, scripts)

Use port **9094** — the external listener:

```
KAFKA_BOOTSTRAP_SERVERS=localhost:9094
```

Use port **9092** only from within the Docker network (container-to-container).

### Create a topic

```bash
docker exec ras_kafka_dev \
  kafka-topics \
  --bootstrap-server localhost:9092 \
  --create \
  --topic ras.scoring.decisions \
  --partitions 4 \
  --replication-factor 1
```

### List topics

```bash
docker exec ras_kafka_dev \
  kafka-topics --bootstrap-server localhost:9092 --list
```

### Produce a test message

```bash
docker exec -it ras_kafka_dev \
  kafka-console-producer \
  --bootstrap-server localhost:9092 \
  --topic ras.scoring.decisions
```

### Consume messages

```bash
docker exec -it ras_kafka_dev \
  kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic ras.scoring.decisions \
  --from-beginning
```

### In Python (aiokafka)

```python
from aiokafka import AIOKafkaProducer
import json

async def publish_decision(decision: dict) -> None:
    producer = AIOKafkaProducer(bootstrap_servers="localhost:9094")
    await producer.start()
    try:
        await producer.send_and_wait(
            "ras.scoring.decisions",
            json.dumps(decision).encode(),
        )
    finally:
        await producer.stop()
```

See `docs/architecture/kafka_topics.md` for the full topic catalog.

---

## Cassandra

**Local cluster:** cassandra:5, single node, cluster name `ras_local`.

First startup takes ~60 seconds for Cassandra to initialize. The healthcheck polls `nodetool status` until the node is `UN` (Up/Normal).

### Connect with cqlsh

```bash
docker exec -it ras_cassandra_dev cqlsh
```

### Create the keyspace (one-time setup)

```cql
CREATE KEYSPACE IF NOT EXISTS ras_dev
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE ras_dev;
```

### Check cluster status

```bash
docker exec ras_cassandra_dev nodetool status
```

### In Python (cassandra-driver)

```python
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider

cluster = Cluster(
    contact_points=["localhost"],
    port=9042,
)
session = cluster.connect("ras_dev")

# Example: write an event log entry
session.execute("""
    INSERT INTO fraud_events (event_id, transaction_id, score, decision, created_at)
    VALUES (%s, %s, %s, %s, toTimestamp(now()))
""", (event_id, transaction_id, score, decision))
```

See `docs/architecture/adr/ADR-002-cassandra-event-log.md` for the schema design rationale.

---

## HashiCorp Vault

**Local instance:** hashicorp/vault:1.17, dev mode. All data is **in-memory only** — it resets on every container restart.

Dev mode means:
- Vault is already unsealed
- Root token is `dev-root-token`
- No TLS (HTTP, not HTTPS)

### Vault UI

Open http://localhost:8200/ui and sign in with token `dev-root-token`.

### Vault CLI (from host)

```bash
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=dev-root-token

# Write a secret
vault kv put secret/ras/database password="postgres"

# Read a secret
vault kv get secret/ras/database

# List secrets
vault kv list secret/ras/
```

### Vault CLI (inside container)

```bash
docker exec -it ras_vault_dev vault kv put secret/ras/test value="hello"
docker exec -it ras_vault_dev vault kv get secret/ras/test
```

### In Python (hvac)

```python
import hvac

client = hvac.Client(url="http://localhost:8200", token="dev-root-token")

# Write
client.secrets.kv.v2.create_or_update_secret(
    path="ras/database",
    secret={"password": "postgres"},
)

# Read
secret = client.secrets.kv.v2.read_secret_version(path="ras/database")
password = secret["data"]["data"]["password"]
```

**Important:** Dev mode token and in-memory storage are **never** used in staging or production. In staging/prod, Vault is provisioned via Terraform with auto-unseal (AWS KMS) and dynamic secrets. See `docs/architecture/adr/ADR-003-kms-envelope-encryption.md`.

---

## Keycloak

**Local instance:** Keycloak 25, dev mode (no TLS, in-memory H2 database). Data resets on container restart.

### Initial setup (one-time, after first `make dev`)

1. Open http://localhost:8080 and sign in: `admin` / `admin`
2. Create realm **`ras`**:
   - Click **Create realm** → Name: `ras` → Create
3. Create backend client **`ras-backend`**:
   - Clients → Create client → Client ID: `ras-backend`
   - Client authentication: **ON** (confidential)
   - Service accounts enabled: **ON**
   - Save → Credentials tab → copy the client secret → add to `.env` as `KEYCLOAK_CLIENT_SECRET`
4. Create frontend client **`ras-frontend`**:
   - Clients → Create client → Client ID: `ras-frontend`
   - Client authentication: **ON**
   - Valid redirect URIs: `http://localhost:3000/*`
   - Web origins: `http://localhost:3000`
   - Save → Credentials tab → copy secret → add to `frontend/.env.local` as `KEYCLOAK_CLIENT_SECRET`
5. Create a test user:
   - Users → Create user → Username: `analyst@ras.dev` → Email verified: ON
   - Credentials tab → Set password: `analyst123` → Temporary: OFF

### Verify OIDC discovery endpoint

```bash
curl http://localhost:8080/realms/ras/.well-known/openid-configuration | jq .
```

### Get an access token (dev testing)

```bash
curl -s -X POST http://localhost:8080/realms/ras/protocol/openid-connect/token \
  -d "grant_type=password" \
  -d "client_id=ras-backend" \
  -d "client_secret=<your-client-secret>" \
  -d "username=analyst@ras.dev" \
  -d "password=analyst123" | jq .access_token
```

### Frontend auth

The frontend uses NextAuth.js v5 with two providers:

- **Keycloak OIDC** — requires `KEYCLOAK_ISSUER`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET` in `frontend/.env.local`. Use this after completing the Keycloak setup above.
- **Dev Credentials** — always available as fallback. Login at http://localhost:3000/login with `analyst@ras.dev` / `analyst123` or `admin@ras.dev` / `admin123`. No Keycloak required.

---

## Resetting Local State

Services use named Docker volumes — data persists across `docker-compose down`.

To reset a specific service:

```bash
# Reset Cassandra data
docker-compose down cassandra && docker volume rm fraud-detection-system_cassandra_data

# Reset Kafka data
docker-compose down kafka && docker volume rm fraud-detection-system_kafka_data

# Reset Vault (also resets on every restart — dev mode is always clean)
docker-compose restart vault

# Reset Keycloak (realm config lost)
docker-compose down keycloak && docker volume rm fraud-detection-system_keycloak_data
```

To wipe everything and start fresh:

```bash
make docker-clean   # stops containers, removes volumes, prunes images
make dev            # start again
```
