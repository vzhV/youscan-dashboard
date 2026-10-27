import { screen } from "@testing-library/react";
import { consumeConsoleErrors } from "@/test/consoleGuard";
import { renderWithProviders } from "@/test/renderWithProviders";
import { RouteErrorBoundary } from "./RouteErrorBoundary";

function Broken(): never {
  throw new Error("chunk failed to load");
}

describe("RouteErrorBoundary", () => {
  it("shows a friendly error with a Reload button when a route fails", () => {
    renderWithProviders(
      <RouteErrorBoundary>
        <Broken />
      </RouteErrorBoundary>,
    );

    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reload" })).toBeInTheDocument();
    // React reports the caught render error through console.error.
    expect(consumeConsoleErrors()).not.toHaveLength(0);
  });

  it("renders its children when nothing fails", () => {
    renderWithProviders(
      <RouteErrorBoundary>
        <p>fine</p>
      </RouteErrorBoundary>,
    );

    expect(screen.getByText("fine")).toBeInTheDocument();
  });
});
