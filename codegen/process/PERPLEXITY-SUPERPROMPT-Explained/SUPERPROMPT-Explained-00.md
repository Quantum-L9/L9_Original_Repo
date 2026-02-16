
1. **Ad-hoc, inline client** (what you have now in the HOW-TO)
    - `requests.post` directly inside `HOW_TO_USE_SUPER_PROMPT.call_perplexity_api(...)`.[^2]
    - Synchronous, no retries, no strong typing, mixed with prompt customization logic.
2. **Structured client class** (what your L9 / autonomous agent uses)
    - In the L9 blueprint there is a `PerplexityClient` using `httpx.AsyncClient`, retry decorators, and a `PerplexityResponse` dataclass.[^3]
    - In `autonomous-research-agent.py` you have `PerplexityLabsClient` with:
        - A model field (`sonar-reasoning`),
        - An async `query(prompt, session_id)` method,
        - Integration with higher-level orchestration (`PromptVariation`, `ResearchResponse`, `SynthesisEngine`).[^1]

“Upgrade to your `perplexity_client.py` style” means: pull that second pattern out into a dedicated `src/perplexity_client.py` and make **all super-prompt and research code depend on it**, instead of each script rolling its own HTTP call.

### What goes in `perplexity_client.py` (concretely)

Conceptually:

- A **dataclass** describing responses (content + citations + raw metadata).[^3]
- A **client class** that:
    - Reads `PERPLEXITY_API_KEY` from env.
    - Knows the base URL and default model.
    - Exposes methods like:
        - `async chat(prompt: str, model: str | None = None) -> PerplexityResponse`
        - Optionally `async deep_research(prompt: str, ...)` if you use sonar-deep-research later.[^4]

The implementation shape is already outlined in your L9 blueprint and Perplexity API guide; you’re just moving it into a small, reusable module.[^4][^3]

## 2. How this connects to the rest of the chat

You actually have **three layers** in play now:

### A. Research foundations and layer docs

The new files you attached are all **outputs / assets from a deep research run**:

- `comprehensive_research_foundation.json`: a big JSON with concepts, sources, maybe synthesis outputs for your AI OS layers.[^5]
- `LAYER_1_Embodied_World_Models.md`, `LAYER_3_Intention_Communication.md`, `LAYER_4_Governance_Loops.md`, `LAYER_5_Economic_Simulation.md`, `LAYER_6_Hierarchical_Models.md`: narrative / design docs for specific layers of your AI Operating System stack.[^6][^7][^8][^9][^10]
- `BOOTSTRAP_Layer2_SemanticOS.md`: bootstrap instructions for one specific layer (Semantic OS).[^11]
- `MASTER_INDEX_Complete_Research_Package.md`: a top-level index that ties the whole research package together.[^12]
- `FILE_MANIFEST.json` + `DELIVERABLES_MANIFEST.txt`: inventories of all the artifacts in this research package (docs, JSON, diagrams, etc.).[^13][^14]

These are **Layer 1** in your Research-to-Code story: the actual content you either got from Deep Research or curated by hand.[^15]

### B. Super-prompt templates and autonomous runner

Earlier, you attached:

- `SUPER_PROMPT_TEMPLATE.py`: parametric super-prompts for generating AI OS layers and governance components.[^16]
- `HOW_TO_USE_SUPER_PROMPT.py`: shows how to fill those templates and call Perplexity once.[^2]
- `autonomous-research-agent.py`: a more advanced **runner** that:
    - Defines prompt variations.
    - Calls Perplexity multiple times in parallel (`PerplexityLabsClient`).
    - Synthesizes results into code + README + `synthesis_metadata.json`.[^1]
- `production-config.py`: requirements + YAML configs for the hybrid sparse-neural model, which is one specific architecture you’re exploring with the super-prompts.[^17]

These are **Layer 2**: machinery to turn prompts into structured research / code.

### C. L9 Research-to-Code and repo architecture

From your L9 files:

- `l9_research_agent_integration_blueprint.md`: defines a first-class L9 `ResearchAgent` that internally uses a `PerplexityClient` and runs a 5-stage pipeline.[^3]
- `L9 Research-to-Code Pipeline` README: documents the four layers:
    - Deep workflows (long literature review).
    - Super-Prompt Pack (fast synthesis).
    - Spec generator.
    - Codegen.[^15]

These are **Layer 3/4**: how research outputs become Module-Specs and then L9 code via CodeGen.

### The glue: a consistent Perplexity client

Right now you have **multiple ways** to hit Perplexity:

- `HOW_TO_USE_SUPER_PROMPT.call_perplexity_api` with `requests` and `sonar-pro`.[^2]
- `autonomous-research-agent.PerplexityLabsClient` (async, probably `httpx` + `tenacity`).[^1]
- The L9 blueprint’s `PerplexityClient` (async `httpx`, `PerplexityResponse` dataclass, retry decorator).[^3]
- The Perplexity API guide examples in `perplexity-api-guide.md` / `perplexity-api-guide-b.md`.[^18][^4]

Upgrading to a single `perplexity_client.py` style is what **unifies** all of this:

- **Research package** (JSON + layer docs): stays as content; when you run new super-prompts to extend it, they go through the same `PerplexityClient`.
- **Super-prompt templates**: generate prompt strings, but **never talk to the network directly**—they pass prompts to the client.
- **Autonomous runner**: uses the same `PerplexityClient` for variations.
- **L9 ResearchAgent**: either uses the same client module or keeps a very similar one that adheres to the same contract, so from the outside it feels consistent.[^15][^3]


## 3. How to wire it practically

High level:

- Create `src/perplexity_client.py` in your Perplexity research repo.
- Move / adapt the async client from `autonomous-research-agent.py` or the L9 blueprint into it, using patterns from the Perplexity API guide (model selection, rate limits, citations).[^4][^1][^3]
- Update:
    - `HOW_TO_USE_SUPER_PROMPT.py` to **import** `PerplexityClient` instead of calling `requests.post`.
    - `autonomous-research-agent.py` (renamed as `superprompt_runner.py`) to import the same client.
- Keep your layer docs + `comprehensive_research_foundation.json` as **inputs** or **ground truth** for future runs; they are independent of how the HTTP call is implemented.[^9][^5][^12]
