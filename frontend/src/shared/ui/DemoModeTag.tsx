import { Tag } from "antd";
import { DEMO_MODES, type DemoMode } from "@/shared/api/demoMode";

type DemoModeTagProps = { modes: ReadonlySet<DemoMode> };

export function DemoModeTag({ modes }: DemoModeTagProps) {
  const activeModes = DEMO_MODES.filter((mode) => modes.has(mode));
  if (activeModes.length === 0) return null;

  return <Tag color="warning">Demo mode: {activeModes.join(", ")}</Tag>;
}
