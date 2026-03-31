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
import re
from pathlib import Path
from typing import Optional, Tuple, Set
from core.logger_config import setup_agent_logger
from core.log_decorators import log_agent_call
import config


# Get logger for agent operations
logger = setup_agent_logger(__name__)


# Agent types
AGENT_TYPES = {
    'story': 'Story generation agent',
    'shots': 'Shots prompt engineering agent',
}


class AgentLoader:
    """Load and manage agent system prompts from the agents folder."""

    def __init__(self, agents_dir: str = None):
        """
        Initialize the agent loader.

        Args:
            agents_dir: Path to the agents directory (default: "agents" in project root)
        """
        if agents_dir is None:
            self.agents_dir = Path(config.PROJECT_ROOT) / "agents"
        else:
            self.agents_dir = Path(agents_dir)
        
        logger.debug(f"AgentLoader initialized with directory: {self.agents_dir}")

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
        # Support both flat files and agents design nested in subdirectories
        for item in agent_dir.iterdir():
            # Skip hidden folders and partial/internal folders
            if item.is_dir():
                if item.name.startswith(("_", ".")) or item.name in ["base", "styles", "contexts", "cameras", "common"]:
                    continue
                
                for file in item.glob("*.md"):
                    # Skip internal/partial files starting with underscore
                    if file.name.startswith("_"):
                        continue
                    # Format as category/filename (e.g., documentary/default)
                    agents.append(f"{item.name}/{file.name[:-3]}")
            
            elif item.is_file() and item.suffix == ".md":
                # Skip internal/partial files starting with underscore
                if item.name.startswith(("_", ".")):
                    continue
                agents.append(item.stem)

                    
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

        # Support composite agent names (comma-separated)
        if "," in agent_name:
            names = [n.strip() for n in agent_name.split(",")]
            contents = []
            for name in names:
                contents.append(self.load_prompt(agent_type, name))
            return "\n\n".join(contents)

        agent_file = self.agents_dir / agent_type / f"{agent_name}.md"

        if not agent_file.exists():
            available = self.list_agents(agent_type)
            raise FileNotFoundError(
                f"Agent not found: {agent_file}\n"
                f"Available {agent_type} agents: {available}"
            )

        with open(agent_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Process includes recursively
        # Use parent folder of agent_file as initial base_dir
        return self._process_includes(agent_type, content, {str(agent_file.resolve())}, base_dir=agent_file.parent)

    def _process_includes(self, agent_type: str, content: str, seen_paths: Set[str] = None, base_dir: Path = None) -> str:
        """
        Process {{include:path}} directives in the content.
        
        Args:
            agent_type: Type of agent
            content: The prompt content to process
            seen_paths: Set of already seen file paths (for circular dependency protection)
            base_dir: Base directory for resolving includes (defaults to agents_dir/agent_type)
            
        Returns:
            Content with inclusions resolved
        """
        if seen_paths is None:
            seen_paths = set()
        
        if base_dir is None:
            base_dir = self.agents_dir / agent_type

        include_pattern = re.compile(r'\{\{include:(.+?)\}\}')
        
        def replace_include(match):
            include_name = match.group(1).strip()
            
            # Resolve the include path
            # Strategy:
            # 1. If it contains a slash, try relative to agents_dir root (global include)
            # 2. Try relative to the current file's directory (sibling include)
            # 3. Try relative to search subdirectories (e.g. _base, _styles, _contexts)
            # 4. Try relative to the agent_type root (standard include)
            
            paths_to_try = []
            if "/" in include_name:
                paths_to_try.append(self.agents_dir / f"{include_name}.md")
            
            # 1. Direct path in base_dir
            paths_to_try.append(base_dir / f"{include_name}.md")
            
            # 2. Search in subdirectories of base_dir (e.g., _base, _contexts)
            if base_dir.exists():
                for item in base_dir.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        paths_to_try.append(item / f"{include_name}.md")
            
            # 3. Direct path in agent_type root
            agent_type_dir = self.agents_dir / agent_type
            paths_to_try.append(agent_type_dir / f"{include_name}.md")
            
            # 4. Search in subdirectories of agent_type root
            if agent_type_dir.exists() and agent_type_dir != base_dir:
                for item in agent_type_dir.iterdir():
                    if item.is_dir() and not item.name.startswith("."):
                        paths_to_try.append(item / f"{include_name}.md")

            include_file = None
            for p in paths_to_try:
                if p.exists():
                    include_file = p
                    break

            if not include_file:
                logger.error(f"Include file not found: {include_name} (Tried: {[str(p) for p in paths_to_try]})")
                return f"<!-- Include not found: {include_name} -->"


            abs_path = str(include_file.resolve())
            
            if abs_path in seen_paths:
                logger.warning(f"Circular dependency detected for: {abs_path}")
                return f"<!-- Circular dependency detected: {include_name} -->"
            
            with open(include_file, 'r', encoding='utf-8') as f:
                include_content = f.read()
            
            # Recursive call with new base_dir (parent of current include)
            new_seen_paths = seen_paths | {abs_path}
            return self._process_includes(agent_type, include_content, new_seen_paths, base_dir=include_file.parent)

        return include_pattern.sub(replace_include, content)

    def save_prompt(self, agent_type: str, agent_name: str, content: str):
        """
        Save/update a system prompt for a specific agent.

        Args:
            agent_type: Type of agent ('story', 'narration', 'image', 'video')
            agent_name: Name of the agent
            content: The new system prompt content
        """
        if agent_type not in AGENT_TYPES:
            raise ValueError(f"Unknown agent type: {agent_type}. Must be one of: {list(AGENT_TYPES.keys())}")

        agent_dir = self.agents_dir / agent_type
        os.makedirs(agent_dir, exist_ok=True)
        
        agent_file = agent_dir / f"{agent_name}.md"
        
        with open(agent_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Saved agent prompt: {agent_file}")

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


def list_agents() -> list:
    """
    List all available agents across all types.
    Used by the Web UI API.

    Returns:
        List of dictionaries with agent info
    """
    loader = get_agent_loader()
    all_agents = []
    
    for agent_type in AGENT_TYPES.keys():
        agents = loader.list_agents(agent_type)
        for agent_id in agents:
            all_agents.append({
                "id": agent_id,
                "name": agent_id.replace('_', ' ').title(),
                "type": agent_type
            })
            
    return all_agents


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
