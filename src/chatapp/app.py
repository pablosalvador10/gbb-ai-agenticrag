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
    def __init__(self, agents, maximum_iterations=3):
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

def get_agent_style(agent_name):
    if agent_name == RETRIEVER_NAME:
        # Light blue for the Retriever agent
        return "background-color: #E3F2FD; border-radius: 10px; padding: 10px; margin: 5px 0;"
    elif agent_name == EVALUATOR_NAME:
        # Light teal for the Evaluator agent
        return "background-color: #E0F7FA; border-radius: 10px; padding: 10px; margin: 5px 0;"
    else:
        # Default light gray for other agents
        return "background-color: #F5F5F5; border-radius: 10px; padding: 10px; margin: 5px 0;"

# --- Async Main ---
async def main():
    st.set_page_config(page_title="Azure AI Chat Interface")
    st.markdown("<h2 style='text-align: center;'>R+D Chat 🤖</h2>", unsafe_allow_html=True)
    async with (
        DefaultAzureCredential() as creds,
        AzureAIAgent.create_client(credential=creds) as client,
    ):
        ValidationInsightsAgentID = "asst_cflIDuNZR0fOpTJp59zhhDdn"
        DataRetrievalAgentID = "asst_BN7AvpIntZuA4s7nI2wQB4ri"

        dataretrieval_def = await client.agents.get_agent(agent_id=DataRetrievalAgentID)
        validation_def = await client.agents.get_agent(agent_id=ValidationInsightsAgentID)

        agent_retriever = AzureAIAgent(client=client, definition=dataretrieval_def)
        agent_evaluator = AzureAIAgent(client=client, definition=validation_def)

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
        SYSTEM_MESSAGE = """
        You are a helpful assistant. Your task is to assist the user in retrieving and evaluating data."""
        
        await st.session_state.chat.add_chat_message(SYSTEM_MESSAGE)
        st.session_state.chat_history = []
        st.session_state.chat_history.append({"role": "system", "content": SYSTEM_MESSAGE})

        chat_container = st.container(height=400)

        with chat_container:
            for msg in st.session_state.chat_history:
                avatar = "🧑‍💻" if msg["role"] == "user" else msg.get("avatar", "🤖")
                with st.chat_message(msg["role"], avatar=avatar):
                    st.markdown(msg["content"], unsafe_allow_html=True)

        agent_name_to_id = {
            RETRIEVER_NAME: DataRetrievalAgentID,
            EVALUATOR_NAME: ValidationInsightsAgentID,
        }

        prompt = st.chat_input("Type your message here...")

        if prompt:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user", avatar="🧑‍💻"):
                    st.markdown(prompt, unsafe_allow_html=True)
        
                await st.session_state.chat.add_chat_message(prompt)
                with st.spinner(f"Thinking..."):
                    try:
                        async for response in st.session_state.chat.invoke():
                            agent_name = response.name or "Agent"
                            avatar = "📖" if agent_name == RETRIEVER_NAME else "🔎" if agent_name == EVALUATOR_NAME else "🤖"
                            agent_style = get_agent_style(agent_name)  # Get the CSS style for the agent
        
                            # Extract citations from the response
                            citations = []
                            unique_urls = set()  # To track unique URLs and avoid duplicates
                            if hasattr(response, "items"):  # Check if response has items
                                for item in response.items:
                                    if item.content_type == "annotation" and item.url:
                                        if item.url not in unique_urls:
                                            unique_urls.add(item.url)
                                            citations.append({"quote": item.quote, "url": item.url})
        
                            agent_id = agent_name_to_id.get(agent_name, 'unknown')
        
                            # Combine the response content with citations
                            combined_content = response.content
                            if citations:
                                combined_content += "\n\n**Citations:**\n"
                                for citation in citations:
                                    combined_content += f"- **Quote**: {citation['quote']}  \n  **URL**: [{citation['url']}]({citation['url']})\n"
        
                            # Add the response and citations to the chat history
                            with st.expander(f"**{avatar} {agent_name}** ..."):
                                with st.chat_message(f"Azure AI Agent {agent_id}", avatar=avatar):
                                    # Display the agent's response content with a styled background
                                    st.markdown(
                                        f"<div style='{agent_style}'>"
                                        f"<strong>Azure AI Agent (ID: {agent_id}) -> </strong>"  # Add a line of separation
                                        f"{combined_content}"  # Display the combined content
                                        f"</div>",
                                        unsafe_allow_html=True,
                                    )
        
                            # Append the response and citations to the session state
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": combined_content,
                                "avatar": avatar,
                                "citations": citations if citations else None
                            })
        
                    except Exception as e:
                        detailed_traceback = traceback.format_exc()
                        st.error(f"Error: {e}\n\nTraceback:\n```\n{detailed_traceback}\n```")
                        logger.error(f"Chat error: {e}\nDetailed traceback:\n{detailed_traceback}")
        
                    finally:
                        # Safely extract the last assistant message from the chat history
                        final_message = next(
                            (msg for msg in reversed(st.session_state.chat_history) if msg["role"] == "assistant"), 
                            None
                        )
                        if final_message:
                            final_response = final_message["content"]
                            # Prominently display the final Assistant response
                            with st.chat_message("assistant", avatar="🤖"):
                                st.markdown(final_response, unsafe_allow_html=True)

if __name__ == "__main__":
    asyncio.run(main())
