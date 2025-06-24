import asyncio
import os
import streamlit as st
import traceback
import json
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from src.aoai.aoai_helper import AzureOpenAIManager
import time
from concurrent.futures import TimeoutError as FuturesTimeout
import dotenv
from usecases.agenticrag.aoaiAgents.base import AzureOpenAIAgent
from usecases.agenticrag.prompts import (
    generate_user_prompt,
    SYSTEM_PROMPT_PLANNER,
    SYSTEM_PROMPT_VERIFIER,
    generate_verifier_prompt,
    generate_final_summary,
    SYSTEM_PROMPT_SUMMARY,
)
from usecases.agenticrag.settings import (
    AZURE_AI_FOUNDRY_AGENT_IDS,
    VERIFIER_AGENT,
    PLANNER_AGENT,
    SUMMARY_AGENT,
    AZURE_AI_FOUNDRY_SHAREPOINT_AGENT,
    AZURE_AI_FOUNDRY_FABRIC_AGENT,
    AZURE_AI_FOUNDRY_WEB_AGENT,
    CUSTOM_AGENT_NAMES,
    VERIFIER_AGENT)
from usecases.agenticrag.tools import run_agent
from utils.ml_logging import get_logger
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up logger
logger = get_logger()

def setup_environment():
    """Load environment variables and initialize session state."""
    logger.info("Setting up environment and initializing session state.")
    dotenv.load_dotenv(".env", override=True)
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "project_client" not in st.session_state:
        logger.info("Initializing Azure AI Project Client.")
        st.session_state.project_client = AIProjectClient.from_connection_string(
            credential=DefaultAzureCredential(),
            conn_str=os.environ["AZURE_AI_FOUNDRY_CONNECTION_STRING"],
        )
    for agent_key, config_path in CUSTOM_AGENT_NAMES.items():
        if agent_key not in st.session_state:
            logger.info(f"Loading agent '{agent_key}' from config: {config_path}")
            st.session_state[agent_key] = AzureOpenAIAgent(config_path=config_path)


def render_chat_history(chat_container):
    """Render the chat history in the provided Streamlit container."""
    logger.debug("Rendering chat history.")
    for idx, msg in enumerate(st.session_state.chat_history):
        role = msg["role"]
        content = msg["content"]
        avatar = msg.get("avatar", "🤖")
        if role.lower() == "user":
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(content, unsafe_allow_html=True)
        elif role.lower() == "assistant":
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(content, unsafe_allow_html=True)
        elif role.lower() == "system":
            pass
        else:
            with st.expander(f"{avatar} {role} says...", expanded=False):
                st.markdown(content, unsafe_allow_html=True)


def select_agents(current_query):
    """
    Use the planner agent to select which agents are needed for the query.
    Returns the agents dict or None if selection fails.
    Logs each step for traceability.
    """
    logger.info(f"Selecting agents for query: {current_query}")
    try:
        agents = asyncio.run(st.session_state[PLANNER_AGENT].run(
            user_prompt=generate_user_prompt(current_query),
            conversation_history=[],
            system_message_content=SYSTEM_PROMPT_PLANNER,
            response_format="json_object",
        ))
        logger.debug(f"Planner agent response: {agents}")
        if not agents or not agents["response"].get("agents_needed"):
            logger.warning("No agents selected by planner agent.")
            st.warning("No agents selected. Please refine your query.")
            return None
        st.info(
            f"""
            **Agents Selected:** {', '.join(agents['response']['agents_needed'])}  
            **Reason:** {agents['response']['justification']}
            """,
            icon="ℹ️",
        )
        logger.info(f"Agents selected: {agents['response']['agents_needed']}")
        return agents
    except Exception as e:
        logger.error(f"Planner agent selection failed: {e}")
        st.error(f"Planner agent selection failed: {e}")
        return None


async def _invoke_agent(agent_name: str, agent_id: str, query: str, avatar: str,
                        project_client: AIProjectClient, timeout: int = 90):
    """Run a Foundry agent in a worker thread and return (agent_name, response or None)."""
    loop = asyncio.get_running_loop()
    try:
        response, thread_id = await asyncio.wait_for(
            loop.run_in_executor(
                None,  # default ThreadPoolExecutor
                run_agent,                # blocking function
                project_client,
                agent_id,
                query,
            ),
            timeout=timeout,
        )
        return agent_name, response
    except (asyncio.TimeoutError, FuturesTimeout):
        logger.error(f"{agent_name} timed out after {timeout}s")
        return agent_name, None
    except Exception as exc:
        logger.error(f"{agent_name} failed: {exc}")
        return agent_name, None


def run_selected_agents(agents_needed, current_query):
    """
    Run all selected agents in parallel using ThreadPoolExecutor and collect responses.
    Returns a dict: {agent_name: response_or_None}.
    All Streamlit UI and session state updates are done in the main thread.
    """
    logger.info(f"Running agents in parallel: {agents_needed}")
    dicta = {}
    results = []
    # --- Mind map agent status tracking (local, not in session state) ---
    agent_status = {a: 'pending' for a in agents_needed}
    render_agent_mind_map(agent_status)
    def run_agent_worker(a_id, query, pc, agent_name):
        try:
            # Only update local dict, not session state
            return 'running', None, run_agent(pc, a_id, query)
        except Exception as exc:
            logger.error(f"{agent_name} failed: {exc}")
            return 'error', str(exc), (None, None)
    with ThreadPoolExecutor(max_workers=len(agents_needed)) as executor:
        future_to_agent = {}
        for agent in agents_needed:
            if agent not in AZURE_AI_FOUNDRY_AGENT_IDS:
                logger.error(f"{agent} missing in AZURE_AI_FOUNDRY_AGENT_IDS.")
                results.append((agent, None, f"Agent {agent} not configured."))
                agent_status[agent] = 'error'
                continue
            agent_id = AZURE_AI_FOUNDRY_AGENT_IDS[agent]
            future = executor.submit(run_agent_worker, agent_id, current_query, st.session_state.project_client, agent)
            future_to_agent[future] = agent
        for future in as_completed(future_to_agent):
            agent = future_to_agent[future]
            status, error, (response, thread_id) = future.result()
            agent_status[agent] = 'done' if status == 'running' and response else status
            render_agent_mind_map(agent_status)
            results.append((agent, response, error))
    # Hide mind map after all agents are done
    render_agent_mind_map({a: 'done' for a in agents_needed})
    # Now update UI and session state in main thread
    for agent, response, error in results:
        avatar = (
            "📖" if agent == AZURE_AI_FOUNDRY_SHAREPOINT_AGENT
            else "🔎" if agent == AZURE_AI_FOUNDRY_WEB_AGENT
            else "🛠️" if agent == AZURE_AI_FOUNDRY_FABRIC_AGENT
            else "✅"
        )
        expander = st.expander(f"{avatar} {agent} says...", expanded=False)
        with expander:
            if error:
                st.warning(f"Agent {agent} failed: {error}")
            elif response:
                st.markdown(response, unsafe_allow_html=True)
                st.session_state.chat_history.append({
                    "role": agent,
                    "content": response,
                    "avatar": avatar,
                })
                dicta[agent] = response
            else:
                st.warning(f"No response from agent {agent} (timeout or error).")
    logger.info(f"Collected responses: {list(dicta.keys())}")
    return dicta


def evaluate_with_verifier(current_query, dicta):
    """
    Use the verifier agent to evaluate the responses from the selected agents.
    Returns a tuple (status, content, rewritten_query) or (None, None, None) on error.
    Handles stringified JSON and logs errors.
    Logs each step for traceability.
    """
    logger.info(f"Evaluating agent responses with verifier for query: {current_query}")
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
        max_tokens=400,
    ))
    logger.debug(f"Verifier agent raw response: {evaluation}")
    response_obj = None
    if (
        evaluation
        and isinstance(evaluation, dict)
        and "response" in evaluation
    ):
        if isinstance(evaluation["response"], str):
            try:
                response_obj = json.loads(evaluation["response"])
            except Exception:
                logger.error(f"Verifier agent returned unparseable string: {evaluation['response']}")
                st.error(f"Verifier agent returned a string response that could not be parsed as JSON: {evaluation['response']}")
                return None, None, None
        elif isinstance(evaluation["response"], dict):
            response_obj = evaluation["response"]
    if response_obj and "status" in response_obj:
        status = response_obj["status"]
        response_content = response_obj.get("response", "")
        rewritten_query = response_obj.get("rewritten_query", "")
        avatar = "✅" if status == "Approved" else "❌"
        content = response_content if status == "Approved" else rewritten_query
        logger.info(f"Verifier agent status: {status}")
        with st.expander(f"{avatar} {VERIFIER_AGENT} says..."):
            st.markdown(f"**{status}:** {content}", unsafe_allow_html=True)
        st.session_state.chat_history.append(
            {
                "role": VERIFIER_AGENT,
                "content": content,
                "avatar": avatar,
            }
        )
        return status, content, rewritten_query
    else:
        logger.error(f"Verifier agent returned unexpected response: {evaluation}")
        st.error(f"Verifier agent returned an unexpected response: {evaluation}")
        return None, None, None


def summarize_results(initial_message, dicta):
    """
    Use the summary agent to generate a final summary from all agent responses.
    Handles stringified JSON and logs errors.
    Logs each step for traceability.
    """
    logger.info("Summarizing results with summary agent.")
    summary_content = asyncio.run(st.session_state[SUMMARY_AGENT].run(
        user_prompt=generate_final_summary(
            initial_message,
            dicta=dicta,
        ),
        conversation_history=[],
        system_message_content=SYSTEM_PROMPT_SUMMARY,
        max_tokens=3000,
    ))
    logger.debug(f"Summary agent raw response: {summary_content}")
    summary_response = None
    if (
        summary_content
        and isinstance(summary_content, dict)
        and "response" in summary_content
    ):
        if isinstance(summary_content["response"], str):
            summary_response = summary_content["response"]
        elif isinstance(summary_content["response"], dict):
            summary_response = summary_content["response"].get("response", "")
    if summary_response:
        logger.info("Summary agent produced a valid response.")
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(summary_response, unsafe_allow_html=True)
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": summary_response,
                    "avatar": "🤖",
                }
            )
    else:
        logger.error(f"Summary agent returned unexpected response: {summary_content}")
        st.error(f"Summary agent returned an unexpected response: {summary_content}")
    st.toast(
        "📧 An email with the results of your query has been sent!",
        icon="📩",
    )

PLANNER  = "PlannerAgent"
SP       = "SharePointDataRetrievalAgent"
WEB      = "BingDataRetrievalAgent"
FAB      = "FabricDataRetrievalAgent"
VERIFY   = "VerifierAgent"
SUMMARY  = "SummaryAgent"

ICONS = {PLANNER:"🧩", SP:"📖", WEB:"🔎", FAB:"🛠️", VERIFY:"✅", SUMMARY:"📝"}
LABELS = {PLANNER:"Planner", SP:"SP", WEB:"Bing", FAB:"Fabric", VERIFY:"Verifier", SUMMARY:"Summ.."}

# Panel size
WIDTH, HEIGHT = 300, 420   # <- a bit wider / taller
NODE_W, NODE_H = 96, 36
# Horizontal helpers
COL_LEFT   = 20
COL_CENTER = WIDTH//2 - NODE_W//2   # centred x
COL_RIGHT  = WIDTH - NODE_W - 20

NODE_POS = {
    PLANNER: (COL_CENTER, 24),
    SP:      (COL_LEFT,   120),
    WEB:     (COL_CENTER, 120),
    FAB:     (COL_RIGHT, 120),
    VERIFY:  (COL_CENTER, 230),
    SUMMARY: (COL_CENTER, 335),
}

EDGES = [
    (PLANNER, SP), (PLANNER, WEB), (PLANNER, FAB),
    (SP, VERIFY), (WEB, VERIFY), (FAB, VERIFY),
    (VERIFY, SUMMARY),
]

STATUS_COLOURS = {
    "pending": ("#f5f5f5", "#9e9e9e"),
    "running": ("#fff7d1", "#e6b800"),
    "done":    ("#e8f5e9", "#00b050"),
    "error":   ("#ffebee", "#d32f2f"),
    "denied":  ("#ffebee", "#d32f2f"),
}

# ------------------------------------------------------------------
STYLE = f"""
<style>
.mind-popup {{ position:fixed; top:110px; left:28px; width:{WIDTH+40}px; z-index:9999;
              background:#fffffffa; padding:20px 24px 28px 24px;
              border-radius:20px; border:3px solid #0078D4;
              box-shadow:0 8px 28px rgba(0,0,0,.18);
              font-family:'Segoe UI', Tahoma, sans-serif; }}
.mind-title  {{ font-weight:700; font-size:1.15rem; color:#0078D4; margin-bottom:10px; }}
.node        {{ position:absolute; width:{NODE_W}px; height:{NODE_H}px; border-radius:12px;
               display:flex; align-items:center; justify-content:center; gap:4px;
               font-weight:600; box-shadow:0 1px 6px rgba(0,0,0,.08); transition:background .25s; }}
</style>
"""

# ------------------------------------------------------------------

def render_agent_mind_map(status_dict):
    """Render or update floating mind‑map. status_dict maps agent ➜ status string."""
    if not status_dict:
        return

    # Build SVG edges
    svg_lines = []
    for src, dst in EDGES:
        x1, y1 = NODE_POS[src][0] + NODE_W//2, NODE_POS[src][1] + NODE_H//2
        x2, y2 = NODE_POS[dst][0] + NODE_W//2, NODE_POS[dst][1] + NODE_H//2
        svg_lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="#0078D4" stroke-width="2.4" stroke-dasharray="6,4" />'
        )
    lines_svg = "".join(svg_lines)

    # Build nodes
    nodes_html = []
    order = [PLANNER, SP, WEB, FAB, VERIFY, SUMMARY]
    for ag in order:
        status = status_dict.get(ag, "pending" if ag != PLANNER else "done")
        bg, txt = STATUS_COLOURS.get(status, STATUS_COLOURS["pending"])
        x, y = NODE_POS[ag]
        nodes_html.append(
            f'<div class="node" style="left:{x}px;top:{y}px;'
            f'background:{bg};color:{txt};border-left:6px solid {txt};">'
            f'{ICONS[ag]} {LABELS[ag]}</div>'
        )
    nodes = "".join(nodes_html)

    st.markdown(
        STYLE +
        f'<div class="mind-popup"><div class="mind-title">🧠 Agent Mind Map</div>'
        f'<div style="position:relative;width:{WIDTH}px;height:{HEIGHT}px;">'
        f'<svg width="{WIDTH}" height="{HEIGHT}" style="position:absolute;top:0;left:0;pointer-events:none">{lines_svg}</svg>'
        f'{nodes}</div></div>',
        unsafe_allow_html=True,
    )

def main():
    """Main entry point for the Streamlit app."""
    logger.info("Starting R+D Intelligent Multi-Agent Assistant app.")
    setup_environment()
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
        render_chat_history(chat_container)
    MAX_RETRIES = 3
    verifier_statuses = []  # Track verifier status for each attempt
    last_verifier_content = None
    last_dicta = None
    # Main layout: advice panel on the right after 3 denials
    advice_panel_visible = (
        len(verifier_statuses) == MAX_RETRIES and all(s == "Denied" for s in verifier_statuses)
    )
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
                    logger.info(f"--- Attempt {attempt} for query: {current_query}")
                    try:
                        agents = select_agents(current_query)
                        if not agents:
                            logger.warning("Agent selection failed or no agents selected. Breaking retry loop.")
                            break
                        dicta = run_selected_agents(agents["response"]["agents_needed"], current_query)
                        status, content, rewritten_query = evaluate_with_verifier(current_query, dicta)
                        verifier_statuses.append(status)
                        last_verifier_content = content
                        last_dicta = dicta
                        if status == "Approved":
                            logger.info("Verifier approved the response. Exiting retry loop.")
                            break
                        elif status == "Denied":
                            logger.info("Verifier denied the response.")
                            if rewritten_query:
                                logger.info(f"Verifier provided a rewritten query: {rewritten_query}")
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
                                logger.warning("Verifier denied but no rewritten query provided. Breaking retry loop.")
                                st.warning(
                                    "Verifier denied but no rewritten query provided."
                                )
                                break
                        if attempt == MAX_RETRIES:
                            logger.warning("Maximum retries reached. User should refine query or try again later.")
                            st.warning(
                                "Maximum retries reached. Please refine your query or try again later."
                            )
                    except Exception as e:
                        tb = traceback.format_exc()
                        logger.error(f"Exception in main loop: {e}\nTraceback:\n{tb}")
                        st.error(f"Error: {e}\n\nTraceback:\n```\n{tb}\n```")
                        break
            # Show advice panel in right column if needed
            if advice_panel_visible:
                col1, col2 = st.columns([2,1], gap="large")
                with col2:
                    st.markdown(
                        """
                        <div style="background: linear-gradient(135deg, #0078D4 60%, #00B4FF 100%); color: #fff; border-radius: 18px; box-shadow: 0 6px 24px rgba(0,0,0,0.13); padding: 28px 24px 20px 24px; margin-top: 32px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
                        <div style="font-size:1.25rem;font-weight:700;display:flex;align-items:center;gap:8px;">🧠 Query Genius Azure</div>
                        <div style="font-size:1.05rem;margin:10px 0 0 0;">Our agents tried their best, but couldn't find a confident answer after several attempts.</div>
                        <div style="margin:18px 0 0 0;font-size:1.05rem;">
                        <b>Tips to improve your query:</b>
                        <ul style="margin:8px 0 0 18px;padding:0;">
                        <li>Be specific about what you want to know or compare.</li>
                        <li>Add context, such as timeframes, product names, or data ranges.</li>
                        <li>Clarify your goal (e.g., "summarize clinical impact" or "compare accuracy in a range").</li>
                        </ul>
                        <div style="margin-top:10px;font-size:0.98rem;opacity:0.85;">Try rephrasing your question in the chat below. When you send a new query, this advice will disappear!</div>
                        </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
            elif 'dicta' in locals() and dicta:
                summarize_results(initial_message, dicta)

def run():
    try:
        main()
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        st.error(f"Runtime error: {e}")

if __name__ == "__main__":
    run()
