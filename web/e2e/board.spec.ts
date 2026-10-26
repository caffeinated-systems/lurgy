import { expect, type Page, test } from "@playwright/test";

// The fixture Monday (api/tests/fixtures/puzzles), in a forced order from
// api/tests/test_monday_sample.py, after Jas (B3) who starts revealed.
const ORDER = "A3 A4 A5 D2 D1 D3 C3 C2 D4 D5 A1 A2 B2 B1 C1 C5 B5 C4 B4".split(
	" ",
);
const SICK = new Set("A1 C1 D1 A2 C2 A3 A5 D5".split(" "));

const tile = (page: Page, desk: string) =>
	page
		.getByRole("grid", { name: /office floor/i })
		.locator(`[data-desk="${desk}"]`);

/** Column and row of a desk, as numbers. */
const at = (desk: string) => [
	"ABCD".indexOf(desk.charAt(0)),
	Number(desk.slice(1)),
];

/** Arrow from the focused tile to `desk`. */
async function goTo(page: Page, desk: string) {
	const from =
		(await page.locator("[data-desk]:focus").getAttribute("data-desk")) ?? "";
	const [x0 = 0, y0 = 0] = at(from);
	const [x1 = 0, y1 = 0] = at(desk);
	const steps = [
		[x1 - x0, "ArrowRight", "ArrowLeft"],
		[y1 - y0, "ArrowDown", "ArrowUp"],
	] as const;
	for (const [delta, forward, back] of steps) {
		for (let i = 0; i < Math.abs(delta); i++) {
			await page.keyboard.press(delta > 0 ? forward : back);
		}
	}
	await expect(tile(page, desk)).toBeFocused();
}

test("solves the fixture day by keyboard and keeps it after a reload", async ({
	page,
}) => {
	await page.goto("/?day=2026-10-19");
	const status = page.getByRole("status");

	await expect(tile(page, "A1")).toBeVisible();
	await page.keyboard.press("Tab");
	await expect(tile(page, "A1")).toBeFocused();

	// A3 is sick, so calling them well is a mistake.
	await goTo(page, "A3");
	await page.keyboard.press("w");
	await expect(status).toHaveText("Not enough evidence.");
	await expect(tile(page, "A3")).toHaveAttribute(
		"aria-label",
		"A3, Imogen, IT, unknown, one mistake",
	);

	for (const desk of ORDER) {
		const state = SICK.has(desk) ? "sick" : "well";
		await goTo(page, desk);
		await page.keyboard.press(state === "sick" ? "s" : "w");
		await expect(status).toContainText(` is ${state}. `);
		await expect(tile(page, desk)).toHaveAttribute(
			"aria-label",
			new RegExp(`^${desk}, \\w+, \\w+, ${state}`),
		);
	}
	await expect(status).toContainText(/Office cleared in \d\d:\d\d\.$/);
	const time = (await page.getByRole("timer").textContent()) ?? "";

	await page.reload();

	await expect(page.getByRole("timer")).toHaveText(time);
	for (const desk of [...ORDER, "B3"]) {
		await expect(tile(page, desk)).toHaveAttribute(
			"aria-label",
			/, (sick|well)(, one mistake)?, says: /,
		);
	}
	await expect(tile(page, "A3")).toHaveAttribute("aria-label", /one mistake/);
});

test("a hint shows Jas's clue, then that it settles Imogen", async ({
	page,
}) => {
	await page.goto("/?day=2026-10-19");
	const status = page.getByRole("status");

	await page.getByRole("button", { name: "Hint" }).click();
	await expect(status).toContainText("Look at what Jas said.");
	await expect(tile(page, "B3")).toHaveAttribute("aria-label", /hinted clue/);
	await expect(tile(page, "A3")).toHaveAttribute("aria-label", /one hint/);

	await page.getByRole("button", { name: "Who do they settle?" }).click();
	await expect(status).toContainText("Those clues settle Imogen.");
	await expect(tile(page, "A3")).toHaveAttribute(
		"aria-label",
		/two hints, the hint is about them$/,
	);

	await page.getByRole("button", { name: "Declare Imogen sick" }).click();
	await expect(status).toContainText("Imogen is sick.");
	await expect(tile(page, "A3")).toHaveAttribute("aria-label", /two hints/);
	await expect(page.getByRole("button", { name: "Hint" })).toBeEnabled();
});
