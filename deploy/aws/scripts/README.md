# GreenGovRAG Scripts

Helper scripts for managing and accessing the GreenGovRAG AWS infrastructure.

## Database Access

### PostgreSQL Tunnel

Access RDS PostgreSQL database from your local machine via SSM port forwarding.

```bash
./scripts/db-tunnel.sh
```

**Connect with pgAdmin:**
- Host: `localhost`
- Port: `5432`
- Database: `greengovrag`
- Username: `postgres`
- Password: From your AWS secrets/GitHub secrets

**Connect with psql:**
```bash
psql -h localhost -p 5432 -U postgres -d greengovrag
```

**Connect with Python:**
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="greengovrag",
    user="postgres",
    password="YOUR_PASSWORD"
)
```

---

## Vector Store Access

### Qdrant Tunnel

Access Qdrant vector database from your local machine via SSM port forwarding.

```bash
./scripts/qdrant-tunnel.sh
```

**Access Points:**
- Web UI: http://localhost:6333/dashboard
- API Endpoint: http://localhost:6333
- Collections: http://localhost:6333/collections
- Metrics: http://localhost:6333/metrics

**Example API Calls:**
```bash
# List all collections
curl http://localhost:6333/collections

# Get collection info
curl http://localhost:6333/collections/greengovrag

# Search vectors (example)
curl -X POST http://localhost:6333/collections/greengovrag/points/search \
  -H 'Content-Type: application/json' \
  -d '{
    "vector": [0.1, 0.2, ...],
    "limit": 5
  }'
```

**Python Client:**
```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")
collections = client.get_collections()
print(collections)
```

---

## Prerequisites

1. **AWS CLI** configured with valid credentials
2. **Session Manager Plugin** installed:
   ```bash
   # macOS
   brew install --cask session-manager-plugin

   # Ubuntu/Debian
   curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "session-manager-plugin.deb"
   sudo dpkg -i session-manager-plugin.deb
   ```

3. **Stack deployed**: `GreenGovRAGStack` must be deployed to AWS

---

## Troubleshooting

### "Could not retrieve stack outputs"
- Verify stack is deployed: `aws cloudformation describe-stacks --stack-name GreenGovRAGStack`
- Check AWS credentials: `aws sts get-caller-identity`

### "TargetNotConnected" error
- Wait 1-2 minutes after stack deployment for SSM agent to register
- Check instance is running: `aws ec2 describe-instances --instance-ids <INSTANCE_ID>`

### Port already in use
```bash
# Find process using port 5432 (PostgreSQL)
lsof -ti:5432 | xargs kill -9

# Find process using port 6333 (Qdrant)
lsof -ti:6333 | xargs kill -9
```

### Cannot connect to database after tunnel is open
- Verify tunnel is running (should show "Waiting for connections...")
- Check firewall settings allow localhost connections
- Verify password is correct (check GitHub Secrets or AWS Secrets Manager)

---

## Architecture

Both tunnels use the Qdrant EC2 instance as a bastion host:

```
Your Machine → SSM Agent on EC2 → RDS/Qdrant
(localhost:5432)                    (private IP)
(localhost:6333)                    (private IP)
```

**Security:**
- No SSH keys required
- No public IPs on databases
- IAM-based authentication via SSM
- All traffic encrypted via TLS
- Port forwarding sessions logged in CloudTrail

---

## Concurrent Access

You can run both tunnels simultaneously in separate terminal windows:

```bash
# Terminal 1: PostgreSQL
./scripts/db-tunnel.sh

# Terminal 2: Qdrant
./scripts/qdrant-tunnel.sh
```

Press `Ctrl+C` in each terminal to close the respective tunnel.