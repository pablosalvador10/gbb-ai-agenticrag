import os

# Load environment variables early
from dotenv import load_dotenv

load_dotenv(".env", override=True)

# Streamlit session keys
CHAT_HISTORY_KEY = "chat_history"
AGENTS_KEY = "agents"

# Agent names and IDs
VERIFIER_AGENT = "VerifierAgent"
PLANNER_AGENT = "PlannerAgent"
SUMMARY_AGENT = "SummaryAgent"
AZURE_AI_FOUNDRY_SHAREPOINT_AGENT = "SharePointDataRetrievalAgent"
AZURE_AI_FOUNDRY_FABRIC_AGENT = "FabricDataRetrievalAgent"
AZURE_AI_FOUNDRY_WEB_AGENT = "BingDataRetrievalAgent"

CUSTOM_AGENT_NAMES = {
    PLANNER_AGENT: "usecases/agenticrag/aoaiAgents/agent_store/planner_agent.yaml",
    SUMMARY_AGENT: "usecases/agenticrag/aoaiAgents/agent_store/summary_agent.yaml",
    VERIFIER_AGENT: "usecases/agenticrag/aoaiAgents/agent_store/verifier_agent.yaml",
}

AZURE_AI_FOUNDRY_AGENT_IDS = {
    AZURE_AI_FOUNDRY_SHAREPOINT_AGENT: "asst_S0hdvZFiiBDBLZQLpewl1eWE",
    AZURE_AI_FOUNDRY_FABRIC_AGENT: "asst_iyRaKRHpkLsWBByZJR80b5KC",
    AZURE_AI_FOUNDRY_WEB_AGENT: "asst_CmPBsqtQXXtDsaiQPsN0gLyH",
}
