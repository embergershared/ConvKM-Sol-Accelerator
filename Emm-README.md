# Emm-README — Extra Steps Beyond the Standard Deployment

Follow instructions from
/documents/DeploymentGuide.md



## Deploy from scratch


1. Switch to Dev Container



azd auth login
azd config set provision.preflight off

azd env new iter02 --location swedencentral --subscription 4c88693f-5cc9-4f30-9d1e-d58d4221cf25 --set-default

# Set starter values
```
AZURE_ENV_CU_LOCATION="swedencentral"
AZURE_ENV_NAME="iter02"
AZURE_ENV_SECONDARY_LOCATION="centralus"
AZURE_LOCATION="swedencentral"
AZURE_RESOURCE_GROUP="rg-swc-s3-sc-ccanalysis-iter-02"
AZURE_SUBSCRIPTION_ID="4c88693f-5cc9-4f30-9d1e-d58d4221cf25"
RESOURCE_GROUP_LOCATION="swedencentral"
USE_CASE="telecom"
USE_CHAT_HISTORY_ENABLED="True"
```

azd up

Enter a value for the 'aiServiceLocation' infrastructure parameter:
 4. (Europe) Sweden Central (swedencentral)

Pick a resource group to use: 1. Create a new resource group
Enter a name for the new resource group: (rg-swc-s3-sc-ccanalysis-iter-02)

Ouput looks like that:

  You can view detailed progress in the Azure Portal:
  https://portal.azure.com/#view/HubsExtension/DeploymentDetailsBlade/~/overview/id/%2Fsubscriptions%2F4c88693f-5cc9-4f30-9d1e-d58d4221cf25%2FresourceGroups%2Frg-swc-s3-sc-ccanalysis-iter-02%2Fproviders%2FMicrosoft.Resources%2Fdeployments%2Fiter02-1780964655

  (✓) Done: Search service: srch-iter02l25d3 (6.455s)
  (✓) Done: App Service plan: asp-iter02l25d3 (9.857s)
  (✓) Done: Storage account: stiter02l25d3 (25.072s)
  (✓) Done: Foundry: aisa-iter02l25d3-cu (25.417s)
  (✓) Done: Foundry: aif-iter02l25d3 (24.272s)
  (✓) Done: App Service: app-iter02l25d3 (27.424s)
  (✓) Done: Azure AI Services Model Deployment: aif-iter02l25d3/text-embedding-3-small (7.072s)
  (✓) Done: Azure AI Services Model Deployment: aif-iter02l25d3/gpt-4o-mini (5.04s)
  (✓) Done: Foundry project: aif-iter02l25d3/proj-iter02l25d3 (9.321s)
  (✓) Done: Foundry project connection: aif-iter02l25d3/proj-iter02l25d3/foundry-search-connection-iter02l25d3 (1.06s)
  (✓) Done: Azure SQL Server: sql-iter02l25d3 (1m20.061s)
  (✓) Done: Azure Cosmos DB: cosmos-iter02l25d3 (1m57.889s)
  (✓) Done: App Service: api-iter02l25d3 (24.969s)
Web app URL:
https://app-iter02l25d3.azurewebsites.net

Create and activate a virtual environment if not already done, then run the following command in the bash terminal to create agents:
bash ./infra/scripts/run_create_agents_scripts.sh

Run the following command in your Bash terminal. It will grant the necessary permissions between resources and your user account, and also process and load the sample data into the application.
bash ./infra/scripts/process_sample_data.sh

SUCCESS: Your application was provisioned and deployed to Azure in 4 minutes 20 seconds.
  Provisioning: 5 minutes 45 seconds
  Deploying:    less than a second



Activate the environment (Linuc Dev Container):
source .venv_dev_cont/bin/activate

### Launch script 1:
bash ./infra/scripts/run_create_agents_scripts.sh

Output:
```
vscode ➜ /workspaces/ConvKM-Sol-Accelerator (iteration-02) $ source .venv_dev_cont/bin/activate
(.venv_dev_cont) vscode ➜ /workspaces/ConvKM-Sol-Accelerator (iteration-02) $ bash ./infra/scripts/run_create_agents_scripts.sh
Started the agent creation script setup...
Checking Azure authentication...
Already authenticated with Azure.


===============================================
Values to be used:
===============================================
Resource Group: rg-swc-s3-sc-ccanalysis-iter-03
Project Endpoint: https://aif-iter02n7y67.services.ai.azure.com/api/projects/proj-iter02n7y67
Solution Name: iter02n7y67
GPT Model Name: gpt-4o-mini
AI Foundry Resource ID: /subscriptions/4c88693f-5cc9-4f30-9d1e-d58d4221cf25/resourceGroups/rg-swc-s3-sc-ccanalysis-iter-03/providers/Microsoft.CognitiveServices/accounts/aif-iter02n7y67
API App Name: api-iter02n7y67
AI Search Connection Name: foundry-search-connection-iter02n7y67
AI Search Index: call_transcripts_index
===============================================

✓ Running as user: Emm-391575 (737657da-f203-4fcc-9e8c-7c47e93b0cd9)
✓ Assigning Azure AI User role for AI Foundry

Requirement already satisfied: pip in ./.venv_dev_cont/lib/python3.11/site-packages (24.0)
Collecting pip
  Using cached pip-26.1.2-py3-none-any.whl.metadata (4.6 kB)
Using cached pip-26.1.2-py3-none-any.whl (1.8 MB)
Installing collected packages: pip
  Attempting uninstall: pip
    Found existing installation: pip 24.0
    Uninstalling pip-24.0:
      Successfully uninstalled pip-24.0
Successfully installed pip-26.1.2
Running Python agents creation script...
Agents creation completed.
✅ Script completed successfully
```

### Launch script 2:
bash ./infra/scripts/process_sample_data.sh

Output
```
Checking Azure authentication...
Already authenticated with Azure.
Update available: 1.25.4 -> 1.25.5 (https://github.com/Azure/azure-dev/releases/tag/azure-dev-cli_1.25.5)

Proceeding with the subscription: ME-MngEnvMCAP391575-emberger-3 ( 4c88693f-5cc9-4f30-9d1e-d58d4221cf25 )

===============================================
Values to be used:
===============================================
Resource Group Name: rg-swc-s3-sc-ccanalysis-iter-03
Storage Account Name: stiter02n7y67
Storage Container Name: data
SQL Server Name: sql-iter02n7y67
SQL Database Name: sqldb-iter02n7y67
Backend User-Assigned Managed Identity Display Name: id-backend-iter02n7y67
Backend User-Assigned Managed Identity Client ID: c89e3b1d-7e56-467a-bb77-ddb65677c67c
AI Search Service Name: srch-iter02n7y67
AI Foundry Resource ID: /subscriptions/4c88693f-5cc9-4f30-9d1e-d58d4221cf25/resourceGroups/rg-swc-s3-sc-ccanalysis-iter-03/providers/Microsoft.CognitiveServices/accounts/aif-iter02n7y67
CU Foundry Resource ID: /subscriptions/4c88693f-5cc9-4f30-9d1e-d58d4221cf25/resourceGroups/rg-swc-s3-sc-ccanalysis-iter-03/providers/Microsoft.CognitiveServices/accounts/aisa-iter02n7y67-cu
Search Endpoint: https://srch-iter02n7y67.search.windows.net
OpenAI Endpoint: https://aif-iter02n7y67.openai.azure.com/
Embedding Model: text-embedding-3-small
CU Endpoint: https://aisa-iter02n7y67-cu.cognitiveservices.azure.com/
CU API Version: 2024-12-01-preview
AI Agent Endpoint: https://aif-iter02n7y67.services.ai.azure.com/api/projects/proj-iter02n7y67
Deployment Model: gpt-4o-mini
Solution Name: iter02n7y67
===============================================

## Got a pip error, relaunched


Running copy_kb_files.sh
✓ Running as user: 737657da-f203-4fcc-9e8c-7c47e93b0cd9
⏳ Waiting for role assignment to propagate...
✓ Role assignment propagated successfully
⏳ Uploading call transcripts...
✓ Uploaded call transcripts successfully
⏳ Uploading audio data...
✓ Uploaded audio data successfully
copy_kb_files.sh completed successfully.
Running run_create_index_scripts.sh
✓ Running as user: Emm-391575 (737657da-f203-4fcc-9e8c-7c47e93b0cd9)
Installing requirements
✓ Creating search index
✓ Search index 'call_transcripts_index' created
✓ Creating CU template for text
✓ Analyzer 'ckm-json' created
✓ Creating CU template for audio
✓ Analyzer 'ckm-audio' created
✓ Processing data with CU
Inserted 5 records into processed_data using optimized SQL script.
✓ Processed 5 files
Inserted 851 records into processed_data using optimized SQL script.
Inserted 8510 records into processed_data_key_phrases using optimized SQL script.
✓ Loaded 112 sample records
Creating topic mining and mapping agents...
✓ Created agents: KM-TopicMiningAgent-iter02n7y67, KM-TopicMappingAgent-iter02n7y67
✓ Mined 8 topics
Inserted 856 records into km_processed_data using optimized SQL script.
Inserted 50 records into processed_data_key_phrases using optimized SQL script.
✓ Data processing completed
Deleting topic mining and mapping agents...
✓ Deleted agents: KM-TopicMiningAgent-iter02n7y67, KM-TopicMappingAgent-iter02n7y67
✓ Assigning SQL roles to managed identity
✓ Created user: id-backend-iter02n7y67
✓ Assigned db_datareader to id-backend-iter02n7y67
✓ Assigned db_datawriter to id-backend-iter02n7y67
run_create_index_scripts.sh completed successfully.
All scripts executed successfully.

✅ Script completed successfully
```

### Setup authentication

/documents/AppAuthentication.md


### Login to the application

- Accept the App authorization

- Check the app works



### Deploy the "updated look" version of the app

#### Set the variables

- Check the values are here first:
`azd env get-values`

Ouput:
```
ACR_NAME="kmcontainerreg"
AGENT_NAME_CONVERSATION="KM-ConversationAgent-iter02n7y67"
AGENT_NAME_TITLE="KM-TitleAgent-iter02n7y67"
AI_FOUNDRY_RESOURCE_ID="/subscriptions/4c88693f-5cc9-4f30-9d1e-d58d4221cf25/resourceGroups/rg-swc-s3-sc-ccanalysis-iter-03/providers/Microsoft.CognitiveServices/accounts/aif-iter02n7y67"
API_APP_NAME="api-iter02n7y67"
...
```

```bash
RG=$(azd env get-value RESOURCE_GROUP_NAME)
ACR=acr$(azd env get-value SOLUTION_NAME)
# Control
echo "$ACR"
APP=app-$(azd env get-value SOLUTION_NAME)
IMAGE_WEB=sc-ccanalysis-web
API_APP=$(azd env get-value API_APP_NAME)
IMAGE_API=sc-ccanalysis-api
```

#### Create an ACR

```bash
az acr create -g "$RG" -n "$ACR" --sku Basic --admin-enabled true
```

#### Assign Web App and Web API managed Identities AcrPull role on ACR

```bash
WEB_MI_PRINCIPAL_ID=$(az webapp identity assign -g "$RG" -n "$APP" --query principalId -o tsv)
API_MI_PRINCIPAL_ID=$(az webapp identity assign -g "$RG" -n "$API_APP" --query principalId -o tsv)

ACR_ID=$(az acr show -g "$RG" -n "$ACR" --query id -o tsv)

az role assignment create \
   --assignee-object-id "$WEB_MI_PRINCIPAL_ID" \
   --assignee-principal-type ServicePrincipal \
   --role AcrPull \
   --scope "$ACR_ID"
 
az role assignment create \
   --assignee-object-id "$API_MI_PRINCIPAL_ID" \
   --assignee-principal-type ServicePrincipal \
   --role AcrPull \
   --scope "$ACR_ID"
```

#### Switch Web App and Web API authentication to ACR from admin credentials to Managed Identity

```bash
 az resource update \
   --ids "$(az webapp show -g "$RG" -n "$APP" --query id -o tsv)/config/web" \
   --set properties.acrUseManagedIdentityCreds=true \
          properties.acrUserManagedIdentityID=null
 
 # Clear any stored ACR admin credentials (DOCKER_REGISTRY_SERVER_USERNAME/PASSWORD)
 az webapp config appsettings delete -g "$RG" -n "$APP" \
   --setting-names DOCKER_REGISTRY_SERVER_USERNAME DOCKER_REGISTRY_SERVER_PASSWORD \
   -o none 2>/dev/null || true
```


#### Create Image of the WebApp and make it used
```bash
cd src/App
# Remove local node_modules before upload. The Dockerfile runs `npm ci` inside the
# image, so the host copy is unused — and azure-cli's archiver walks every file
# under node_modules even when .dockerignore excludes it (only `.venv` gets a
# hardcoded skip-recursion fast-path in azure/cli/command_modules/acr/_archive_utils.py).
# rm -rf node_modules
TAG_WEB=iter02-$(date +%Y%m%d-%H%M)
az acr build -r "$ACR" -t "$IMAGE_WEB:$TAG_WEB" -f WebApp.Dockerfile .
az webapp config container set -g "$RG" -n "$APP" --container-image-name "$ACR.azurecr.io/$IMAGE_WEB:$TAG_WEB"
az webapp restart -g "$RG" -n "$APP"
cd ../..
```

---

## 1. Fix CRLF line endings on shell scripts

Scripts under `infra/scripts/` were checked out with Windows line endings,
which causes `bad interpreter: /bin/bash^M` errors when running them inside
the Linux dev container.

```bash
find ./infra/scripts -type f \( -name "*.sh" -o -name "*.py" \) \
  -exec sed -i 's/\r$//' {} +
```

Run this once after cloning, before executing any `./infra/scripts/*.sh`.

---

## 2. Customize the header (logo / labels)

Branding lives in the React frontend at `src/App/src/App.tsx` (around
lines 256–262):

```tsx
<div className="header-left-section">
  <AppLogo />                                  {/* SVG component in src/components/Svg/Svg.tsx */}
  <Subtitle2>
    Woodgrove <Body2 style={{ gap: "10px" }}>| Call Analysis</Body2>
  </Subtitle2>
</div>
```

- **Text:** edit the `Woodgrove` / `| Call Analysis` strings.
- **Logo:** see section 3 below.

---

## 3. Swap the header logo image

The logo is a Fluent UI `Avatar` whose `image.src` is a giant inline base64
JPEG, defined in `src/App/src/components/Svg/Svg.tsx` (the `AppLogo` export).
Replace that `src` value with your own image. Easiest path:

### Option A — drop a file into `public/` (no imports needed)

1. Copy your image into `src/App/public/`, e.g. `src/App/public/my-logo.png`.
2. Edit `src/App/src/components/Svg/Svg.tsx` and replace the long
   `data:image/jpeg;base64,...` string with `"/my-logo.png"`:

   ```tsx
   <Avatar
     image={{ src: "/my-logo.png" }}
     name="App Logo"
     shape="square"
     size={56}
     aria-label="App Logo"
     style={{ width: "25px", height: "25px" }}
   />
   ```

Anything in `public/` is served from the site root, so `/my-logo.png` works
in the running container.

### Option B — import from `src/` (bundled with content-hash)

1. Put the file under `src/`, e.g. `src/App/src/assets/my-logo.png`.
2. At the top of `Svg.tsx`:
   ```tsx
   import logoSrc from "../../assets/my-logo.png";
   ```
3. Replace the `src` value with `logoSrc`.

### Option C — keep it inline as base64

```bash
echo "data:image/png;base64,$(base64 -w0 my-logo.png)"
```
Paste the output as the new `src` value.

### Tips

- The Avatar is constrained to 25×25 px by the inline `style`. If your logo
  is wider than tall, swap `<Avatar>` for a plain `<img>`:
  ```tsx
  <img src="/my-logo.png" alt="App Logo" style={{ height: 28 }} />
  ```
- For transparent backgrounds, use PNG or SVG (not JPEG).

---

## 4. Renaming dashboard cards (e.g. "Topics Overview" → "Sentiment overview")

Card titles come from **two** places, and the order matters:

1. **Backend SQL query** — `src/api/common/database/sqldb_service.py` (look
   for `as chart_name` in the big `UNION ALL` around lines 227–247). When
   the chart data API returns a row, the frontend uses that `chart_name`.
2. **Layout config JSON** — `REACT_APP_LAYOUT_CONFIG` env var on the
   backend Web App (also defined in `infra/main.bicep` /
   `infra/main_custom.bicep`). Used as a fallback when the API returns
   nothing.

`src/App/src/components/Chart/Chart.tsx` line ~129:
```ts
title: apiData ? apiData.chart_name : configChart.name || "",
```

So **for any card that has live data, you must update the SQL string** and
rebuild the backend image. Updating only the layout config will not change
the title.

### 4a. Edit both sources

In `src/api/common/database/sqldb_service.py`, change the literal in the
SELECT, e.g.:
```python
select 'SENTIMENT' as id, 'Sentiment overview' as chart_name, 'donutchart' as chart_type,
```

In `infra/main.bicep` and `infra/main_custom.bicep`, update the matching
chart `"name"` inside the `reactAppLayoutConfig` JSON so future provisions
stay in sync:
```json
{ "id": "SENTIMENT", "name": "Sentiment overview", "type": "donutchart", ... }
```

### 4b. Rebuild & deploy the backend image

The backend container is `kmcontainerreg.azurecr.io/km-api:<tag>` by
default. Build your own and point the backend Web App at it:

```bash
RG=<your-resource-group>
ACR=<your-acr-name>
API_APP=$(az webapp list -g "$RG" --query "[?starts_with(name,'api-')].name" -o tsv)

TAG=custom-$(date +%Y%m%d-%H%M)
cd src/api
az acr build -r "$ACR" -t "km-api:$TAG" -f ApiApp.Dockerfile .
cd -

ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR" --query passwords[0].value -o tsv)
az webapp config container set \
  -g "$RG" -n "$API_APP" \
  --container-image-name "$ACR.azurecr.io/km-api:$TAG" \
  --container-registry-url "https://$ACR.azurecr.io" \
  --container-registry-user "$ACR_USER" \
  --container-registry-password "$ACR_PASS"
az webapp restart -g "$RG" -n "$API_APP"
```

Also bump the matching IaC params in `infra/main.bicep` so future provisions
use your backend image (mirrors section 6 for the frontend):

```bicep
param backendContainerRegistryHostname string = '<your-acr>.azurecr.io'
param backendContainerImageName       string = 'km-api'
param backendContainerImageTag        string = 'custom'
```

### 4c. (Optional) Patch the layout-config env var as a one-off

Only useful for cards/sections whose title falls through to the config
(no live data, or you want a temporary override):

```bash
CURRENT=$(az webapp config appsettings list -g "$RG" -n "$API_APP" \
  --query "[?name=='REACT_APP_LAYOUT_CONFIG'].value | [0]" -o tsv)
UPDATED=$(printf '%s' "$CURRENT" | sed 's/"Topics Overview"/"Sentiment overview"/')
az webapp config appsettings set -g "$RG" -n "$API_APP" \
  --settings REACT_APP_LAYOUT_CONFIG="$UPDATED"
az webapp restart -g "$RG" -n "$API_APP"
```

---

## 5. Build & deploy the customized frontend image

The standard deployment pulls the frontend image from Microsoft's public
registry (`kmcontainerreg.azurecr.io/km-app:<tag>` — see
`infra/main.bicep` lines 115–122). To ship your changes you must build your
own image, push it to a registry you control, and repoint the Web App at it.

### 5a. Set variables

```bash
RG=<your-resource-group>          # same RG the accelerator deployed into
ACR=<your-acr-name>               # globally unique, lowercase, alphanumeric
APP=$(az webapp list -g "$RG" --query "[?starts_with(name,'app-')].name" -o tsv)
echo "Web App: $APP"
```

### 5b. Create an ACR (skip if you already have one)

```bash
az acr create -g "$RG" -n "$ACR" --sku Basic --admin-enabled true
```

### 5c. Build & push the image (cloud build, no local Docker needed)

```bash
cd src/App
az acr build -r $ACR -t sc-ccanalysis:iter01-01 -f WebApp.Dockerfile .
cd -
```

### 5d. Point the Web App at your image

```bash
ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR" --query passwords[0].value -o tsv)

az webapp config container set \
  -g "$RG" -n "$APP" \
  --container-image-name "$ACR.azurecr.io/km-app:custom" \
  --container-registry-url "https://$ACR.azurecr.io" \
  --container-registry-user "$ACR_USER" \
  --container-registry-password "$ACR_PASS"

az webapp restart -g "$RG" -n "$APP"
```

Wait ~1–2 minutes for the pull + cold start, then reload the Web App URL.

---

## 6. (Optional) Make the image change persistent in IaC

So that future `azd provision` / `azd up` runs don't revert to the upstream
image, update these params in `infra/main.bicep`:

```bicep
param frontendContainerRegistryHostname string = '<your-acr>.azurecr.io'
param frontendContainerImageName       string = 'km-app'
param frontendContainerImageTag        string = 'custom'
```

---

## Iterating on further frontend changes

Repeat steps **5c** and **5d** (bump the tag, e.g. `custom-v2`, so the Web
App definitely re-pulls):

```bash
# RG=rg-swc-s3-sc-ccanalysis-iter-01
# ACR=acrsccanalysisit01
# APP=app-iter01l2yhy
# IMAGE=sc-ccanalysis-web
TAG=iter01-$(date +%Y%m%d-%H%M)

az acr build -r "$ACR" -t "$IMAGE:$TAG" -f WebApp.Dockerfile .
az webapp config container set -g "$RG" -n "$APP" --container-image-name "$ACR.azurecr.io/$IMAGE:$TAG"
az webapp restart -g "$RG" -n "$APP"
```


## Rebuild the Backend API

```bash
# Rebuild the API backend now:
API_APP=api-iter01l2yhy
IMAGE_API=sc-ccanalysis-api

# build & push from src/api (note: Dockerfile is ApiApp.Dockerfile)
TAG_API=custom-$(date +%Y%m%d-%H%M)
cd src/api
az acr build -r "$ACR" -t "$IMAGE_API:$TAG_API" -f ApiApp.Dockerfile .

# point the backend Web App at it
ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR" --query passwords[0].value -o tsv)
az webapp config container set \
  -g "$RG" -n "$API_APP" \
  --container-image-name "$ACR.azurecr.io/$IMAGE_API:$TAG_API" \
  --container-registry-url "https://$ACR.azurecr.io" \
  --container-registry-user "$ACR_USER" \
  --container-registry-password "$ACR_PASS"

az webapp restart -g "$RG" -n "$API_APP"
```

## Samples questions

https://github.com/embergershared/ConvKM-Sol-Accelerator/blob/main/documents/SampleQuestions.md

