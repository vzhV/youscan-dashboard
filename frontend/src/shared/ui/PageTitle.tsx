const APP_NAME = "YouScan Dashboard";

type PageTitleProps = { children: string };

// React 19 hoists a <title> rendered anywhere in the tree into the document head.
export function PageTitle({ children }: PageTitleProps) {
  return <title>{`${children} · ${APP_NAME}`}</title>;
}
