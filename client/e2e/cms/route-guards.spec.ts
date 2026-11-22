import { expect, signedInAs, test } from "../support/test";

// Guarded CMS pages opened directly by a student without those permissions.
const RESTRICTED_PAGES = ["escalations", "reopen-requests", "feedback", "reports", "policy"];

test.describe("cms: guarded routes", () => {
  test.use(signedInAs("student"));

  for (const path of RESTRICTED_PAGES) {
    test(`a student who opens /cms/${path} is told it is not for them`, async ({ page }) => {
      await page.goto(`/cms/${path}`);
      await expect(page.getByText("Not available to your role")).toBeVisible();
      await expect(page.getByRole("main").getByRole("button")).toHaveCount(0);
    });
  }
});
