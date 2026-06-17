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
import os

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition

from common.logging.event_utils import track_event_if_configured
from services.agent_definition import get_conversation_agent_tools

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent-compatibility filter
# ---------------------------------------------------------------------------
#
# Foundry's Agent Service can only use a deployment that simultaneously:
#   1. Speaks chat completion (every chat model does — necessary but not sufficient).
#   2. Exposes function/tool calling — required by our KM-ConversationAgent which
#      uses FunctionTool (get_sql_response) and AzureAISearchAgentTool.
#   3. Is published by a model publisher that Foundry's Agent Service supports.
#      The Foundry portal's "Agent → Model" dropdown today lists models from
#      OpenAI, Microsoft, xAI (Grok), DeepSeek, Mistral AI, and Meta among
#      others — empirically verified against the live "Deployments" picker.
#      We mirror that set here so our dropdown matches the Foundry portal.
#
# The publisher allowlist is overridable at deploy-time so we don't need a code
# change when Microsoft adds a new agent-capable publisher.
#
_DEFAULT_AGENT_COMPATIBLE_PUBLISHERS = (
    "OpenAI,Microsoft,xAI,DeepSeek,Meta"
)

# Model-name substrings that should always be excluded even if their
# capabilities dict happens to claim chat completion. Empirically, these are
# never agent-compatible because the Foundry runtime can't bind tools to them.
_EXCLUDED_MODEL_NAME_SUBSTRINGS = (
    "embedding",
    "whisper",      # speech-to-text
    "tts",          # text-to-speech
    "dall-e",       # image gen
    "babbage",      # legacy completion
    "davinci",      # legacy completion
    "ada",          # legacy completion
)


def _truthy(value) -> bool:
    """Return True for the strings/values Foundry uses to mean 'enabled'."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in ("", "false", "0", "no", "disabled", "none")


def _capability_lookup(capabilities, *aliases: str):
    """Look up a capability tolerating key-name casing/separator variants.

    Foundry's deployments API has shipped capability keys in several shapes
    over time (``chatCompletion``, ``chat_completion``, ``ChatCompletion``,
    and occasionally as a nested ``{"supported": true}`` object). We
    normalize keys to lowercase with underscores removed and try every
    alias. Returns the raw value, or ``None`` if no alias is present.
    """
    if not capabilities:
        return None
    try:
        items = capabilities.items()
    except AttributeError:
        return None
    norm = {str(k).lower().replace("_", "").replace("-", ""): v for k, v in items}
    for alias in aliases:
        key = alias.lower().replace("_", "").replace("-", "")
        if key in norm:
            return norm[key]
    return None


def _capability_truthy(capabilities, *aliases: str):
    """Return True/False if the capability is explicitly set, else ``None``.

    Handles the nested ``{"supported": true}`` / ``{"enabled": true}`` shape
    by drilling into common inner keys before falling back to ``_truthy``.
    A returned ``None`` means "key absent" — callers should not treat that
    as a rejection signal, only an explicit ``False`` should.
    """
    value = _capability_lookup(capabilities, *aliases)
    if value is None:
        return None
    if isinstance(value, dict):
        for inner in ("supported", "enabled", "available", "value"):
            if inner in value:
                return _truthy(value[inner])
        return bool(value)
    return _truthy(value)


def _allowed_publishers() -> set[str]:
    """Comma-separated publisher allowlist from the env, case-insensitive."""
    raw = os.getenv("MODEL_FILTER_ALLOWED_PUBLISHERS", _DEFAULT_AGENT_COMPATIBLE_PUBLISHERS)
    return {p.strip().lower() for p in raw.split(",") if p.strip()}


def _require_function_calling() -> bool:
    """Whether to drop deployments that don't advertise function-calling support."""
    return _truthy(os.getenv("MODEL_FILTER_REQUIRE_FUNCTION_CALLING", "true"))


def _is_model_deployment(deployment) -> bool:
    """Return True when *deployment* represents a model deployment.

    Unknown / missing types are treated as model deployments so nothing is
    hidden by an overly strict filter.
    """
    deployment_type = getattr(deployment, "type", None)
    if deployment_type is None:
        return True
    return "model" in str(deployment_type).lower()


def _is_agent_compatible(deployment, requirements: "AgentCompatibilityRequirements") -> tuple[bool, str]:
    """Return ``(included, reason)`` for the conversation-agent dropdown.

    Inclusion is conservative: a deployment is shown only when ALL of the
    following hold. The returned reason explains every exclusion so we can
    log it for visibility — never silently drop a deployment.

    1. The model name doesn't match a hardcoded "never an agent" substring
       (embedding, whisper, tts, dall-e, legacy completion families).
    2. ``capabilities["chatCompletion"]`` is not explicitly False (both
       KM-ConversationAgent and KM-TitleAgent need chat completion). A
       missing key is treated as "unknown" and does NOT reject — the
       publisher allowlist + name-substring excludes still keep
       non-chat models out.
    3. ``capabilities["functionCalling"]`` is not explicitly False IF the
       conversation agent's current definition declares any tools (which
       it does — SQL + Azure AI Search). Override with
       MODEL_FILTER_REQUIRE_FUNCTION_CALLING=false.
    4. The model's publisher is in MODEL_FILTER_ALLOWED_PUBLISHERS
       (default: OpenAI, Microsoft — the publishers Foundry's Agent Service
       currently supports as agent runtime targets). Only enforced when at
       least one agent uses a Foundry-managed tool such as
       ``AzureAISearchAgentTool`` that requires the agent-service runtime.
    """
    name = getattr(deployment, "name", "") or ""
    model_name = getattr(deployment, "model_name", "") or name
    publisher = (getattr(deployment, "model_publisher", "") or "").strip()
    capabilities = getattr(deployment, "capabilities", None) or {}

    lower_model = str(model_name).lower()
    for excluded in _EXCLUDED_MODEL_NAME_SUBSTRINGS:
        if excluded in lower_model:
            return False, f"model name contains excluded substring '{excluded}'"

    chat = _capability_truthy(capabilities, "chatCompletion", "chat_completion", "chat")
    if chat is False:
        return False, "capabilities.chatCompletion is explicitly false"

    if requirements.requires_function_calling and _require_function_calling():
        fn = _capability_truthy(
            capabilities,
            "functionCalling",
            "function_calling",
            "tools",
            "toolCalling",
            "tool_calling",
        )
        if fn is False:
            return False, "capabilities.functionCalling is explicitly false"

    if requirements.requires_agent_service_runtime:
        allowed = _allowed_publishers()
        if allowed and publisher.lower() not in allowed:
            return False, (
                f"publisher '{publisher or '(unknown)'}' is not in "
                f"MODEL_FILTER_ALLOWED_PUBLISHERS ({sorted(allowed)}) — required by "
                f"one of the agents' Foundry-managed tools"
            )

    return True, "ok"


class AgentCompatibilityRequirements:
    """Capabilities a model deployment must satisfy to be usable by ALL the
    agents this service manages.

    Built by ``ModelService._discover_agent_requirements`` from the live agent
    definitions, so adding/removing a tool on the conversation agent
    automatically changes which deployments appear in the dropdown — no code
    change required.
    """

    def __init__(self):
        self.required_capabilities: set[str] = {"chatCompletion"}
        self.requires_function_calling: bool = False
        self.requires_agent_service_runtime: bool = False
        self.tool_types_seen: set[str] = set()
        self.agents_inspected: list[str] = []
        self.agents_failed: list[tuple[str, str]] = []

    def add_tool(self, tool: object) -> None:
        type_name = getattr(tool, "type", None) or type(tool).__name__
        type_name = str(type_name)
        self.tool_types_seen.add(type_name)

        # Any tool requires the model to support function calling.
        self.requires_function_calling = True

        # Foundry-managed tools (Azure AI Search, File Search, Code Interpreter,
        # MCP, Browser Automation, etc.) plug into the Agent Service runtime,
        # which only supports certain model publishers.
        lower = type_name.lower()
        if (
            "azure_ai_search" in lower
            or "file_search" in lower
            or "code_interpreter" in lower
            or "browser_automation" in lower
            or "mcp" in lower
            or "memory_search" in lower
            or "bing" in lower
            or "sharepoint" in lower
            or "fabric" in lower
            or "openapi" in lower
        ):
            self.requires_agent_service_runtime = True

    def summary(self) -> str:
        parts = ["chatCompletion"]
        if self.requires_function_calling:
            parts.append("functionCalling")
        if self.requires_agent_service_runtime:
            parts.append("agentServiceRuntime(publisher allowlist)")
        return ", ".join(parts)


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

    async def _current_models(self) -> dict[str, str | None]:
        """Return ``{agent_name: model}`` for every agent this service manages.

        Reads the latest version's model for both KM-ConversationAgent and
        KM-TitleAgent. Best-effort: failure on one agent does not stop the
        other, and ``None`` for a slot just means we couldn't read that agent.
        """
        result: dict[str, str | None] = {}
        for agent_name in (self._conversation_agent_name, self._title_agent_name):
            if not agent_name:
                continue
            try:
                agent_details = await self._client.agents.get(agent_name)
                result[agent_name] = agent_details.versions.latest.definition.model
            except Exception:
                logger.warning(
                    "Unable to read current model for agent %s",
                    agent_name,
                    exc_info=True,
                )
                result[agent_name] = None
        return result

    async def _current_model(self) -> str | None:
        """Return the model the conversation agent's latest version is using.

        Falls back to the title agent's model when the conversation agent
        can't be read, so the dropdown is never left without a selection.
        """
        models = await self._current_models()
        return (
            models.get(self._conversation_agent_name)
            or models.get(self._title_agent_name)
        )

    async def get_status(self) -> dict:
        """Aggregate model + readiness status across every managed agent.

        Foundry sets ``AgentVersionDetails.status`` to ``"creating"`` while a
        newly-published version is provisioning and flips it to ``"active"``
        once the underlying model deployment is bound and routable. Polling
        this method lets the UI display a "pending model change" indicator
        until BOTH KM-ConversationAgent and KM-TitleAgent report ``"active"``
        on their latest version.

        Returns:
            ``{"model": <current model id or None>,
               "status": "active"|"creating"|"failed"|"unknown",
               "ready": bool,
               "agents": {<agent_name>: {"model", "status", "version"|"error"}}}``

            ``status`` is the worst-case aggregate across agents:
            ``failed`` if any agent reports failed; otherwise ``creating``
            if any agent is still provisioning; ``active`` only when every
            agent is active; ``unknown`` if we couldn't read any agent.
            ``ready`` is True iff status == "active".
        """
        per_agent: dict[str, dict] = {}
        for agent_name in (self._conversation_agent_name, self._title_agent_name):
            if not agent_name:
                continue
            try:
                agent_details = await self._client.agents.get(agent_name)
                latest = agent_details.versions.latest
                per_agent[agent_name] = {
                    "model": getattr(latest.definition, "model", None),
                    "status": str(getattr(latest, "status", None) or "unknown").lower(),
                    "version": getattr(latest, "version", None),
                }
            except Exception as exc:
                logger.warning(
                    "Unable to read status for agent %s",
                    agent_name,
                    exc_info=True,
                )
                per_agent[agent_name] = {
                    "model": None,
                    "status": "unknown",
                    "error": repr(exc),
                }

        statuses = {info["status"] for info in per_agent.values()}
        if "failed" in statuses:
            overall = "failed"
        elif statuses and statuses == {"active"}:
            overall = "active"
        elif "creating" in statuses:
            overall = "creating"
        else:
            overall = "unknown"

        current_model = (
            per_agent.get(self._conversation_agent_name, {}).get("model")
            or (per_agent.get(self._title_agent_name) or {}).get("model")
        )

        return {
            "model": current_model,
            "status": overall,
            "ready": overall == "active",
            "agents": per_agent,
        }

    async def _discover_agent_requirements(self) -> AgentCompatibilityRequirements:
        """Inspect every agent this service manages and aggregate the model
        capabilities they collectively require.

        A model that fails this aggregated requirement cannot be used by
        :meth:`select_model` (which republishes BOTH agents with the chosen
        model), so it must not appear in the dropdown.

        Best-effort: if an agent can't be read, that failure is logged and
        the discovery continues with the others. The result is at minimum
        ``{chatCompletion}`` so the filter is never empty.
        """
        requirements = AgentCompatibilityRequirements()
        agent_names = [
            n for n in (self._conversation_agent_name, self._title_agent_name) if n
        ]
        for agent_name in agent_names:
            try:
                agent_details = await self._client.agents.get(agent_name)
                definition = agent_details.versions.latest.definition
                tools = getattr(definition, "tools", None) or []
                requirements.agents_inspected.append(agent_name)
                for tool in tools:
                    requirements.add_tool(tool)
            except Exception as exc:  # noqa: BLE001 — discovery is best-effort
                requirements.agents_failed.append((agent_name, repr(exc)))
                logger.warning(
                    "Agent compatibility discovery: could not inspect %r — %r",
                    agent_name, exc,
                )

        logger.info(
            "Agent compatibility requirements (agents=%s, failed=%s, tool_types=%s): %s",
            requirements.agents_inspected,
            [n for n, _ in requirements.agents_failed],
            sorted(requirements.tool_types_seen),
            requirements.summary(),
        )
        return requirements

    async def _deployment_names(
        self,
        requirements: AgentCompatibilityRequirements | None = None,
    ) -> list[str]:
        """Return the names of model deployments compatible with ALL the
        agents this service manages.

        Every deployment seen is logged at INFO; every rejection is logged
        with the reason so the operator can tell — from the API log alone —
        why a given model didn't appear in the dropdown.
        """
        if requirements is None:
            requirements = await self._discover_agent_requirements()

        names: list[str] = []
        async for deployment in self._client.deployments.list():
            dep_name = getattr(deployment, "name", "") or "(unnamed)"

            if not _is_model_deployment(deployment):
                logger.info(
                    "Model dropdown: skip deployment %r (type=%s, not a model deployment)",
                    dep_name, getattr(deployment, "type", None),
                )
                continue

            included, reason = _is_agent_compatible(deployment, requirements)
            if not included:
                logger.info(
                    "Model dropdown: skip deployment %r — %s (publisher=%r, capabilities=%r)",
                    dep_name,
                    reason,
                    getattr(deployment, "model_publisher", "?"),
                    getattr(deployment, "capabilities", None),
                )
                continue

            logger.info(
                "Model dropdown: include deployment %r (publisher=%r, model=%r)",
                dep_name,
                getattr(deployment, "model_publisher", "?"),
                getattr(deployment, "model_name", "?"),
            )
            names.append(str(dep_name))
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
        # Discover requirements ONCE and pass them into both helper calls so
        # we don't read the agent definitions twice on the same request.
        requirements = await self._discover_agent_requirements()
        current_models = await self._current_models()
        names = await self._deployment_names(requirements=requirements)

        # The conversation agent drives the dropdown's selected value; fall
        # back to the title agent if the conversation agent can't be read.
        current_model = (
            current_models.get(self._conversation_agent_name)
            or current_models.get(self._title_agent_name)
        )

        # Log per-agent models so drift between the two agents (e.g. a manual
        # edit in the Foundry portal that updated only one) is visible.
        if not current_models:
            logger.error(
                "Model dropdown: no agent names configured "
                "(AGENT_NAME_CONVERSATION=%r, AGENT_NAME_TITLE=%r). "
                "The dropdown cannot determine which model is currently active.",
                self._conversation_agent_name,
                self._title_agent_name,
            )
        logger.info(
            "Model dropdown: current agent models = %s (selected for dropdown=%r)",
            current_models, current_model,
        )
        distinct = {m for m in current_models.values() if m}
        if len(distinct) > 1:
            logger.warning(
                "Model dropdown: managed agents are on DIFFERENT models %s — "
                "the dropdown reflects the conversation agent's model. "
                "Selecting a model from the dropdown will realign both agents.",
                current_models,
            )

        # ALWAYS surface the model that's actually applied to the agents, even
        # when the compatibility filter would otherwise hide it (e.g. a model
        # published by a vendor outside MODEL_FILTER_ALLOWED_PUBLISHERS that
        # was selected directly in the Foundry portal). Without this, the
        # dropdown would silently fall back to "first item" and mislead the
        # operator about which model is running.
        if current_model and current_model not in names:
            logger.info(
                "Model dropdown: forcing inclusion of currently-applied model "
                "%r even though it was filtered out — so the UI shows what is "
                "actually running on the agents.",
                current_model,
            )
            names = [current_model, *names]

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

        NOTE FOR ADMINISTRATORS: This is the ONLY supported way to change the
        chat agents' model. Do NOT change the model from the Azure AI Foundry
        portal — the portal's "Unsupported tools" compatibility check will
        offer to STRIP the Azure AI Search agent tool from the conversation
        agent (which breaks search-grounded citations). This method
        side-steps that portal check by submitting a new version via the SDK
        and ALWAYS rebuilds the tool list from source so the connection ID
        and index name stay wired up. See README → "Operating the chat
        agents — model changes" for details.

        Args:
            model_id: A model deployment name returned by :meth:`list_models`.

        Returns:
            ``{"model": model_id}``.

        Raises:
            ValueError: if *model_id* is not a known deployment, or is known
                but not compatible with all the agents this service manages.
        """
        requirements = await self._discover_agent_requirements()
        valid_names = await self._deployment_names(requirements=requirements)
        if model_id not in valid_names:
            raise ValueError(
                f"Model deployment '{model_id}' is not compatible with the "
                f"agents managed by this service "
                f"(agents={requirements.agents_inspected}, "
                f"required capabilities=[{requirements.summary()}]). "
                f"See the API logs for the per-deployment rejection reason."
            )

        agent_names = [
            name
            for name in (self._conversation_agent_name, self._title_agent_name)
            if name
        ]

        if not agent_names:
            raise ValueError(
                "No agent names configured (AGENT_NAME_CONVERSATION / "
                "AGENT_NAME_TITLE are both empty). Cannot apply model selection."
            )

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
