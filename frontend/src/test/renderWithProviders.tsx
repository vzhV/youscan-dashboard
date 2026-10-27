import type { QueryClient } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router";
import { AppProviders, createQueryClient } from "@/app/providers";

type RenderOptions = { route?: string };
type RenderWithProvidersResult = RenderResult & { queryClient: QueryClient };

export function renderWithProviders(
  ui: ReactElement,
  { route = "/" }: RenderOptions = {},
): RenderWithProvidersResult {
  const queryClient = createQueryClient();
  const result = render(
    <AppProviders queryClient={queryClient}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </AppProviders>,
  );
  return { ...result, queryClient };
}
