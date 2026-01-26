# 🛡️ **L9 MASTER GOD-MODE SCHEMA EXTRACTION PLAN v3.0**

**Universal Prompt — works for ALL L9 schemas**
**Schema version: `l9_schema / v1.x`**

Use this prompt with ANY schema you create. This is the **canonical** extraction plan for Cursor.

---

# **1 — PURPOSE (NON-NEGOTIABLE)**

Convert ANY `l9_schema` YAML file into a full set of production Python modules
according to:

- **Memory.yaml** (PacketEnvelope, SRB, ArtifactPointer)
- **Packet Protocol.yaml** (routing rules, target directories)
- The schema being extracted
- Pydantic v2
- LangGraph runtime signatures
- L9 model placement conventions

All output MUST be **import-clean**, **runtime-clean**, **pass validation**, **contain zero placeholders**, and be fully **schema-complete**.

---

# **2 — REQUIRED INPUT FILES (ALWAYS LOAD THESE FOUR)**

Cursor must load these **every time**:

### 2.1 Main schema to extract

```
<SCHEMA_TO_EXTRACT.yaml>
```

### 2.2 Memory substrate spec

Defines PacketEnvelope, ArtifactPointer, StructuredReasoningBlock.
**Used for ALL schemas.**

### 2.3 Packet Protocol routing spec

Determines exact final file placement.
**Used for ALL schemas.**

### 2.4 This master plan

Orchestrates EVERYTHING.

No other files are required.

---

# **3 — GLOBAL RULES (APPLY TO ALL SCHEMAS)**

### 3.1 Schema→Model conversion

- Every field MUST map 1:1 into Python with Pydantic v2 syntax.
- No enums may be dropped.
- No variant/discriminated unions may be simplified.
- Every nested schema = its own model.

### 3.2 Pydantic requirements

```
python >= 3.11
pydantic >= 2.6,<3.0
```

### 3.3 Memory substrate rules (ALWAYS ACTIVE)

From Memory.yaml:

- PacketEnvelope is **immutable**
- Must use Pydantic `frozen=True`
- Must use `.model_copy(update=...)` for safe mutation
- Embedding field must support vectors up to dim 3072
- Must include lineage (`parent_ids`)
- Must support variant payloads based on `kind`

### 3.4 StructuredReasoningBlock is global

Every model that embeds reasoning MUST use SRB exactly as defined in Memory.yaml.

### 3.5 LangGraph compliance

Every schema that defines a node must include:

```
async def pass_X(state: ResearchState) -> ResearchState
```

### 3.6 Packet Protocol file placement

Routing MUST obey Packet Protocol.yaml exactly.

If a generated file matches any `explicit_files`
→ route THERE
Otherwise match patterns
→ route THERE
Else → fallback rules.

No overwrites unless `force_update=true`.

---

# **4 — UNIVERSAL EXTRACTION PIPELINE (ALWAYS FOLLOW THIS)**

## **STEP 1 — Parse All Inputs**

Load:

1. Main schema
2. Memory.yaml
3. Packet Protocol.yaml
4. This plan

Construct the full schema DAG.

---

## **STEP 2 — Build the FIELD MAP**

For every field across every schema:

```
schema_path → python_type → constraints → required? → default → notes
```

Example (Cursor must generate this automatically):

```
packet_envelope.packet_id → UUID → required → pk
packet_envelope.content → variant → discriminator="kind"
something.value → list[str] → unique? → length?
```

The FIELD MAP is used for:

- Type correctness
- Validator construction
- Avoiding missing fields
- Order correctness
- Memory substrate integration
- LangGraph runtime binding

---

## **STEP 3 — Determine MODULE SET**

The module list is computed automatically from the schema contents.

Cursor must generate:

- One module per top-level schema block
- Additional modules for:

  - PacketEnvelope
  - StructuredReasoningBlock
  - ArtifactPointer
  - Substrate models
  - Node models
  - Runtime profiles
  - Universal schema aggregator
  - Any LangGraph node set

**Minimum modules: 4**
**Typical modules: 7–12**

All MUST be placed via Packet Protocol routing rules.

---

## **STEP 4 — Generate All Modules**

Each module must contain:

- Fully typed Pydantic v2 models
- Strict validation
- No placeholders
- No TODOs
- No commented code
- Clean imports
- Correct routing decorators if applicable
- Correct discriminated unions
- Correct enum classes
- Correct ARTIFACT POINTER references
- Correct PacketEnvelope invariants
- Correct SRB embedding

---

## **STEP 5 — Apply \*\***Memory.yaml Requirements\*\* to ALL schemas

Memory.yaml governs:

- Immutability rules
- Reasoning block structure
- ArtifactPointer structure
- Postgres index artifacts
- pgvector embeddings

All these rules apply globally—no exceptions.

---

## **STEP 6 — Apply \*\***Packet Protocol.yaml Routing Rules\*\*

Use Packet Protocol.yaml verbatim.
Place each generated file based on:

- `explicit_files`
- `patterns`
- fallback rules

**Never** guess file locations.
**Never** create new routing groups.
**Never** deviate from the spec.

If routing fails → FAIL HARD.

---

## **STEP 7 — Validation Suite (MANDATORY)**

Cursor must run:

### 7.1 Syntax

```
python -m compileall /L9
```

### 7.2 AST Validity

For every generated file:

```
ast.parse(open(file).read())
```

### 7.3 Instantiation Test

Each model must:

- Instantiate with example data
- Reject invalid data
- Enforce all constraints

### 7.4 PacketEnvelope Immutability Test

```
try: envelope.packet_id = "new"
except: pass
else: FAIL
```

### 7.5 Variant Payload Test

Instantiate all `kind` variations.

---

# **8 — OUTPUT STRUCTURE**

Cursor must produce:

```
/L9/
  core/
    schemas/
      <N dynamically generated modules>
    interfaces/
    ...
  memory/
    <substrate models if routed here>
```

PLUS a generated test suite:

```
/L9/core/schemas/tests/
    test_packet_envelope.py
    test_schema_core.py
    test_discriminators.py
    test_langgraph_nodes.py
```

All must pass.

---

# **9 — EXECUTION COMMAND FOR CURSOR (COPY/PASTE)**

Use this EXACT block to run extraction for ANY schema:

```
RUN L9_MASTER_SCHEMA_EXTRACTOR:
- Load <SCHEMA_TO_EXTRACT.yaml>
- Load Memory.yaml (PacketEnvelope, SRB, ArtifactPointer)
- Load Packet Protocol.yaml (routing rules)
- Load MASTER Extraction Plan v3.0
- Parse all files
- Build FIELD MAP
- Determine module list
- Generate ALL modules (no TODOs, no omissions)
- Route using Packet Protocol only
- Run full validation suite
- Produce final production-grade Python files
- Output final file list + routing map + diagnostics
```

---

# **10 — CONFIRMATION CHECKLIST (SUCCESS = ALL TRUE)**

Cursor MUST confirm:

- 100% of schema fields mapped
- All models typed + validated
- All discriminators correct
- PacketEnvelope immutable
- SRB present where needed
- ArtifactPointer references correct
- All routing matches Packet Protocol
- No circular imports
- No syntax errors
- All files load cleanly
- All LangGraph nodes pass signature rules
- Test suite passes
- All output is production-grade

If ANY fail → regenerate EVERYTHING.
