import { expect, test } from "@playwright/test";

test("the built app talks to the API", async ({ page }) => {
	await page.goto("/");

	await expect(page.getByRole("heading")).toHaveText("Office bug: ok");
});
