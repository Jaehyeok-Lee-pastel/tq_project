import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("http://localhost:8000/**", async (route) => {
    const url = route.request().url();
    if (url.includes("/managed-strategies")) {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
      return;
    }
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "E2E offline fixture" }),
    });
  });
});

test("primary workflow pages remain reachable", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "TQ Coach" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /현재 포트폴리오/ })).toBeVisible();

  await page.getByRole("link", { name: "오늘 판단" }).click();
  await expect(page.getByRole("heading", { name: /채택한 전략을 계속 관리/ })).toBeVisible();

  await page.getByRole("link", { name: "개인연구" }).click();
  await expect(page.getByText("현재 보유와 적립 조건")).toBeVisible();

  await page.getByRole("link", { name: "추가정보" }).click();
  await expect(page.getByRole("heading", { name: /핵심 판단에 필요하지 않은 연구 정보/ })).toBeVisible();
});

test("layout has no horizontal overflow", async ({ page }) => {
  for (const path of ["/", "/manage", "/lab", "/info"]) {
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow, `${path} horizontal overflow`).toBeLessThanOrEqual(1);
  }
});
