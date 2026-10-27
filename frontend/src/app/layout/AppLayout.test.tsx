import { screen } from "@testing-library/react";
import { Route, Routes } from "react-router";
import { renderWithProviders } from "@/test/renderWithProviders";
import { AppLayout } from "./AppLayout";

function renderLayout(route: string): void {
  renderWithProviders(
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="*" element={<p>content</p>} />
      </Route>
    </Routes>,
    { route },
  );
}

describe("AppLayout", () => {
  it("shows Dashboard, Datasets and API docs links", () => {
    renderLayout("/");

    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/");
    expect(screen.getByRole("link", { name: "Datasets" })).toHaveAttribute("href", "/datasets");
    const apiDocs = screen.getByRole("link", { name: /^API docs/ });
    expect(apiDocs).toHaveAttribute("href", "/api/v1/docs");
    expect(apiDocs).toHaveAttribute("target", "_blank");
  });

  it("announces that the API docs link opens in a new tab", () => {
    renderLayout("/");

    expect(screen.getByRole("link", { name: "API docs (opens in a new tab)" })).toBeInTheDocument();
  });

  it("marks the current page link as active", () => {
    renderLayout("/datasets");

    expect(screen.getByRole("link", { name: "Datasets" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Dashboard" })).not.toHaveAttribute("aria-current");
  });
});
