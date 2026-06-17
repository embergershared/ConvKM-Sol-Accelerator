import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { FluentProvider, webLightTheme } from "@fluentui/react-components";
import UserMenu from "./UserMenu";

const renderWithProvider = (ui: React.ReactElement) =>
  render(<FluentProvider theme={webLightTheme}>{ui}</FluentProvider>);

describe("UserMenu", () => {
  const originalLocation = window.location;

  beforeEach(() => {
    localStorage.clear();
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...originalLocation, href: "" },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      writable: true,
      value: originalLocation,
    });
  });

  it("renders the avatar trigger with the user name", () => {
    renderWithProvider(<UserMenu userName="Jane Doe" />);
    const trigger = screen.getByRole("button", {
      name: /user menu for jane doe/i,
    });
    expect(trigger).toBeInTheDocument();
  });

  it("opens the menu when the avatar is clicked", () => {
    renderWithProvider(<UserMenu userName="Jane Doe" />);
    const trigger = screen.getByRole("button", {
      name: /user menu for jane doe/i,
    });
    fireEvent.click(trigger);
    expect(screen.getByText("Sign out")).toBeInTheDocument();
  });

  it("shows the user name in the menu header", () => {
    renderWithProvider(<UserMenu userName="Jane Doe" />);
    fireEvent.click(
      screen.getByRole("button", { name: /user menu for jane doe/i })
    );
    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
  });

  it("clears localStorage and redirects on sign out", () => {
    localStorage.setItem("userId", "test-user-id");
    renderWithProvider(<UserMenu userName="Jane Doe" />);
    fireEvent.click(
      screen.getByRole("button", { name: /user menu for jane doe/i })
    );
    fireEvent.click(screen.getByText("Sign out"));
    expect(localStorage.getItem("userId")).toBeNull();
    expect(window.location.href).toBe(
      "/.auth/logout?post_logout_redirect_uri=/"
    );
  });

  it("falls back to 'User' when userName is empty", () => {
    renderWithProvider(<UserMenu userName="" />);
    fireEvent.click(
      screen.getByRole("button", { name: /user menu for user/i })
    );
    expect(screen.getByText("User")).toBeInTheDocument();
  });
});
