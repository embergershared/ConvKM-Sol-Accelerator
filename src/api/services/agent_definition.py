"""
Shared agent definition module.

This module provides the canonical tool definitions and default instructions
for the KM-ConversationAgent. Both the provisioning script
(infra/scripts/agent_scripts/01_create_agents.py) and the admin service
import from here to ensure consistency.
"""

from azure.ai.projects.models import (
    AzureAISearchAgentTool,
    AzureAISearchToolResource,
    AISearchIndexResource,
    FunctionTool,
)


def get_conversation_agent_tools(
    azure_ai_search_connection_name: str,
    azure_ai_search_index: str,
) -> list:
    """Return the canonical tool list for the conversation agent."""
    return [
        FunctionTool(
            name="get_sql_response",
            description="Execute T-SQL queries on the database to retrieve quantified, numerical, or metric-based data.",
            parameters={
                "type": "object",
                "properties": {
                    "sql_query": {
                        "type": "string",
                        "description": "A valid T-SQL query to execute against the database.",
                    }
                },
                "required": ["sql_query"],
            },
        ),
        AzureAISearchAgentTool(
            azure_ai_search=AzureAISearchToolResource(
                indexes=[
                    AISearchIndexResource(
                        project_connection_id=azure_ai_search_connection_name,
                        index_name=azure_ai_search_index,
                        query_type="vector_simple_hybrid",
                        top_k=5,
                    )
                ]
            )
        ),
    ]
