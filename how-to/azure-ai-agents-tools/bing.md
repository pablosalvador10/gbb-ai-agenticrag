# Setting Up Bing Integration (Tool) with Azure AI Agents

## 📝 Overview

Grounding with Bing Search enables your Azure AI Agents to incorporate real-time public web data when generating responses. By leveraging Bing Search, your agent can fetch the latest information—such as top news or industry updates—and return relevant, cited content. 

When a user sends a query, the agent first determines if it should invoke Bing Search. If so, it sends a Bing search query (using only your resource key for billing and rate limiting) and retrieves search results. These results are then used to generate a final, human-readable response that includes required citations and links, as specified by Microsoft’s use and display requirements.

> **Important**: Usage of Grounding with Bing Search can incur additional costs. For pricing and legal details, review the [Bing Grounding Terms](https://www.microsoft.com).

---

## ✅ Prerequisites

### 1. **Grounding with Bing Search Resource**
- Create a Grounding with Bing Search resource using the Azure portal or a code-first approach.
- Ensure you have **Owner** or **Contributor** permissions to register the resource provider `Microsoft.Bing` if using a code-first approach.

### 2. **Azure AI Agent Setup**
- Ensure you have an Azure AI Agent created (via the Agent Playground or quickstart).

### 3. **Permission/Role Assignment**
- **Access to Bing Search**: Users do not have access to raw search content; instead, they receive model-generated responses that include citations and links.
- **RBAC for Foundry Project**: End users must have the `AI Developer` role assigned.

### 4. **Supported Models**
- Grounding with Bing Search currently works with specific Azure OpenAI models (e.g., `gpt-3.5-turbo-0125`, `gpt-4-0125-preview`, etc.).

---

## Step-by-Step Guide

### 1. **Access the Agent Playground**
- Navigate to the Agent Playground in your Azure AI environment.

### 2. **Create or Use an Existing Agent**
- Either create a new agent or select an existing one to configure.

### 3. **Add a Knowledge Source**
- Click to add a knowledge source and select **Grounding with Bing Search**.
- If you don’t see this option:
  - Verify that your resource has been created in the same resource group as your AI Agent.
  - Ensure you have the necessary permissions.

### 4. **Create a New Connection**
- Provide the required key-value pairs for the connection:
  - **`resource-key`**: Your Bing resource key.
  - **`endpoint`**: Your Bing search endpoint (typically provided in your resource details).
- Example endpoint format: