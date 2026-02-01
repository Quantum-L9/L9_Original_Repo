# C1 Firewall Configuration

## Server Details

- **Server:** C1
- **IP:** 46.62.243.82
- **Provider:** Hetzner Cloud
- **Firewall:** Hetzner Cloud Firewall + UFW (host-level)

---

## Inbound Rules

| Port | Protocol | Source | Service | Auth | Notes |
|------|----------|--------|---------|------|-------|
| 22 | TCP | Any | SSH | Key-based | Remote admin |
| 80 | TCP | Any | HTTP | None | nginx reverse proxy → l9-api |
| 443 | TCP | Any | HTTPS | TLS | Future: Let's Encrypt |
| 30432 | TCP | Trusted IPs | PostgreSQL | pg_hba.conf | Stream proxy via nginx |
| 30474 | TCP | Trusted IPs | Neo4j HTTP | Basic auth | Stream proxy via nginx |
| 30687 | TCP | Trusted IPs | Neo4j Bolt | Basic auth | Stream proxy via nginx |
| 30379 | TCP | Trusted IPs | Redis | REQUIREPASS | Stream proxy via nginx |

---

## Trusted IPs

| IP | Owner | Purpose | Added | Expires |
|----|-------|---------|-------|---------|
| `<IGOR_MAC_IP>` | Igor | Development access | 2026-01-31 | Never |

> **Note:** Replace `<IGOR_MAC_IP>` with actual IP. Get current IP: `curl ifconfig.me`

---

## Security Model (Defense-in-Depth)

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Hetzner Cloud Firewall (Network Level)                 │
│   - IP whitelist for TCP stream ports (30xxx)                   │
│   - Drops packets before they reach the server                  │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 2: UFW (Host Firewall)                                    │
│   - Backup rules if Hetzner firewall misconfigured              │
│   - Logging for audit trail                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 3: nginx Stream Proxy                                     │
│   - Connection rate limiting (future)                           │
│   - TLS termination (future)                                    │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 4: Application Authentication                             │
│   - PostgreSQL: pg_hba.conf + password                          │
│   - Neo4j: Built-in auth (NEO4J_AUTH)                           │
│   - Redis: REQUIREPASS (REDIS_PASSWORD env var)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Hetzner Cloud Firewall Setup

### Via Hetzner Console

1. Go to: https://console.hetzner.cloud/projects → Select project → Firewalls
2. Create/edit firewall attached to C1
3. Add inbound rules for TCP stream ports with source IP restriction

### Via API

```bash
# List firewalls
curl -H "Authorization: Bearer $HETZNER_API_TOKEN" \
  https://api.hetzner.cloud/v1/firewalls

# Get firewall rules
curl -H "Authorization: Bearer $HETZNER_API_TOKEN" \
  https://api.hetzner.cloud/v1/firewalls/<FIREWALL_ID>
```

---

## UFW Backup Rules (Host-Level)

```bash
# SSH to C1
ssh -i ~/.ssh/Hetzner-C1-nopass root@46.62.243.82

# Add rules for trusted IP (replace <TRUSTED_IP>)
sudo ufw allow from <TRUSTED_IP> to any port 30432 proto tcp comment "PostgreSQL stream"
sudo ufw allow from <TRUSTED_IP> to any port 30474 proto tcp comment "Neo4j HTTP stream"
sudo ufw allow from <TRUSTED_IP> to any port 30687 proto tcp comment "Neo4j Bolt stream"
sudo ufw allow from <TRUSTED_IP> to any port 30379 proto tcp comment "Redis stream"

# Verify
sudo ufw status numbered
```

---

## Verification Commands

### From Untrusted IP (Should Timeout)

```bash
# These should ALL timeout if firewall is working
timeout 5 telnet 46.62.243.82 30432  # PostgreSQL
timeout 5 telnet 46.62.243.82 30379  # Redis
```

### From Trusted IP (Should Connect, Then Auth)

```bash
# PostgreSQL (requires password)
psql -h 46.62.243.82 -p 30432 -U l9_user -d l9_memory

# Redis (requires REQUIREPASS)
redis-cli -h 46.62.243.82 -p 30379 -a "$REDIS_PASSWORD" PING
# Expected: PONG

# Neo4j Bolt
cypher-shell -a bolt://46.62.243.82:30687 -u neo4j -p "$NEO4J_PASSWORD"
```

---

## Incident Response

### If Unauthorized Access Detected

1. **Immediate:** Revoke all firewall rules for affected port
   ```bash
   sudo ufw delete allow 30379/tcp
   ```
2. **Investigate:** Check logs
   ```bash
   docker compose logs redis | grep -i auth
   docker compose logs nginx | grep stream
   ```
3. **Rotate:** Change passwords in `.env.c1` and redeploy
4. **Document:** Add incident to this file

---

## Audit Log

| Date | Action | By | Notes |
|------|--------|----|-------|
| 2026-01-31 | Created firewall policy | Igor | Initial TCP stream exposure for Cursor access |

---

## Related Files

- `docker-compose.prod.yml` — Port exposure configuration
- `deploy/nginx/nginx.conf` — Stream proxy blocks
- `.env` — Passwords (REDIS_PASSWORD, NEO4J_PASSWORD, POSTGRES_PASSWORD)
