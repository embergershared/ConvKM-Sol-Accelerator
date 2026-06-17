#!/usr/bin/env bash
# Rebuild-database.sh
# Clean rebuild of the database: creates index, CU analyzers,
# processes sample transcripts (DROP mode), then appends audio files.
#
# Usage:
#   bash scripts/Rebuild-database.sh
#
# Prerequisites:
#   - Python virtual environment activated with requirements installed
#   - Azure CLI logged in (az login)
#   - azd environment configured (azd env values available)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRA_SCRIPTS="$REPO_ROOT/infra/scripts"
INDEX_SCRIPTS="$INFRA_SCRIPTS/index_scripts"

echo "============================================="
echo "  Database Clean Rebuild"
echo "============================================="
echo ""

# Load azd env values (strip any trailing whitespace/control chars)
echo "Loading azd environment values..."
searchEndpoint=$(azd env get-value AZURE_AI_SEARCH_ENDPOINT 2>/dev/null | tr -d '\r')
openaiEndpoint=$(azd env get-value AZURE_OPENAI_ENDPOINT 2>/dev/null | tr -d '\r')
aiProjectEndpoint=$(azd env get-value AZURE_AI_AGENT_ENDPOINT 2>/dev/null | tr -d '\r')
deploymentModel=$(azd env get-value AZURE_ENV_GPT_MODEL_NAME 2>/dev/null | tr -d '\r')
embeddingModel=$(azd env get-value AZURE_ENV_EMBEDDING_MODEL_NAME 2>/dev/null | tr -d '\r')
storageAccountName=$(azd env get-value STORAGE_ACCOUNT_NAME 2>/dev/null | tr -d '\r')
sqlServer=$(azd env get-value SQLDB_SERVER 2>/dev/null | tr -d '\r')
sqlDatabase=$(azd env get-value SQLDB_DATABASE 2>/dev/null | tr -d '\r')
cuEndpoint=$(azd env get-value AZURE_OPENAI_CU_ENDPOINT 2>/dev/null | tr -d '\r')
cuApiVersion=$(azd env get-value AZURE_CONTENT_UNDERSTANDING_API_VERSION 2>/dev/null | tr -d '\r')
solutionName=$(azd env get-value SOLUTION_NAME 2>/dev/null | tr -d '\r')
usecase=$(azd env get-value USE_CASE 2>/dev/null | tr -d '\r')

# Ensure SQL server is FQDN
sqlServer="${sqlServer%.database.windows.net}"
sqlServerFQDN="${sqlServer}.database.windows.net"

echo "  Search Endpoint: $searchEndpoint"
echo "  Storage Account: $storageAccountName"
echo "  SQL Server:      $sqlServerFQDN"
echo "  SQL Database:    $sqlDatabase"
echo "  Solution Name:   $solutionName"
echo ""

# Check that a virtual environment is active
if [ -z "${VIRTUAL_ENV:-}" ]; then
  echo "⚠ No virtual environment detected. Please activate your venv first:"
  echo "  source .venv/bin/activate"
  exit 1
fi
echo "Using venv: $VIRTUAL_ENV"
echo ""

# Step 1: Create search index
echo "▶ Step 1/5: Creating search index..."
python3 "$INDEX_SCRIPTS/01_create_search_index.py" \
  --search_endpoint="$searchEndpoint" \
  --openai_endpoint="$openaiEndpoint" \
  --embedding_model="$embeddingModel"
echo "✓ Search index created"
echo ""

# Step 2: Create CU analyzers
echo "▶ Step 2/5: Creating CU template (text)..."
python3 "$INDEX_SCRIPTS/02_create_cu_template_text.py" \
  --cu_endpoint="$cuEndpoint" \
  --cu_api_version="$cuApiVersion"
echo "✓ CU text template ready"
echo ""

echo "▶ Step 3/5: Creating CU template (audio)..."
python3 "$INDEX_SCRIPTS/02_create_cu_template_audio.py" \
  --cu_endpoint="$cuEndpoint" \
  --cu_api_version="$cuApiVersion"
echo "✓ CU audio template ready"
echo ""

# Step 3: Process sample transcripts (DROP mode — clean tables)
echo "▶ Step 4/5: Processing sample transcripts (DROP mode, has_audio=0)..."
python3 "$INDEX_SCRIPTS/03_cu_process_data_text.py" \
  --search_endpoint="$searchEndpoint" \
  --ai_project_endpoint="$aiProjectEndpoint" \
  --deployment_model="$deploymentModel" \
  --embedding_model="$embeddingModel" \
  --storage_account_name="$storageAccountName" \
  --sql_server="$sqlServerFQDN" \
  --sql_database="$sqlDatabase" \
  --cu_endpoint="$cuEndpoint" \
  --cu_api_version="$cuApiVersion" \
  --usecase="$usecase" \
  --solution_name="$solutionName"
echo "✓ Sample transcripts processed"
echo ""

# Step 4: Append audio files
echo "▶ Step 5/6: Appending audio files (APPEND mode, has_audio=1)..."
python3 "$INDEX_SCRIPTS/04_cu_process_custom_data.py" \
  --search_endpoint="$searchEndpoint" \
  --openai_endpoint="$openaiEndpoint" \
  --ai_project_endpoint="$aiProjectEndpoint" \
  --deployment_model="$deploymentModel" \
  --embedding_model="$embeddingModel" \
  --storage_account_name="$storageAccountName" \
  --sql_server="$sqlServerFQDN" \
  --sql_database="$sqlDatabase" \
  --cu_endpoint="$cuEndpoint" \
  --cu_api_version="$cuApiVersion" \
  --solution_name="$solutionName" \
  --append
echo "✓ Audio files processed"
echo ""

# Step 5: Adjust audio dates to align with current date range
echo "▶ Step 6/6: Adjusting audio record dates to recent range..."
python3 "$INDEX_SCRIPTS/05_adjust_audio_dates.py" \
  --sql_server="$sqlServerFQDN" \
  --sql_database="$sqlDatabase"
echo "✓ Audio dates adjusted"
echo ""

echo "============================================="
echo "  ✅ Database rebuild complete"
echo "============================================="
