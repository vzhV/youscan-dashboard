import { render, screen } from "@testing-library/react";
import { useEffect, useRef, useState } from "react";
import { setIntersectionMode, triggerIntersection } from "./intersectionObserver";

function observe(target: Element) {
  const callback = vi.fn<IntersectionObserverCallback>();
  new IntersectionObserver(callback).observe(target);
  return callback;
}

describe("intersection observer stub", () => {
  it("reports observed elements as intersecting immediately by default", () => {
    const target = document.createElement("div");

    const callback = observe(target);

    expect(callback).toHaveBeenCalledOnce();
  });

  it("waits for triggerIntersection in manual mode, so enter and leave can be tested", () => {
    setIntersectionMode("manual");
    const target = document.createElement("div");
    const callback = observe(target);
    expect(callback).not.toHaveBeenCalled();

    triggerIntersection(target, true);
    triggerIntersection(target, false);

    const reported = callback.mock.calls.map(([entries]) => entries[0]?.isIntersecting);
    expect(reported).toEqual([true, false]);
  });
});

function VisibilityProbe() {
  const [isVisible, setIsVisible] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const observer = new IntersectionObserver(([entry]) => {
      setIsVisible(entry?.isIntersecting ?? false);
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, []);
  return <div ref={ref}>{isVisible ? "visible" : "hidden"}</div>;
}

describe("triggerIntersection", () => {
  it("updates rendered output without an act warning", () => {
    setIntersectionMode("manual");
    render(<VisibilityProbe />);
    expect(screen.getByText("hidden")).toBeInTheDocument();

    triggerIntersection(screen.getByText("hidden"), true);

    expect(screen.getByText("visible")).toBeInTheDocument();
  });
});
