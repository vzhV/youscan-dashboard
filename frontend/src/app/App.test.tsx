import { render, screen } from "@testing-library/react";
import { App } from "./App";

describe("App", () => {
  it("renders the layout and the dashboard page on the root path", async () => {
    window.history.pushState({}, "", "/");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Dashboard", level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^API docs/ })).toBeInTheDocument();
  });
});
