import {
  actAs, expect, openModuleNav, sidebar, signedInAs, test, uniqueName,
} from "../support/test";

test.describe("cms: handler announcements and operational reports", () => {
  test.use(signedInAs("cmsHandler"));

  test("UC-CMS-013 & UC-CMS-015: handler publishes an announcement and views operational report", async ({ page }) => {
    const noticeTitle = uniqueName("E2E Notice");

    await page.goto("/");
    await actAs(page, "cmsHandler");
    await openModuleNav(page, "Complaints");
    await sidebar(page).getByRole("link", { name: "Announcements" }).click();
    await page.getByRole("button", { name: "Publish announcement" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Title").fill(noticeTitle);
    await dialog.getByLabel("Body").fill("Scheduled maintenance notice.");

    const created = page.waitForResponse((r) =>
      r.url().includes("/api/v1/cms/announcements/") && r.request().method() === "POST");
    await dialog.getByRole("button", { name: "Publish" }).click();
    expect((await created).status()).toBe(201);
    await expect(page.getByText(noticeTitle)).toBeVisible();

    await sidebar(page).getByRole("link", { name: "Reports & Analytics" }).click();
    await expect(page.getByText("Operational Report")).toBeVisible();
  });
});

test.describe("cms: supervisor escalations and reopen requests", () => {
  test.use(signedInAs("cmsSupervisor"));

  test("UC-CMS-012, UC-CMS-016 & UC-CMS-020: supervisor opens escalations, reopen requests, and escalation summary", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "cmsSupervisor");
    await openModuleNav(page, "Complaints");
    await sidebar(page).getByRole("link", { name: "Escalations" }).click();
    await expect(page.getByRole("heading", { name: "Escalated Complaints", level: 2 })).toBeVisible();

    await sidebar(page).getByRole("link", { name: "Reopen Requests" }).click();
    await expect(page.getByRole("heading", { name: "Reopen Requests", level: 2 })).toBeVisible();

    await sidebar(page).getByRole("link", { name: "Reports & Analytics" }).click();
    await expect(page.getByText("Escalation Summary")).toBeVisible();
  });
});

test.describe("cms: system admin analytics and policy", () => {
  test.use(signedInAs("cmsAdmin"));

  test("UC-CMS-017: system admin views analytics and CMS policy", async ({ page }) => {
    await page.goto("/");
    await actAs(page, "cmsAdmin");
    await openModuleNav(page, "Complaints");
    await sidebar(page).getByRole("link", { name: "Reports & Analytics" }).click();
    await expect(page.getByText("CMS Analytics")).toBeVisible();

    await sidebar(page).getByRole("link", { name: "CMS Policy" }).click();
    await expect(page.getByRole("heading", { name: "CMS Policy & Categories", level: 2 })).toBeVisible();
  });
});
