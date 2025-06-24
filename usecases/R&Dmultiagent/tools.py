import json
import logging
from datetime import timedelta
from azure.core.exceptions import HttpResponseError
from semantic_kernel.agents.azure_ai import AzureAIAgent, AzureAIAgentSettings
from semantic_kernel.agents.open_ai.run_polling_options import RunPollingOptions


def process_citations(content) -> str:
    """
    Return content plus any citations in Markdown format, ensuring no duplicated citations.

    Args:
        content: The content object retrieved from the agent.

    Returns:
        A string containing the agent's text plus any unique citations in Markdown format.
    """
    combined_content = content.content

    if hasattr(content, "items"):
        unique_citation_set = set()
        for item in content.items:
            if item.content_type == "annotation" and item.url:
                unique_citation_set.add((item.quote, item.url))

        if unique_citation_set:
            combined_content += "\n\n**Citations:**\n"
            for quote, url in unique_citation_set:
                combined_content += f"- **Quote**: {quote}  \n"
                combined_content += f"  **URL**: [{url}]({url})\n"

    return combined_content


async def run_agent(project_client, agent_id: str, user_input: str) -> str:
    """
    Runs the data-retrieval agent to process a single user input and returns
    a single string containing both user input and the agent responses.

    Args:
        project_client: A client object for interacting with Azure AI project resources.
        agent_id: The ID of the agent to retrieve from project_client.
        user_input: A string representing the user's query.

    Returns:
        A single string with user input and each agent response (enriched with citations).
    """
    # Initialize the string to include the user query
    responses = ""

    # Fetch the agent definition using the provided ID
    agent_definition = await project_client.agents.get_agent(agent_id)

    # Create the AzureAIAgent instance
    agent = AzureAIAgent(
        client=project_client,
        definition=agent_definition,
        polling_options=RunPollingOptions(run_polling_interval=timedelta(seconds=1)),
    )

    # Create a new conversation thread
    thread = await project_client.agents.create_thread()

    try:
        # Send user input to the agent
        await agent.add_chat_message(thread_id=thread.id, message=user_input)

        # Stream non-tool responses from the agent
        async for content in agent.invoke(thread_id=thread.id):
            enriched_content = process_citations(content)
            responses += f"\n🤖 **{agent.name}** (Azure AI Agent ID {agent_id}): {enriched_content}"

    except HttpResponseError as e:
        try:
            error_json = json.loads(e.response.content)
            message = error_json.get("Message", "No error message found")
            logging.error(f"❌ **HTTP Error:** {message}")
            responses += f"\n❌ **HTTP Error:** {message}"
        except json.JSONDecodeError:
            logging.error(f"❌ **Non-JSON Error Content:** {e.response.content}")
            responses += f"\n❌ **Non-JSON Error Content:** {e.response.content}"

    return responses, thread.id
