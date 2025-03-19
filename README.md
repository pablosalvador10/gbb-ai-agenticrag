# azure-ai-agent-services-demo

## Setting Up Your Development Environment 

<details>
<summary><strong>📦 PyPI Dependencies (Click to Expand)</strong></summary>
<div style="background-color: #e8f4fd; border: 1px solid #0078d4; border-radius: 5px; padding: 15px; margin-top: 10px; color: #000; font-size: 14px; line-height: 1.6;">

Keeping up with the latest library versions can be tricky, but don’t worry—we’ve got you covered! To make sure everything works smoothly, you’ll need the correct versions of the Semantic Kernel library installed:

- **Chat Completion Agents**: Requires Semantic Kernel version **1.3.0** or higher.
- **Agent Group Chat**: Requires Semantic Kernel version **1.6.0** or higher.
- **Streaming OpenAI Assistant Agents**: Requires a minimum Semantic Kernel PyPI version of **1.11.0**.
- **Azure AI Agent Integration**: Install using the following command:
  ```bash
  pip install semantic-kernel[azure]
  ```

> **Note**: All required Python packages are listed in the `requirements.txt` file for your convenience.

</div>
</details>

1. Install the **VS Code Python extension** if you haven't already.
2. Ensure you are in the **project root directory** (`azure-ai-agent-services-demo`).
3. Create the required Conda environment using the provided `environment.yaml` file:
   ```bash
   conda env create -f environment.yaml
   ```
4. Activate the Conda environment:
   ```bash
   conda activate vector-indexing-azureaisearch
   ```
5. Attach the Python kernel to the notebook in VS Code.

Once the environment is set up, you're ready to dive in! 🎉 Open the notebook `01-run-the-demo.ipynb` and attach the kernel you created in the top-right corner. Explore a multi-agent architecture in action and see how the Semantic Kernel and Azure AI Agent services seamlessly work together with your Fabric and SharePoint. Enjoy the journey!