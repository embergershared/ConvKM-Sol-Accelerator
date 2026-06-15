import { createAsyncThunk, createSlice, type PayloadAction } from "@reduxjs/toolkit";
import { generateUUIDv4 } from "../../configs/Utils";
import {
  fetchModels as fetchModelsApi,
  getLayoutConfig,
  selectModel as selectModelApi,
} from "../../api/api";
import {
  type AppConfig,
  type ChartConfigItem,
  type CosmosDBHealth,
  type ModelOption,
} from "../../types/AppTypes";

export type AppSliceState = {
  selectedConversationId: string;
  generatedConversationId: string;
  availableModels: ModelOption[];
  selectedModelId: string;
  modelSwitching: boolean;
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
    return modelId;
  } catch {
    return rejectWithValue("Unable to apply the selected model.");
  }
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

        if (
          state.selectedModelId &&
          action.payload.some((model) => model.id === state.selectedModelId)
        ) {
          return;
        }

        state.selectedModelId = getDefaultModelId(action.payload);
      })
      .addCase(selectModel.pending, (state) => {
        state.modelSwitching = true;
      })
      .addCase(selectModel.fulfilled, (state, action) => {
        state.modelSwitching = false;
        state.selectedModelId = action.payload;
      })
      .addCase(selectModel.rejected, (state) => {
        state.modelSwitching = false;
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
  setConfig,
} = appSlice.actions;

export default appSlice.reducer;
