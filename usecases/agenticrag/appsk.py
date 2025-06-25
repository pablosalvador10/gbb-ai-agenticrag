import asyncio
import os
import traceback

import streamlit as st
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.agents import AgentGroupChat
from semantic_kernel.agents.azure_ai import AzureAIAgent
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)
from semantic_kernel.contents import ChatHistoryTruncationReducer
from semantic_kernel.functions import KernelFunctionFromPrompt

load_dotenv()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Agent name constants
VERIFIER_NAME = "VerifierAgent"
SHAREPOINT_AGENT = "SharePointDataRetrievalAgent"
FABRIC_AGENT = "FabricDataRetrievalAgent"
WEB_AGENT = "BingDataRetrievalAgent"


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


selection_function = KernelFunctionFromPrompt(
    function_name="selection",
    prompt=f"""
    Examine the provided RESPONSE and choose the next participant.
    State only the name of the chosen participant without explanation.
    Never choose the participant named in the RESPONSE.

    Choose only from these participants:
    - {FABRIC_AGENT}
    - {VERIFIER_NAME}
    - {SHAREPOINT_AGENT}
    - {WEB_AGENT}

    Rules:
    - If RESPONSE is user input, it is {FABRIC_AGENT}'s turn.
    - If RESPONSE is by {FABRIC_AGENT}, it is {SHAREPOINT_AGENT}'s turn.
    - If RESPONSE is by {SHAREPOINT_AGENT}, it is {VERIFIER_NAME}'s turn.

    RESPONSE:
    {{$lastmessage}}
    """,
)

termination_function = KernelFunctionFromPrompt(
    function_name="termination",
    prompt="""
    Check if the VerifierAgent explicitly approved the retrieved information.
    If approved, reply "yes"; if additional information or review needed, reply "no".

    Last Message:
    {{$history}}
    """,
)


async def main():
    st.set_page_config(page_title="R+D Intelligent Multi-Agent Assistant")
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
            <h3>powered by Azure AI Foundry Agent Service</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------
    # Create/Reuse the Azure client (avoid async with)
    # -------------------------------------------------
    async with DefaultAzureCredential() as creds, AzureAIAgent.create_client(
        credential=creds
    ) as client:
        # Define agent IDs
        agents_ids = {
            SHAREPOINT_AGENT: "asst_kTtpnCZGYWammSC1PyYO6ljp",
            FABRIC_AGENT: "asst_IJLeIajKKCp0VRgneCkAutdg",
            WEB_AGENT: "asst_E7bYR4yLZXBdQdodvd5prSYc",
            VERIFIER_NAME: "asst_nkhC85ADcuFVvhLqC76mCXc0",
        }

        # Initialize our four agents only once
        agents = {}
        for name, agent_id in agents_ids.items():
            definition = await client.agents.get_agent(agent_id)
            agents[name] = AzureAIAgent(client=client, definition=definition)

        # Build multi-agent chat in session state if not present
        st.session_state.chat = AgentGroupChat(
            agents=list(agents.values()),
            selection_strategy=KernelFunctionSelectionStrategy(
                function=selection_function,
                kernel=create_kernel(),
                result_parser=lambda result: str(result.value[0]).strip(),
                history_variable_name="lastmessage",
                history_reducer=ChatHistoryTruncationReducer(target_count=1),
            ),
            termination_strategy=KernelFunctionTerminationStrategy(
                agents=[agents[VERIFIER_NAME]],
                function=termination_function,
                kernel=create_kernel(),
                result_parser=lambda result: "yes" in str(result.value[0]).lower(),
                history_variable_name="history",
                maximum_iterations=6,
            ),
        )

        # Omni system prompt
        SYSTEM_MESSAGE = """
        You are an intelligent multi-agent R&D assistant designed to help Product Managers quickly access, integrate, and evaluate information from multiple specialized sources.
        Aim to support fast and accurate decision-making for R&D insights, leveraging internal and external data comprehensively and effectively.
        """

        await st.session_state.chat.add_chat_message(SYSTEM_MESSAGE)

        # First system message
        if not any(msg["role"] == "system" for msg in st.session_state.chat_history):
            # Add system message to local chat history
            st.session_state.chat_history.append(
                {"role": "system", "content": SYSTEM_MESSAGE}
            )
        # Chat interface
        user_input = st.chat_input("Ask your R+D query here...")
        chat_container = st.container(height=400)

        with chat_container:
            for idx, msg in enumerate(st.session_state.chat_history):
                role = msg["role"]  # Could be "user", "system", or the agent's name
                content = msg["content"]
                avatar = msg.get("avatar", "🤖")

                if role.lower() == "user":
                    with st.chat_message("user", avatar="🧑‍💻"):
                        st.markdown(content, unsafe_allow_html=True)
                elif role.lower() == "assistant":
                    # You might display system messages differently if you want
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(content, unsafe_allow_html=True)
                elif role.lower() == "system":
                    pass
                else:
                    # For agent roles
                    with st.expander(f"{avatar} {role} says...", expanded=False):
                        st.markdown(content, unsafe_allow_html=True)

        if user_input:
            # Add user to local chat history with role "user"

            st.session_state.chat_history.append(
                {"role": "user", "content": user_input}
            )
            with chat_container:
                with st.chat_message("user", avatar="🧑‍💻"):
                    st.markdown(user_input, unsafe_allow_html=True)

                await st.session_state.chat.add_chat_message(user_input)

                with st.spinner("Agents collaborating..."):
                    try:
                        combined_content = ""  # Ensure it's always defined
                        async for response in st.session_state.chat.invoke():
                            agent_name = response.name or "Agent"
                            avatar = (
                                "📖"
                                if agent_name == SHAREPOINT_AGENT
                                else (
                                    "🔎"
                                    if agent_name == WEB_AGENT
                                    else "🛠️" if agent_name == FABRIC_AGENT else "✅"
                                )
                            )
                            combined_content = response.content or ""
                            # Pass the agent’s name + content as the last message
                            combined_content = (
                                f"[{agent_name}] {response.content or ''}"
                            )

                            # Handle citations
                            citations = []
                            if hasattr(response, "items"):
                                for item in response.items:
                                    if item.content_type == "annotation" and item.url:
                                        citations.append(
                                            {"quote": item.quote, "url": item.url}
                                        )
                            if citations:
                                combined_content += "\n\n**Citations:**\n"
                                for citation in citations:
                                    combined_content += (
                                        f"- **Quote**: {citation['quote']}  \n"
                                    )
                                    combined_content += f"  **URL**: [{citation['url']}]({citation['url']})\n"

                            # Save to history
                            st.session_state.chat_history.append(
                                {
                                    "role": agent_name,
                                    "content": combined_content,
                                    "avatar": avatar,
                                }
                            )

                            # Display each agent message immediately
                            with st.expander(f"{avatar} {agent_name} says..."):
                                st.markdown(combined_content, unsafe_allow_html=True)

                    except Exception as e:
                        tb = traceback.format_exc()
                        st.error(f"Error: {e}\n\nTraceback:\n```\n{tb}\n```")
                        print(f"Chat error: {e}\nDetailed traceback:\n{tb}")

                    finally:
                        if combined_content:
                            with st.chat_message("assistant", avatar="🤖"):
                                st.markdown(combined_content, unsafe_allow_html=True)
                            st.session_state.chat_history.append(
                                {
                                    "role": "assistant",
                                    "content": combined_content,
                                    "avatar": "🤖",
                                }
                            )


def run():
    asyncio.run(main())


if __name__ == "__main__":
    run()
