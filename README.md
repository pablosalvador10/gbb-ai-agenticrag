<!-- markdownlint-disable MD033 -->

## **🤖🧠 R&D AgenticRAG: Adaptive Multi‑Agent Retrieval for R&D Workflows**

[![Azure AI Agent Service](https://img.shields.io/badge/Azure%20AI-Agent%20Service-4A90E2.svg?logo=microsoftazure)](https://learn.microsoft.com/en-us/azure/ai-services/agents/)  [![Fabric Data Agent](https://img.shields.io/badge/Azure%20AI-Fabric%20Data%20Agent-%231072C2.svg?logo=microsoftazure)](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/fabric?tabs=csharp&pivots=overview) [![SharePoint](https://img.shields.io/badge/Azure%20AI-SharePoint-4A90E2.svg?logo=microsoftsharepoint)](https://sharepoint.microsoft.com/) [![Semantic Kernel](https://img.shields.io/badge/Semantic%20Kernel-4A90E2.svg?logo=github)](https://github.com/microsoft/semantic-kernel) [![HLS Ignited](https://img.shields.io/badge/HLS%20Ignited-blue.svg?logo=github)](https://github.com/microsoft/aihlsIgnited) [![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> This project is **part of the [HLS Ignited Program](https://github.com/microsoft/aihlsIgnited)**, a series of hands-on accelerators designed to democratize AI in healthcare. 

<div align="center">
   <a href="https://www.youtube.com/watch?v=YOUR_VIDEO_ID" target="_blank">
      <img src="https://img.youtube.com/vi/YOUR_VIDEO_ID/maxresdefault.jpg" alt="Watch the demo video on YouTube" style="max-width:100%; height:auto;">
   </a>
   <p><strong>Watch the demo video on YouTube</strong></p>
</div>

**R&D AgenticRAG** is a multi‑Agent Agentic RAG System is an enterprise‑grade research assistant that harnesses a network of specialized AI agents to power complex R&D workflows. At its core, it uses **[Azure AI Agent Service](https://learn.microsoft.com/en-us/azure/ai-services/agents/overview)** and the **Semantic Kernel Agent Framework** to plan, coordinate, and refine multi‑step reasoning pipelines; security is enforced with **[OAuth 2.0 On‑Behalf‑Of (OBO) authentication](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-on-behalf-of-flow)** to ensure each agent only accesses data the user is entitled to.

Built for scenarios where decisions hinge on both structured and unstructured information, this system seamlessly integrates [Microsoft Fabric](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/fabric) (lakehouse, warehouse, semantic model), SharePoint (documents, blueprints, policies), live web data via the [Bing Search API](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/bing-grounding?tabs=python&pivots=overview), and [Azure AI Search’s](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/azure-ai-search?tabs=azurecli%2Cpython&pivots=overview-azure-ai-search) combined semantic/vector capabilities. The result is a secure, real‑time orchestration layer that moves beyond one‑shot Q&A—iteratively rewriting queries, invoking the right tools, and cross‑validating results—to deliver concise, actionable insights that accelerate innovation in R&D environments.

## **🚀 Embracing Agentic RAG for Enterprise Agility**

> "Agentic Retrieval‑Augmented Generation (Agentic RAG) transcends these limitations by embedding autonomous AI agents into the RAG pipeline. These agents leverage agentic design patterns—reflection, planning, tool use, and multi‑agent collaboration—to dynamically manage retrieval strategies, iteratively refine contextual understanding, and adapt workflows through clearly defined operational structures."  
> — *Singh et al., [Agentic Retrieval‑Augmented Generation: A Survey on Agentic RAG](https://arxiv.org/abs/2501.09136v3)*

Enterprises today wrestle with siloed data and rigid, one‑shot retrieval pipelines that quickly go stale. Agentic RAG empowers organizations to move beyond “thought: data” reasoning—automating continuous **search**, **validation**, and **action** across all their information sources in real time.

**Strategic Playbook:**
1. **Identify a high‑impact use case** (e.g., real‑time market insights, support escalation).  
2. **Spin up a Planner Agent** using Azure AI Agent Service + Semantic Kernel to coordinate domain‑specific retriever agents.  
3. **Embed Reflection loops** to critique and refine each agent’s output before proceeding.  
4. **Wire in Function‑Calling agents** to trigger downstream actions—reports, alerts, or transactions—directly from the workflow.  
5. **Measure and iterate** on accuracy, latency, and business impact to continuously optimize your Agentic RAG deployment.  

By adopting this component‑based, autonomous approach, you transform static RAG into a self‑optimizing intelligence layer—delivering governed, real‑time insights and actions at enterprise scale.  

## **👩🏾‍💻 How to Get Started**

**First‑time users** – Open the notebooks listed under **AgenticRAG Labs**. They walk you through provisioning Azure AI Agent Service, registering Planner/Fabric/SharePoint agents, and running your first multi‑agent retrieval workflow. **Experienced engineers** – Jump straight to **Use Cases** for complete, production‑style patterns that show how AgenticRAG powers domain‑specific knowledge stores and decision support.

### **🧪 [AgenticRAG Labs](labs/README.md)**

- **Intro to Azure AI Agent Service**: 🧾 [Notebook – Getting Started with Azure AI Agent Service](labs/01-intro-azure-ai-agent-service.ipynb)  
  Provision your Azure AI Agent Service instance, configure OBO authentication, and register your first Planner agent.

- **Deep Dive into Semantic Kernel**: 🧾 [Notebook – Orchestrating Agents with Semantic Kernel](labs/02-deep-dive-semantic-kernel.ipynb)  
  Use the Semantic Kernel SDK to build multi‑step workflows, chain prompts, and implement reflection loops.

- **Azure Fabric Data Agent**: 🧾 [Notebook – Connecting Microsoft Fabric to Your Agents](labs/03-azure-fabric-data-agent.ipynb)  
  Create and register a Fabric Data Agent to transform lakehouse and warehouse tables into conversational Q&A.

- **Azure SharePoint Agent**: 🧾 [Notebook – On‑Behalf‑Of Access & SharePoint Retrieval](labs/04-azure-sharepoint-agent.ipynb)  
  Connect to SharePoint, and surface documents, blueprints, and notes in context.

### **🏭 Use Cases**

#### **📊 R&D Intelligent Assistant for MedTech**

<div align="center">

<img src="utils/images/R%2BD%20Usecase.png" alt="R&D Use Case" style="max-width:100%; height:auto; border:1px solid #d0d7de; border-radius:12px;" />

</div>
<br>

A Product Manager at a leading MedTech company uses Agentic RAG to analyze next‑gen Continuous Glucose Monitor (CGM) performance. By orchestrating multiple agents, the system delivers rapid, validated insights across diverse data sources:

1. **Query Understanding**  
   The **Planner Agent** ingests the question — “In which glucose ranges does Product A underperform compared to Product B, and what clinical impact could this have?” — using Azure OpenAI & Semantic Kernel.

2. **Query Rewriting**  
   The **Rewriter Agent** refines the phrasing (“compare CGM performance by glucose band”) to maximize retrieval relevance.

3. **Intelligent Routing**  
   Parallel retriever agents are invoked:  
   - **SharePoint Retriever** for research notes & design docs  
   - **Fabric Retriever** for clinical trial metrics  
   - **Web Retriever** (Bing) for market studies & publications  

4. **Verification Layer**  
   The **Verifier Agent** cross‑checks results for consistency, flags discrepancies, and triggers corrective re‑queries.

5. **Insight Synthesis**  
   The **Planner Agent** consolidates all validated data into a concise summary and delivers actionable recommendations back to the user.


## 📚 More Resources

- **[Azure AI Agent Service](https://learn.microsoft.com/en-us/azure/ai-services/agents/overview)** – Official overview and getting‑started guide for Azure AI Agent Service.  
- **[Semantic Kernel](https://github.com/microsoft/semantic-kernel)** – Open‑source SDK and docs for building and orchestrating AI agents.  
- **[Fabric Data Agent](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/fabric?tabs=csharp&pivots=overview)** – How‑to guide on connecting Microsoft Fabric to your Agentic RAG pipeline.  
- **[SharePoint Data Agent](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/sharepoint?tabs=csharp&pivots=overview)** – Steps to configure OBO and surface SharePoint content via agents.  
- **[Grounding with Bing Search](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/bing-grounding?tabs=python&pivots=overview)** – Documentation for integrating live web search into your workflows.  
- **[Azure AI Search tool](https://learn.microsoft.com/en-us/azure/search/semantic-vector-search-overview)** – Semantic and vector search capabilities to enrich retrieval.  

<br>

> [!IMPORTANT]  
> This software is provided for demonstration purposes only. It is not intended to be relied upon for any production workload. The creators of this software make no representations or warranties of any kind, express or implied, about the completeness, accuracy, reliability, suitability, or availability of the software or related content. Any reliance placed on such information is strictly at your own risk.
