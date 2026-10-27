import { Button, Result } from "antd";
import { Component, type ReactNode } from "react";

type RouteErrorBoundaryProps = { children: ReactNode };
type RouteErrorBoundaryState = { hasError: boolean };

// Class component: React error boundaries have no hook equivalent.
export class RouteErrorBoundary extends Component<
  RouteErrorBoundaryProps,
  RouteErrorBoundaryState
> {
  override state: RouteErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): RouteErrorBoundaryState {
    return { hasError: true };
  }

  override render(): ReactNode {
    if (!this.state.hasError) return this.props.children;
    return (
      <Result
        status="error"
        title="Something went wrong"
        subTitle="The page failed to load. Reloading usually fixes it."
        extra={
          <Button
            type="primary"
            onClick={() => {
              window.location.reload();
            }}
          >
            Reload
          </Button>
        }
      />
    );
  }
}
