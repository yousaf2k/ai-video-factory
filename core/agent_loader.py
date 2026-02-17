"""
Agent Loader - Load and manage system prompts for LLM agents.

Agent folder structure:
agents/
├── story/
│   ├── default.md
│   ├── dramatic.md
│   └── documentary.md
├── narration/
│   ├── default.md
│   └── documentary.md
├── image/
│   ├── default.md
│   └── artistic.md
└── video/
    ├── default.md
    └── cinematic.md
"""
import os
from pathlib import Path
from typing import Optional, Tuple
from core.logger_config import setup_agent_logger
from core.log_decorators import log_agent_call


# Get logger for agent operations
logger = setup_agent_logger(__name__)


# Agent types
AGENT_TYPES = {
    'story': 'Story generation agent',
    'narration': 'Narration script agent',
    'image': 'Image prompt engineering agent',
    'video': 'Video motion/camera agent'
}


class AgentLoader:
    """Load and manage agent system prompts from the agents folder."""

    def __init__(self, agents_dir: str = "agents"):
        """
        Initialize the agent loader.

        Args:
            agents_dir: Path to the agents directory (default: "agents")
        """
        self.agents_dir = Path(agents_dir)

    def list_agents(self, agent_type: str) -> list:
        """
        List all available agents for a given type.

        Args:
            agent_type: Type of agent ('story', 'narration', 'image', 'video')

        Returns:
            List of agent names (without .md extension)
        """
        if agent_type not in AGENT_TYPES:
            raise ValueError(f"Unknown agent type: {agent_type}. Must be one of: {list(AGENT_TYPES.keys())}")

        agent_dir = self.agents_dir / agent_type
        if not agent_dir.exists():
            return []

        agents = []
        for file in agent_dir.glob("*.md"):
            agents.append(file.stem)
        return sorted(agents)

    def load_prompt(self, agent_type: str, agent_name: str = "default") -> str:
        """
        Load a system prompt for a specific agent.

        Args:
            agent_type: Type of agent ('story', 'narration', 'image', 'video')
            agent_name: Name of the agent (default: "default")

        Returns:
            The system prompt as a string

        Raises:
            FileNotFoundError: If the agent file doesn't exist
            ValueError: If the agent_type is invalid
        """
        if agent_type not in AGENT_TYPES:
            raise ValueError(f"Unknown agent type: {agent_type}. Must be one of: {list(AGENT_TYPES.keys())}")

        agent_file = self.agents_dir / agent_type / f"{agent_name}.md"

        if not agent_file.exists():
            available = self.list_agents(agent_type)
            raise FileNotFoundError(
                f"Agent not found: {agent_file}\n"
                f"Available {agent_type} agents: {available}"
            )

        with open(agent_file, 'r', encoding='utf-8') as f:
            return f.read()

    def format_prompt(self, agent_type: str, user_input: str, agent_name: str = "default") -> str:
        """
        Load and format a system prompt with user input.

        Args:
            agent_type: Type of agent ('story', 'narration', 'image', 'video')
            user_input: The user input to insert into the prompt
            agent_name: Name of the agent (default: "default")

        Returns:
            Formatted prompt with user input inserted
        """
        prompt = self.load_prompt(agent_type, agent_name)
        return prompt.replace("{USER_INPUT}", user_input)

    def get_agent_info(self, agent_type: str) -> dict:
        """
        Get information about available agents for a type.

        Args:
            agent_type: Type of agent

        Returns:
            Dict with 'type', 'description', and 'available_agents'
        """
        return {
            'type': agent_type,
            'description': AGENT_TYPES.get(agent_type, ''),
            'available_agents': self.list_agents(agent_type)
        }

    def print_all_agents(self):
        """Print a summary of all available agents."""
        print("\n" + "="*60)
        print("AVAILABLE AGENTS")
        print("="*60)

        for agent_type in AGENT_TYPES.keys():
            agents = self.list_agents(agent_type)
            print(f"\n{agent_type.upper()}: {AGENT_TYPES[agent_type]}")
            if agents:
                for agent in agents:
                    marker = " [DEFAULT]" if agent == "default" else ""
                    print(f"  - {agent}{marker}")
            else:
                print(f"  (no agents found)")

        print("\n" + "="*60)


# Global agent loader instance
_agent_loader = None


def get_agent_loader() -> AgentLoader:
    """Get the global agent loader instance."""
    global _agent_loader
    if _agent_loader is None:
        _agent_loader = AgentLoader()
    return _agent_loader


def load_agent_prompt(agent_type: str, user_input: str, agent_name: str = "default") -> str:
    """
    Convenience function to load and format an agent prompt.

    Args:
        agent_type: Type of agent ('story', 'narration', 'image', 'video')
        user_input: The user input to insert into the prompt
        agent_name: Name of the agent (default: "default")

    Returns:
        Formatted prompt ready to send to LLM
    """
    loader = get_agent_loader()
    return loader.format_prompt(agent_type, user_input, agent_name)


if __name__ == "__main__":
    # Test: list all available agents
    loader = AgentLoader()
    loader.print_all_agents()

    # Test: load a prompt
    print("\n" + "="*60)
    print("EXAMPLE: Loading story/default agent")
    print("="*60)
    prompt = loader.format_prompt("story", "A cat dancing in the rain")
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
