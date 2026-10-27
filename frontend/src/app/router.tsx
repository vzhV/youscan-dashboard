import { Spin } from "antd";
import { lazy, Suspense } from "react";
import { BrowserRouter, useRoutes, type RouteObject } from "react-router";
import { DashboardPage } from "@/pages/DashboardPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { AppLayout } from "./layout/AppLayout";

const DatasetsPage = lazy(() =>
  import("@/pages/DatasetsPage").then((module) => ({ default: module.DatasetsPage })),
);

export const routes: RouteObject[] = [
  {
    element: <AppLayout />,
    children: [
      { path: "/", element: <DashboardPage /> },
      {
        path: "/datasets",
        element: (
          <Suspense fallback={<Spin />}>
            <DatasetsPage />
          </Suspense>
        ),
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];

export function AppRoutes() {
  return useRoutes(routes);
}

export function AppRouter() {
  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  );
}
