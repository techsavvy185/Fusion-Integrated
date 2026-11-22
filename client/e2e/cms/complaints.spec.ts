import {
  expect, openModuleNav, sidebar, signedInAs, test, uniqueName,
} from "../support/test";

test.describe("cms: student complaint submission and tracking", () => {
  test.use(signedInAs("student"));

  test("UC-CMS-001 & UC-CMS-002: a student submits a complaint and sees it listed", async ({ page }) => {
    const title = uniqueName("E2E Complaint");

    await page.goto("/");
    await openModuleNav(page, "Complaints");
    await sidebar(page).getByRole("link", { name: "Complaints" }).click();
    await expect(page.getByRole("heading", { name: "Complaints", level: 2 })).toBeVisible();

    await page.getByRole("button", { name: "Submit complaint" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Category").click();
    await page.getByRole("option").first().click();
    await dialog.getByLabel("Title").fill(title);
    await dialog.getByLabel("Description").fill("Automated E2E verification description.");

    const created = page.waitForResponse((r) =>
      r.url().includes("/api/v1/cms/complaints/") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Submit" }).click();
    expect((await created).status()).toBe(201);

    await expect(dialog).toBeHidden();
    await expect(page.getByText(title)).toBeVisible();
  });

  test("UC-CMS-014: a student opens announcements and sees no publish control", async ({ page }) => {
    await page.goto("/");
    await openModuleNav(page, "Complaints");
    await sidebar(page).getByRole("link", { name: "Announcements" }).click();
    await expect(page.getByRole("heading", { name: "CMS Announcements", level: 2 })).toBeVisible();
    await expect(page.getByRole("button", { name: "Publish announcement" })).toHaveCount(0);
  });
});
