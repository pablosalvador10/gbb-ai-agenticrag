import os
import asyncio
import streamlit as st
import traceback
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel import Kernel
from semantic_kernel.agents import AgentGroupChat
from semantic_kernel.agents.azure_ai import AzureAIAgent
from semantic_kernel.agents.strategies import (
    TerminationStrategy,
    KernelFunctionSelectionStrategy,
)
from semantic_kernel.functions import KernelFunctionFromPrompt
from utils.ml_logging import get_logger
from dotenv import load_dotenv

load_dotenv()
logger = get_logger()

RETRIEVER_NAME = "ValidationInsightsAgent"
EVALUATOR_NAME = "DataRetrievalAgent"

# --- Termination Strategy ---
class ApprovalTerminationStrategy(TerminationStrategy):
    def __init__(self, agents, maximum_iterations=10):
        super().__init__(maximum_iterations=maximum_iterations)
        self.agents = agents

    async def should_agent_terminate(self, agent, history) -> bool:
        last_msg = history[-1]
        return (last_msg.name in [a.name for a in self.agents]) and ("approved" in last_msg.content.lower())

# --- Kernel Creation ---
def create_kernel() -> Kernel:
    from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

    kernel = Kernel()
    kernel.add_service(
        AzureChatCompletion(
            deployment_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_ID"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        )
    )
    return kernel

# --- Agent Selection Function ---
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
    - {RETRIEVER_NAME} retrieving the document or relevant data the query.
    - After {RETRIEVER_NAME}, it is {EVALUATOR_NAME}'s turn to evaluate the content.
    - After {EVALUATOR_NAME}, the workflow may terminate if 'approved'.

    You MUST respond with ONLY the exact participant's name. No extra words or characters.

    History:
    {{{{$history}}}}
    """,
    )

# --- Async Main ---
async def main():
    st.set_page_config(page_title="Azure AI Chat Interface")
    st.markdown("<h2 style='text-align: center;'>R+D Chat 🤖</h2>", unsafe_allow_html=True)
    async with (
        DefaultAzureCredential() as creds,
        AzureAIAgent.create_client(credential=creds) as client,
    ):

        retriever_def = await client.agents.get_agent("asst_cflIDuNZR0fOpTJp59zhhDdn")
        evaluator_def = await client.agents.get_agent("asst_BN7AvpIntZuA4s7nI2wQB4ri")

        agent_retriever = AzureAIAgent(client=client, definition=retriever_def)
        agent_evaluator = AzureAIAgent(client=client, definition=evaluator_def)

        st.session_state.chat = AgentGroupChat(
            agents=[agent_retriever, agent_evaluator],
            termination_strategy=ApprovalTerminationStrategy(agents=[agent_evaluator]),
            selection_strategy=KernelFunctionSelectionStrategy(
                function=selection_function,
                kernel=create_kernel(),
                result_parser=lambda result: str(result.value[0]) if result.value else EVALUATOR_NAME,
                agent_variable_name="agents",
                history_variable_name="history",
            ),
        )
        st.session_state.chat_history = []

        chat_container = st.container(height=500)

        with chat_container:
            for msg in st.session_state.chat_history:
                avatar = "🧑‍💻" if msg["role"] == "user" else msg.get("avatar", "🤖")
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"], unsafe_allow_html=True)

        prompt = st.chat_input("Type your message here...")

        if prompt:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user", avatar="🧑‍💻"):
                    st.markdown(prompt, unsafe_allow_html=True)

                await st.session_state.chat.add_chat_message(prompt)

                try:
                    async for response in st.session_state.chat.invoke():
                        st.spinner("Thinking...")
                        agent_name = response.name or "Agent"
                        avatar = "📖" if agent_name == RETRIEVER_NAME else "🔎" if agent_name == EVALUATOR_NAME else "🤖"
                        
                        with st.expander(f"**{agent_name}** is thinking..."):
                            with st.chat_message("assistant", avatar=avatar):
                                st.markdown(f"**{agent_name}:** {response.content}")

                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": f"**{agent_name}:** {response.content}",
                                "avatar": avatar
                            })

                except Exception as e:
                    detailed_traceback = traceback.format_exc()
                    st.error(f"Error: {e}\n\nTraceback:\n```\n{detailed_traceback}\n```")
                    logger.error(f"Chat error: {e}\nDetailed traceback:\n{detailed_traceback}")



if __name__ == "__main__":
    asyncio.run(main())
