"""ModelService — lists Foundry model deployments and applies a selected model
to the chat agents.

This service lists the live model deployments in the Foundry project and, when a
model is selected, updates the model of BOTH conversational agents
(KM-ConversationAgent and KM-TitleAgent) by publishing a new version that
preserves the existing instructions and REBUILDS tools from source.

IMPORTANT: This service MUST use AIProjectClient from azure.ai.projects.aio.
           Only AIProjectClient.agents exposes the version-management methods
           (get / create_version) and AIProjectClient.deployments exposes the
           deployment listing required here.
"""

import logging

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

from common.logging.event_utils import track_event_if_configured
from services.agent_definition import get_conversation_agent_tools

logger = logging.getLogger(__name__)


def _is_model_deployment(deployment) -> bool:
    """Return True when *deployment* represents a model deployment.

    Unknown / missing types are treated as model deployments so nothing is
    hidden by an overly strict filter.
    """
    deployment_type = getattr(deployment, "type", None)
    if deployment_type is None:
        return True
    return "model" in str(deployment_type).lower()


def _is_chat_model(deployment) -> bool:
    """Return True when *deployment* is a chat-completion–capable model.

    Primary check: the ``capabilities`` dict (present on ``ModelDeployment``
    objects in azure-ai-projects 2.0.0b3) is inspected for ``"chatCompletion"``.
    Any truthy value (e.g. ``"true"``, ``"enabled"``) means the deployment
    supports chat completion and should appear in the dropdown.

    Fallback heuristic (when ``capabilities`` is absent or lacks
    ``"chatCompletion"``): exclude any deployment whose ``model_name`` or
    ``name`` contains ``"embedding"`` (case-insensitive). All other deployments
    pass through so no unfamiliar-but-valid chat model is silently dropped.
    """
    capabilities = getattr(deployment, "capabilities", None)
    if capabilities:
        chat_cap = capabilities.get("chatCompletion", "")
        if chat_cap:
            return str(chat_cap).lower() not in ("false", "0", "no", "disabled")
        # capabilities present but "chatCompletion" absent — fall through.

    model_name = (
        getattr(deployment, "model_name", None)
        or getattr(deployment, "name", None)
        or ""
    )
    return "embedding" not in str(model_name).lower()


class ModelService:
    """Lists model deployments and applies a model choice to the chat agents.

    Args:
        project_client: An open ``AIProjectClient`` instance
            (``azure.ai.projects.aio``). The caller owns its lifecycle.
        conversation_agent_name: Full KM-ConversationAgent name.
        title_agent_name: Full KM-TitleAgent name (may be ``None``).
        chat_service: A ``ChatService`` instance used to clear the thread cache
            after a model change so the next request picks up the new agent
            version.
        search_connection_name: Azure AI Search project-connection name used
            to rebuild conversation-agent tools on each model swap.
        search_index_name: Azure AI Search index name used to rebuild
            conversation-agent tools on each model swap.
    """

    def __init__(
        self,
        project_client: AIProjectClient,
        conversation_agent_name: str,
        title_agent_name: str | None,
        chat_service,
        search_connection_name: str = "",
        search_index_name: str = "",
    ):
        self._client = project_client
        self._conversation_agent_name = conversation_agent_name
        self._title_agent_name = title_agent_name
        self._chat_service = chat_service
        self._search_connection_name = search_connection_name
        self._search_index_name = search_index_name

    async def _current_model(self) -> str | None:
        """Return the model the conversation agent's latest version is using."""
        try:
            agent_details = await self._client.agents.get(self._conversation_agent_name)
            return agent_details.versions.latest.definition.model
        except Exception:
            logger.warning(
                "Unable to read current model for agent %s",
                self._conversation_agent_name,
                exc_info=True,
            )
            return None

    async def _deployment_names(self) -> list[str]:
        """Return the names of chat-capable model deployments in the project."""
        names: list[str] = []
        async for deployment in self._client.deployments.list():
            if not _is_model_deployment(deployment):
                continue
            if not _is_chat_model(deployment):
                continue
            name = getattr(deployment, "name", None)
            if name:
                names.append(str(name))
        return names

    async def list_models(self) -> list[dict]:
        """List available model deployments for the chat dropdown.

        Returns:
            A list of ``{"id", "display_name", "is_default"}`` dicts where
            ``is_default`` marks the deployment currently applied to the
            conversation agent. If the current model is not found among the
            deployments, the first one is marked as default so the dropdown
            always has a selection.
        """
        current_model = await self._current_model()
        names = await self._deployment_names()

        models = [
            {"id": name, "display_name": name, "is_default": name == current_model}
            for name in names
        ]

        if models and not any(model["is_default"] for model in models):
            models[0]["is_default"] = True

        return models

    async def select_model(self, model_id: str) -> dict:
        """Apply *model_id* to both chat agents.

        Publishes a new version of each agent (KM-ConversationAgent and
        KM-TitleAgent) with the selected model, preserving the current
        instructions. Tools are REBUILT from source for the conversation agent
        (never round-tripped): the Foundry GET returns empty
        project_connection_id / index_name on AzureAISearchAgentTool, so
        re-submitting the fetched tools silently wires the search tool to
        nothing and breaks citations. The title agent carries no tools.
        Clears the process-local thread cache so the next chat request uses
        the new agent versions.

        Args:
            model_id: A model deployment name returned by :meth:`list_models`.

        Returns:
            ``{"model": model_id}``.

        Raises:
            ValueError: if *model_id* is not a known deployment.
        """
        valid_names = await self._deployment_names()
        if model_id not in valid_names:
            raise ValueError(f"Unknown model deployment '{model_id}'.")

        agent_names = [
            name
            for name in (self._conversation_agent_name, self._title_agent_name)
            if name
        ]

        for agent_name in agent_names:
            agent_details = await self._client.agents.get(agent_name)
            definition = agent_details.versions.latest.definition

            definition_kwargs = {
                "model": model_id,
                "instructions": definition.instructions,
            }

            if agent_name == self._conversation_agent_name:
                # Rebuild tools from source — never round-trip the GET response.
                # The Foundry service returns empty project_connection_id /
                # index_name on AzureAISearchAgentTool, so re-submitting the
                # fetched tools silently breaks search citations.
                definition_kwargs["tools"] = get_conversation_agent_tools(
                    azure_ai_search_connection_name=self._search_connection_name,
                    azure_ai_search_index=self._search_index_name,
                )
            # Title agent: no tools — omit the key entirely.

            await self._client.agents.create_version(
                agent_name=agent_name,
                definition=PromptAgentDefinition(**definition_kwargs),
            )
            logger.info("Model updated to '%s' for agent %s", model_id, agent_name)

        self._invalidate_thread_cache()
        track_event_if_configured("chat_model_selected", {"model": model_id})

        return {"model": model_id}

    def _invalidate_thread_cache(self) -> None:
        """Clear the process-local thread cache in chat_service.

        After the agents' model changes, existing threads are bound to the
        previous agent versions, so we evict all entries to force new threads
        on the next request.

        LIMITATION: process-local only. In a multi-instance App Service
        deployment each instance manages its own cache and other instances see
        stale data until their TTL expires.
        """
        try:
            self._chat_service.get_thread_cache().clear()
            logger.info("Thread cache cleared after model change (process-local only)")
        except Exception:
            logger.warning("Failed to clear thread cache after model change", exc_info=True)
