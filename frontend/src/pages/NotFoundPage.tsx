import { Result, Typography } from "antd";
import { Link } from "react-router";
import { PageTitle } from "@/shared/ui/PageTitle";
import styles from "./NotFoundPage.module.css";

export function NotFoundPage() {
  return (
    <>
      <PageTitle>Page not found</PageTitle>
      <Result
        status="404"
        title={<Typography.Title level={1}>Page not found</Typography.Title>}
        subTitle="The page you are looking for does not exist."
        extra={
          <Link to="/" className={styles.homeLink}>
            Back to dashboard
          </Link>
        }
      />
    </>
  );
}
