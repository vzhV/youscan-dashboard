import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/test/renderWithProviders";
import { AppRoutes } from "./router";

describe("routes", () => {
  it("shows the not found page for unknown paths", async () => {
    renderWithProviders(<AppRoutes />, { route: "/nope" });

    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("shows the dashboard page on the root path", async () => {
    renderWithProviders(<AppRoutes />, { route: "/" });

    expect(await screen.findByRole("heading", { name: "Dashboard", level: 1 })).toBeInTheDocument();
  });

  it("shows the datasets page on /datasets", async () => {
    renderWithProviders(<AppRoutes />, { route: "/datasets" });

    expect(await screen.findByRole("heading", { name: "Datasets", level: 1 })).toBeInTheDocument();
  });
});
