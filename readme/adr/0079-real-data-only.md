# ADR-0079: Real Data Only

**Status:** Accepted  
**Date:** 2026-01-31  
**Author:** Igor Beylin  

## Context

Fabricating data—making up phone numbers, emails, addresses, metrics, or any other information—breaks trust immediately. Once caught, all future data becomes suspect.

## Decision

**Policy: Never fabricate data. Use real data, leave blank, or explicitly state "example/placeholder."**

### Data Handling Rules

| Situation | Action |
|-----------|--------|
| Real data available | Use it |
| No data available | Leave blank or null |
| Example needed | Label clearly as "EXAMPLE" or "PLACEHOLDER" |
| User provides data | Use exactly as provided |

### Never Fabricate

- Phone numbers
- Email addresses  
- Physical addresses
- API keys or credentials
- Metric values or statistics
- User names or identifiers
- Transaction IDs
- Timestamps for events that didn't happen

### Acceptable Placeholder Patterns

```yaml
# ✅ GOOD — Clearly labeled
phone: "PLACEHOLDER - user to provide"
email: "example@example.com"  # Standard example domain
api_key: "${API_KEY}"  # Environment variable

# ❌ BAD — Fabricated, looks real
phone: "+1-555-867-5309"
email: "john.smith@company.com"
api_key: "sk_live_abc123xyz789"
```

### When Examples Are Needed

If documentation or tests require example data:

1. Use [RFC 2606](https://tools.ietf.org/html/rfc2606) reserved domains: `example.com`, `example.org`
2. Use obviously fake numbers: `555-0100` to `555-0199` (reserved for fiction)
3. Label clearly: `# Example only - replace with real value`

### Confirmation Before Using Data

If uncertain about data source:
- "I see [data] in [source]. Is this the correct value to use?"
- "I don't have access to [data]. Please provide or confirm I should leave blank."

### Anti-Patterns

| Anti-Pattern | Why It's Wrong |
|--------------|----------------|
| "I'll just put something here" | Fabrication |
| Making up realistic-looking data | Deceptive |
| Guessing metric values | Misleading |
| Inventing user information | Trust violation |

## Implementation

### Code Review Signals

Flag for review if:
- Data appears in code that wasn't in requirements
- Metrics or statistics without source citation
- Contact information without confirmation
- API keys that look real but aren't environment variables

### Test Data Guidelines

```python
# ✅ GOOD — Clearly test data
TEST_EMAIL = "test-user@example.com"  # RFC 2606 reserved
TEST_PHONE = "555-0123"  # Reserved for fiction

# ❌ BAD — Looks real
TEST_EMAIL = "sarah.jones@gmail.com"  # Could be real person
TEST_PHONE = "212-555-1234"  # Could be real number
```

## Consequences

### Positive
- Data integrity maintained
- Trust preserved
- No legal issues with fake PII
- Clear separation of test vs production data

### Negative
- May need to ask for data more often
- Some fields remain blank until provided

## Related
- ADR-0063: No Silent Changes
