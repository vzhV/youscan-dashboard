import { render } from "@testing-library/react";
import { PageTitle } from "./PageTitle";

describe("PageTitle", () => {
  it("sets the document title with the app name suffix", () => {
    render(<PageTitle>Reports</PageTitle>);

    expect(document.title).toBe("Reports · YouScan Dashboard");
  });
});
