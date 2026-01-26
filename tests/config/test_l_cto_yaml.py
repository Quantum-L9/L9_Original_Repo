# test_l_cto_yaml.py

import yaml

from agents.l_cto import LCTOAgent
from runtime.kernel_loader import KernelLoader


def test_l_cto_yaml_valid():
    """Verify L-CTO-Agent.yaml is valid YAML"""
    with open("config/agents/L-CTO-Agent.yaml") as f:
        config = yaml.safe_load(f)
    assert config["agent_id"] == "l-cto"
    assert config["model"]["provider"] == "anthropic"
    assert len(config["tools"]) > 0
    print("✅ L-CTO-Agent.yaml valid")


def test_research_overlay_valid():
    """Verify L-CTO-Research-Overlay.yaml is valid YAML"""
    with open("config/agents/L-CTO-Research-Overlay.yaml") as f:
        config = yaml.safe_load(f)
    assert config["agent_id"] == "l-cto-research"
    assert config["baseline_agent"] == "L-CTO-Agent.yaml"
    print("✅ L-CTO-Research-Overlay.yaml valid")


async def test_kernel_absorption():
    """Verify kernels absorb correctly"""
    kernel_loader = KernelLoader(
        kernel_dir="private/kernels/00_system",
        boot_overlay_path="config/boot_overlay.yaml",
    )

    agent = LCTOAgent(
        config_path="config/agents/L-CTO-Agent.yaml", kernel_loader=kernel_loader
    )

    await agent.absorb_kernel()
    assert len(agent.kernels) == 10
    assert agent.kernel_state is not None
    print("✅ Kernel absorption successful")


async def test_tool_registry():
    """Verify tools match governance tiers"""
    with open("config/agents/L-CTO-Agent.yaml") as f:
        config = yaml.safe_load(f)

    t1_tools = [t for t in config["tools"] if t["tier"] == "T1"]
    t2_tools = [t for t in config["tools"] if t["tier"] == "T2"]
    t3_tools = [t for t in config["tools"] if t["tier"] == "T3"]

    # Verify tier rules
    for tool in t1_tools:
        assert not tool["approval_required"]
    for tool in t2_tools:
        assert tool["approval_required"]
        assert tool.get("hitl_approval")
    for tool in t3_tools:
        assert tool["approval_required"]
        assert tool.get("igor_approval_required")

    print(
        f"✅ Tool registry valid: {len(t1_tools)} T1, {len(t2_tools)} T2, {len(t3_tools)} T3"
    )


# Run all tests
if __name__ == "__main__":
    test_l_cto_yaml_valid()
    test_research_overlay_valid()
    asyncio.run(test_kernel_absorption())
    asyncio.run(test_tool_registry())
    print("\n✅ ALL TESTS PASSED - L-CTO YAML Ready for Production")
