import os
import asyncio
import streamlit as st
import traceback
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from src.aoai.aoai_helper import AzureOpenAIManager
import dotenv
from src.agenticrag.customagents.base import CustomAgent
from src.agenticrag.prompts import (
    generate_user_prompt,
    SYSTEM_PROMPT_PLANNER,
    SYSTEM_PROMPT_VERIFIER,
    generate_verifier_prompt,
    generate_final_summary,
    SYSTEM_PROMPT_SUMMARY,
)
from src.agenticrag.settings import (
    AZURE_AI_FOUNDRY_AGENT_IDS,
    VERIFIER_AGENT,
    PLANNER_AGENT,
    SUMMARY_AGENT,
    AZURE_AI_FOUNDRY_SHAREPOINT_AGENT,
    AZURE_AI_FOUNDRY_FABRIC_AGENT,
    AZURE_AI_FOUNDRY_WEB_AGENT,
    CUSTOM_AGENT_NAMES,
    VERIFIER_AGENT)

from src.agenticrag.tools import run_agent
from utils.ml_logging import get_logger

# Set up logger
logger = get_logger()

dotenv.load_dotenv(".env", override=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "project_client" not in st.session_state:
    st.session_state.project_client = AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=os.environ["AZURE_AI_FOUNDRY_CONNECTION_STRING"],
    )
for agent_key, config_path in CUSTOM_AGENT_NAMES.items():
    if agent_key not in st.session_state:
        st.session_state[agent_key] = CustomAgent(config_path=config_path)

def main():
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

    user_input = st.chat_input("Ask your R+D query here...")
    chat_container = st.container(height=500)

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

    MAX_RETRIES = 3
    if user_input:
        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )

        with chat_container:
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(user_input, unsafe_allow_html=True)
            initial_message = user_input
            current_query = user_input

            for attempt in range(1, MAX_RETRIES + 1):
                with st.spinner(f"Agents collaborating..."):
                    dicta = {}
                    try:
                        # Planner Agent Selection
                        agents = asyncio.run(st.session_state[PLANNER_AGENT].run(
                            user_prompt=generate_user_prompt(current_query),
                            conversation_history=[],
                            system_message_content=SYSTEM_PROMPT_PLANNER,
                            response_format="json_object",
                        ))

                        if not agents or not agents["response"].get(
                            "agents_needed"
                        ):
                            st.warning(
                                "No agents selected. Please refine your query."
                            )
                            break

                        st.info(
                            f"""
                            **Agents Selected:** {', '.join(agents['response']['agents_needed'])}  
                            **Reason:** {agents['response']['justification']}
                            """,
                            icon="ℹ️",
                        )

                        # Run the needed agents
                        for agent in agents["response"]["agents_needed"]:
                            if agent in AZURE_AI_FOUNDRY_AGENT_IDS:
                                agent_id = AZURE_AI_FOUNDRY_AGENT_IDS[agent]
                                avatar = (
                                    "📖"
                                    if agent == AZURE_AI_FOUNDRY_SHAREPOINT_AGENT
                                    else "🔎"
                                    if agent == AZURE_AI_FOUNDRY_WEB_AGENT
                                    else "🛠️"
                                    if agent == AZURE_AI_FOUNDRY_FABRIC_AGENT
                                    else "✅"
                                )
                                with st.expander(f"{avatar} {agent} says..."):
                                    response, threadID = run_agent(
                                        st.session_state.project_client, agent_id, current_query
                                    )
                                    if response:
                                        st.markdown(
                                            response, unsafe_allow_html=True
                                        )
                                        st.session_state.chat_history.append(
                                            {
                                                "role": agent,
                                                "content": response,
                                                "avatar": avatar,
                                            }
                                        )
                                        dicta[agent] = response
                            else:
                                st.error(f"Agent {agent} not found.")

                        # Verifier Agent Evaluation
                        evaluation = asyncio.run(st.session_state[VERIFIER_AGENT].run(
                            user_prompt=generate_verifier_prompt(
                                current_query,
                                fabric_data_summary=dicta.get(AZURE_AI_FOUNDRY_FABRIC_AGENT),
                                sharepoint_data_summary=dicta.get(AZURE_AI_FOUNDRY_SHAREPOINT_AGENT),
                                bing_data_summary=dicta.get(AZURE_AI_FOUNDRY_WEB_AGENT),
                            ),
                            conversation_history=[],
                            system_message_content=SYSTEM_PROMPT_VERIFIER,
                            response_format="json_object",
                        ))

                        if evaluation:
                            status = evaluation["response"]["status"]
                            response_content = evaluation["response"].get(
                                "response", ""
                            )
                            rewritten_query = evaluation["response"].get(
                                "rewritten_query", ""
                            )

                            avatar = "✅" if status == "Approved" else "❌"
                            content = (
                                response_content
                                if status == "Approved"
                                else rewritten_query
                            )

                            with st.expander(f"{avatar} {VERIFIER_AGENT} says..."):
                                st.markdown(
                                    f"**{status}:** {content}",
                                    unsafe_allow_html=True,
                                )

                            st.session_state.chat_history.append(
                                {
                                    "role": VERIFIER_AGENT,
                                    "content": content,
                                    "avatar": avatar,
                                }
                            )

                            if status == "Approved":
                                break  # Successfully approved, stop retrying

                            elif status == "Denied":
                                if rewritten_query:
                                    # Update query for next retry
                                    current_query = rewritten_query
                                    st.info(
                                        f"Verifier requested retry with rewritten query:\n\n{rewritten_query}"
                                    )
                                    st.session_state.chat_history.append(
                                        {
                                            "role": "system",
                                            "content": f"Verifier requested retry with rewritten query:\n\n{rewritten_query}",
                                            "avatar": "❌",
                                        }
                                    )
                                else:
                                    st.warning(
                                        "Verifier denied but no rewritten query provided."
                                    )
                                    break  # Can't retry without rewritten query

                            if attempt == MAX_RETRIES:
                                st.warning(
                                    "Maximum retries reached. Please refine your query or try again later."
                                )
                    except Exception as e:
                        tb = traceback.format_exc()
                        st.error(f"Error: {e}\n\nTraceback:\n```\n{tb}\n```")
                        logger.error(f"Chat error: {e}\nDetailed traceback:\n{tb}")
                        break
            if dicta:
                # Summary Agent
                summary_content =  asyncio.run(st.session_state[SUMMARY_AGENT].run(
                    user_prompt=generate_final_summary(
                        initial_message,
                        dicta=dicta,
                    ),
                    conversation_history=[],
                    system_message_content=SYSTEM_PROMPT_SUMMARY,
                ))
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(summary_content["response"], unsafe_allow_html=True)
                    st.session_state.chat_history.append(
                        {
                            "role": "assistant",
                            "content": summary_content["response"],
                            "avatar": "🤖",
                        }
                    )

                st.toast(
                    "📧 An email with the results of your query has been sent!",
                    icon="📩",
                )

def run():
    try:
        main()
    except RuntimeError as e:
        st.error(f"Runtime error: {e}")
        logger.error(f"Runtime error: {e}")

if __name__ == "__main__":
    run()
