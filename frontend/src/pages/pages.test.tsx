import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/test/renderWithProviders";
import { DashboardPage } from "./DashboardPage";
import { DatasetsPage } from "./DatasetsPage";
import { NotFoundPage } from "./NotFoundPage";

describe("page titles", () => {
  it.each([
    ["Dashboard", <DashboardPage key="d" />],
    ["Datasets", <DatasetsPage key="s" />],
    ["Page not found", <NotFoundPage key="n" />],
  ])("sets the document title for %s", (name, page) => {
    renderWithProviders(page);

    expect(document.title).toBe(`${name} · YouScan Dashboard`);
  });
});

describe("NotFoundPage", () => {
  it("offers a single link back to the dashboard", () => {
    renderWithProviders(<NotFoundPage />);

    expect(screen.getByRole("link", { name: "Back to dashboard" })).toHaveAttribute("href", "/");
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
