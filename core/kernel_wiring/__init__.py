"""
L9 Kernel Wiring Module

Provides accessor functions for each of the 10 consolidated kernels.
Imports are lazy to avoid circular dependency issues during testing.
"""

# Lazy imports - functions are imported when accessed
__all__ = [
    "apply_identity_to_response",
    "get_active_mode",
    "get_allowed_event_types",
    "get_allowed_transitions",
    "get_default_channel",
    "get_dev_policies",
    "get_execution_state_machine",
    "get_identity_profile",
    "get_memory_layers_config",
    "get_output_verbosity",
    "get_packet_protocol",
    "get_reasoning_mode",
    "get_safety_policies",
    "get_worldmodel_schema",
    "is_destructive_action",
    "is_topic_blocked",
    "should_checkpoint_now",
    "should_enable_meta_cognition",
]


def __getattr__(name):
    """Lazy import accessor functions."""
    if name == "get_active_mode":
        from .master_wiring import get_active_mode

        return get_active_mode
    if name == "get_identity_profile":
        from .identity_wiring import get_identity_profile

        return get_identity_profile
    if name == "apply_identity_to_response":
        from .identity_wiring import apply_identity_to_response

        return apply_identity_to_response
    if name == "get_reasoning_mode":
        from .cognitive_wiring import get_reasoning_mode

        return get_reasoning_mode
    if name == "should_enable_meta_cognition":
        from .cognitive_wiring import should_enable_meta_cognition

        return should_enable_meta_cognition
    if name == "get_output_verbosity":
        from .behavioral_wiring import get_output_verbosity

        return get_output_verbosity
    if name == "is_topic_blocked":
        from .behavioral_wiring import is_topic_blocked

        return is_topic_blocked
    if name == "get_memory_layers_config":
        from .memory_wiring import get_memory_layers_config

        return get_memory_layers_config
    if name == "should_checkpoint_now":
        from .memory_wiring import should_checkpoint_now

        return should_checkpoint_now
    if name == "get_worldmodel_schema":
        from .worldmodel_wiring import get_worldmodel_schema

        return get_worldmodel_schema
    if name == "get_execution_state_machine":
        from .execution_wiring import get_execution_state_machine

        return get_execution_state_machine
    if name == "get_allowed_transitions":
        from .execution_wiring import get_allowed_transitions

        return get_allowed_transitions
    if name == "get_safety_policies":
        from .safety_wiring import get_safety_policies

        return get_safety_policies
    if name == "is_destructive_action":
        from .safety_wiring import is_destructive_action

        return is_destructive_action
    if name == "get_dev_policies":
        from .developer_wiring import get_dev_policies

        return get_dev_policies
    if name == "get_packet_protocol":
        from .packet_protocol_wiring import get_packet_protocol

        return get_packet_protocol
    if name == "get_allowed_event_types":
        from .packet_protocol_wiring import get_allowed_event_types

        return get_allowed_event_types
    if name == "get_default_channel":
        from .packet_protocol_wiring import get_default_channel

        return get_default_channel
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
