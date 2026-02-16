l9/
├── compiler/
│   ├── __init__.py
│   ├── transcript_compiler.py
│   ├── lexer.py
│   ├── classifier.py
│   ├── emitters/
│   │   ├── decisions.py
│   │   ├── ial_candidates.py
│   │   ├── invariants.py
│   │   └── work_packets.py
│   ├── schemas/
│   │   ├── decisions.schema.yaml
│   │   ├── ial_candidates.schema.yaml
│   │   ├── typed_invariants.schema.yaml
│   │   └── work_packets.schema.yaml
│   └── validator_bridge.py

MENTAL MODEL:
Lex + Segment (claims)
        ↓
Classify (decision | ial | invariant | task | noise)
        ↓
Normalize (canonical fields)
        ↓
Emit (YAML artifacts)
        ↓
Validate (teeth)

COMPILER - WHAT IT DOES:
Applies codegen only to validated artifacts
Refuses to act on raw chat
Chats become source code
Specs become IR
Validators become law
Codegen becomes mechanical
Memory becomes structured, not nostalgic

You just built:
Chat → Law → Code
That’s frontier-grade.