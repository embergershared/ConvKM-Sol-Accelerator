# Conversation knowledge mining solution accelerator

Gain actionable insights from large volumes of conversational data by identifying key themes, patterns, and relationships. Using Microsoft Foundry, Azure Content Understanding, Azure OpenAI Service, and Foundry IQ, this solution analyzes unstructured dialogue and maps it to meaningful, structured insights.

Capabilities such as topic modeling, key phrase extraction, speech-to-text transcription, and interactive chat enable users to explore data naturally and make faster, more informed decisions.

Analysts working with large volumes of conversational data can use this solution to extract insights through natural language interaction. It supports tasks like identifying customer support trends, improving contact center quality, and uncovering operational intelligence—enabling teams to spot patterns, act on feedback, and make informed decisions faster.

<br/>

<div align="center">
  
[**SOLUTION OVERVIEW**](#solution-overview)  \| [**QUICK DEPLOY**](#quick-deploy)  \| [**BUSINESS SCENARIO**](#business-scenario)  \| [**SUPPORTING DOCUMENTATION**](#supporting-documentation)

</div>
<br/>
 
 **Note:** With any AI solutions you create using these templates, you are responsible for assessing all associated risks and for complying with all applicable laws and safety standards. Learn more in the transparency documents for [Agent Service](https://learn.microsoft.com/en-us/azure/ai-foundry/responsible-ai/agents/transparency-note) and [Agent Framework](https://github.com/microsoft/agent-framework/blob/main/TRANSPARENCY_FAQ.md).
<br/>

<h2><img src="./documents/Images/ReadMe/solution-overview.png" width="48" />
Solution overview
</h2>

Leverages Azure Content Understanding, Foundry IQ, Azure OpenAI Service, Azure AI Agent Framework, Azure SQL Database, and Cosmos DB to process large volumes of conversational data. Audio and text inputs are analyzed through event-driven pipelines to extract and vectorize key information, orchestrate intelligent responses, and power an interactive web front-end for exploring insights using natural language.

### Solution architecture
|![image](./documents/Images/ReadMe/solution-architecture.png)|
|---|

### Additional resources

[Technical Architecture](./documents/TechnicalArchitecture.md)

<br/>

## Features

### Key features
<details open>  
<summary>Click to learn more about the key features this solution enables</summary>  

- **Mined entities and relationships** <br/>  
Azure Content Understanding and Azure OpenAI Service extract entities and relationships from unstructured data to create a knowledge base.

- **Processed data at scale** <br/>  
Microsoft Fabric processes conversation data at scale, generating vector embeddings for efficient retrieval using the RAG (Retrieval-Augmented Generation) pattern.

- **Visualized insights** <br/>  
An interactive dashboard delivers actionable insights and trends through rich data visualizations.

- **Natural language interaction** <br/>  
Azure OpenAI Service enables contextual question-answering, conversation capabilities, and chart generation, all powered by the RAG pattern.

- **Actionable insights** <br/>  
Summarized conversations, topic generation, and key phrase extraction support faster decision-making and improved productivity.

- **Dashboard drill-down (Stage B)** <br/>
Click any chart element — sentiment slice, topic bar, trending-topics row, or key-phrase word — to open a right-side overlay drawer that drills from a **time trend** to a **call list** to a **single transcript**. Keyboard-operable, breadcrumb + Esc navigation, resizable, with the drill state mirrored to `window.location.hash` for shareable links. See `plans/dashboard-drill-down.md` for the design and `infra/scripts/sqldb_drill_index.sql` for the optional supporting indexes.

</details>



<br /><br />
## Getting Started

<h2><img src="./documents/Images/ReadMe/quick-deploy.png" width="48" />
Quick deploy
</h2>

### How to install or deploy
Follow the quick deploy steps on the deployment guide to deploy this solution to your own Azure subscription.
[Click here to launch the deployment guide](./documents/DeploymentGuide.md)
<br/><br/>


| [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/microsoft/Conversation-Knowledge-Mining-Solution-Accelerator) | [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/microsoft/Conversation-Knowledge-Mining-Solution-Accelerator) | [![Open in Visual Studio Code Web](https://img.shields.io/static/v1?style=for-the-badge&label=Visual%20Studio%20Code%20(Web)&message=Open&color=blue&logo=visualstudiocode&logoColor=white)](https://vscode.dev/azure/?vscode-azure-exp=foundry&agentPayload=eyJiYXNlVXJsIjogImh0dHBzOi8vcmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbS9taWNyb3NvZnQvQ29udmVyc2F0aW9uLUtub3dsZWRnZS1NaW5pbmctU29sdXRpb24tQWNjZWxlcmF0b3IvcmVmcy9oZWFkcy9tYWluL2luZnJhL3ZzY29kZV93ZWIiLCAiaW5kZXhVcmwiOiAiL2luZGV4Lmpzb24iLCAidmFyaWFibGVzIjogeyJhZ2VudElkIjogIiIsICJjb25uZWN0aW9uU3RyaW5nIjogIiIsICJ0aHJlYWRJZCI6ICIiLCAidXNlck1lc3NhZ2UiOiAiIiwgInBsYXlncm91bmROYW1lIjogIiIsICJsb2NhdGlvbiI6ICIiLCAic3Vic2NyaXB0aW9uSWQiOiAiIiwgInJlc291cmNlSWQiOiAiIiwgInByb2plY3RSZXNvdXJjZUlkIjogIiIsICJlbmRwb2ludCI6ICIifSwgImNvZGVSb3V0ZSI6IFsiYWktcHJvamVjdHMtc2RrIiwgInB5dGhvbiIsICJkZWZhdWx0LWF6dXJlLWF1dGgiLCAiZW5kcG9pbnQiXX0=) | 
|---|---|---|

<br/>

> **Note**: Some tenants may have additional security restrictions that run periodically and could impact the application (e.g., blocking public network access). If you experience issues or the application stops working, check if these restrictions are the cause. In such cases, consider deploying the WAF-supported version to ensure compliance. To configure, [Click here](./documents/DeploymentGuide.md#31-choose-deployment-type-optional).

> ⚠️ **Important: Check Azure OpenAI Quota Availability**
 <br/>To ensure sufficient quota is available in your subscription, please follow [quota check instructions guide](./documents/QuotaCheck.md) before you deploy the solution.

<br/>

## Guidance

### Prerequisites and costs
To deploy this solution accelerator, ensure you have access to an [Azure subscription](https://azure.microsoft.com/free/) with the necessary permissions to create **resource groups, resources, app registrations, and assign roles at the resource group level**. This should include Contributor role at the subscription level and  Role Based Access Control role on the subscription and/or resource group level. Follow the steps in [Azure Account Set Up](./documents/AzureAccountSetUp.md).

Here are some example regions where the services are available: East US, East US2, Australia East, UK South, France Central.

Check the [Azure Products by Region](https://azure.microsoft.com/en-us/explore/global-infrastructure/products-by-region/?products=all&regions=all) page and select a **region** where the following services are available.

Pricing varies by region and usage, so it isn't possible to predict exact costs for your usage. The majority of Azure resources used in this infrastructure are on usage-based pricing tiers. However, some services—such as Azure Container Registry, which has a fixed cost per registry per day, and others like Cosmos DB or SQL Database when provisioned—may incur baseline charges regardless of actual usage.

Use the [Azure pricing calculator](https://azure.microsoft.com/en-us/pricing/calculator) to calculate the cost of this solution in your subscription. 

Review a [sample pricing sheet](https://azure.com/e/67c83432524440d98ccb8c92ebd3e2f7) in the event you want to customize and scale usage.

_Note: This is not meant to outline all costs as selected SKUs, scaled use, customizations, and integrations into your own tenant can affect the total consumption of this sample solution. The sample pricing sheet is meant to give you a starting point to customize the estimate for your specific needs._

<br/>

>⚠️ **Important:** To avoid unnecessary costs, remember to take down your app if it's no longer in use,
either by deleting the resource group in the Portal or running `azd down`.

### Operating the chat agents — model changes

> 🚫 **Do NOT change the chat agents' model from the Azure AI Foundry portal.**
> Always use the **model selector dropdown inside the Chat card** of this app.

The solution manages two Foundry agents (`KM-ConversationAgent-<solutionName>` and
`KM-TitleAgent-<solutionName>`). The conversation agent has tools bound to it
(SQL function tool + **Azure AI Search agent tool**). The Azure AI Search tool
is what produces the inline `[1]`, `[2]` citation markers and powers the
citation side-panel — without it, search-grounded answers and citations break.

When you change the model from the Foundry portal, the portal performs a
conservative compatibility check against its catalog metadata. For many
deployments (including `gpt-4o-mini`) the catalog does not flag the deployment
as compatible with the Azure AI Search agent tool, so the portal shows an
**"Unsupported tools"** dialog offering to drop the tool if you proceed.
Clicking *Confirm* **permanently removes Azure AI Search from the agent**,
breaking citations until someone re-runs `infra/scripts/agent_scripts/01_create_agents.py`
to rebuild the agent definition.

The app's dropdown avoids this entirely:

- `ModelService.select_model()` (`src/api/services/model_service.py`) calls
  `agents.create_version()` directly via the SDK, which does **not** enforce
  the portal's catalog compatibility check.
- On every model swap it **rebuilds** the conversation agent's tools from
  source (`get_conversation_agent_tools(...)`) rather than round-tripping the
  GET response, so the search connection ID and index name are always
  re-wired correctly.
- Both agents are updated in the same request and the thread cache is
  invalidated so the next chat picks up the new version.

Administrator guidance:

| You want to… | Do this | Don't do this |
|---|---|---|
| Change the model used by chat | Use the model dropdown in the Chat card | Open the Foundry portal → agent → Playground → Model picker |
| Add/remove a tool on the conversation agent | Edit `get_conversation_agent_tools()` then redeploy + re-run the agent script | Edit tools in the portal |
| See which model is currently bound | Check the dropdown selection (it reads `versions.latest.definition.model` from both agents) | Trust the portal alone — the app is the source of truth |
| Recover after a portal change accidentally stripped tools | Re-run `infra/scripts/agent_scripts/01_create_agents.py` with the original parameters | Manually re-add tools in the portal |

If the model change is initiated through the app you will see an amber
**"Activating <model>…"** toast in the top-right corner of the page while
Foundry provisions the new agent version (typically 1-2 minutes). The chat
input is disabled until both agents report `status: "active"`.

## Operational scripts

Standalone SQL / Python scripts that are run **once after deployment** to
enable or tune optional features. None of these are wired into the Bicep
deployment — they are explicit, opt-in operator actions.

| Script | Purpose | When to run | How to run |
|---|---|---|---|
| `infra/scripts/sqldb_drill_index.sql` | Adds two `NONCLUSTERED` indexes that keep the dashboard drill-down (L1 time trend, L2 call list) under 500 ms at sample-data scale. Idempotent. | Once, after enabling the Dashboard drill-down feature. Re-run after restoring a backup that did not include the indexes. | `sqlcmd -S <server>.database.windows.net -d <db> -U <user> -P <pwd> -i infra/scripts/sqldb_drill_index.sql` — or paste into Azure Data Studio / portal Query editor. |
| `infra/scripts/agent_scripts/01_create_agents.py` | Creates the orchestrator + title agents in Foundry from `agent_instructions.py`. | First post-deploy, and after a portal change strips tools (see Guidance above). | See `infra/scripts/run_create_agents_scripts.sh`. |
| `infra/scripts/agent_scripts/02_update_agents.py` | Re-publishes agent instructions while preserving the active model + tool bindings. | Whenever `agent_instructions.py` changes. | `python infra/scripts/agent_scripts/02_update_agents.py` |

### Running `process_custom_data.sh` from WSL (Ubuntu)

When running the custom data processing script from Windows Subsystem for Linux,
you need the Microsoft ODBC Driver for SQL Server installed. Run these commands
one at a time:

```bash
# 1. Import the Microsoft GPG signing key
curl -sSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/microsoft.gpg > /dev/null

# 2. Add the Microsoft package repository (Ubuntu 24.04)
echo "deb [arch=amd64] https://packages.microsoft.com/ubuntu/24.04/prod noble main" | sudo tee /etc/apt/sources.list.d/mssql-release.list

# 3. Update package lists
sudo apt-get update

# 4. Install the ODBC driver and unixODBC dev headers
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev
```

> **Note:** If you are on Ubuntu 22.04, replace `24.04/prod noble` with
> `22.04/prod jammy` in step 2.

Then install the Python dependencies (use `--break-system-packages` if not in a
native Linux venv):

```bash
python3 -m pip install --break-system-packages -r infra/scripts/index_scripts/requirements.txt
```

#### SQL Database access for your CLI identity

The processing script authenticates to Azure SQL using your `az login` identity
via a token. Your identity must be a user in the SQL database with write
permissions. If you see `Login failed for user '<token-identified principal>'`,
connect to the database (Azure Portal Query Editor or Azure Data Studio) and run:

```sql
CREATE USER [your-email@domain.com] FROM EXTERNAL PROVIDER;
ALTER ROLE db_owner ADD MEMBER [your-email@domain.com];
```

Replace `your-email@domain.com` with the output of
`az account show --query user.name -o tsv`.

#### Azure CLI token timeout in WSL

The `AzureCliCredential` used by the processing scripts can time out in WSL
because `az` runs on the Windows filesystem. Before running the script, warm up
the token cache:

```bash
az account get-access-token --resource https://cognitiveservices.azure.com/ > /dev/null
az account get-access-token --resource https://database.windows.net/.default > /dev/null
```

## Resources

| Product | Description | Tier / Expected Usage Notes | Cost |
|---|---|---|---|
| [Microsoft Foundry](https://learn.microsoft.com/en-us/azure/ai-foundry) | Used to orchestrate and build AI workflows that combine Azure AI services. | Free Tier | [Pricing](https://azure.microsoft.com/pricing/details/ai-studio/) |
| [Foundry IQ](https://learn.microsoft.com/en-us/azure/search/search-what-is-azure-search) | Powers vector-based semantic search for retrieving indexed conversation data. | Standard S1; costs scale with document count and replica/partition settings. | [Pricing](https://azure.microsoft.com/pricing/details/search/) |
| [Azure Storage Account](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-overview) | Stores transcripts, intermediate outputs, and application assets. | Standard LRS; usage-based cost by storage/operations. | [Pricing](https://azure.microsoft.com/pricing/details/storage/blobs/) |

| [Azure AI Services (OpenAI)](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/overview) | Enables language understanding, summarization, entity extraction, and chat capabilities using GPT models. | S0 Tier; pricing depends on token volume and model used (e.g., GPT-4o-mini). | [Pricing](https://azure.microsoft.com/pricing/details/cognitive-services/) |
| [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/overview) | Hosts microservices and APIs powering the front-end and backend orchestration. | Consumption plan with 0.5 vCPU, 1GiB memory; includes a free usage tier. | [Pricing](https://azure.microsoft.com/pricing/details/container-apps/) |
| [Azure Container Registry](https://learn.microsoft.com/en-us/azure/container-registry/container-registry-intro) | Stores and serves container images used by Azure Container Apps. | Basic Tier; fixed daily cost per registry. | [Pricing](https://azure.microsoft.com/pricing/details/container-registry/) |
| [Azure Monitor / Log Analytics](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/log-analytics-overview) | Collects and analyzes telemetry and logs from services and containers. | Pay-as-you-go; charges based on data ingestion volume. | [Pricing](https://azure.microsoft.com/pricing/details/monitor/) |
| [Azure SQL Database](https://learn.microsoft.com/en-us/azure/azure-sql/database/sql-database-paas-overview) | Stores structured data including insights, metadata, and indexed results. | General Purpose Tier; can be provisioned or serverless. Fixed cost if provisioned. | [Pricing](https://azure.microsoft.com/pricing/details/azure-sql-database/single/) |
| [Azure Cosmos DB](https://learn.microsoft.com/en-us/azure/cosmos-db/introduction) | Used for fast, globally distributed NoSQL data storage for chat history and vector metadata. | Autoscale or provisioned throughput; fixed minimum cost if provisioned. | [Pricing](https://azure.microsoft.com/en-us/pricing/details/cosmos-db/autoscale-provisioned/) |


<br/>


<br /><br />
<h2><img src="./documents/Images/ReadMe/business-scenario.png" width="48" />
Business scenario
</h2>


|![image](./documents/Images/ReadMe/ui.png)|
|---|

<br/>

Analysts often work with large volumes of unstructured conversational data, making it difficult to extract actionable insights quickly and accurately. Traditional tools limit interaction with data, making it hard to surface patterns or ask the right follow-up questions without extensive manual exploration.

This solution addresses those challenges by enabling natural language interaction, dynamic data exploration, and contextual visualization. Analysts can identify key themes, clarify findings, and act with greater confidence—all within a streamlined, insight-driven experience.

⚠️ The sample data used in this repository is synthetic and generated using Azure OpenAI service. The data is intended for use as sample data only.


### Business value
<details>
  <summary>Click to learn more about what value this solution provides</summary>

  - **Better decision-making** 
Summarized, contextualized data helps organizations make informed strategic decisions that drive operational improvements at scale.

- **Time saved**
Automated insight extraction and scalable data exploration reduce manual analysis efforts, leading to improved efficiency and cost savings.

- **Interactive data insights**
Employees can engage directly with conversational data using natural language, enabling quicker understanding and faster resolution of issues.

- **Actionable insights** 
Clear, contextual insights empower employees to take meaningful action based on data-driven evidence.

     
</details>

### Use Case
<details>
  <summary>Click to learn more about what use cases this solution provides</summary>
<br/>

  | **Use case** | **Persona** | **Challenges** | **Summary/approach** |
  |---|---|---|---|
  | Contact Center Customer Support | Analyst | Difficulty in extracting actionable insights from large, complex datasets due to limited context or practical considerations.   Limited ability to engage with data interactively, making it challenging to find the right questions to dig deeper.| Contextualized insights from mined data that enables employees to solve problems and take action. Interactive data that allow employees to ask questions and receive timely responses, providing better understanding and problem-solving.| 
  IT Helpdesk | IT Helpdesk Analyst | Manually reviewing IT Helpdesk calls to identify recurring issues is time-consuming and inefficient. Creating graphs, analyzing performance problems, and drafting FAQs is often a slow process, leaving gaps in self-service support. | Address these challenges by leveraging AI to gain insights from call data, generating visual summaries, uncovering common issues, and producing FAQ content, transforming a labor-intensive review process into a fast, accurate, and actionable workflow. |

</details>

<br /><br />

<h2><img src="./documents/Images/ReadMe/supporting-documentation.png" width="48" />
Supporting documentation
</h2>

### Security guidelines

This solution leverages [Managed Identity](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview) for secure access to Azure resources during local development and production deployment, eliminating the need for hard-coded credentials.

To maintain strong security practices, it is recommended that GitHub repositories built on this solution enable [GitHub secret scanning](https://docs.github.com/code-security/secret-scanning/about-secret-scanning) to detect accidental secret exposure.

Additional security considerations include:

- Enabling [Microsoft Defender for Cloud](https://learn.microsoft.com/en-us/azure/defender-for-cloud) to monitor and secure Azure resources.
- Using [Virtual Networks](https://learn.microsoft.com/en-us/azure/container-apps/networking?tabs=workload-profiles-env%2Cazure-cli) or [firewall rules](https://learn.microsoft.com/en-us/azure/container-apps/waf-app-gateway) to protect Azure Container Apps from unauthorized access.

<br/>

### Cross references
Check out similar solution accelerators

| Solution Accelerator | Description |
|---|---|
| [Document&nbsp;knowledge&nbsp;mining](https://github.com/microsoft/Document-Knowledge-Mining-Solution-Accelerator) | 	Identify relevant documents, summarize unstructured information, and generate document templates. |
| [Content&nbsp;processing](https://github.com/microsoft/document-generation-solution-accelerator) | Extracts data from multi-modal content, maps it to schemas with confidence scoring and user validation, and enables accurate processing of documents like contracts, claims, and invoices. |

<br/>

💡 Want to get familiar with Microsoft's AI and Data Engineering best practices? Check out our playbooks to learn more

| Playbook | Description |
|:---|:---|
| [AI&nbsp;playbook](https://learn.microsoft.com/en-us/ai/playbook/) | The Artificial Intelligence (AI) Playbook provides enterprise software engineers with solutions, capabilities, and code developed to solve real-world AI problems. |
| [Data&nbsp;playbook](https://learn.microsoft.com/en-us/data-engineering/playbook/understanding-data-playbook) | The data playbook provides enterprise software engineers with solutions which contain code developed to solve real-world problems. Everything in the playbook is developed with, and validated by, some of Microsoft's largest and most influential customers and partners. |

<br/> 

## Provide feedback

Have questions, find a bug, or want to request a feature? [Submit a new issue](https://github.com/microsoft/Conversation-Knowledge-Mining-Solution-Accelerator/issues) on this repo and we'll connect.

<br/>

## Responsible AI Transparency FAQ 
Please refer to [Transparency FAQ](./TRANSPARENCY_FAQ.md) for responsible AI transparency details of this solution accelerator.

<br/>

## Disclaimers

To the extent that the Software includes components or code used in or derived from Microsoft products or services, including without limitation Microsoft Azure Services (collectively, “Microsoft Products and Services”), you must also comply with the Product Terms applicable to such Microsoft Products and Services. You acknowledge and agree that the license governing the Software does not grant you a license or other right to use Microsoft Products and Services. Nothing in the license or this ReadMe file will serve to supersede, amend, terminate or modify any terms in the Product Terms for any Microsoft Products and Services. 

You must also comply with all domestic and international export laws and regulations that apply to the Software, which include restrictions on destinations, end users, and end use. For further information on export restrictions, visit https://aka.ms/exporting. 

You acknowledge that the Software and Microsoft Products and Services (1) are not designed, intended or made available as a medical device(s), and (2) are not designed or intended to be a substitute for professional medical advice, diagnosis, treatment, or judgment and should not be used to replace or as a substitute for professional medical advice, diagnosis, treatment, or judgment. Customer is solely responsible for displaying and/or obtaining appropriate consents, warnings, disclaimers, and acknowledgements to end users of Customer’s implementation of the Online Services. 

You acknowledge the Software is not subject to SOC 1 and SOC 2 compliance audits. No Microsoft technology, nor any of its component technologies, including the Software, is intended or made available as a substitute for the professional advice, opinion, or judgement of a certified financial services professional. Do not use the Software to replace, substitute, or provide professional financial advice or judgment.  

BY ACCESSING OR USING THE SOFTWARE, YOU ACKNOWLEDGE THAT THE SOFTWARE IS NOT DESIGNED OR INTENDED TO SUPPORT ANY USE IN WHICH A SERVICE INTERRUPTION, DEFECT, ERROR, OR OTHER FAILURE OF THE SOFTWARE COULD RESULT IN THE DEATH OR SERIOUS BODILY INJURY OF ANY PERSON OR IN PHYSICAL OR ENVIRONMENTAL DAMAGE (COLLECTIVELY, “HIGH-RISK USE”), AND THAT YOU WILL ENSURE THAT, IN THE EVENT OF ANY INTERRUPTION, DEFECT, ERROR, OR OTHER FAILURE OF THE SOFTWARE, THE SAFETY OF PEOPLE, PROPERTY, AND THE ENVIRONMENT ARE NOT REDUCED BELOW A LEVEL THAT IS REASONABLY, APPROPRIATE, AND LEGAL, WHETHER IN GENERAL OR IN A SPECIFIC INDUSTRY. BY ACCESSING THE SOFTWARE, YOU FURTHER ACKNOWLEDGE THAT YOUR HIGH-RISK USE OF THE SOFTWARE IS AT YOUR OWN RISK.
