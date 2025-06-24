<!-- markdownlint-disable MD033 -->

## **🤖🧠 R&D AgenticRAG: Adaptive Multi‑Agent Retrieval System for R&D Workflows**

[![Azure AI Foundry Agent Service](https://img.shields.io/badge/Azure%20AI-Foundry%20Agent%20Service-4A90E2.svg?logo=microsoftazure)](https://learn.microsoft.com/en-us/azure/ai-services/agents/overview)  [![Fabric Data Agent](https://img.shields.io/badge/Azure%20AI-Fabric%20Data%20Agent-%231072C2.svg?logo=microsoftazure)](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/fabric?tabs=csharp&pivots=overview) [![Semantic Kernel](https://img.shields.io/badge/Semantic%20Kernel-4A90E2.svg?logo=github)](https://github.com/microsoft/semantic-kernel) [![HLS Ignited](https://img.shields.io/badge/HLS%20Ignited-blue.svg?logo=github)](https://github.com/microsoft/aihlsIgnited) [![MIT License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> This project is **part of the [HLS Ignited Program](https://github.com/microsoft/aihlsIgnited)**, a series of hands-on accelerators designed to democratize AI in healthcare. 

[![YouTube](https://github.com/pablosalvador10/gbb-ai-agenticrag/blob/9997a65135bdac229f6c48995ea00003534a9296/utils/images/youtube.png?raw=true)](https://www.youtube.com/watch?v=eJ_eS-V_Bvk)

<div align="center">

**▶️ [Watch the demo video on YouTube](https://www.youtube.com/watch?v=eJ_eS-V_Bvk)**

</div>

**R&D AgenticRAG** is an enterprise-grade *Agentic Retrieval-Augmented Generation* system that orchestrates a **network of specialised AI agents** to automate complex research & development tasks. At its core, it uses **[Azure AI Foundry Agent Service](https://learn.microsoft.com/en-us/azure/ai-services/agents/overview)** and the **Semantic Kernel Agent Framework** to plan, coordinate, and refine multi‑step reasoning pipelines; security is enforced with **[OAuth 2.0 On‑Behalf‑Of (OBO) authentication](https://learn.microsoft.com/en-us/azure/active-directory/develop/v2-oauth2-on-behalf-of-flow)** to ensure each agent only accesses data the user is entitled to.

Built for scenarios where decisions hinge on both structured and unstructured information, this system seamlessly integrates [Microsoft Fabric](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/fabric) (lakehouse, warehouse, semantic model), **SharePoint (documents, blueprints, policies), live web data via the [Bing Search API](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/bing-grounding?tabs=python&pivots=overview), and [Azure AI Search’s](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/azure-ai-search?tabs=azurecli%2Cpython&pivots=overview-azure-ai-search) combined semantic/vector capabilities. The result is a secure, real‑time orchestration layer that moves beyond one‑shot Q&A—iteratively rewriting queries, invoking the right tools, and cross‑validating results—to deliver concise, actionable insights that accelerate innovation in R&D environments.

**SharePoint tool/connector available soon

## **🚀 Embracing Agentic RAG for Enterprise Agility**

> "Agentic Retrieval‑Augmented Generation (Agentic RAG) transcends these limitations by embedding autonomous AI agents into the RAG pipeline. These agents leverage agentic design patterns—reflection, planning, tool use, and multi‑agent collaboration—to dynamically manage retrieval strategies, iteratively refine contextual understanding, and adapt workflows through clearly defined operational structures."  
> — *Singh et al., [Agentic Retrieval‑Augmented Generation: A Survey on Agentic RAG](https://arxiv.org/abs/2501.09136v3)*

Enterprises today wrestle with siloed data and rigid, one‑shot retrieval pipelines that quickly go stale. Agentic RAG empowers organizations to move beyond “thought: data” reasoning—automating continuous **search**, **validation**, and **action** across all their information sources in real time. By adopting this component‑based, autonomous agentic retrieval approach, you transform static RAG into a self‑optimizing intelligence layer—delivering governed, real‑time insights and actions at enterprise scale. Put simply, the AI does all the legwork—locating, validating, and polishing the critical retrieval step. We know LLM/SLM models are formidable, but only when they receive the right context. Put simply, the AI does all the legwork—locating, validating, and polishing the critical retrieval step. We know LLMs/SLMs are formidable, but only when they receive the right context. **Agentic RAG aims to automate that hand-off, providing an LLM with the precise information it needs at exactly the right moment.** - Fresh from Build 2025: if you’re interested in this space, I highly recommend exploring [Azure AI Search’s approach](https://techcommunity.microsoft.com/blog/azure-ai-services-blog/introducing-agentic-retrieval-in-azure-ai-search/4414677) and the latest developments in agentic retrieval. 

## **🤖 Building Agentic Systems in Azure**

Our approach in ths repo is to keep it simple and to the point, starting with the development of robust, scalable **enterprise single agents** using the Azure AI Foundry Agent Service. These production-ready agents come equipped with integrated tools, persistent memory, traceability, and isolated execution—providing a solid foundation before scaling up.

Then, of course, we'll tackle communication patterns between single agents. Just as clear conversation drives human collaboration, real-time event exchange between agents unlocks their full potential as a cohesive system. By leveraging frameworks like **Semantic Kernel**—or even crafting your own— you can establish an event-driven architecture that seamlessly ties everything together (single-agents) to build multi-agent systems. Here is my high level formula to build MaS

```text
Multi-Agent Architecture = Σ (Production-Ready Single Agents [tools, memory, traceability, isolation]) + Preferred Framework (e.g., Semantic Kernel, AutoGen)
```

**Breaking It Down**

- **Step 1:** Build robust, scalable single agents with the **Azure AI Foundry Agent Service**, managing them as micro-services.
- **Step 2:** For complex tasks, deploy a fleet of specialized agents that communicate seamlessly via an event-driven framework of your choice.

## **👩🏾‍💻 How to Get Started**

**First‑time users** – Open the notebooks listed under **AgenticRAG Labs**. They walk you through provisioning Azure AI Foundry Agent Service and running your first multi‑agent retrieval workflow. **Experienced engineers** – Jump straight to **Use Cases**- where we showcase how to build AgenticRAG powers domain‑specific knowledge stores and decision support.

### **🧪 [AgenticRAG Labs](labs/README.md)**

- **Intro to Azure AI Foundry Agent Service**: 🧾 [Notebook – Building Single Agents with Azure AI Foundry Agent Service](labs/01-single-agent-with-azure-ai-agents.ipynb)  
  Provision your Azure AI Foundry Agent Service instance, configure OBO authentication, and register your first Planner agent.
- **Azure Fabric Retriever Agent**: 🧾 [Notebook – Connecting Microsoft Fabric to Your Agents](labs/02-azure-fabric-data-agent.ipynb)  
  Create and register a Fabric Data Agent to transform lakehouse and warehouse tables into conversational Q&A.
- **Azure SharePoint Retriever Agent**: 🧾 [Notebook – Connecting SharePoint Sites to Your Agents](labs/03-azure-sharepoint-retriever-agent.ipynb)  
  Connect to SharePoint, and surface documents, blueprints, and notes in context.
- **Azure Bing Retriever Agent**: 🧾 [Notebook – Connecting Real-Time Data to Your Agents](labs/04-azure-bing-retriever-agent.ipynb)  
  Connect to the Web, and surface latest news, research to add real-time context.
- **Building MaS with Azure AI Agents & Semantic Kernel Agent Framework**: 🧾 [Notebook – Orchestrating Agents with Semantic Kernel](labs/05-semantic-kernel-agent-framework.ipynb)  Use the Semantic Kernel SDK to build multi‑step workflows, chain prompts, and implement reflection loops.

### **🏭 Reference Use Case - MedTech R&D Assistant**

<div align="center">

<img src="utils/images/R%2BD%20Usecase.png" alt="R&D Use Case" style="max-width:100%; height:auto; border:1px solid #d0d7de; border-radius:12px;" />

</div>
<br>

A Product Manager at a leading MedTech company uses Agentic RAG to analyze next‑gen Continuous Glucose Monitor (CGM) performance. By orchestrating multiple agents, the system delivers rapid, validated insights across diverse data sources:

1. **Planning & Intelligent Routing**  
   The **Planner Agent** parses the user question, builds an intent map, and selects the optimal retriever agents—e.g., **Fabric Retriever** (lakehouse metrics), **SharePoint Retriever** (design docs), or **Web Retriever** (market studies).  
   *Optionally*, the Planner may call the **Query Rewriter** up front to maximise retrieval precision.

2. **Retrieval**  
   The selected *family agents* run in parallel, each pulling evidence from its source of truth.

3. **Verification / Reflection Layer**  
   A dedicated **Verifier Agent** cross-checks results, detects contradictions, and confirms that the aggregated evidence actually answers the original intent.

4. **Insight Synthesis**  
   - **If verification passes:** the Planner merges validated evidence into a concise, actionable response and returns it to the user.  
   - **If verification fails:** the Verifier triggers the **Query Rewriter**, which refines the search terms; the Planner re-routes the new query to the relevant retrievers and the cycle repeats.

This closed-loop **plan → retrieve → verify → (rewrite) → synthesize** pattern ensures every answer is context-rich, conflict-free, and delivered in real time.


## 📚 More Resources

- **[Azure AI Foundry](https://azure.microsoft.com/en-us/products/ai-foundry/?msockid=0b24a995eaca6e7d3c1dbc1beb7e6fa8#Use-cases-and-Capabilities)**: Develop and deploy custom AI apps and APIs responsibly with a comprehensive platform.
- **[Azure AI Foundry Agent Service](https://learn.microsoft.com/en-us/azure/ai-services/agents/overview)**: Learn about Azure AI Foundry Agent Service and its capabilities.
- **[Semantic Kernel Documentation](https://learn.microsoft.com/en-us/semantic-kernel/overview/)**: Detailed documentation on Semantic Kernel's features and capabilities.
- **[Fabric Data Agent](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/fabric?tabs=csharp&pivots=overview)** – How‑to guide on connecting Microsoft Fabric to your Agentic RAG pipeline.  
- **[SharePoint Data Agent](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/sharepoint?tabs=csharp&pivots=overview)** – Steps to configure OBO and surface SharePoint content via agents.  
- **[Grounding with Bing Search](https://learn.microsoft.com/en-us/azure/ai-services/agents/how-to/tools/bing-grounding?tabs=python&pivots=overview)** – Documentation for integrating live web search into your workflows.  
- **[Azure AI Search tool](https://learn.microsoft.com/en-us/azure/search/semantic-vector-search-overview)** – Semantic and vector search capabilities to enrich retrieval.  

<br>

> [!IMPORTANT]  
> This software is provided for demonstration purposes only. It is not intended to be relied upon for any production workload. The creators of this software make no representations or warranties of any kind, express or implied, about the completeness, accuracy, reliability, suitability, or availability of the software or related content. Any reliance placed on such information is strictly at your own risk.
