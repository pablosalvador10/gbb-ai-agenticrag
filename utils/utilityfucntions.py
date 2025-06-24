def print_agent_summary(agent):
    """
    Print a comprehensive summary of the created AI agent.

    This function outputs a formatted summary that includes the agent's name, ID,
    metadata details, and the raw dictionary representation of the agent. It assumes
    that the `agent` object has the following attributes:
      - 'name': The name of the agent.
      - 'id': The unique identifier for the agent.
      - 'metadata': A dictionary containing additional details about the agent.

    Parameters:
        agent: An object representing the AI agent.

    Returns:
        None
    """
    print("\n=== Agent Creation Summary ===")
    print(f"Agent Name    : {getattr(agent, 'name', 'N/A')}")
    print(f"Agent ID      : {agent.id}")
    print("Agent Metadata:")
    for key, value in agent.metadata.items():
        print(f"  - {key}: {value}")
