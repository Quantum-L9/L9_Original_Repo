"""
L9 IR Engine - Meta to IR Compiler
===================================

Compiles MetaContract YAML specifications into Intermediate Representation
suitable for code generation.

Transforms validated MetaContract into:
- Code generation targets from repo.allowed_new_files
- Dependency graph from dependencies.outbound_calls
- Packet type requirements from packet_contract
- Test obligations from test_scope and acceptance
- Wiring requirements from runtime_wiring

Version: 1.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import structlog
import yaml

from ir_engine.meta_ir import (
    MetaContract,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# INTERMEDIATE REPRESENTATION MODELS
# =============================================================================


@dataclass
class GenerationTarget:
    """A single file to be generated."""
    
    path: str
    target_type: str  # adapter, client, route, ingest, test, doc
    template_name: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyEdge:
    """A single dependency edge in the module graph."""
    
    source_module: str
    target_module: str
    interface: str  # http, tool
    endpoint: str
    
    def to_import(self) -> str:
        """Generate Python import statement for this dependency."""
        # Extract module path from endpoint
        if self.target_module == "memory.service":
            return "from memory.substrate_service import MemorySubstrateService"
        elif self.target_module == "aios.runtime":
            return "from core.agents.runtime import AIOSRuntime"
        else:
            # Generic import based on module name
            parts = self.target_module.split(".")
            return f"from {'.'.join(parts[:-1])} import {parts[-1]}"


@dataclass
class PacketSpec:
    """Packet specification for code generation."""
    
    packet_type: str
    required_metadata: List[str]
    
    @property
    def class_name(self) -> str:
        """Generate class name from packet type."""
        # slack_adapter.in -> SlackAdapterInPacket
        parts = self.packet_type.replace(".", "_").split("_")
        return "".join(p.capitalize() for p in parts) + "Packet"


@dataclass
class TestSpec:
    """Test specification derived from acceptance criteria."""
    
    test_file: str
    test_function: str
    description: str
    is_positive: bool
    acceptance_id: str


@dataclass
class WiringSpec:
    """Wiring specification for server integration."""
    
    service: str
    startup_phase: str
    depends_on: List[str]
    blocks_startup_on_failure: bool
    router_include: Optional[str] = None
    lifespan_init: Optional[str] = None


@dataclass
class ModuleIR:
    """
    Intermediate Representation of a module.
    
    Contains all information needed for code generation
    extracted from a MetaContract.
    """
    
    # Identity
    module_id: str
    module_name: str
    description: str
    tier: str
    
    # Generation targets
    targets: List[GenerationTarget] = field(default_factory=list)
    
    # Dependencies
    dependencies: List[DependencyEdge] = field(default_factory=list)
    required_imports: Set[str] = field(default_factory=set)
    
    # Packets
    packets: List[PacketSpec] = field(default_factory=list)
    
    # Tests
    tests: List[TestSpec] = field(default_factory=list)
    
    # Wiring
    wiring: Optional[WiringSpec] = None
    
    # Interfaces
    inbound_routes: List[Dict[str, Any]] = field(default_factory=list)
    outbound_clients: List[Dict[str, Any]] = field(default_factory=list)
    
    # Environment
    required_env_vars: List[Dict[str, str]] = field(default_factory=list)
    optional_env_vars: List[Dict[str, str]] = field(default_factory=list)
    
    # Observability
    counters: List[str] = field(default_factory=list)
    histograms: List[str] = field(default_factory=list)
    
    # Generation context (for templates)
    context: Dict[str, Any] = field(default_factory=dict)
    
    def get_imports(self) -> List[str]:
        """Get all required imports as sorted list."""
        imports = set(self.required_imports)
        
        # Add standard L9 imports
        imports.add("import structlog")
        imports.add("from typing import Any, Dict, List, Optional")
        
        # Add dependency imports
        for dep in self.dependencies:
            imports.add(dep.to_import())
        
        # Add packet imports if needed
        if self.packets:
            imports.add("from memory.models import PacketEnvelopeIn")
        
        return sorted(imports)


# =============================================================================
# IR COMPILER
# =============================================================================


class MetaToIRCompiler:
    """
    Compiles MetaContract to ModuleIR.
    
    Transforms declarative spec into actionable code generation targets.
    """
    
    def __init__(self, repo_root: str = "/Users/ib-mac/Projects/L9"):
        """
        Initialize the compiler.
        
        Args:
            repo_root: Root path of the L9 repository
        """
        self.repo_root = Path(repo_root)
        logger.info("ir_compiler_initialized", repo_root=str(self.repo_root))
    
    def compile(self, contract: MetaContract) -> ModuleIR:
        """
        Compile a MetaContract to ModuleIR.
        
        Args:
            contract: Validated MetaContract instance
            
        Returns:
            ModuleIR ready for code generation
        """
        logger.info(
            "compiling_contract",
            module_id=contract.metadata.module_id,
        )
        
        ir = ModuleIR(
            module_id=contract.metadata.module_id,
            module_name=contract.metadata.name,
            description=contract.metadata.description,
            tier=contract.metadata.tier,
        )
        
        # Compile each aspect
        self._compile_generation_targets(contract, ir)
        self._compile_dependencies(contract, ir)
        self._compile_packets(contract, ir)
        self._compile_tests(contract, ir)
        self._compile_wiring(contract, ir)
        self._compile_interfaces(contract, ir)
        self._compile_environment(contract, ir)
        self._compile_observability(contract, ir)
        self._compile_context(contract, ir)
        
        logger.info(
            "contract_compiled",
            module_id=ir.module_id,
            target_count=len(ir.targets),
            dependency_count=len(ir.dependencies),
            test_count=len(ir.tests),
        )
        
        return ir
    
    def compile_from_yaml(self, yaml_path: str) -> ModuleIR:
        """
        Compile a YAML file to ModuleIR.
        
        Args:
            yaml_path: Path to YAML file
            
        Returns:
            ModuleIR ready for code generation
        """
        with open(yaml_path, 'r', encoding='utf-8') as f:
            raw = yaml.safe_load(f)
        
        contract = MetaContract(**raw)
        return self.compile(contract)
    
    # =========================================================================
    # PRIVATE COMPILATION METHODS
    # =========================================================================
    
    def _compile_generation_targets(
        self,
        contract: MetaContract,
        ir: ModuleIR
    ) -> None:
        """Extract generation targets from repo spec."""
        module_id = contract.metadata.module_id
        
        for file_path in contract.repo.allowed_new_files:
            # Replace {{module}} placeholder
            resolved_path = file_path.replace("{{module}}", module_id)
            
            # Determine target type from path pattern
            target_type = self._infer_target_type(resolved_path)
            
            # Determine template name
            template_name = self._infer_template_name(target_type)
            
            ir.targets.append(GenerationTarget(
                path=resolved_path,
                target_type=target_type,
                template_name=template_name,
                context={"module_id": module_id},
            ))
    
    def _compile_dependencies(
        self,
        contract: MetaContract,
        ir: ModuleIR
    ) -> None:
        """Extract dependencies from dependency spec."""
        module_id = contract.metadata.module_id
        
        for call in contract.dependencies.outbound_calls:
            ir.dependencies.append(DependencyEdge(
                source_module=module_id,
                target_module=call.module,
                interface=call.interface,
                endpoint=call.endpoint,
            ))
    
    def _compile_packets(
        self,
        contract: MetaContract,
        ir: ModuleIR
    ) -> None:
        """Extract packet specifications."""
        for packet_type in contract.packet_contract.emits:
            ir.packets.append(PacketSpec(
                packet_type=packet_type,
                required_metadata=list(contract.packet_contract.requires_metadata),
            ))
    
    def _compile_tests(
        self,
        contract: MetaContract,
        ir: ModuleIR
    ) -> None:
        """Extract test specifications from acceptance criteria."""
        module_id = contract.metadata.module_id
        
        # Positive tests
        for criterion in contract.acceptance.positive:
            if criterion.test:
                ir.tests.append(TestSpec(
                    test_file=f"tests/test_{module_id}_adapter.py",
                    test_function=criterion.test,
                    description=criterion.description,
                    is_positive=True,
                    acceptance_id=criterion.id,
                ))
        
        # Negative tests
        for criterion in contract.acceptance.negative:
            if criterion.test:
                ir.tests.append(TestSpec(
                    test_file=f"tests/test_{module_id}_adapter.py",
                    test_function=criterion.test,
                    description=criterion.description,
                    is_positive=False,
                    acceptance_id=criterion.id,
                ))
    
    def _compile_wiring(
        self,
        contract: MetaContract,
        ir: ModuleIR
    ) -> None:
        """Extract wiring specification."""
        module_id = contract.metadata.module_id
        rw = contract.runtime_wiring
        
        ir.wiring = WiringSpec(
            service=rw.service,
            startup_phase=rw.startup_phase,
            depends_on=list(rw.depends_on),
            blocks_startup_on_failure=rw.blocks_startup_on_failure,
            router_include=f"{module_id}_router" if contract.external_surface.exposes_http_endpoint else None,
            lifespan_init=f"init_{module_id}" if rw.startup_phase == "early" else None,
        )
    
    def _compile_interfaces(
        self,
        contract: MetaContract,
        ir: ModuleIR
    ) -> None:
        """Extract interface specifications."""
        for inbound in contract.interfaces.inbound:
            ir.inbound_routes.append(inbound.model_dump())
        
        for outbound in contract.interfaces.outbound:
            ir.outbound_clients.append(outbound.model_dump())
    
    def _compile_environment(
        self,
        contract: MetaContract,
        ir: ModuleIR
    ) -> None:
        """Extract environment variable specifications."""
        for env in contract.environment.required:
            ir.required_env_vars.append({
                "name": env.name.replace("{{MODULE}}", contract.metadata.module_id.upper()),
                "description": env.description,
            })
        
        for env in contract.environment.optional:
            ir.optional_env_vars.append({
                "name": env.name,
                "description": env.description,
                "default": env.default,
            })
    
    def _compile_observability(
        self,
        contract: MetaContract,
        ir: ModuleIR
    ) -> None:
        """Extract observability specifications."""
        module_id = contract.metadata.module_id
        obs = contract.observability
        
        if obs.metrics.enabled:
            for counter in obs.metrics.counters:
                ir.counters.append(counter.replace("{{module}}", module_id))
            for histogram in obs.metrics.histograms:
                ir.histograms.append(histogram.replace("{{module}}", module_id))
    
    def _compile_context(
        self,
        contract: MetaContract,
        ir: ModuleIR
    ) -> None:
        """Build generation context for templates."""
        ir.context = contract.to_generation_context()
        
        # Add computed values
        ir.context["imports"] = ir.get_imports()
        ir.context["packet_class_names"] = [p.class_name for p in ir.packets]
        ir.context["test_functions"] = [t.test_function for t in ir.tests]
        ir.context["has_http_endpoint"] = contract.external_surface.exposes_http_endpoint
        ir.context["has_webhook"] = contract.external_surface.exposes_webhook
        ir.context["has_tool"] = contract.external_surface.exposes_tool
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _infer_target_type(self, path: str) -> str:
        """Infer target type from file path pattern."""
        if path.endswith("_adapter.py"):
            return "adapter"
        elif path.endswith("_client.py"):
            return "client"
        elif path.startswith("api/routes/"):
            return "route"
        elif path.endswith("_ingest.py"):
            return "ingest"
        elif path.startswith("tests/"):
            if "_smoke" in path:
                return "smoke_test"
            else:
                return "test"
        elif path.endswith(".md"):
            return "doc"
        else:
            return "module"
    
    def _infer_template_name(self, target_type: str) -> str:
        """Infer template name from target type."""
        templates = {
            "adapter": "module_adapter.py.j2",
            "client": "module_client.py.j2",
            "route": "module_route.py.j2",
            "ingest": "module_ingest.py.j2",
            "test": "module_test.py.j2",
            "smoke_test": "module_smoke_test.py.j2",
            "doc": "module_doc.md.j2",
            "module": "module_base.py.j2",
        }
        return templates.get(target_type, "module_base.py.j2")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def compile_meta_to_ir(yaml_path: str) -> ModuleIR:
    """
    Compile a YAML meta specification to IR.
    
    Args:
        yaml_path: Path to YAML file
        
    Returns:
        ModuleIR ready for code generation
    """
    compiler = MetaToIRCompiler()
    return compiler.compile_from_yaml(yaml_path)


def compile_contract_to_ir(contract: MetaContract) -> ModuleIR:
    """
    Compile a MetaContract to IR.
    
    Args:
        contract: Validated MetaContract instance
        
    Returns:
        ModuleIR ready for code generation
    """
    compiler = MetaToIRCompiler()
    return compiler.compile(contract)

