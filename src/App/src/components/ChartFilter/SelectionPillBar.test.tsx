import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import SelectionPillBar from "./SelectionPillBar";
import dashboardReducer, {
  addChip,
} from "../../state/slices/dashboardSlice";

function makeStore() {
  return configureStore({
    reducer: { dashboards: dashboardReducer },
  });
}

describe("SelectionPillBar", () => {
  it("renders nothing when there are no chips", () => {
    const store = makeStore();
    const { container } = render(
      <Provider store={store}>
        <SelectionPillBar />
      </Provider>
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders chart and manual chips with the right text", () => {
    const store = makeStore();
    store.dispatch(
      addChip({ dimension: "Topic", value: "Billing", source: "chart" })
    );
    store.dispatch(
      addChip({ dimension: "Sentiment", value: "Negative", source: "manual" })
    );
    render(
      <Provider store={store}>
        <SelectionPillBar />
      </Provider>
    );
    expect(screen.getByText(/Topic: Billing/i)).toBeInTheDocument();
    expect(screen.getByText(/Sentiment: Negative/i)).toBeInTheDocument();
  });

  it("Reset all wipes every chip and fires onChipsChanged", () => {
    const store = makeStore();
    store.dispatch(
      addChip({ dimension: "Topic", value: "Billing", source: "chart" })
    );
    const onChange = jest.fn();
    render(
      <Provider store={store}>
        <SelectionPillBar onChipsChanged={onChange} />
      </Provider>
    );
    const reset = screen.getByRole("button", { name: /Reset all/i });
    fireEvent.click(reset);
    expect(store.getState().dashboards.chartFilterChips).toEqual([]);
    expect(onChange).toHaveBeenCalledTimes(1);
  });
});
