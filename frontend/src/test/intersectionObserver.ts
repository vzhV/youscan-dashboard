import { act } from "react";

export type IntersectionMode = "immediate" | "manual";

const observers = new Set<MockIntersectionObserver>();
let mode: IntersectionMode = "immediate";

function buildEntry(target: Element, isIntersecting: boolean): IntersectionObserverEntry {
  const rect = target.getBoundingClientRect();
  return {
    boundingClientRect: rect,
    intersectionRect: rect,
    intersectionRatio: isIntersecting ? 1 : 0,
    isIntersecting,
    rootBounds: null,
    target,
    time: 0,
  };
}

class MockIntersectionObserver implements IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "";
  readonly scrollMargin = "";
  readonly thresholds: readonly number[] = [];
  private readonly targets = new Set<Element>();
  private readonly callback: IntersectionObserverCallback;

  constructor(callback: IntersectionObserverCallback) {
    this.callback = callback;
    observers.add(this);
  }

  observe(target: Element): void {
    this.targets.add(target);
    if (mode === "immediate") this.notify(target, true);
  }

  unobserve(target: Element): void {
    this.targets.delete(target);
  }

  disconnect(): void {
    this.targets.clear();
    observers.delete(this);
  }

  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }

  notify(target: Element, isIntersecting: boolean): void {
    if (this.targets.has(target)) this.callback([buildEntry(target, isIntersecting)], this);
  }
}

export function installIntersectionObserver(): void {
  globalThis.IntersectionObserver = MockIntersectionObserver;
}

/** "immediate" reports every observed element as visible at once; "manual" waits for triggerIntersection. */
export function setIntersectionMode(nextMode: IntersectionMode): void {
  mode = nextMode;
}

export function triggerIntersection(target: Element, isIntersecting: boolean): void {
  // Like RTL's fireEvent, flush React updates caused by the callbacks so tests see the result.
  act(() => {
    observers.forEach((observer) => {
      observer.notify(target, isIntersecting);
    });
  });
}

export function resetIntersectionObserver(): void {
  mode = "immediate";
  observers.clear();
}
