import os
import asyncio
import streamlit as st
from azure.identity.aio import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError
from semantic_kernel import Kernel
from semantic_kernel.agents import AgentGroupChat
from semantic_kernel.agents.azure_ai import AzureAIAgent
from semantic_kernel.agents.strategies import TerminationStrategy, KernelFunctionSelectionStrategy
from semantic_kernel.functions import KernelFunctionFromPrompt
from utils.ml_logging import get_logger

logger = get_logger()

project_client = AzureAIAgent.create_client(credential=DefaultAzureCredential())

# ------------------------------
# 1. Define the Approval Termination Strategy
# ------------------------------
class ApprovalTerminationStrategy(TerminationStrategy):
    """
    Ends the conversation if the Evaluator agent's last output includes the word 'approved'.
    """
    def __init__(self, agents, maximum_iterations=10):
        super().__init__(maximum_iterations=maximum_iterations)
        self.agents = agents

    async def should_agent_terminate(self, agent, history) -> bool:
        last_msg = history[-1]
        # Use .get() for safe access to keys in the chat history dictionary
        agent_name = last_msg.get("name", "")
        content = last_msg.get("content", "")
        return (agent_name in [a.name for a in self.agents]) and ("approved" in content.lower())

###############################################################################
# 3) Creating a Kernel for the Selection Function
###############################################################################
def _create_kernel_with_chat_completion(service_id: str) -> Kernel:
    """
    Creates a Semantic Kernel instance with an Azure OpenAI chat completion service.
    Make sure you have environment variables for your Azure OpenAI keys/endpoint.
    """
    from semantic_kernel import Kernel
    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

    kernel = Kernel()
    # Retrieve environment vars (adjust to your naming)
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_API_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
    AZURE_AOAI_CHAT_MODEL_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_ID", "gpt-4o-standard")  

    # Register an Azure Chat Completion service in the kernel
    kernel.add_service(
        service=AzureChatCompletion(
            deployment_name=AZURE_AOAI_CHAT_MODEL_DEPLOYMENT,
            api_key=AZURE_OPENAI_KEY,
            endpoint=AZURE_OPENAI_API_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
        )
    )
    return kernel

# ------------------------------
# 3. Define the Selection Function Prompt
# ------------------------------
RETRIEVER_NAME = "ValidationInsightsAgent"
EVALUATOR_NAME = "DataRetrievalAgent"

selection_function = KernelFunctionFromPrompt(
    function_name="selection",
    prompt=f"""
Determine which participant takes the next turn in a conversation based on the most recent participant.
State only the name of the participant to take the next turn.
No participant should take more than one turn in a row.

Choose only from these participants:
- {RETRIEVER_NAME}
- {EVALUATOR_NAME}

Always follow these rules when selecting the next participant:
- {RETRIEVER_NAME} retrieves the document or relevant data for the query.
- After {RETRIEVER_NAME}, it is {EVALUATOR_NAME}'s turn to evaluate the content.
- After {EVALUATOR_NAME}, the workflow may terminate if 'approved'.

History:
{{{{$history}}}}
""",
)

# ------------------------------
# 4. Initialize Agents and Chat
# ------------------------------
async def initialize_agents():
# Create credential and project_client using async context managers

    # Agent IDs (adjust these to match your setup)
    ValidationInsightsAgentID = "asst_kdFT72VdYH0YpoG3tJ5lmoFy"
    DataRetrievalAgentID = "asst_Wo0GJ9MpmvkfRPNwllC7bYFS"

    dataretrieval_def = await project_client.agents.get_agent(agent_id=DataRetrievalAgentID)
    validation_def = await project_client.agents.get_agent(agent_id=ValidationInsightsAgentID)

    # Build agents
    agent_retriever = AzureAIAgent(client=project_client, definition=dataretrieval_def)
    agent_evaluator = AzureAIAgent(client=project_client, definition=validation_def)

    # Setup the multi-agent chat
    chat = AgentGroupChat(
        agents=[agent_retriever, agent_evaluator],
        termination_strategy=ApprovalTerminationStrategy(
            maximum_iterations=10,
            agents=[agent_evaluator],  # Evaluator decides final approval
        ),
        selection_strategy=KernelFunctionSelectionStrategy(
            function=selection_function,
            kernel=_create_kernel_with_chat_completion("chat"),
            # Custom result parser to ensure we return a valid agent name:
            result_parser=lambda result: (
                result.value.strip()
                if result.value and result.value.strip() in [RETRIEVER_NAME, EVALUATOR_NAME]
                else EVALUATOR_NAME
            ),
            agent_variable_name="agents",
            history_variable_name="history",
        ),
    )

    logger.info("Agents initialized successfully.")
    return chat

# ------------------------------
# 5. Build the Streamlit Interface
# ------------------------------
async def main():
    st.set_page_config(page_title="Multi-Agent Chat Interface", layout="wide")
    st.title("Multi-Agent Chat Interface")

    # Initialize session state if not already set
    if "chat" not in st.session_state:
        st.session_state.chat = await initialize_agents()
        st.session_state.history = []

    # Display chat history in a ChatGPT-like interface
    for message in st.session_state.history:
        role = message.get("role", "system")
        name = message.get("name", "System")
        content = message.get("content", "")
        with st.chat_message(role):
            st.markdown(f"**{name}:** {content}")

    # Get user input
    user_input = st.chat_input("Enter your message:")
    if user_input:
        # Append user message to chat history and display it
        st.session_state.history.append({"role": "user", "name": "User", "content": user_input})
        with st.chat_message("user"):
            st.markdown(f"**User:** {user_input}")

        # Add the user message to the multi-agent chat for processing
        await st.session_state.chat.add_chat_message(message=user_input)

        try:
            # Process agent responses
            async for content in st.session_state.chat.invoke():
                agent_name = content.name or "Unknown"
                agent_role = content.role.name
                agent_output = content.content

                st.session_state.history.append({
                    "role": agent_role,
                    "name": agent_name,
                    "content": agent_output
                })
                with st.chat_message(agent_role):
                    st.markdown(f"**{agent_name}:** {agent_output}")
        except Exception as ex:
            st.error(f"Error during chat invocation: {ex}")
            logger.error(f"Error during chat invocation: {ex}")

        # If conversation is complete, notify and reset chat
        if st.session_state.chat.is_complete:
            st.info("Conversation has been approved and terminated.")
            await st.session_state.chat.reset()
            st.session_state.history = []

if __name__ == "__main__":
    asyncio.run(main())
