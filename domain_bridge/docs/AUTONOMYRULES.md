# Autonomy Rules

## Escalation Policy

Decisions are escalated when:

| Condition            | Trigger             | Escalation Level |
| -------------------- | ------------------- | ---------------- |
| Low confidence       | < 0.5               | Standard         |
| High risk            | `high_risk: true`   | Compliance       |
| Destructive          | `destructive: true` | Igor             |
| Critical             | `critical: true`    | Igor             |
| Compliance violation | Rule fails          | Compliance       |

## Governance Anchors

| Anchor     | Authority          | Response Time |
| ---------- | ------------------ | ------------- |
| Igor       | Critical decisions | < 5 min       |
| Compliance | Regulatory         | < 15 min      |
| Standard   | Low-risk           | Async         |

## Human Override

Human overrides take precedence:

```python
if override_active:
    # Skip automated decision
    return human_decision
```

## Audit Requirements

All governance interactions logged:

- Decision context
- Escalation trigger
- Anchor response
- Override applied
- Timestamp
