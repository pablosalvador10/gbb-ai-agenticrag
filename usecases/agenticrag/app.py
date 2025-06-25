import asyncio
import json
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from concurrent.futures import as_completed
from typing import Any, Dict, List, Optional, Tuple

import dotenv
import streamlit as st
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

from src.aoai.aoai_helper import AzureOpenAIManager
from usecases.agenticrag.aoaiAgents.base import AzureOpenAIAgent
from usecases.agenticrag.prompts import (
    SYSTEM_PROMPT_PLANNER,
    SYSTEM_PROMPT_SUMMARY,
    SYSTEM_PROMPT_VERIFIER,
    generate_final_summary,
    generate_user_prompt,
    generate_verifier_prompt,
)
from usecases.agenticrag.settings import (
    AZURE_AI_FOUNDRY_AGENT_IDS,
    AZURE_AI_FOUNDRY_FABRIC_AGENT,
    AZURE_AI_FOUNDRY_SHAREPOINT_AGENT,
    AZURE_AI_FOUNDRY_WEB_AGENT,
    CUSTOM_AGENT_NAMES,
    PLANNER_AGENT,
    SUMMARY_AGENT,
    VERIFIER_AGENT,
)
from usecases.agenticrag.tools import run_agent
from utils.ml_logging import get_logger

# --- Logging ---
logger = get_logger()

# --- Type Aliases ---
AgentStatusDict = Dict[str, str]
AgentResponseDict = Dict[str, Optional[str]]

# --- UI Constants ---
PLANNER = "PlannerAgent"
SP = "SharePointDataRetrievalAgent"
WEB = "BingDataRetrievalAgent"
FAB = "FabricDataRetrievalAgent"
VERIFY = "VerifierAgent"
SUMMARY = "SummaryAgent"

ICONS = {
    PLANNER: "🧩",
    SP: "📖",
    WEB: "🔎",
    FAB: "🛠️",
    VERIFY: "✅",
    SUMMARY: "📝",
}
LABELS = {
    PLANNER: "Planner",
    SP: "SP",
    WEB: "Bing",
    FAB: "Fabric",
    VERIFY: "Verifier",
    SUMMARY: "Summ..",
}

WIDTH, HEIGHT = 300, 420
NODE_W, NODE_H = 96, 36
COL_LEFT = 20
COL_CENTER = WIDTH // 2 - NODE_W // 2
COL_RIGHT = WIDTH - NODE_W - 20

NODE_POS = {
    PLANNER: (COL_CENTER, 24),
    SP: (COL_LEFT, 120),
    WEB: (COL_CENTER, 120),
    FAB: (COL_RIGHT, 120),
    VERIFY: (COL_CENTER, 230),
    SUMMARY: (COL_CENTER, 335),
}

EDGES = [
    (PLANNER, SP),
    (PLANNER, WEB),
    (PLANNER, FAB),
    (SP, VERIFY),
    (WEB, VERIFY),
    (FAB, VERIFY),
    (VERIFY, SUMMARY),
]

# restore glow and approved color
STATUS_COLOURS = {
    "pending": ("#f5f5f5", "#9e9e9e", ""),
    "running": ("#fff7d1", "#e6b800", "0 0 16px 4px #ffe066"),
    "done": ("#e8f5e9", "#00b050", "0 0 10px 2px #b2f2bb"),
    "error": ("#ffebee", "#d32f2f", "0 0 16px 4px #ff6b6b"),
    "denied": ("#ffebee", "#d32f2f", "0 0 16px 4px #ff6b6b"),
    "approved": ("#e8f5e9", "#00b050", "0 0 16px 4px #69f0ae"),
}


def setup_environment() -> None:
    """Initialize environment variables and session state."""
    logger.info("Setting up environment and initialising session state.")
    dotenv.load_dotenv(".env", override=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "project_client" not in st.session_state:
        logger.info("Initialising Azure AI Project Client.")
        st.session_state.project_client = AIProjectClient.from_connection_string(
            credential=DefaultAzureCredential(),
            conn_str=os.environ["AZURE_AI_FOUNDRY_CONNECTION_STRING"],
        )

    for agent_key, config_path in CUSTOM_AGENT_NAMES.items():
        if agent_key not in st.session_state:
            logger.info(f"Loading agent '{agent_key}' from config: {config_path}")
            st.session_state[agent_key] = AzureOpenAIAgent(config_path=config_path)


def render_chat_history(chat_container: Any) -> None:
    """Render the chat history in the Streamlit container."""
    logger.debug("Rendering chat history.")
    for msg in st.session_state.chat_history:
        role = msg["role"].lower()
        content = msg["content"]
        avatar = msg.get("avatar", "🤖")

        # show info & system messages
        if role in ("info", "system"):
            st.info(content, icon=avatar)
        elif role == "user":
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(content, unsafe_allow_html=True)
        elif role == "assistant":
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(content, unsafe_allow_html=True)
        else:  # agent responses
            with st.expander(f"{avatar} {msg['role']} says...", expanded=False):
                st.markdown(content, unsafe_allow_html=True)


def select_agents(current_query: str) -> Optional[Dict[str, Any]]:
    """Select which agents are needed for the query."""
    logger.info(f"Selecting agents for query: {current_query}")
    try:
        st.session_state.agent_status[PLANNER] = "running"
        render_agent_mind_map(st.session_state.agent_status)

        agents = asyncio.run(
            st.session_state[PLANNER_AGENT].run(
                user_prompt=generate_user_prompt(current_query),
                conversation_history=[],
                system_message_content=SYSTEM_PROMPT_PLANNER,
                response_format="json_object",
            )
        )
        logger.debug(f"Planner agent response: {agents}")

        st.session_state.agent_status[PLANNER] = "done"
        render_agent_mind_map(st.session_state.agent_status)

        if not agents or not agents["response"].get("agents_needed"):
            st.warning("No agents selected. Please refine your query.")
            return None
        # Display an info message so the user sees the selected agents and justification
        st.info(
            f"**Agents Selected:** {', '.join(agents['response']['agents_needed'])}\n"
            f"**Justification:** {agents['response']['justification']}",
            icon="ℹ️",
        )
        return agents

    except Exception as e:
        st.error(f"Planner agent selection failed: {e}")
        logger.exception("Planner agent selection failed")
        return None


def run_selected_agents(
    agents_needed: List[str], current_query: str
) -> AgentResponseDict:
    """Run selected retriever agents in parallel and return their responses."""
    logger.info(f"Running agents in parallel: {agents_needed}")
    dicta: AgentResponseDict = {}
    results: List[Tuple[str, Optional[str], Optional[str]]] = []

    local_status: AgentStatusDict = {a: "pending" for a in agents_needed}
    render_agent_mind_map({**st.session_state.agent_status, **local_status})

    def worker(agent_id: str, query: str, pc: AIProjectClient, name: str):
        try:
            return "running", None, run_agent(pc, agent_id, query)
        except Exception as exc:
            logger.error(f"{name} failed: {exc}")
            return "error", str(exc), (None, None)

    with ThreadPoolExecutor(max_workers=len(agents_needed)) as executor:
        future_map = {}
        for ag in agents_needed:
            if ag not in AZURE_AI_FOUNDRY_AGENT_IDS:
                logger.error(f"{ag} missing in AZURE_AI_FOUNDRY_AGENT_IDS.")
                results.append((ag, None, "Not configured"))
                local_status[ag] = "error"
                continue

            fid = AZURE_AI_FOUNDRY_AGENT_IDS[ag]
            fut = executor.submit(
                worker, fid, current_query, st.session_state.project_client, ag
            )
            future_map[fut] = ag

        for fut in as_completed(future_map):
            ag = future_map[fut]
            status_flag, err, (resp, _) = fut.result()
            local_status[ag] = (
                "done" if status_flag == "running" and resp else status_flag
            )
            render_agent_mind_map({**st.session_state.agent_status, **local_status})
            results.append((ag, resp, err))

    # Persist + UI (expander) for each agent in original order
    for ag in agents_needed:
        item = next((x for x in results if x[0] == ag), None)
        if not item:
            continue
        _, resp, err = item
        avatar = ICONS.get(ag, "🤖")
        with st.expander(f"{avatar} {ag} says...", expanded=False):
            if err or resp is None:
                st.warning(f"Agent {ag} failed: {err or 'No response.'}")
            else:
                st.markdown(resp, unsafe_allow_html=True)

        st.session_state.chat_history.append(
            {
                "role": ag,
                "content": err or resp or "No response",
                "avatar": avatar,
                "error": bool(err or resp is None),
            }
        )
        if resp:
            dicta[ag] = resp

    # Update global status
    for k, v in local_status.items():
        st.session_state.agent_status[k] = v

    logger.info(f"Collected retriever responses: {list(dicta.keys())}")
    return dicta


def evaluate_with_verifier(
    current_query: str, dicta: AgentResponseDict
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Run verifier agent and return its decision."""
    logger.info("Running verifier agent")
    st.session_state.agent_status[VERIFY] = "running"
    render_agent_mind_map(st.session_state.agent_status)

    try:
        evaluation = asyncio.run(
            st.session_state[VERIFIER_AGENT].run(
                user_prompt=generate_verifier_prompt(
                    current_query,
                    fabric_data_summary=dicta.get(AZURE_AI_FOUNDRY_FABRIC_AGENT),
                    sharepoint_data_summary=dicta.get(
                        AZURE_AI_FOUNDRY_SHAREPOINT_AGENT
                    ),
                    bing_data_summary=dicta.get(AZURE_AI_FOUNDRY_WEB_AGENT),
                ),
                conversation_history=[],
                system_message_content=SYSTEM_PROMPT_VERIFIER,
                response_format="json_object",
                max_tokens=400,
            )
        )
    except Exception as exc:
        logger.exception("Verifier agent crashed")
        st.session_state.agent_status[VERIFY] = "error"
        render_agent_mind_map(st.session_state.agent_status)
        st.error(f"Verifier agent exception: {exc}")
        return None, None, None

    logger.debug(f"Verifier raw: {evaluation}")
    response_obj = None
    if isinstance(evaluation, dict) and "response" in evaluation:
        inner = evaluation["response"]
        if isinstance(inner, str):
            try:
                response_obj = json.loads(inner)
            except json.JSONDecodeError:
                pass
        elif isinstance(inner, dict):
            response_obj = inner

    if not response_obj or "status" not in response_obj:
        st.session_state.agent_status[VERIFY] = "error"
        render_agent_mind_map(st.session_state.agent_status)
        st.error(f"Verifier returned unexpected format: {evaluation}")
        return None, None, None

    status = response_obj["status"]
    resp_txt = response_obj.get("response", "")
    rewritten_query = response_obj.get("rewritten_query", "")

    st.session_state.agent_status[VERIFY] = (
        "approved" if status == "Approved" else "denied"
    )
    render_agent_mind_map(st.session_state.agent_status)

    avatar = "✅" if status == "Approved" else "❌"
    with st.expander(f"{avatar} {VERIFY} says...", expanded=False):
        st.markdown(
            f"**{status}:** {resp_txt if status == 'Approved' else rewritten_query}",
            unsafe_allow_html=True,
        )

    st.session_state.chat_history.append(
        {
            "role": VERIFY,
            "content": resp_txt if status == "Approved" else rewritten_query,
            "avatar": avatar,
        }
    )

    return status, resp_txt, rewritten_query


def summarize_results(
    initial_message: str, dicta: AgentResponseDict, chat_container: Any
) -> None:
    """Summarize results and reply as assistant."""
    logger.info("Running summary agent")
    st.session_state.agent_status[SUMMARY] = "running"
    render_agent_mind_map(st.session_state.agent_status)

    summary_content = asyncio.run(
        st.session_state[SUMMARY_AGENT].run(
            user_prompt=generate_final_summary(initial_message, dicta=dicta),
            conversation_history=[],
            system_message_content=SYSTEM_PROMPT_SUMMARY,
            max_tokens=3000,
        )
    )
    logger.debug(f"Summary raw: {summary_content}")

    summary_resp = None
    if isinstance(summary_content, dict) and "response" in summary_content:
        inner = summary_content["response"]
        summary_resp = inner if isinstance(inner, str) else inner.get("response", "")

    if not summary_resp:
        st.session_state.agent_status[SUMMARY] = "error"
        render_agent_mind_map(st.session_state.agent_status)
        with chat_container:
            st.error("Summary agent failed to produce a response.")
        return

    st.session_state.agent_status[SUMMARY] = "done"
    render_agent_mind_map(st.session_state.agent_status)

    with chat_container:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(summary_resp, unsafe_allow_html=True)
    st.session_state.chat_history.append(
        {
            "role": "assistant",
            "content": summary_resp,
            "avatar": "🤖",
        }
    )
    st.toast("📧 An email with the results of your query has been sent!", icon="📩")


STYLE_FLOAT = f"""
<style>
.mind-float {{
    position: fixed;
    left: 24px;
    top: 50%;
    transform: translateY(-50%);
    width: {WIDTH+40}px;
    z-index: 9999;
    background: #fffffffa;
    padding: 20px 24px 28px 24px;
    border-radius: 20px;
    border: 3px solid #0078D4;
    box-shadow: 0 8px 28px rgba(0,0,0,.18);
    font-family: 'Segoe UI', Tahoma, sans-serif;
}}
.mind-title  {{ font-weight:700; font-size:1.15rem; color:#0078D4; margin-bottom:10px; }}
.node        {{ position:absolute; width:{NODE_W}px; height:{NODE_H}px; border-radius:12px;
               display:flex; align-items:center; justify-content:center; gap:4px;
               font-weight:600; transition:box-shadow .25s,background .25s; }}
.stExpander {{ box-shadow: none !important; background: transparent !important; }}
</style>
"""


def render_agent_mind_map(status_dict: AgentStatusDict) -> None:
    """Render the agent mind map visualization."""
    if not status_dict:
        return

    # build edges svg
    svg_lines = []
    for src, dst in EDGES:
        x1, y1 = NODE_POS[src][0] + NODE_W // 2, NODE_POS[src][1] + NODE_H // 2
        x2, y2 = NODE_POS[dst][0] + NODE_W // 2, NODE_POS[dst][1] + NODE_H // 2
        svg_lines.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="#0078D4" stroke-width="2.4" stroke-dasharray="6,4" />'
        )
    line_svg = "".join(svg_lines)

    # build nodes with glow
    node_divs = []
    for ag in [PLANNER, SP, WEB, FAB, VERIFY, SUMMARY]:
        st_key = status_dict.get(ag, "pending" if ag != PLANNER else "done")
        bg, txt, glow = STATUS_COLOURS.get(st_key, STATUS_COLOURS["pending"])
        x, y = NODE_POS[ag]
        node_divs.append(
            f'<div class="node" style="left:{x}px;top:{y}px;'
            f"background:{bg};color:{txt};border-left:6px solid {txt};"
            f'box-shadow:{glow};">'
            f"{ICONS[ag]} {LABELS[ag]}</div>"
        )
    nodes_html = "".join(node_divs)

    st.markdown(
        STYLE_FLOAT + f'<div class="mind-float">'
        f'<details open><summary style="font-size:1.1rem;font-weight:600;cursor:pointer;">🗺️ Agent Workflow Visualization</summary>'
        f'<div class="mind-title" style="margin-top:10px;">&nbsp;</div>'
        f'<div style="position:relative;width:{WIDTH}px;height:{HEIGHT}px;">'
        f'<svg width="{WIDTH}" height="{HEIGHT}" style="position:absolute;top:0;left:0;pointer-events:none">{line_svg}</svg>'
        f"{nodes_html}</div></details></div>",
        unsafe_allow_html=True,
    )


def main() -> None:
    """Main entry point for the Streamlit app."""
    try:
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
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-weight: 600;
                color: #FFFFFF;
                letter-spacing: 0.8px;
            }
            .titleContainer h3 {
                margin: 8px 0 0;
                font-size: 1rem;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
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

        agents_for_map = [PLANNER, SP, WEB, FAB, VERIFY, SUMMARY]
        if "agent_status" not in st.session_state:
            st.session_state.agent_status = {a: "pending" for a in agents_for_map}

        render_agent_mind_map(st.session_state.agent_status)

        user_input = st.chat_input("Ask your R+D query here...")
        chat_container = st.container(height=500)

        with chat_container:
            render_chat_history(chat_container)

            MAX_RETRIES = 3
            verifier_statuses: List[Optional[str]] = []
            current_query: str = ""

            if user_input:
                st.session_state.chat_history.append(
                    {"role": "user", "content": user_input, "avatar": "🧑‍💻"}
                )
                with st.chat_message("user", avatar="🧑‍💻"):
                    st.markdown(user_input, unsafe_allow_html=True)

                initial_message = user_input
                current_query = user_input

                for attempt in range(1, MAX_RETRIES + 1):
                    with st.spinner("Agents collaborating..."):
                        logger.info(f"Attempt {attempt} – query: {current_query}")
                        try:
                            agents_dict = select_agents(current_query)
                            if not agents_dict:
                                break

                            selected_agents = agents_dict["response"]["agents_needed"]
                            for a in selected_agents:
                                st.session_state.agent_status[a] = "running"
                            render_agent_mind_map(st.session_state.agent_status)

                            dicta = run_selected_agents(selected_agents, current_query)

                            for a in selected_agents:
                                if st.session_state.agent_status[a] == "running":
                                    st.session_state.agent_status[a] = "done"
                            render_agent_mind_map(st.session_state.agent_status)

                            status, content, rewritten = evaluate_with_verifier(
                                current_query, dicta
                            )
                            verifier_statuses.append(status)

                            if status == "Approved":
                                summarize_results(
                                    initial_message, dicta, chat_container
                                )
                                break
                            elif status == "Denied" and rewritten:
                                current_query = rewritten
                                st.session_state.chat_history.append(
                                    {
                                        "role": "system",
                                        "content": f"Verifier requested retry with rewritten query:\n\n{rewritten}",
                                        "avatar": "❌",
                                    }
                                )
                                st.info(
                                    f"Verifier requested retry with rewritten query:\n\n{rewritten}",
                                    icon="ℹ️",
                                )
                            else:
                                st.warning(
                                    "Verifier denied but no rewritten query provided. Stopping."
                                )
                                break
                        except Exception as e:
                            logger.error(f"Error in agent workflow: {e}")
                            st.error(f"Error in agent workflow: {e}")
                            break
                else:
                    st.warning("Maximum retries reached. Please refine your query.")
    except Exception as e:
        logger.error(f"Runtime error in main: {e}")
        st.error(f"Runtime error: {e}")
    finally:
        logger.info("App execution finished.")


def run() -> None:
    """Run the Streamlit app."""
    try:
        main()
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        st.error(f"Runtime error: {e}")


if __name__ == "__main__":
    run()
