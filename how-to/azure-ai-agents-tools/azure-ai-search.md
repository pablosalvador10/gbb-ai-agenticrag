# Setting Up Azure AI Search Tooling with Azure AI Agents

## 📝 Overview
Integrate your Azure AI Agent with Azure AI Search Tooling to unlock powerful enterprise search capabilities. Azure AI Search Tooling transforms your indexed data into a searchable format, enabling users to interact with and retrieve precise, context-rich information through natural language queries. When a user sends a query, the agent determines whether Azure AI Search Tooling should be used. If applicable, it sends the query to your search index—using secure, role-based access—and incorporates the retrieved results into the final response.

---

## ✅ Prerequisites

### 1. **Azure Cognitive Search Resource**
- Deploy an Azure Cognitive Search instance with your data properly indexed.

### 2. **Published Search Index**
- Ensure your search index is published and available for querying.

### 3. **Permission/Role Assignment**
- **Access to Search Resource**: Users must have at least “Read” access to the search index and connected data sources.
- **RBAC for Foundry Project**: End users must have the `AI Developer` role assigned.

---

## Step-by-Step Guide

### 1. **Access the Agent Playground**
- Navigate to the Agent Playground in your Azure AI environment.

### 2. **Create or Use an Existing Agent**
- Either create a new agent or select an existing one for configuration.

### 3. **Add a Knowledge Source**
- Click to add a knowledge source and select **Azure AI Search Tooling**.
- If the option isn’t visible:
  - Ensure your Azure Cognitive Search resource is deployed in the same resource group as your AI Agent.
  - Verify that you have the necessary permissions.

### 4. **Create a New Connection**
- Provide the following key-value pairs for the connection:
  - **`search-service-name`**: Your Azure AI Search service name.
  - **`index-name`**: Your published search AI index name.
  - **`api-key`**: Your Azure AI Search API key.
- These values can be found in your Azure AI Search resource details.

### 5. **Mark Fields as Secret**
- Check the “is secret” option for all sensitive fields to ensure secure handling of your API key and other credentials.

### 6. **Name Your Connection**
- Assign a meaningful name to your connection for easy identification.

### 7. **Start Chatting with Azure AI Search**
- Once the connection is set up, you can begin interacting with your Azure AI Agent.
