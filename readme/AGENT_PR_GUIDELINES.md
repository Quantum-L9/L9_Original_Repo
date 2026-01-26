# Agent PR & Code Generation Guidelines

> **IMPORTANT:** Agents MUST read this BEFORE generating any code changes.

## 🚨 MANDATORY: DIFFS ONLY

```
┌──────────────────────────────────────────────────────────────────────────┐
│  GENERATE DIFFS, NOT ENTIRE FILES                                        │
│                                                                          │
│  ❌ WRONG: Generate entire 500-line file with your 3-line change         │
│  ✅ RIGHT: Show only the diff (before → after) for review                │
└──────────────────────────────────────────────────────────────────────────┘
```

### Why This Matters

Recent PRs (#57, #58, #59, #60, #61) required **manual review and partial integration** because:

1. PRs contained entire file rewrites instead of targeted diffs
2. Changes conflicted with existing L9 implementations
3. New patterns were introduced that didn't exist in the codebase
4. Reviewers couldn't easily identify what actually changed

**Result:** Hours of manual cherry-picking instead of simple merges.

---

## 📋 Before Generating Code

### 1. CHECK IF IT EXISTS

```bash
# Before creating ANY new file or pattern:
grep -r "ClassName" readme/repo-index/class_definitions.txt
grep -r "function_name" readme/repo-index/function_signatures.txt
ls -la path/to/suspected/location/
```

### 2. CHECK EXISTING IMPLEMENTATIONS

| Pattern               | L9 Already Has                  | Location                          |
| --------------------- | ------------------------------- | --------------------------------- |
| Singleton             | `@register_singleton` decorator | `core/singleton_auto_registry.py` |
| DI Container          | Full 886-line implementation    | `core/di/container.py`            |
| DI Bootstrap          | Tiered initialization           | `core/di/bootstrap.py`            |
| Protocol abstractions | `typing.Protocol` based         | `core/protocols/`                 |
| Service adapters      | Adapter pattern                 | `memory/service_adapter.py`       |

### 3. DO NOT DUPLICATE

These patterns were **rejected** from recent PRs:

| ❌ Rejected Pattern                             | Why                             | L9 Alternative            |
| ----------------------------------------------- | ------------------------------- | ------------------------- |
| `from core.patterns.singleton import singleton` | Module doesn't exist            | Use `@register_singleton` |
| `@singleton` class decorator                    | Not L9's pattern                | Use factory functions     |
| Simplified DI container (229 lines)             | Conflicts with 886-line version | Use existing `core/di/`   |
| Stricter Ruff/MyPy in pyproject.toml            | Breaking changes                | See ADR-0062              |

---

## ✅ Correct PR Format

### Small Change (< 20 lines)

````markdown
## Change: Add timeout parameter to fetch_data()

**File:** `core/api/client.py`

**Diff:**

```diff
- async def fetch_data(self, endpoint: str) -> dict:
+ async def fetch_data(self, endpoint: str, timeout: int = 30) -> dict:
      """Fetch data from endpoint."""
-     response = await self.session.get(endpoint)
+     response = await self.session.get(endpoint, timeout=timeout)
      return response.json()
```
````

**Tests:** Add test in `tests/core/api/test_client.py`

````

### Multi-File Change

```markdown
## Change: Add rate limiting to API client

**Files affected:**
1. `core/api/client.py` — Add rate limiter integration
2. `core/api/rate_limiter.py` — New rate limiter class
3. `tests/core/api/test_rate_limiter.py` — Tests

**Diff 1: core/api/client.py (lines 45-52)**
```diff
+ from core.api.rate_limiter import RateLimiter
+
  class APIClient:
      def __init__(self):
          self.session = aiohttp.ClientSession()
+         self.rate_limiter = RateLimiter(requests_per_minute=60)
````

**Diff 2: core/api/rate_limiter.py (NEW FILE)**

```python
# Only show new file if truly new and doesn't duplicate existing
```

````

---

## 🚫 Anti-Patterns That Cause Partial Integration

### 1. Entire File Dumps

```markdown
❌ WRONG:
"Here's the updated file:"
[500 lines of code where 3 lines changed]

✅ RIGHT:
"Here's the change:"
[3-line diff with context]
````

### 2. Importing Non-Existent Modules

```python
# ❌ WRONG - This module doesn't exist
from core.patterns.singleton import singleton

# ✅ WRONG - This was in PRs #57, #60, #61 and was REJECTED
@singleton
class MyService:
    pass

# ✅ RIGHT - Use what L9 actually has
from core.singleton_auto_registry import register_singleton

@register_singleton(
    category="core",
    lifecycle=SingletonLifecycle.LAZY,
    description="My service"
)
async def get_my_service() -> MyService:
    return MyService()
```

### 3. Replacing Existing Implementations

```markdown
❌ WRONG:
"I'll create a new DI container at core/di/container.py"
(File already exists with 886 lines)

✅ RIGHT:
"I'll extend the existing DI container with..."
[Show only the additions as a diff]
```

### 4. Introducing New Patterns Without Checking

```markdown
❌ WRONG:
"Let's add a @singleton decorator pattern"
(Without checking if L9 already has singleton handling)

✅ RIGHT:
"L9 uses @register_singleton from core/singleton_auto_registry.py.
Here's how to apply it to this class..."
```

---

## 📖 Required Reading Before PRs

1. **`readme/PR_ADOPTION_SUMMARY.md`** — What was integrated, what wasn't, why
2. **`readme/repo-index/class_definitions.txt`** — All existing classes
3. **`readme/repo-index/function_signatures.txt`** — All existing functions
4. **`core/di/`** — Existing DI system (don't replace)
5. **`core/protocols/`** — Existing protocol abstractions

---

## 🔍 PR Review Checklist

Before submitting code:

- [ ] Searched repo-index for existing implementations
- [ ] Checked if pattern already exists in L9
- [ ] Generated DIFFS, not entire files
- [ ] No imports from non-existent modules
- [ ] No replacement of existing larger implementations
- [ ] Tested that code compiles (`python -m py_compile file.py`)

---

## 📊 Recent PR Integration Results

| PR     | Status     | Integration | Reason                                  |
| ------ | ---------- | ----------- | --------------------------------------- |
| #57    | ❌ Closed  | 0%          | `@singleton` from non-existent module   |
| #58    | ⚠️ Partial | 30%         | Stricter linting = breaking changes     |
| #59    | ❌ Closed  | 0%          | Files already existed                   |
| #60    | ⚠️ Partial | 20%         | 9/49 files adopted, rest had @singleton |
| #61    | ⚠️ Partial | 5%          | 3/57 files adopted, rest duplicated #60 |
| #62-66 | ✅ Merged  | 100%        | Clean Dependabot updates (diffs only)   |

**Lesson:** Dependabot PRs merged cleanly because they're **diffs only**.
Manual PRs required cherry-picking because they contained **entire file rewrites**.

---

## Reference

- **ADR-0062:** Deferred Strict Linting
- **PR Adoption Summary:** `readme/PR_ADOPTION_SUMMARY.md`
- **Repo Indexes:** `readme/repo-index/*.txt`
- **Session:** 2026-01-24 — PRs #57-#66 processed
