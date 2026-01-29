# C1 Hetzner Firewall Configuration

**Last Updated:** 2026-01-28
**Status:** Active and verified

## Current Firewall Rules (Applied)

These rules are currently active on C1 via Hetzner Console.

### Inbound Rules

| Description    | Protocol | Port  | Source        | Status |
| -------------- | -------- | ----- | ------------- | ------ |
| SSH            | TCP      | 22    | Any IPv4/IPv6 | ✅     |
| Ping           | ICMP     | -     | Any IPv4/IPv6 | ✅     |
| K8s API        | TCP      | 6443  | Any IPv4/IPv6 | ✅     |
| L9 API         | TCP      | 30080 | Any IPv4/IPv6 | ✅     |
| Grafana        | TCP      | 30300 | Any IPv4/IPv6 | ✅     |
| PostgreSQL     | TCP      | 30432 | Any IPv4/IPv6 | ✅     |
| Neo4j Browser  | TCP      | 30474 | Any IPv4/IPv6 | ✅     |
| Neo4j Bolt     | TCP      | 30687 | Any IPv4/IPv6 | ✅     |
| MCP Memory     | TCP      | 30902 | Any IPv4/IPv6 | ✅     |
| Prometheus     | TCP      | 30909 | Any IPv4/IPv6 | ✅     |

### Outbound Rules

| Description  | Protocol | Port | Destination |
| ------------ | -------- | ---- | ----------- | --------------- |
| All outbound | All      | All  | Any         | (default allow) |

---

## Hetzner Console Steps

1. Go to: https://console.hetzner.cloud
2. Select project: L9
3. Navigate to: Firewalls
4. Either:
   - Edit existing `firewall-1` (currently applied to L9)
   - Create new `firewall-c1` for C1 specifically

### To Create New Firewall for C1:

```
Name: firewall-c1
Rules:
  Inbound:
    - TCP 22 (SSH)
    - ICMP
    - TCP 80
    - TCP 443
    - TCP 30080 (L9 API)
    - TCP 30902 (MCP Memory)
    - TCP 30432 (PostgreSQL - restrict to admin IPs)
    - TCP 30300 (Grafana)
    - TCP 30474 (Neo4j Browser)
    - TCP 30687 (Neo4j Bolt)
    - TCP 30909 (Prometheus)
    - TCP 6443 (K8s API - restrict to your IP)
  Outbound:
    - Allow all
Apply to: C1
```

---

## Security Recommendations

### Production Hardening

1. **Restrict K8s API (6443)** to specific admin IPs only
2. **Restrict Neo4j ports** to VPN or specific IPs (contains graph data)
3. **Use TLS** - configure Let's Encrypt via cert-manager
4. **Change default passwords** in `c1-secrets.yaml`

### IP Restrictions (Optional)

For sensitive services, limit source IPs:

```
# Only allow your office/home IP
Source: 203.0.113.50/32  # Replace with your IP

# Or use VPN subnet
Source: 10.8.0.0/24  # WireGuard/OpenVPN subnet
```

---

## Quick Commands

### Check current firewall on server:

```bash
ssh root@46.62.243.82
iptables -L -n
```

### Test port accessibility:

```bash
# From your local machine
nc -zv 46.62.243.82 30080  # L9 API
nc -zv 46.62.243.82 30902  # MCP Memory
nc -zv 46.62.243.82 30432  # PostgreSQL
nc -zv 46.62.243.82 30300  # Grafana
nc -zv 46.62.243.82 30474  # Neo4j Browser
nc -zv 46.62.243.82 30687  # Neo4j Bolt
nc -zv 46.62.243.82 30909  # Prometheus
```

---

## Verification

All ports verified working on 2026-01-28:

```bash
# Test from local machine
curl http://46.62.243.82:30080/health  # L9 API ✅
curl http://46.62.243.82:30902/health  # MCP Memory ✅
```

## History

| Date       | Change                                    |
| ---------- | ----------------------------------------- |
| 2026-01-28 | Added all required ports (30080-30909)    |
| 2026-01-28 | Fixed docker port bindings (127.0.0.1 → 0.0.0.0) |
| 2026-01-28 | Removed conflicting k8s NodePort services |
