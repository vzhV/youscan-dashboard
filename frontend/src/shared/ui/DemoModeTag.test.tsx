import { render, screen } from "@testing-library/react";
import type { DemoMode } from "@/shared/api/demoMode";
import { DemoModeTag } from "./DemoModeTag";

describe("DemoModeTag", () => {
  it("shows the active modes in a fixed order", () => {
    const modes = new Set<DemoMode>(["fail", "slow"]);

    render(<DemoModeTag modes={modes} />);

    expect(screen.getByText("Demo mode: slow, fail")).toBeInTheDocument();
  });

  it("shows a single active mode", () => {
    render(<DemoModeTag modes={new Set<DemoMode>(["fail"])} />);

    expect(screen.getByText("Demo mode: fail")).toBeInTheDocument();
  });

  it("renders nothing without modes", () => {
    const { container } = render(<DemoModeTag modes={new Set<DemoMode>()} />);

    expect(container).toBeEmptyDOMElement();
  });
});
