# toolset.py

import logging
import os
from typing import Any, List, Optional

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AzureAISearchTool,
    BingGroundingTool,
    FabricTool,
    FileSearchTool,
    FunctionTool,
    SharepointTool,
    ToolSet,
)

from src.azureaiagents.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)


class LoggingToolSet(ToolSet):
    """
    Subclass of ToolSet that logs function calls for debugging.
    Prints two lines per function call:
      1) function name + arguments
      2) function name + output
    """

    def execute_tool_calls(self, tool_calls):
        # Print inputs
        for call in tool_calls:
            if hasattr(call, "function") and call.function:
                fn_name = call.function.name
                fn_args = call.function.arguments
                print(f"{fn_name} inputs > {fn_args} (id:{call.id})")

        # Execute via parent method
        raw_outputs = super().execute_tool_calls(tool_calls)

        # Print outputs
        for item in raw_outputs:
            print(f"output > {item['output']}")
        return raw_outputs


class FlexibleToolsetBuilder:
    """
    Builds a LoggingToolSet for an Azure AI Agent, while also registering each tool
    in the provided ToolRegistry for consistent metadata usage in conversation handling.
    """

    def __init__(
        self, project_client: AIProjectClient, registry: Optional[ToolRegistry] = None
    ):
        """
        :param project_client: The AIProjectClient to retrieve connections or build tools.
        :param registry: A pre-initialized ToolRegistry or None to create a new one.
        """
        self.project_client = project_client
        self.registry = registry if registry else ToolRegistry()

    def build_toolset(
        self,
        include_bing: bool = True,
        include_azure_search: bool = True,
        include_sharepoint: bool = False,
        include_fabric: bool = False,
        include_file_search: bool = False,
        custom_function_list: Optional[List[dict]] = None,
    ) -> LoggingToolSet:
        """
        Builds the LoggingToolSet with optional tools (Bing, Azure AI Search, SharePoint, Fabric, FileSearch,
        plus custom function definitions).

        :param include_bing: Whether to add BingGroundingTool.
        :param include_azure_search: Whether to add AzureAISearchTool.
        :param include_sharepoint: Whether to add SharePointTool.
        :param include_fabric: Whether to add FabricTool.
        :param include_file_search: Whether to add FileSearchTool.
        :param custom_function_list: A list of function definitions for FunctionTool.
                                     Example: [{'name': 'fetch_weather', 'description': '...'}, ...]
        :return: A LoggingToolSet with the chosen tools added.
        """
        toolset = LoggingToolSet()

        # 1) Bing Search
        if include_bing:
            bing_conn_name = os.getenv("TOOL_CONNECTION_NAME_BING")
            if bing_conn_name:
                bing_conn = self.project_client.connections.get(
                    connection_name=bing_conn_name
                )
                bing_tool = BingGroundingTool(connection_id=bing_conn.id)
                toolset.add(bing_tool)
                self.registry.register_tool(
                    tool_type="bing_grounding",
                    title="🔍 searching bing",
                    description="Leverages Bing to retrieve real-time public data.",
                )

        # 2) Azure AI Search
        if include_azure_search:
            search_conn_name = os.getenv("TOOL_CONNECTION_NAME_SEARCH")
            if search_conn_name:
                search_conn = self.project_client.connections.get(
                    connection_name=search_conn_name
                )
                azure_search_tool = AzureAISearchTool(
                    index_connection_id=search_conn.id,
                    index_name=os.getenv(
                        "AZURE_AI_SEARCH_INDEX_NAME", "ai-agentic-index"
                    ),
                )
                toolset.add(azure_search_tool)
                self.registry.register_tool(
                    tool_type="azure_ai_search",
                    title="🔎 enterprise search",
                    description="Queries an Azure Cognitive Search index for internal data.",
                )

        # 3) SharePoint
        if include_sharepoint:
            sharepoint_conn_name = os.getenv("TOOL_CONNECTION_NAME_SHAREPOINT")
            if sharepoint_conn_name:
                sp_conn = self.project_client.connections.get(
                    connection_name=sharepoint_conn_name
                )
                sharepoint_tool = SharepointTool(connection_id=sp_conn.id)
                toolset.add(sharepoint_tool)
                self.registry.register_tool(
                    tool_type="sharepoint_search",
                    title="📂 sharepoint docs",
                    description="Retrieves documents stored in SharePoint.",
                )

        # 4) Fabric
        if include_fabric:
            fabric_conn_name = os.getenv("TOOL_CONNECTION_NAME_FABRIC")
            if fabric_conn_name:
                fabric_conn = self.project_client.connections.get(
                    connection_name=fabric_conn_name
                )
                fabric_tool = FabricTool(connection_id=fabric_conn.id)
                toolset.add(fabric_tool)
                self.registry.register_tool(
                    tool_type="fabric_data",
                    title="🔧 fabric data",
                    description="Retrieves and analyzes data from Microsoft Fabric.",
                )

        # 5) File Search
        if include_file_search:
            file_conn_name = os.getenv("TOOL_CONNECTION_NAME_FILESEARCH")
            if file_conn_name:
                fs_conn = self.project_client.connections.get(
                    connection_name=file_conn_name
                )
                file_search_tool = FileSearchTool(connection_id=fs_conn.id)
                toolset.add(file_search_tool)
                self.registry.register_tool(
                    tool_type="file_search",
                    title="📁 file search",
                    description="Searches documents in connected file stores.",
                )

        # 6) Custom Function Tools
        if custom_function_list:
            # Typically, you'd define your custom function schema (args, description, etc.)
            # For example, a list of dicts describing each function
            custom_function_tool = FunctionTool(custom_function_list)
            toolset.add(custom_function_tool)
            # Optionally register each function individually (or as one group)
            for fn_def in custom_function_list:
                fn_name = fn_def.get("name", "custom_function")
                self.registry.register_tool(
                    tool_type=fn_name,
                    title=f"⚙️ {fn_name}",
                    description=fn_def.get("description", "A custom function."),
                )

        return toolset
