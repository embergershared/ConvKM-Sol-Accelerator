## Technical Architecture

This section outlines the components and interactions that power the conversational insights platform. The architecture ingests call transcripts and audio files, applies AI services for enrichment and structuring, and surfaces insights via an interactive web experience.

![image](./Images/ReadMe/solution-architecture.png)

### Call Audio Files / Call Transcripts  
Raw audio and text-based transcripts are the primary input into the system. These files are uploaded and stored for downstream processing.

### Storage Account  
Stores uploaded call transcripts and audio files. Serves as the initial staging layer before processing begins.

### Azure AI Content Understanding  
Processes the audio and text files to extract conversation details, including speaker turns, timestamps, and semantic structure.

### Foundry IQ 
Indexes the vectorized transcripts for semantic search. Enables rapid retrieval of relevant conversation snippets and contextual fragments using vector search and keyword matching.

### SQL Database  
Stores structured output including extracted entities, mapped concepts, and additional metadata.

### Microsoft Foundry 
Performs topic modeling on enriched transcript data, uncovering themes and conversation patterns using pre-trained models.

### Azure OpenAI Service  
Provides large language model (LLM) capabilities to support summarization, natural language querying, and semantic enrichment.

### Agent Framework  
Handles orchestration and intelligent function calling for contextualized responses and multi-step reasoning over retrieved data.

### App Service  
Hosts the web application and API layer that interfaces with the AI services and storage layers. Manages user sessions and handles REST calls.

### Container Registry  
Stores containerized deployments for use in the hosting environment.

### Azure Cosmos DB  
Persists chat history and session context for the web interface. Enables retrieval of past interactions.

### Web Front-End  
An interactive UI where users can explore call insights, visualize trends, ask questions in natural language, and generate charts. Connects directly to Cosmos DB and App Services for real-time interaction.

### Dashboard drill-down (Stage B)
A right-side overlay drawer launched from any of the four interactive chart widgets (sentiment donut, AHT-by-topic bar, trending topics table, key-phrases word cloud). The drawer exposes a three-level navigation: **L1 time trend** (day or week buckets) → **L2 paginated call list** for a chosen bucket → **L3 transcript** for a chosen call.

Backed by three new FastAPI endpoints mounted at `/api/drill` (`drill_routes.py` → `drill_service.py` → `sqldb_service.fetch_drill_*`). All three SQL fetchers use bound `?` parameters via `cursor.execute(sql, params)` and `CAST(StartTime AS DATETIME)` because the underlying `processed_data.StartTime` / `EndTime` columns are stored as `VARCHAR(255)`. The optional `infra/scripts/sqldb_drill_index.sql` script ships two `NONCLUSTERED` indexes to keep L1 / L2 below 500 ms at sample-data scale.

The drawer state lives in a Redux Toolkit slice (`drillSlice`). The active drill stack is mirrored to `window.location.hash` (e.g. `#/drill/topic=Billing&bucket=week&from=...&to=...&call=...`), so a copied URL reproduces the same drilled view in another tab or shared chat message.