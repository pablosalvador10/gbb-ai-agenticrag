from typing import Dict, Optional


class ToolRegistry:
    """
    A flexible registry for tool metadata. Each tool is identified by a tool_type
    (e.g., 'bing_grounding', 'azure_ai_search', 'fabric_data'), which maps to
    user-friendly titles and optional descriptions.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Dict[str, str]] = {}

    def register_tool(self, tool_type: str, title: str, description: str = "") -> None:
        """
        Register or update a tool in the registry.

        :param tool_type: Unique identifier for the tool (e.g. 'bing_grounding').
        :param title: A short, user-friendly title (e.g. '🔍 searching bing').
        :param description: Optional longer description about the tool usage.
        """
        self._tools[tool_type] = {"title": title, "description": description}

    def get_tool_title(self, tool_type: str) -> str:
        """
        Retrieve the user-friendly title for a tool. If not found, falls back
        to a generic label.

        :param tool_type: The tool type (e.g. 'bing_grounding').
        :return: A string representing the tool's title.
        """
        if tool_type in self._tools:
            return self._tools[tool_type].get("title", f"🛠 calling {tool_type}")
        return f"🛠 calling {tool_type}"

    def get_tool_description(self, tool_type: str) -> str:
        """
        Retrieve a longer description for a tool if available.

        :param tool_type: The tool identifier.
        :return: The description string, or empty if not found.
        """
        if tool_type in self._tools:
            return self._tools[tool_type].get("description", "")
        return ""
