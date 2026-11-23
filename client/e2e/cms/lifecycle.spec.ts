import {
  actAs, expect, openModuleNav, sidebar, signedInAs, test, uniqueName,
} from "../support/test";

test.describe("cms: full lifecycle browser walkthrough", () => {
  test.use(signedInAs("student"));

  test("UC-CMS-001 keyboard-only: submit complaint using Tab and Enter", async ({ page }) => {
    const title = uniqueName("E2E Keyboard Complaint");
    await page.goto("/");
    await openModuleNav(page, "Complaints");
    await sidebar(page).getByRole("link", { name: "Complaints" }).click();

    await page.getByRole("button", { name: "Submit complaint" }).focus();
    await page.keyboard.press("Enter");
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();

    await dialog.getByRole("textbox", { name: "Category" }).click();
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");
    await dialog.getByLabel("Title").focus();
    await page.keyboard.type(title);
    await page.keyboard.press("Tab");
    await page.keyboard.type("Submitted using keyboard navigation.");

    const created = page.waitForResponse((r) =>
      r.url().includes("/api/v1/cms/complaints/") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Submit" }).focus();
    await page.keyboard.press("Enter");
    expect((await created).status()).toBe(201);
    await expect(page.getByText(title)).toBeVisible();
  });
});

test.describe("cms: handler worklist, setup, progress, resolve, feedback review", () => {
  test.use(signedInAs("cmsHandler"));

  test("UC-CMS-003, UC-CMS-004, UC-CMS-005, UC-CMS-006 & UC-CMS-010: handler handles a complaint and reviews feedback", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "cmsHandler");
    await openModuleNav(page, "Complaints");
    await sidebar(page).getByRole("link", { name: "Complaints" }).click();
    await expect(page.getByRole("heading", { name: "Complaints", level: 2 })).toBeVisible();

    // Open the first complaint's detail drawer and verify handler controls appear.
    await page.getByRole("button", { name: "View details" }).first().click();
    await expect(page.getByText("Handling setup", { exact: true })).toBeVisible();
    await page.getByLabel("Assigned unit").fill("Network Operations");

    const setupResp = page.waitForResponse((r) =>
      r.url().includes("/handling-setup/") && r.request().method() === "POST");
    await page.getByRole("button", { name: "Save handling setup" }).click();
    expect((await setupResp).status()).toBe(200);

    await page.getByLabel("Progress note").fill("Investigating in E2E run.");
    const progResp = page.waitForResponse((r) =>
      r.url().includes("/progress/") && r.request().method() === "POST");
    await page.getByRole("button", { name: "Add progress update" }).click();
    expect((await progResp).status()).toBe(200);

    await page.getByLabel("Resolution details").fill("Resolved in E2E run.");
    const resResp = page.waitForResponse((r) =>
      r.url().includes("/resolve/") && r.request().method() === "POST");
    await page.getByRole("button", { name: "Resolve complaint" }).click();
    expect((await resResp).status()).toBe(200);

    await page.keyboard.press("Escape");
    await sidebar(page).getByRole("link", { name: "Feedback" }).click();
    await expect(page.getByRole("heading", { name: "Submitted Feedback", level: 2 })).toBeVisible();
  });
});
