import os
import asyncio
import streamlit as st
import traceback
from azure.identity.aio import DefaultAzureCredential
from semantic_kernel.agents.azure_ai import AzureAIAgent
from src.aoai.aoai_helper import AzureOpenAIManager
import dotenv
from src.chatapp.prompts import (generate_user_prompt, 
                                 SYSTEM_PROMPT_PLANNER, 
                                 SYSTEM_PROMPT_VERIFIER, 
                                 generate_verifier_prompt,
                                 generate_final_summary,
                                 SYSTEM_PROMPT_SUMMARY)

from src.chatapp.tools import run_agent

from utils.ml_logging import get_logger

# Set up logger
logger = get_logger()

dotenv.load_dotenv(".env", override=True)

if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

if "azure_openai_client" not in st.session_state:
    st.session_state["azure_openai_client"] = AzureOpenAIManager(
        api_key=os.getenv("AZURE_OPENAI_KEY_PS"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT_PS"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION_PS"),
        chat_model_name=os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_ID_PS"),
    )

# Agent name constants
VERIFIER_NAME = "VerifierAgent"
SHAREPOINT_AGENT = "SharePointDataRetrievalAgent"
FABRIC_AGENT = "FabricDataRetrievalAgent"
WEB_AGENT = "BingDataRetrievalAgent"

# Define agent IDs
agents_ids = {
    SHAREPOINT_AGENT: "asst_19kRBhLMCPuO13tJsOuWfvuU",
    FABRIC_AGENT: "asst_NyyLBIVx6QNFRKA2YPOXk2ZC",
    WEB_AGENT: "asst_WLcRfqHJo7qS1V3wxK1S7f79",
}

async def main():
    async with DefaultAzureCredential() as creds, AzureAIAgent.create_client(credential=creds) as client:
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
                <h3>powered by Azure AI Agent Service</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

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
        
        MAX_RETRIES = 3
        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            with chat_container:
                with st.chat_message("user", avatar="🧑‍💻"):
                    st.markdown(user_input, unsafe_allow_html=True)
                initial_message = user_input
                current_query = user_input  # Initialize current_query

                for attempt in range(1, MAX_RETRIES + 1):
                    with st.spinner(f"Agents collaborating..."):
                        dicta = {}
                        try:
                            # Planner Agent Selection
                            agents = await st.session_state.azure_openai_client.generate_chat_response(
                                query=generate_user_prompt(current_query),
                                conversation_history=[],
                                system_message_content=SYSTEM_PROMPT_PLANNER,
                                response_format="json_object"
                            )

                            if not agents or not agents['response'].get('agents_needed'):
                                st.warning("No agents selected. Please refine your query.")
                                break

                            st.info(
                                f"""
                                **Agents Selected:** {', '.join(agents['response']['agents_needed'])}  
                                **Reason:** {agents['response']['justification']}
                                """,
                                icon="ℹ️"
                            )

                            # Run the needed agents
                            for agent in agents['response']['agents_needed']:
                                if agent in agents_ids:
                                    agent_id = agents_ids[agent]
                                    avatar = (
                                        "📖" if agent == SHAREPOINT_AGENT
                                        else "🔎" if agent == WEB_AGENT
                                        else "🛠️" if agent == FABRIC_AGENT
                                        else "✅")
                                    with st.expander(f"{avatar} {agent} says..."):
                                        response, threadID = await run_agent(
                                            client,
                                            agent_id,
                                            current_query
                                        )
                                        if response:
                                            st.markdown(response, unsafe_allow_html=True)
                                            st.session_state.chat_history.append({
                                                "role": agent,
                                                "content": response,
                                                "avatar": avatar,
                                            })
                                            dicta[agent] = response
                                else:
                                    st.error(f"Agent {agent} not found.")

                            # Verifier Agent Evaluation
                            evaluation = await st.session_state.azure_openai_client.generate_chat_response(
                                query=generate_verifier_prompt(
                                    current_query,
                                    fabric_data_summary=dicta.get(FABRIC_AGENT),
                                    sharepoint_data_summary=dicta.get(SHAREPOINT_AGENT),
                                    bing_data_summary=dicta.get(WEB_AGENT)
                                ),
                                conversation_history=[],
                                system_message_content=SYSTEM_PROMPT_VERIFIER,
                                max_tokens=3000,
                                response_format="json_object"
                            )

                            if evaluation:
                                status = evaluation['response']['status']
                                response_content = evaluation['response'].get('response', '')
                                rewritten_query = evaluation['response'].get('rewritten_query', '')

                                avatar = "✅" if status == "Approved" else "❌"
                                content = response_content if status == "Approved" else rewritten_query

                                with st.expander(f"{avatar} {VERIFIER_NAME} says..."):
                                    st.markdown(f"**{status}:** {content}", unsafe_allow_html=True)

                                st.session_state.chat_history.append({
                                    "role": VERIFIER_NAME,
                                    "content": content,
                                    "avatar": avatar,
                                })

                                if status == "Approved":
                                    break  # Successfully approved, stop retrying

                                elif status == "Denied":
                                    if rewritten_query:
                                        # Update query for next retry
                                        current_query = rewritten_query
                                        st.info(f"Verifier requested retry with rewritten query:\n\n{rewritten_query}")
                                        st.session_state.chat_history.append({
                                            "role": "system",
                                            "content": f"Verifier requested retry with rewritten query:\n\n{rewritten_query}",
                                            "avatar": "❌",
                                        })
                                    else:
                                        st.warning("Verifier denied but no rewritten query provided.")
                                        break  # Can't retry without rewritten query

                                if attempt == MAX_RETRIES:
                                    st.warning("Maximum retries reached. Please refine your query or try again later.")
                        except Exception as e:
                            tb = traceback.format_exc()
                            st.error(f"Error: {e}\n\nTraceback:\n```\n{tb}\n```")
                            logger.error(f"Chat error: {e}\nDetailed traceback:\n{tb}")
                            break 
                if dicta:
                    summary_content = await st.session_state.azure_openai_client.generate_chat_response(
                            query=generate_final_summary(
                                initial_message,
                                dicta=dicta,
                            ),
                            conversation_history=[],
                            system_message_content=SYSTEM_PROMPT_SUMMARY,
                            max_tokens=3000)
                    with st.chat_message("assistant", avatar="🤖"):
                        st.markdown(summary_content['response'], unsafe_allow_html=True)
                        st.session_state.chat_history.append({
                            "role": "assistant",
                            "content": summary_content['response'],
                            "avatar": "🤖",
                        })   

                    st.toast(
                        "📧 An email with the results of your query has been sent!",
                        icon="📩")  
def run():
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(main())

if __name__ == "__main__":
    run()