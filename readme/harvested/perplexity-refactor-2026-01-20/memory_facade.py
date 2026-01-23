@dataclass
class MemorySubstrateService:
    packets: PacketService
    search: SemanticSearchService
    traces: ReasoningTraceService
    checkpoints: CheckpointService
    knowledge: KnowledgeService
