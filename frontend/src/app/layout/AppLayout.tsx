import { Layout } from "antd";
import { NavLink, Outlet, useLocation } from "react-router";
import styles from "./AppLayout.module.css";
import { RouteErrorBoundary } from "./RouteErrorBoundary";

const API_DOCS_PATH = "/api/v1/docs";

export function AppLayout() {
  const { pathname } = useLocation();

  return (
    <Layout className={styles.layout}>
      <Layout.Header className={styles.header}>
        <span className={styles.brand}>Dashboard</span>
        <nav aria-label="Main" className={styles.nav}>
          <NavLink to="/" end className={styles.link}>
            Dashboard
          </NavLink>
          <NavLink to="/datasets" className={styles.link}>
            Datasets
          </NavLink>
          <a href={API_DOCS_PATH} target="_blank" rel="noreferrer" className={styles.link}>
            API docs <span className={styles.visuallyHidden}>(opens in a new tab)</span>
          </a>
        </nav>
      </Layout.Header>
      <Layout.Content className={styles.content}>
        <RouteErrorBoundary key={pathname}>
          <Outlet />
        </RouteErrorBoundary>
      </Layout.Content>
    </Layout>
  );
}
