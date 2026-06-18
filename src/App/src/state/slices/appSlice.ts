import { createAsyncThunk, createSlice, type PayloadAction } from "@reduxjs/toolkit";
import { generateUUIDv4 } from "../../configs/Utils";
import {
  fetchModelStatus as fetchModelStatusApi,
  fetchModels as fetchModelsApi,
  getLayoutConfig,
  selectModel as selectModelApi,
} from "../../api/api";
import {
  type AppConfig,
  type ChartConfigItem,
  type CosmosDBHealth,
  type ModelOption,
  type ModelStatus,
  type ModelStatusValue,
} from "../../types/AppTypes";

export type AppSliceState = {
  selectedConversationId: string;
  generatedConversationId: string;
  availableModels: ModelOption[];
  selectedModelId: string;
  modelSwitching: boolean;
  modelStatus: ModelStatusValue;
  modelStatusError: string | null;
  pendingModelId: string | null;
  config: {
    appConfig: AppConfig;
    charts: ChartConfigItem[];
  };
  cosmosInfo: CosmosDBHealth;
  showAppSpinner: boolean;
};

const initialState: AppSliceState = {
  selectedConversationId: "",
  generatedConversationId: generateUUIDv4(),
  availableModels: [],
  selectedModelId: "",
  modelSwitching: false,
  modelStatus: "active",
  modelStatusError: null,
  pendingModelId: null,
  config: {
    appConfig: null,
    charts: [],
  },
  cosmosInfo: { cosmosDB: false, status: "" },
  showAppSpinner: false,
};

export const fetchLayoutConfig = createAsyncThunk(
  "app/fetchLayoutConfig",
  async () => getLayoutConfig()
);

export const fetchModels = createAsyncThunk<
  ModelOption[],
  void,
  { rejectValue: string }
>("app/fetchModels", async (_, { rejectWithValue }) => {
  try {
    return await fetchModelsApi();
  } catch {
    return rejectWithValue("Unable to load models.");
  }
});

const getDefaultModelId = (models: ModelOption[]) =>
  models.find((model) => model.is_default)?.id ?? models[0]?.id ?? "";

export const selectModel = createAsyncThunk<
  string,
  string,
  { rejectValue: string }
>("app/selectModel", async (modelId, { dispatch, rejectWithValue }) => {
  try {
    await selectModelApi(modelId);
    // Re-read the deployments so is_default reflects the agents' new model.
    await dispatch(fetchModels());
    // Kick off polling so the UI can show "activating model…" until both
    // agent versions report "active".
    void dispatch(pollModelStatus(modelId));
    return modelId;
  } catch {
    return rejectWithValue("Unable to apply the selected model.");
  }
});

export const fetchModelStatusOnce = createAsyncThunk<
  ModelStatus,
  void,
  { rejectValue: string }
>("app/fetchModelStatusOnce", async (_, { rejectWithValue }) => {
  try {
    return await fetchModelStatusApi();
  } catch {
    return rejectWithValue("Unable to read model status.");
  }
});

// Poll /api/models/status until BOTH agents' latest versions become active
// (or until we hit the timeout / a permanent failure). Foundry typically
// takes 30-120 seconds to provision a new agent version after a model
// change, so we poll every 5s for up to 3 minutes.
const POLL_INTERVAL_MS = 5_000;
const POLL_MAX_ATTEMPTS = 36; // 36 * 5s = 180s

export const pollModelStatus = createAsyncThunk<
  void,
  string | undefined,
  { rejectValue: string }
>("app/pollModelStatus", async (_targetModelId, { dispatch, rejectWithValue }) => {
  for (let attempt = 0; attempt < POLL_MAX_ATTEMPTS; attempt += 1) {
    let status: ModelStatus;
    try {
      status = await fetchModelStatusApi();
    } catch {
      // Transient failure — keep polling rather than giving up.
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
      continue;
    }
    dispatch(setModelStatus(status));
    if (status.ready) {
      return;
    }
    if (status.status === "failed") {
      return rejectWithValue(
        "Foundry reported a failure provisioning the new model version."
      );
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
  return rejectWithValue(
    "Timed out waiting for the new model to become active (3 minutes)."
  );
});

const appSlice = createSlice({
  name: "app",
  initialState,
  reducers: {
    setSelectedConversationId(state, action: PayloadAction<string>) {
      state.selectedConversationId = action.payload;
    },
    setGeneratedConversationId(state, action: PayloadAction<string>) {
      state.generatedConversationId = action.payload;
    },
    setSelectedModelId(state, action: PayloadAction<string>) {
      state.selectedModelId = action.payload;
    },
    startNewConversation(state) {
      state.selectedConversationId = "";
      state.generatedConversationId = generateUUIDv4();
    },
    setShowAppSpinner(state, action: PayloadAction<boolean>) {
      state.showAppSpinner = action.payload;
    },
    setCosmosInfo(state, action: PayloadAction<CosmosDBHealth>) {
      state.cosmosInfo = action.payload;
    },
    setModelStatus(state, action: PayloadAction<ModelStatus>) {
      state.modelStatus = action.payload.status;
      if (action.payload.ready) {
        state.modelStatusError = null;
      }
    },
    setConfig(
      state,
      action: PayloadAction<{ appConfig: AppConfig; charts: ChartConfigItem[] }>
    ) {
      state.config = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchLayoutConfig.fulfilled, (state, action) => {
        state.config = action.payload;
      })
      .addCase(fetchModels.fulfilled, (state, action) => {
        state.availableModels = action.payload;

        // During a model switch the thunk sets selectedModelId itself, so
        // don't override it here — just keep the in-flight selection.
        if (
          state.modelSwitching &&
          state.selectedModelId &&
          action.payload.some((model) => model.id === state.selectedModelId)
        ) {
          return;
        }

        // Otherwise always pick the backend's is_default (reflects the model
        // actually running on the agents) so a page refresh is authoritative.
        state.selectedModelId = getDefaultModelId(action.payload);
      })
      .addCase(selectModel.pending, (state, action) => {
        state.modelSwitching = true;
        state.modelStatus = "creating";
        state.modelStatusError = null;
        state.pendingModelId = action.meta.arg;
      })
      .addCase(selectModel.fulfilled, (state, action) => {
        state.modelSwitching = false;
        state.selectedModelId = action.payload;
        // Status stays "creating" — pollModelStatus will flip it to "active"
        // once Foundry finishes provisioning both agent versions.
      })
      .addCase(selectModel.rejected, (state, action) => {
        state.modelSwitching = false;
        state.modelStatus = "failed";
        state.modelStatusError =
          action.payload ?? "Unable to apply the selected model.";
        state.pendingModelId = null;
      })
      .addCase(pollModelStatus.fulfilled, (state) => {
        state.modelStatus = "active";
        state.modelStatusError = null;
        state.pendingModelId = null;
      })
      .addCase(pollModelStatus.rejected, (state, action) => {
        // Timeouts are not actionable — the model change already went through
        // on the backend; Foundry just takes time to report "active". Silently
        // reset to active so the user isn't shown a scary banner they can't act on.
        const isTimeout = action.payload?.includes("Timed out");
        if (isTimeout) {
          state.modelStatus = "active";
          state.modelStatusError = null;
        } else {
          state.modelStatus = "failed";
          state.modelStatusError =
            action.payload ?? "Model activation failed.";
        }
        state.pendingModelId = null;
      })
      .addCase(fetchModelStatusOnce.fulfilled, (state, action) => {
        state.modelStatus = action.payload.status;
        if (action.payload.ready) {
          state.modelStatusError = null;
          state.pendingModelId = null;
        }
      });
  },
});

export const {
  setSelectedConversationId,
  setGeneratedConversationId,
  setSelectedModelId,
  startNewConversation,
  setShowAppSpinner,
  setCosmosInfo,
  setModelStatus,
  setConfig,
} = appSlice.actions;

export default appSlice.reducer;
