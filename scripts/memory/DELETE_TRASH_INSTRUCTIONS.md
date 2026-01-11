# Delete Trash Embeddings - Instructions

## SQL File Generated

The SQL file with 52 trash embedding IDs is at: `/tmp/delete_trash.sql`

## Option 1: Via Docker (if running locally)

```bash
docker exec -i l9-postgres psql -U l9_user -d l9_memory < /tmp/delete_trash.sql
```

## Option 2: Via VPS SSH

```bash
# SSH into VPS
ssh root@157.180.73.53

# Copy SQL file to VPS (or generate on VPS)
cd /opt/l9
python3 scripts/generate_delete_sql.py > /tmp/delete_trash.sql

# Execute via Docker
docker exec -i l9-postgres psql -U l9_user -d l9_memory < /tmp/delete_trash.sql
```

## Option 3: Direct psql (if DATABASE_URL is accessible)

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/l9_memory"
psql $DATABASE_URL -f /tmp/delete_trash.sql
```

## Option 4: Via Python Script (if DATABASE_URL is set)

```bash
# Set DATABASE_URL in .env or environment
export DATABASE_URL="postgresql://user:pass@host:5432/l9_memory"
python3 scripts/delete_trash_via_service.py
```

## Verification

After deletion, verify:

```bash
# Check embedding count
python3 scripts/check_embeddings_via_api.py

# Search for error messages (should return 0 or very few)
# The error message embeddings should be gone
```

## What Gets Deleted

The SQL deletes 52 embeddings containing:
- "Sorry, I encountered a temporary error. Please try again."
- "Sorry, I encountered an error processing your command."
- "No response generated."
- Very short content (< 20 chars)

## Re-indexing Status

✅ All re-indexing scripts have been run:
- GMP Reports indexed
- Error Patterns indexed  
- Architecture indexed
- Preferences indexed
- Tool Usage indexed

High-value content is now in the memory graphs!

