import type { Day, Desk } from "./game.ts";

// Test-only: a small day in the API's shape, desks A1–D5 with made-up names.
export const DESKS = Array.from(
	{ length: 20 },
	(_, i) => `${"ABCD"[i % 4]}${Math.floor(i / 4) + 1}` as Desk,
);

export const DAY: Day = {
	date: "2026-10-19",
	coworkers: DESKS.map((desk) => ({
		desk,
		name: `Name${desk}`,
		department: "HR",
	})),
	start: { desk: "A1", state: "well", kind: "clue", text: "Two in my row." },
};
