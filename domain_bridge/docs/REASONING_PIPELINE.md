# Reasoning Pipeline

## Overview

The reasoning pipeline has 5 stages:

## Stage 1: Ingestion & Validation

- Receive PacketEnvelope
- Validate structure and fields
- Route to appropriate handler

## Stage 2: Context Enrichment

- Query world model for causal factors
- Retrieve episodic memory
- Build domain-specific context

## Stage 3: Tensor Scoring

- Batch entity scoring requests
- Call TensorAIOS layer
- Process embeddings
- Detect anomalies

## Stage 4: Multi-Modal Reasoning

Apply reasoning modes in parallel:

- **Symbolic**: Domain business rules
- **Causal**: World model causal logic
- **Analogical**: Cross-domain patterns
- **Reflective**: Self-critique

## Stage 5: Decision Synthesis

- Combine reasoning outputs
- Resolve conflicts (weighted voting)
- Check governance
- Format response

## Confidence Calculation

Final confidence = weighted average of mode confidences:

- Symbolic: 0.30
- Causal: 0.25
- Analogical: 0.20
- Reflective: 0.25
