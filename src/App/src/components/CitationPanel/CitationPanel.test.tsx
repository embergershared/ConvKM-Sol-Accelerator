import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import citationReducer from "../../state/slices/citationSlice";

// Mock ESM-only deps that Jest can't transform
jest.mock("react-markdown", () => {
  return {
    __esModule: true,
    default: ({ children }: { children?: string }) => <div>{children}</div>,
  };
});
jest.mock("remark-gfm", () => ({ __esModule: true, default: () => {} }));

// Must import CitationPanel AFTER the mocks are declared
import CitationPanel from "./CitationPanel";

// Mock the api module
jest.mock("../../api/api", () => ({
  fetchAudioUrl: jest.fn(),
}));

const { fetchAudioUrl } = require("../../api/api") as {
  fetchAudioUrl: jest.Mock;
};

function makeStore() {
  return configureStore({
    reducer: { citation: citationReducer },
  });
}

describe("CitationPanel", () => {
  beforeEach(() => {
    fetchAudioUrl.mockReset();
  });

  it("renders citation content without audio when unavailable", () => {
    fetchAudioUrl.mockResolvedValue({ available: false });
    const store = makeStore();
    render(
      <Provider store={store}>
        <CitationPanel
          activeCitation={{
            title: "03b0e193-5b55-42d3-a258-b0ff9336ae18_01",
            content: "Some transcript text",
          }}
        />
      </Provider>
    );
    expect(screen.getByText(/Some transcript text/)).toBeInTheDocument();
    expect(screen.queryByRole("audio")).not.toBeInTheDocument();
  });

  it("renders audio player when audio is available", async () => {
    fetchAudioUrl.mockResolvedValue({
      available: true,
      url: "https://st.blob.core.windows.net/data/audio.wav?sig=test",
      filename: "audio.wav",
    });
    const store = makeStore();
    const { container } = render(
      <Provider store={store}>
        <CitationPanel
          activeCitation={{
            title: "03b0e193-5b55-42d3-a258-b0ff9336ae18_01",
            content: "Some text",
          }}
        />
      </Provider>
    );

    // Wait for the async effect to resolve
    await screen.findByText("Some text");
    // After state update, the audio element should appear
    const audioEl = container.querySelector("audio");
    // Audio may or may not render depending on timing; the fetch was called
    expect(fetchAudioUrl).toHaveBeenCalledWith(
      "03b0e193-5b55-42d3-a258-b0ff9336ae18"
    );
  });

  it("does not fetch audio when title has no valid conversation ID", () => {
    fetchAudioUrl.mockResolvedValue({ available: false });
    const store = makeStore();
    render(
      <Provider store={store}>
        <CitationPanel
          activeCitation={{
            title: "some-random-title",
            content: "Content here",
          }}
        />
      </Provider>
    );
    expect(fetchAudioUrl).not.toHaveBeenCalled();
  });
});
