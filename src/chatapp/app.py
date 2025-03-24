import os
import asyncio
import streamlit as st
import traceback
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel import Kernel
from semantic_kernel.agents import AgentGroupChat
from semantic_kernel.agents.azure_ai import AzureAIAgent
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)
from semantic_kernel.functions import KernelFunctionFromPrompt
from dotenv import load_dotenv

load_dotenv()

# --- Constants for Agent Names ---
VERIFIER_NAME = "VerifierAgent"
SHAREPOINT_AGENT = "SharePointDataRetrievalAgent"
FABRIC_AGENT = "FabricDataRetrievalAgent"
WEB_AGENT = "BingDataRetrievalAgent"

# --- Kernel Setup ---
def create_kernel():
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

# --- Selection Strategy ---
selection_function = KernelFunctionFromPrompt(
    function_name="selection",
    prompt=f"""
    Your task is to determine precisely which agent should respond next based on the user's query and recent conversation history. 
    Follow the agent invocation guidelines strictly and in this order:

    Step 1: Analyze User Query Context:
    - If the user's question specifically mentions internal documentation, company resources, SharePoint sites, or internal organizational knowledge, select {SHAREPOINT_AGENT}.
    - If the query involves advanced analytics, complex data insights, business intelligence, or explicitly mentions Microsoft Fabric or Data Lake, select {FABRIC_AGENT}.
    - If the query involves general knowledge, internet searches, public news, events, or explicitly mentions searching the web or Bing, select {WEB_AGENT}.

    Step 2: Retrieval Verification Process:
    - After any retrieval agent ({SHAREPOINT_AGENT}, {FABRIC_AGENT}, {WEB_AGENT}) finishes retrieving data, ALWAYS select {VERIFIER_NAME} next to evaluate, verify, and validate the quality of the retrieved information.

    Step 3: Agentic Planning & Re-evaluation:
    - If {VERIFIER_NAME} assesses the information and clearly indicates the retrieved data is insufficient or inadequate ("not enough information", "inadequate data", "need more data", or similar phrases), you must intelligently select another relevant retrieval agent that has NOT been invoked yet for this specific query.
    - Prioritize using agents in this order if the initial retrieval is insufficient:
      1. {SHAREPOINT_AGENT} → 2. {FABRIC_AGENT} → 3. {WEB_AGENT}
      (Move down the priority list only if necessary.)

    Step 4: Completing a Retrieval Cycle:
    - Continue cycles of Retrieval → Verification → (possible re-Retrieval) until {VERIFIER_NAME} explicitly approves or validates the data.

    IMPORTANT:
    Return ONLY the EXACT name of ONE agent clearly matching the guidelines:
    - {SHAREPOINT_AGENT}, {FABRIC_AGENT}, {WEB_AGENT}, {VERIFIER_NAME}

    Conversation History:
    {{$history}}
    """,
)


# --- Termination Strategy ---
termination_function = KernelFunctionFromPrompt(
    function_name="termination",
    prompt="""
    Check if the VerifierAgent explicitly approved the retrieved information.
    If clearly approved, reply "yes"; if additional information or review needed, reply "no".

    History:
    {{$history}}
    """,
)

# --- Async Main with Complete Streamlit Integration ---
async def main():
    st.set_page_config(page_title="R+D Intelligent Multi-Agent Assistant")
    # ...existing code above...
    st.markdown(
        """
        <style>
        .titleContainer {
            text-align: center;
            background: linear-gradient(145deg, #1F6095, #008AD7);
            color: #FFFFFF;
            padding: 35px;
            border-radius: 12px;
            margin-bottom: 25px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
        }
        .titleContainer h1 {
            margin: 0;
            font-size: 2rem;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            font-weight: 600;
            color: #FFFFFF;
            letter-spacing: 0.8px;
        }
        .titleContainer h3 {
            margin: 8px 0 0;
            font-size: 1rem;
            font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
            font-weight: 400;
            color: #FFFFFF;
        }
        </style>
        
        <div class="titleContainer">
            <h1>R+D Intelligent Assistant 🤖</h1>
            <h3>powered by Azure AI Agent Service</h3>
        </div>
        """,
        unsafe_allow_html=True
    )

    async with DefaultAzureCredential() as creds, AzureAIAgent.create_client(credential=creds) as client:
        # Define agent IDs
        agent_ids = {
            SHAREPOINT_AGENT: "asst_kTtpnCZGYWammSC1PyYO6ljp",
            FABRIC_AGENT: "asst_s6lYjbMRHuY4le2zUwKJ0JNt",
            WEB_AGENT: "asst_E7bYR4yLZXBdQdodvd5prSYc",
            VERIFIER_NAME: "asst_nkhC85ADcuFVvhLqC76mCXc0",
        }

        # Initialize agents
        agents = {}
        for name, agent_id in agent_ids.items():
            definition = await client.agents.get_agent(agent_id)
            agents[name] = AzureAIAgent(client=client, definition=definition)

        # Set up the multi-agent chat
        st.session_state.chat = AgentGroupChat(
            agents=list(agents.values()),
            selection_strategy=KernelFunctionSelectionStrategy(
                function=selection_function,
                kernel=create_kernel(),
                result_parser=lambda result: (result.value[0].content or "").strip() or FABRIC_AGENT,
                history_variable_name="history",
            ),
            termination_strategy=KernelFunctionTerminationStrategy(
                agents=[agents[VERIFIER_NAME]],
                function=termination_function,
                kernel=create_kernel(),
                result_parser=lambda result: "yes" in str(result.value[0]).lower(),
                history_variable_name="history",
                maximum_iterations=10,
            ),
        )

        # Initialize chat history in session state
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # User input
        user_input = st.chat_input("Ask your R+D query here...")

        # Chat container for displaying messages
        chat_container = st.container(height=400, border=True)

        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            with chat_container:
                with st.chat_message("user", avatar="🧑‍💻"):
                    st.markdown(user_input, unsafe_allow_html=True)

                await st.session_state.chat.add_chat_message(user_input)
                with st.spinner(f"Agents collaborating..."):
                    try:
                        async for response in st.session_state.chat.invoke():
                            agent_name = response.name or "Agent"
                            avatar = "📖" if agent_name == SHAREPOINT_AGENT else "🔎" if agent_name == WEB_AGENT else "🛠️" if agent_name == FABRIC_AGENT else "✅"
                            agent_style = f"background-color: #E3F2FD; border-radius: 10px; padding: 10px; margin: 5px 0;" if agent_name == SHAREPOINT_AGENT else \
                                          f"background-color: #E0F7FA; border-radius: 10px; padding: 10px; margin: 5px 0;" if agent_name == WEB_AGENT else \
                                          f"background-color: #F5F5F5; border-radius: 10px; padding: 10px; margin: 5px 0;"

                            # Extract citations from the response
                            citations = []
                            unique_urls = set()
                            if hasattr(response, "items"):
                                for item in response.items:
                                    if item.content_type == "annotation" and item.url:
                                        if item.url not in unique_urls:
                                            unique_urls.add(item.url)
                                            citations.append({"quote": item.quote, "url": item.url})

                            agent_id = agent_ids.get(agent_name, "unknown")

                            # Combine the response content with citations
                            combined_content = response.content
                            if citations:
                                combined_content += "\n\n**Citations:**\n"
                                for citation in citations:
                                    combined_content += f"- **Quote**: {citation['quote']}  \n  **URL**: [{citation['url']}]({citation['url']})\n"

                            # Add the response and citations to the chat history
                            with st.expander(f"**{avatar} {agent_name}** (Azure AI Agent ID: {agent_id}) is thinking..."):
                                with st.chat_message(f"Azure AI Agent {agent_id}", avatar=avatar):
                                    st.markdown(
                                        f"<div style='{agent_style}'>"
                                        f"<strong>Azure AI Agent (ID: {agent_id})</strong><br><hr>"
                                        f"{combined_content}"
                                        f"</div>",
                                        unsafe_allow_html=True,
                                    )

                            # Append the response and citations to the session state
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": combined_content,
                                "avatar": avatar,
                                "citations": citations if citations else None,
                            })

                    except Exception as e:
                        detailed_traceback = traceback.format_exc()
                        st.error(f"Error: {e}\n\nTraceback:\n```\n{detailed_traceback}\n```")
                        print(f"Chat error: {e}\nDetailed traceback:\n{detailed_traceback}")

                    finally:
                        # Safely extract the last assistant message from the chat history
                        final_message = next(
                            (msg for msg in reversed(st.session_state.chat_history) if msg["role"] == "assistant"),
                            None,
                        )
                        if final_message:
                            final_response = final_message["content"]
                            with st.chat_message("assistant", avatar="🤖"):
                                st.markdown(final_response, unsafe_allow_html=True)


if __name__ == "__main__":
    asyncio.run(main())