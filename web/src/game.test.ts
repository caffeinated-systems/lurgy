import { beforeEach, expect, test, vi } from "vitest";
import { DAY, DESKS } from "./fixture.ts";
import {
	declared,
	elapsed,
	formatTime,
	HINT_TAUNTS,
	load,
	pick,
	REMARKS,
	reducer,
	save,
	start,
} from "./game.ts";

beforeEach(() => localStorage.clear());

const reveal = (desk: (typeof DESKS)[number]) =>
	({ desk, state: "sick", kind: "clue", text: "Hi." }) as const;

test("a new day starts with the starting coworker and selects the first hidden desk", () => {
	const game = start(DAY, 1000);

	expect(game.progress).toEqual({
		reveals: [DAY.start],
		masks: [],
		hints: {},
		startedAt: 1000,
	});
	expect(game.selected).toBe("B1");
});

test("a saved day resumes where it left off", () => {
	const progress = {
		reveals: [DAY.start, reveal("B1")],
		masks: ["C1" as const],
		hints: {},
		startedAt: 5,
	};
	save(DAY.date, progress);

	const game = start(DAY, 1000);

	expect(game.progress).toEqual(progress);
	expect(game.selected).toBe("C1");
});

test("a solved day resumes with the starting coworker selected", () => {
	save(DAY.date, {
		reveals: [DAY.start, ...DESKS.slice(1).map(reveal)],
		masks: [],
		hints: {},
		startedAt: 0,
		solvedAt: 9,
	});

	expect(start(DAY, 1000).selected).toBe("A1");
});

test("broken or foreign storage starts the day afresh", () => {
	localStorage.setItem("office-bug:2026-10-19", "{not json");
	expect(load(DAY)).toBeUndefined();

	for (const saved of [
		{ reveals: 3 },
		{ reveals: [], masks: [], startedAt: 0 },
		{ reveals: [DAY.start], masks: 3, startedAt: 0 },
		{ reveals: [DAY.start], masks: [] },
		{ reveals: [DAY.start], masks: [], startedAt: 0, hints: "oops" },
		{ reveals: [DAY.start], masks: [], startedAt: 0, hints: [] },
	]) {
		localStorage.setItem("office-bug:2026-10-19", JSON.stringify(saved));
		expect(load(DAY)).toBeUndefined();
	}
});

test("a day saved before hints existed loads with none taken", () => {
	const saved = { reveals: [DAY.start], masks: [], startedAt: 0 };
	for (const hints of [undefined, null]) {
		localStorage.setItem(
			"office-bug:2026-10-19",
			JSON.stringify({ ...saved, hints }),
		);
		expect(load(DAY)).toEqual({ ...saved, hints: {} });
	}
});

const HINT = { clues: ["A1" as const, "C2" as const], coworker: "B3" as const };

test("a first hint points at its clues and marks its coworker once", () => {
	const game = reducer(
		{ ...start(DAY, 0), pending: true },
		{ type: "hinted", hint: HINT },
	);

	expect(game.hint).toEqual({ ...HINT, presses: 1 });
	expect(game.progress.hints).toEqual({ B3: 1 });
	expect(game.pending).toBe(false);
	expect(HINT_TAUNTS.some((t) => game.message.startsWith(t))).toBe(true);
	expect(game.message).toMatch(/Look at what NameA1 and NameC2 said\.$/);
	expect(game.selected).toBe("B1");
});

test("a second press names and selects the coworker, and marks them twice", () => {
	const first = reducer(start(DAY, 0), { type: "hinted", hint: HINT });

	const game = reducer(first, { type: "hinted-again" });

	expect(game.hint?.presses).toBe(2);
	expect(game.progress.hints).toEqual({ B3: 2 });
	expect(game.selected).toBe("B3");
	expect(game.message).toMatch(/Those clues settle NameB3\.$/);
});

test("a second press with no open hint does nothing", () => {
	const game = start(DAY, 0);

	expect(reducer(game, { type: "hinted-again" })).toBe(game);
});

test("asking again keeps the strongest mark", () => {
	const twice = reducer(
		reducer(start(DAY, 0), { type: "hinted", hint: HINT }),
		{
			type: "hinted-again",
		},
	);

	const again = reducer(twice, { type: "hinted", hint: HINT });

	expect(again.progress.hints).toEqual({ B3: 2 });
});

test("the hint closes when its coworker is declared, and not before", () => {
	const hinted = reducer(start(DAY, 0), { type: "hinted", hint: HINT });

	const other = reducer(hinted, {
		type: "accepted",
		reveal: reveal("D1"),
		at: 1,
	});
	expect(other.hint).toEqual(hinted.hint);
	const done = reducer(other, {
		type: "accepted",
		reveal: reveal("B3"),
		at: 2,
	});
	expect(done.hint).toBeUndefined();
	expect(done.progress.hints).toEqual({ B3: 1 });
});

test("a taunt depends only on the game state, so a reload shows the same one", () => {
	const lines = ["a", "b", "c", "d", "e", "f", "g", "h"];
	// Pinned: changing the hash would change every saved game's taunts.
	expect(pick(lines, "2026-10-19", 1, 1)).toBe("b");
	expect(pick(lines, "2026-10-19", 1, 2)).toBe("c");
	expect(pick(lines, "2026-10-20", 1, 1)).toBe("h");
	expect(pick([], "x")).toBe("");
});

test("blocked storage neither loads nor throws", () => {
	vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
		throw new Error("blocked");
	});
	vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
		throw new Error("blocked");
	});

	expect(load(DAY)).toBeUndefined();
	expect(() => save(DAY.date, start(DAY, 0).progress)).not.toThrow();
	vi.restoreAllMocks();
});

test("declared leaves out the starting coworker", () => {
	const game = reducer(start(DAY, 0), {
		type: "accepted",
		reveal: reveal("B1"),
		at: 1,
	});

	expect(declared(game.progress)).toEqual([{ desk: "B1", state: "sick" }]);
});

test("an accepted declaration reveals the coworker and says so", () => {
	const game = reducer(start(DAY, 0), {
		type: "accepted",
		reveal: reveal("B1"),
		at: 1,
	});

	expect(game.message).toBe("NameB1 is sick. NameB1 says: Hi.");
	expect(game.said).toBe(1);
	expect(game.progress.solvedAt).toBeUndefined();
});

test("the last reveal solves the day and stops the timer", () => {
	let game = start(DAY, 0);
	for (const desk of DESKS.slice(1)) {
		game = reducer(game, {
			type: "accepted",
			reveal: reveal(desk),
			at: 83_000,
		});
	}

	expect(game.progress.solvedAt).toBe(83_000);
	expect(elapsed(game.progress, 999_999)).toBe(83_000);
	expect(game.message).toBe(
		"NameD5 is sick. NameD5 says: Hi. Office cleared in 01:23.",
	);
});

test("a rejection masks the coworker once and they answer back", () => {
	let game = reducer(start(DAY, 0), {
		type: "rejected",
		desk: "B1",
		state: "well",
	});
	game = reducer(game, { type: "rejected", desk: "B1", state: "well" });

	expect(game.progress.masks).toEqual(["B1"]);
	expect(game.message).toBe(
		`Not enough evidence. NameB1 says: “${pick(REMARKS, DAY.date, "B1", "well", 1)}”`,
	);
	expect(game.said).toBe(2);
});

test("a remark depends only on what the player did, so it can't tell wrong from unforced", () => {
	const remark = (desk: "B1" | "C1", state: "sick" | "well") =>
		reducer(start(DAY, 0), { type: "rejected", desk, state }).message;

	// The same declaration at the same point always gets the same remark, and the
	// action carries nothing about whether it was wrong.
	expect(remark("B1", "sick")).toBe(remark("B1", "sick"));
	const said = new Set(
		(["B1", "C1"] as const).flatMap((d) =>
			(["sick", "well"] as const).map((s) => remark(d, s)),
		),
	);
	expect(said.size).toBeGreaterThan(1);
	for (const message of said) {
		expect(REMARKS.some((r) => message.endsWith(`“${r}”`))).toBe(true);
	}
});

test("a network failure says so without a mask", () => {
	const game = reducer(start(DAY, 0), { type: "failed" });

	expect(game.progress.masks).toEqual([]);
	expect(game.message).toBe("Couldn't reach the office, try again.");
});

test("a declaration is pending until its answer", () => {
	const sent = reducer(start(DAY, 0), { type: "sent" });
	expect(sent.pending).toBe(true);

	for (const action of [
		{ type: "accepted", reveal: reveal("B1"), at: 1 },
		{ type: "rejected", desk: "B1", state: "well" },
		{ type: "failed" },
	] as const) {
		expect(reducer(sent, action).pending).toBe(false);
	}
});

test("declaring a revealed coworker says so", () => {
	expect(reducer(start(DAY, 0), { type: "already" }).message).toBe(
		"Already declared.",
	);
});

test("selecting moves the selection", () => {
	expect(
		reducer(start(DAY, 0), { type: "selected", desk: "D5" }).selected,
	).toBe("D5");
});

test("times are always mm:ss", () => {
	expect(formatTime(0)).toBe("00:00");
	expect(formatTime(-5)).toBe("00:00");
	expect(formatTime(283_999)).toBe("04:43");
	expect(formatTime(6_000_000)).toBe("100:00");
});
