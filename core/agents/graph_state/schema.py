"""
Neo4j Graph Schema for Agent State
==================================

Defines the graph schema and Cypher queries for agent state management.
This replaces static YAML kernel loading with a living Neo4j graph.

Node Labels:
- Agent: The agent instance (L, CA, etc.)
- Responsibility: Agent responsibilities with priority
- Directive: Behavioral directives with severity
- SOP: Standard Operating Procedures with steps
- Tool: Available tools with approval requirements

Relationship Types:
- HAS_RESPONSIBILITY: Agent → Responsibility
- HAS_DIRECTIVE: Agent → Directive
- HAS_SOP: Agent → SOP
- CAN_EXECUTE: Agent → Tool
- REPORTS_TO: Agent → Agent (supervisor)
- COLLABORATES_WITH: Agent → Agent (peers)

Version: 1.0.0
Created: 2026-01-05
"""

# =============================================================================
# NODE LABELS
# =============================================================================

AGENT_LABEL = "Agent"
RESPONSIBILITY_LABEL = "Responsibility"
DIRECTIVE_LABEL = "Directive"
SOP_LABEL = "SOP"
TOOL_LABEL = "Tool"

# =============================================================================
# RELATIONSHIP TYPES
# =============================================================================

HAS_RESPONSIBILITY = "HAS_RESPONSIBILITY"
HAS_DIRECTIVE = "HAS_DIRECTIVE"
HAS_SOP = "HAS_SOP"
CAN_EXECUTE = "CAN_EXECUTE"
REPORTS_TO = "REPORTS_TO"
COLLABORATES_WITH = "COLLABORATES_WITH"

# =============================================================================
# QUERIES: READ OPERATIONS
# =============================================================================

# Load complete agent state with all relationships
LOAD_AGENT_STATE_QUERY = """
MATCH (a:Agent {agent_id: $agent_id})
OPTIONAL MATCH (a)-[r1:HAS_RESPONSIBILITY]->(resp:Responsibility)
OPTIONAL MATCH (a)-[r2:HAS_DIRECTIVE]->(dir:Directive)
OPTIONAL MATCH (a)-[r3:HAS_SOP]->(sop:SOP)
OPTIONAL MATCH (a)-[r4:CAN_EXECUTE]->(tool:Tool)
OPTIONAL MATCH (a)-[r5:REPORTS_TO]->(supervisor:Agent)
OPTIONAL MATCH (a)-[r6:COLLABORATES_WITH]->(peer:Agent)
RETURN a,
       collect(DISTINCT resp) as responsibilities,
       collect(DISTINCT dir) as directives,
       collect(DISTINCT sop) as sops,
       collect(DISTINCT tool) as tools,
       supervisor,
       collect(DISTINCT peer) as collaborators
"""

# Check if agent exists
AGENT_EXISTS_QUERY = """
MATCH (a:Agent {agent_id: $agent_id})
RETURN a IS NOT NULL as exists
"""

# Get agent responsibilities only
GET_RESPONSIBILITIES_QUERY = """
MATCH (a:Agent {agent_id: $agent_id})-[:HAS_RESPONSIBILITY]->(r:Responsibility)
RETURN r.title as title, r.description as description, r.priority as priority
ORDER BY r.priority
"""

# Get agent directives by severity
GET_DIRECTIVES_BY_SEVERITY_QUERY = """
MATCH (a:Agent {agent_id: $agent_id})-[:HAS_DIRECTIVE]->(d:Directive)
WHERE d.severity = $severity
RETURN d.text as text, d.context as context, d.severity as severity
"""

# Get agent tools with approval requirements
GET_TOOLS_QUERY = """
MATCH (a:Agent {agent_id: $agent_id})-[:CAN_EXECUTE]->(t:Tool)
RETURN t.name as name, 
       t.risk_level as risk_level, 
       t.requires_approval as requires_approval,
       t.approval_source as approval_source
ORDER BY t.risk_level DESC
"""

# =============================================================================
# QUERIES: WRITE OPERATIONS (Self-Modify)
# =============================================================================

# Add directive to agent
ADD_DIRECTIVE_QUERY = """
CREATE (d:Directive {
    id: randomUUID(),
    text: $text,
    context: $context,
    severity: $severity,
    created_by: $created_by,
    created_at: datetime()
})
WITH d
MATCH (a:Agent {agent_id: $agent_id})
CREATE (a)-[:HAS_DIRECTIVE {added_at: datetime()}]->(d)
RETURN d.id as directive_id, d.text as text
"""

# Update responsibility description
UPDATE_RESPONSIBILITY_QUERY = """
MATCH (a:Agent {agent_id: $agent_id})-[:HAS_RESPONSIBILITY]->(r:Responsibility {title: $title})
SET r.description = $new_description,
    r.updated_at = datetime(),
    r.updated_by = $agent_id
RETURN r.title as title, r.description as description
"""

# Add SOP step
ADD_SOP_STEP_QUERY = """
MATCH (a:Agent {agent_id: $agent_id})-[:HAS_SOP]->(s:SOP {name: $sop_name})
SET s.steps = s.steps + [$step],
    s.updated_at = datetime()
RETURN s.name as name, size(s.steps) as step_count
"""

# =============================================================================
# QUERIES: BOOTSTRAP (One-Time Migration)
# =============================================================================

# Create agent node
CREATE_AGENT_QUERY = """
MERGE (a:Agent {agent_id: $agent_id})
ON CREATE SET
    a.designation = $designation,
    a.role = $role,
    a.mission = $mission,
    a.authority_level = $authority_level,
    a.status = 'ACTIVE',
    a.created_at = datetime()
ON MATCH SET
    a.updated_at = datetime()
RETURN a.agent_id as agent_id
"""

# Create responsibility and link to agent
CREATE_RESPONSIBILITY_QUERY = """
MATCH (a:Agent {agent_id: $agent_id})
MERGE (r:Responsibility {title: $title})
ON CREATE SET
    r.description = $description,
    r.priority = $priority,
    r.created_at = datetime()
MERGE (a)-[:HAS_RESPONSIBILITY]->(r)
RETURN r.title as title
"""

# Create directive and link to agent
CREATE_DIRECTIVE_QUERY = """
MATCH (a:Agent {agent_id: $agent_id})
CREATE (d:Directive {
    id: randomUUID(),
    text: $text,
    context: $context,
    severity: $severity,
    created_at: datetime()
})
CREATE (a)-[:HAS_DIRECTIVE]->(d)
RETURN d.id as directive_id
"""

# Create SOP and link to agent
CREATE_SOP_QUERY = """
MATCH (a:Agent {agent_id: $agent_id})
MERGE (s:SOP {name: $name})
ON CREATE SET
    s.steps = $steps,
    s.created_at = datetime()
ON MATCH SET
    s.steps = $steps,
    s.updated_at = datetime()
MERGE (a)-[:HAS_SOP]->(s)
RETURN s.name as name
"""

# Create tool and link to agent
CREATE_TOOL_QUERY = """
MATCH (a:Agent {agent_id: $agent_id})
MERGE (t:Tool {name: $name})
ON CREATE SET
    t.risk_level = $risk_level,
    t.requires_approval = $requires_approval,
    t.approval_source = $approval_source,
    t.created_at = datetime()
MERGE (a)-[:CAN_EXECUTE]->(t)
RETURN t.name as name
"""

# Create REPORTS_TO relationship
CREATE_REPORTS_TO_QUERY = """
MATCH (agent:Agent {agent_id: $agent_id})
MATCH (supervisor:Agent {agent_id: $supervisor_id})
MERGE (agent)-[:REPORTS_TO]->(supervisor)
RETURN agent.agent_id as agent, supervisor.agent_id as supervisor
"""

# =============================================================================
# QUERIES: SHARED WITH TOOL GRAPH (UKG Phase 2)
# =============================================================================

# Ensure agent exists (create if not) - shared by Graph State and Tool Graph
ENSURE_AGENT_QUERY = """
MERGE (a:Agent {agent_id: $agent_id})
ON CREATE SET
    a.status = 'ACTIVE',
    a.created_at = datetime(),
    a.created_by = 'system'
RETURN a.agent_id as agent_id, 
       a.created_at IS NOT NULL as created
"""

# Get agent by ID (for Tool Graph lookup)
GET_AGENT_QUERY = """
MATCH (a:Agent {agent_id: $agent_id})
RETURN a.agent_id as agent_id,
       a.designation as designation,
       a.role as role,
       a.status as status
"""

# =============================================================================
# QUERIES: AUDIT
# =============================================================================

# Get modification history for agent
GET_AGENT_HISTORY_QUERY = """
MATCH (a:Agent {agent_id: $agent_id})-[r]->(n)
WHERE r.added_at IS NOT NULL OR n.created_at IS NOT NULL
RETURN type(r) as relationship_type,
       labels(n)[0] as node_type,
       n.text as text,
       n.title as title,
       n.name as name,
       coalesce(r.added_at, n.created_at) as timestamp
ORDER BY timestamp DESC
LIMIT $limit
"""

