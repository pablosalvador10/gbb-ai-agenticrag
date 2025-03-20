# Setting Up Fabric Integration (Tool) with Azure AI Agents

## 📝 Overview

Integrate your Azure AI Agent with Fabric `Data agent` to unlock powerful data analysis capabilities. Fabric `Data Agent` transforms enterprise data into conversational Q&A systems, allowing users to interact with data through chat and uncover actionable insights effortlessly.

When a user sends a query, the Azure AI Agent first determines if Fabric `Data agent` should be leveraged. If so, it uses the end user’s identity to generate queries over accessible data, and then returns responses based on the queried results. With **on-behalf-of (OBO) authorization**, this integration simplifies secure access to enterprise data in Fabric while ensuring robust protection and proper access control.

## ✅ Prerequisites

- **Published Fabric AI Skill**: Ensure you have a published Fabric `Data Agent` (before called AI Skill), or use the provided Fabric link to access pre-created skills.
- **Permission/Role Assignment**:
  - **Access to AI Skill**: Users must have at least “Read” access to the `Data Agent` and connected data sources.
  - **RBAC for Foundry Project**: End users must have the `AI Developer` role assigned.

## Step-by-Step Guide

1. **Access the Agent Playground**:
   - Navigate to the Agent Playground in your Azure AI environment.

2. **Create or Use an Existing Agent**:
   - Either create a new agent or select an existing one to configure.

3. **Add a Knowledge Source**:
   - Click to add a knowledge source and select **Microsoft Fabric**.
   - If you don’t see this option, ensure the feature flag `&flight=MicrosoftFabricKnowledge` is enabled.

4. **Create a New Connection**:
   - Provide the following key-value pairs for the connection:
     - `workspace-id`: `xxx`
     - `artifact-id`: `xxx`
     - `audience`: `xxx`
   - These values can be found in your AI Skill endpoint. The endpoint format is:
     ```
     https://daily.powerbi.com/groups/<workspace_id>/aiskills/<artifact-id>
     ```

5. **Mark Fields as Secret**:
   - Check the “is secret” option for all fields to ensure secure handling of sensitive information.

6. **Name Your Connection**:
   - Assign a meaningful name to your connection for easy identification.

7. **Start Chatting with Fabric**:
   - Once the connection is set up, you can begin interacting with Fabric through your Azure AI Agent.
