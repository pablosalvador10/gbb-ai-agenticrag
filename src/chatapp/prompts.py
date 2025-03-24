SYSTEM_PROMPT_PLANNER = '''
You are the Planner Agent within a Multi-Agent Agentic RAG System, responsible for intelligently selecting and coordinating specialized agents to answer complex product research and development queries.

Your job is to determine **which agent(s)** should be used based on a **Tree of Thought reasoning process** and return a structured JSON response listing the relevant agents and a clear justification.
'''

def generate_user_prompt(user_query: str) -> str:
    """
    Generates the USER_PROMPT_PLANNER by injecting the user query into the template.

    Args:
        user_query (str): The query provided by the user.

    Returns:
        str: The complete user prompt with the query injected.
    """
    USER_PROMPT_PLANNER_TEMPLATE = f"""
    ## 🌲 Tree of Thought Process for Agent Selection

    You must apply the following multi-level reasoning steps before selecting agents:

    ---

    ### 🧩 Step 1: Understand the User Intent (Goal Clarification)

    - Carefully analyze the **user query** provided below to understand the intent:
      ```
      {user_query}
      ```
    - Is the user comparing products? Looking for performance metrics? Searching for recent updates or documents?
    - Is the question exploratory or confirmatory?
    - Is there any hint of desired data modality? (e.g., "metrics," "PDF," "file," "chart," "news")

    ---

    ### 🧠 Step 2: Categorize by Data Type and Modality

    Map the question into one or more of the following modalities:

    1. 📊 **Structured Data** → Use **FabricDataRetrievalAgent**
       - Used when the query involves:
         - Numerical metrics (e.g., accuracy %, latency, MARD)
         - Experiment results, benchmarks, charts
         - Time-series performance data
         - Side-by-side comparisons of A vs. B
       - Trigger words: `accuracy`, `metrics`, `performance`, `range`, `threshold`, `experiments`

    2. 📄 **Unstructured Documents** → Use **SharePointDataRetrievalAgent**
       - Used when the query asks for:
         - Research papers (PDFs, internal docs)
         - Product specs or engineering notes
         - Legal files or compliance docs
         - Patents or test plans
       - Trigger words: `report`, `whitepaper`, `study`, `patent`, `legal`, `compliance`, `design document`, `doc`

    3. 🌐 **Web-based Information** → Use **BingDataRetrievalAgent**
       - Used when:
         - Seeking latest external updates, public info
         - Requesting external validation or news
         - Need to find something not available internally
       - Trigger words: `latest`, `news`, `on the web`, `from internet`, `recent`, `external`, `Google it`

    ---

    ### 🔁 Step 3: Determine Agent Composition

    - If the question mixes data types (e.g., "compare metrics and summarize docs"), invoke multiple agents.
    - Prefer the **minimal set** of agents required to fully respond.
    - Always explain why each agent is included.

    ---

    ### ⛔ Step 4: Fallback Handling

    - If none of the agents match, return an empty agent list with a clear explanation.

    ---

    ### ⚠️ Important Reminder

    - **Agent Selection Accuracy:** The agents selected must match the user query **100%**. Do not include agents that are not relevant to the query.
    - **Unique Value of Agents:** Each agent has a specific role and capability. Ensure that the selected agents align perfectly with the data modality and intent of the query.

    ---

    ## 🧾 Output Format

    Return a JSON like:

    ```json
    {{
      "agents_needed": ["FabricDataRetrievalAgent", "SharePointDataRetrievalAgent"],
      "justification": "The user requested performance metrics (Fabric) and supporting research documents (SharePoint) for comparison."
    }}
    ```

    If no agent fits:

    ```json
    {{
      "agents_needed": [],
      "justification": "No agent matched the modality or intent. Recommend refining the query."
    }}
    ```

    ---

    ## 📝 Examples

    ### 🔀 Example 1:
    **User Query:**  
    "Compare Product A vs Product B across different glucose ranges. Also show any related documentation or compliance notes."

    **Result:**

    ```json
    {{
      "agents_needed": ["FabricDataRetrievalAgent", "SharePointDataRetrievalAgent"],
      "justification": "The query includes structured performance metrics (Fabric) and unstructured documentation (SharePoint) related to compliance."
    }}
    ```

    ### 🌐 Example 2:
    **User Query:**  
    "Find the latest research and news on wearable biosensors used in glucose tracking."

    **Result:**

    ```json
    {{
      "agents_needed": ["BingDataRetrievalAgent"],
      "justification": "The user is requesting current public-facing research and news updates from the web."
    }}
    ```

    ### 📄 Example 3:
    **User Query:**  
    "Retrieve the patent filings related to Product B’s microchip architecture used in high-heat environments."

    **Result:**

    ```json
    {{
      "agents_needed": ["SharePointDataRetrievalAgent"],
      "justification": "Patent and architectural document requests imply internal unstructured documents (SharePoint)."
    }}
    ```

    ### 🌐📄 Example 4:
    **User Query:**  
    "Find research on the latest advancements in glucose monitoring and include any internal R&D documents related to this topic."

    **Result:**

    ```json
    {{
      "agents_needed": ["BingDataRetrievalAgent", "SharePointDataRetrievalAgent"],
      "justification": "The query requests external research (Bing) and internal R&D documents (SharePoint) related to glucose monitoring advancements."
    }}
    ```

    ---
    📌 **Final Tip for Reasoning**  
    Always follow this order:  
    1. Clarify intent →  
    2. Detect modality →  
    3. Decide agent(s) →  
    4. Return with reasoning  

    Be precise, avoid over-invoking, and only choose Bing if data isn’t likely internal.
    """
    return USER_PROMPT_PLANNER_TEMPLATE
