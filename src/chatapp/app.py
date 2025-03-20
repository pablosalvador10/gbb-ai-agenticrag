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
from typing import List, Dict, Any

# Initialize logger
logger = get_logger()

# Set the correct tenant ID explicitly
TENANT_ID = "72f988bf-86f1-41af-91ab-2d7cd011db47"

async def get_credential():
    return DefaultAzureCredential()

class ApprovalTerminationStrategy(TerminationStrategy):
    """
    Ends the conversation if the Evaluator agent's last output includes the word 'approved'.
    """
    def __init__(self, agents: List[AzureAIAgent], maximum_iterations: int = 10):
        super().__init__(maximum_iterations=maximum_iterations)
        self.agents = agents

    async def should_agent_terminate(self, agent: AzureAIAgent, history: List[Dict[str, Any]]) -> bool:
        last_msg = history[-1]
        agent_name = last_msg.get("name", "")
        content = last_msg.get("content", "")
        return (agent_name in [a.name for a in self.agents]) and ("approved" in content.lower())

def _create_kernel_with_chat_completion(service_id: str) -> Kernel:
    """
    Creates a Semantic Kernel instance with an Azure OpenAI chat completion service.
    """
    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

    kernel = Kernel()
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    AZURE_OPENAI_API_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
    AZURE_AOAI_CHAT_MODEL_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_ID", "gpt-4o-standard")

    kernel.add_service(
        service=AzureChatCompletion(
            deployment_name=AZURE_AOAI_CHAT_MODEL_DEPLOYMENT,
            api_key=AZURE_OPENAI_KEY,
            endpoint=AZURE_OPENAI_API_ENDPOINT,
            api_version=AZURE_OPENAI_API_VERSION,
        )
    )
    return kernel

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

async def initialize_agents() -> AgentGroupChat:
    """
    Initializes the Azure AI agents and sets up the multi-agent chat.
    """
    creds = await get_credential()  # ✅ Corrected: Awaiting the async function

    async with AzureAIAgent.create_client(credential=creds) as project_client:
        ValidationInsightsAgentID = "asst_cflIDuNZR0fOpTJp59zhhDdn"
        DataRetrievalAgentID = "asst_BN7AvpIntZuA4s7nI2wQB4ri"

        dataretrieval_def = await project_client.agents.get_agent(agent_id=DataRetrievalAgentID)
        validation_def = await project_client.agents.get_agent(agent_id=ValidationInsightsAgentID)

        agent_retriever = AzureAIAgent(client=project_client, definition=dataretrieval_def)
        agent_evaluator = AzureAIAgent(client=project_client, definition=validation_def)

        chat = AgentGroupChat(
            agents=[agent_retriever, agent_evaluator],
            termination_strategy=ApprovalTerminationStrategy(
                maximum_iterations=10,
                agents=[agent_evaluator],
            ),
            selection_strategy=KernelFunctionSelectionStrategy(
                function=selection_function,
                kernel=_create_kernel_with_chat_completion("chat"),
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

async def main():
    """
    Main function to run the Streamlit app with an Azure Copilot-inspired chat interface.
    """
    st.set_page_config(page_title="Azure AI Chat Interface")
    
    st.markdown("""
        <style>
        .stApp {
            background: linear-gradient(135deg, #001f3f 0%, #0078d4 100%);
            color: #FFFFFF;
            font-family: 'Segoe UI', sans-serif;
        }
        /* Title styling */
        .title {
            text-align: center;
            font-size: 36px;
            margin-top: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # --- Page Title ---
    st.markdown(
        "<h2 style='text-align: center;'>R+D Chat 🤖</h2>", unsafe_allow_html=True
    )
   
    # --- Main Chat Container ---
    if "chat" not in st.session_state:
        # Initialize multi-agent chat once
        st.session_state.chat = await initialize_agents()
        st.session_state.chat_history = []

    respond_container = st.container(height=500)
    with respond_container:
        for message in st.session_state["chat_history"]:
            role, content = message["role"], message["content"]
            avatar = "🧑‍💻" if role == "user" else "🤖"
            with st.chat_message(role, avatar=avatar):
                st.markdown(content, unsafe_allow_html=True)

    prompt = st.chat_input("Type your message here...")
    if prompt:
        st.session_state["messages"].append({"role": "user", "content": prompt})
        st.session_state["chat_history"].append({"role": "user", "content": prompt})

        with respond_container:
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(prompt, unsafe_allow_html=True)

            with st.chat_message("assistant", avatar="🤖"):
                messages = st.session_state["messages"]
                await st.session_state.chat.add_chat_message(message=prompt)
                try:
                    async for content in st.session_state.chat.invoke():
                        agent_name = content.name or "Unknown"
                        agent_role = content.role.name
                        agent_output = content.content
                        st.session_state["chat_history"].append({"role": agent_role, "content": agent_output})
                except Exception as e:
                    st.error(f"Error: {e.message}")
                    logger.error(f"Error: {e.message}")
               
# --- Run the app ---
if __name__ == "__main__":
    asyncio.run(main())