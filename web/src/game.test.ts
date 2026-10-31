import { beforeEach, expect, test, vi } from "vitest";
import { Busy } from "./api.ts";
import { DAY, DESKS } from "./fixture.ts";
import {
	COMPLAINTS,
	type Desk,
	declared,
	elapsed,
	formatTime,
	HINT_TAUNTS,
	load,
	type Progress,
	pick,
	REMARKS,
	reducer,
	result,
	save,
	solved,
	square,
	start,
	suspect,
	VERDICTS,
	verdict,
} from "./game.ts";

beforeEach(() => localStorage.clear());

const reveal = (desk: (typeof DESKS)[number]) =>
	({ desk, state: "sick", kind: "clue", text: "Hi." }) as const;

test("a new day starts with the starting coworker and selects the first hidden desk", () => {
	const game = start(DAY);

	expect(game.progress).toEqual({
		reveals: [DAY.start],
		masks: [],
		hints: {},
		dimmed: [],
		complaints: [],
	});
	expect(game.selected).toBe("B1");
});

test("the clock waits for the first declaration or hint, then keeps its start", () => {
	const fresh = start(DAY);
	expect(elapsed(fresh.progress, 5_000)).toBe(0);
	// A reload before the first move still waits.
	save(DAY.date, fresh.progress);
	expect(load(DAY)).toEqual(fresh.progress);

	const first = reducer(fresh, { type: "sent", at: 7_000 });
	expect(first.progress.startedAt).toBe(7_000);
	expect(elapsed(first.progress, 9_000)).toBe(2_000);

	const second = reducer(first, { type: "sent", at: 8_000 });
	expect(second.progress.startedAt).toBe(7_000);
});

test("a saved day resumes where it left off", () => {
	const progress = {
		reveals: [DAY.start, reveal("B1")],
		masks: ["C1" as const],
		hints: {},
		dimmed: ["A1" as const],
		complaints: [],
		startedAt: 5,
	};
	save(DAY.date, progress);

	const game = start(DAY);

	expect(game.progress).toEqual(progress);
	expect(game.selected).toBe("C1");
});

test("a solved day resumes with the starting coworker selected", () => {
	save(DAY.date, {
		reveals: [DAY.start, ...DESKS.slice(1).map(reveal)],
		masks: [],
		hints: {},
		dimmed: [],
		complaints: [],
		startedAt: 0,
		solvedAt: 9,
	});

	expect(start(DAY).selected).toBe("A1");
});

test("broken or foreign storage starts the day afresh", () => {
	localStorage.setItem("office-bug:2026-10-19", "{not json");
	expect(load(DAY)).toBeUndefined();

	for (const saved of [
		{ reveals: 3 },
		{ reveals: [], masks: [], startedAt: 0 },
		{ reveals: [DAY.start], masks: 3, startedAt: 0 },
		{ reveals: [DAY.start], masks: [], startedAt: "oops" },
		{ reveals: [DAY.start], masks: [], startedAt: 0, hints: "oops" },
		{ reveals: [DAY.start], masks: [], startedAt: 0, hints: [] },
		{ reveals: [DAY.start], masks: [], startedAt: 0, dimmed: "oops" },
		{ reveals: [DAY.start], masks: [], startedAt: 0, complaints: "oops" },
	]) {
		localStorage.setItem("office-bug:2026-10-19", JSON.stringify(saved));
		expect(load(DAY)).toBeUndefined();
	}
});

test("a day saved before hints, dimming or complaints existed loads with none", () => {
	const saved = { reveals: [DAY.start], masks: [], startedAt: 0 };
	for (const missing of [undefined, null]) {
		localStorage.setItem(
			"office-bug:2026-10-19",
			JSON.stringify({
				...saved,
				hints: missing,
				dimmed: missing,
				complaints: missing,
			}),
		);
		expect(load(DAY)).toEqual({
			...saved,
			hints: {},
			dimmed: [],
			complaints: [],
		});
	}
});

test("reading a clue toggles it, and reading another moves on", () => {
	const game = start(DAY);

	const read = reducer(game, { type: "read", desk: "A1" });
	expect(read.reading).toBe("A1");
	expect(reducer(read, { type: "read", desk: "B1" }).reading).toBe("B1");
	expect(reducer(read, { type: "read", desk: "A1" }).reading).toBeUndefined();
});

test("dimming a clue toggles it in the saved progress", () => {
	const game = start(DAY);

	const dimmed = reducer(game, { type: "dimmed", desk: "A1" });
	expect(dimmed.progress.dimmed).toEqual(["A1"]);
	expect(
		reducer(dimmed, { type: "dimmed", desk: "A1" }).progress.dimmed,
	).toEqual([]);
});

const HINT = {
	clues: ["A1" as const, "C2" as const],
	coworker: "B3" as const,
	explanations: [],
};

test("a first hint points at its clues and marks its coworker once", () => {
	const game = reducer(
		{ ...start(DAY), pending: true },
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
	const first = reducer(start(DAY), { type: "hinted", hint: HINT });

	const game = reducer(first, { type: "hinted-again" });

	expect(game.hint?.presses).toBe(2);
	expect(game.progress.hints).toEqual({ B3: 2 });
	expect(game.selected).toBe("B3");
	expect(game.message).toMatch(/Those clues settle NameB3\.$/);
});

test("a second press with no open hint does nothing", () => {
	const game = start(DAY);

	expect(reducer(game, { type: "hinted-again" })).toBe(game);
});

test("asking again keeps the strongest mark", () => {
	const twice = reducer(reducer(start(DAY), { type: "hinted", hint: HINT }), {
		type: "hinted-again",
	});

	const again = reducer(twice, { type: "hinted", hint: HINT });

	expect(again.progress.hints).toEqual({ B3: 2 });
});

test("the hint closes when its coworker is declared, and not before", () => {
	const hinted = reducer(start(DAY), { type: "hinted", hint: HINT });

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
	expect(() => save(DAY.date, start(DAY).progress)).not.toThrow();
	vi.restoreAllMocks();
});

test("declared leaves out the starting coworker", () => {
	const game = reducer(start(DAY), {
		type: "accepted",
		reveal: reveal("B1"),
		at: 1,
	});

	expect(declared(game.progress)).toEqual([{ desk: "B1", state: "sick" }]);
});

test("an accepted declaration reveals the coworker and says so", () => {
	const game = reducer(start(DAY), {
		type: "accepted",
		reveal: reveal("B1"),
		at: 1,
	});

	expect(game.message).toBe("NameB1 is sick. NameB1 says: Hi.");
	expect(game.said).toBe(1);
	expect(game.progress.solvedAt).toBeUndefined();
});

test("the last reveal solves the day and stops the timer", () => {
	let game = reducer(start(DAY), { type: "sent", at: 0 });
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
		`NameD5 is sick. NameD5 says: Hi. ${verdict(game.progress, DAY.date)} Office cleared in 01:23.`,
	);
});

test("a rejection masks the coworker once and they answer back", () => {
	const remark = (said: number) =>
		`Not enough evidence. NameB1 says: “${pick(REMARKS, DAY.date, "B1", "well", said)}”`;
	let game = reducer(start(DAY), {
		type: "rejected",
		desk: "B1",
		state: "well",
	});
	expect(game.message).toBe(remark(0));
	// Trying again gets a new remark, but still one mask.
	game = reducer(game, { type: "rejected", desk: "B1", state: "well" });

	expect(game.progress.masks).toEqual(["B1"]);
	expect(game.message).toBe(remark(1));
	expect(game.said).toBe(2);
});

test("a remark depends only on what the player did, so it can't tell wrong from unforced", () => {
	const remark = (desk: "B1" | "C1", state: "sick" | "well") =>
		reducer(start(DAY), { type: "rejected", desk, state }).message;

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
	const game = reducer(start(DAY), {
		type: "failed",
		error: new Error("down"),
	});

	expect(game.progress.masks).toEqual([]);
	expect(game.message).toBe("Couldn't reach the office, try again.");
});

test("over the API's limit, the office asks the player to wait as long as it said", () => {
	const told = (seconds: number) =>
		reducer(start(DAY), { type: "failed", error: new Busy(seconds) }).message;

	expect(told(20)).toBe(
		"Steady on, the whole office is asking at once. Try again in 20 seconds.",
	);
	expect(told(1)).toMatch(/Try again in 1 second\.$/);
});

test("a declaration is pending until its answer", () => {
	const sent = reducer(start(DAY), { type: "sent", at: 0 });
	expect(sent.pending).toBe(true);

	for (const action of [
		{ type: "accepted", reveal: reveal("B1"), at: 1 },
		{ type: "rejected", desk: "B1", state: "well" },
		{ type: "failed", error: new Error("down") },
	] as const) {
		expect(reducer(sent, action).pending).toBe(false);
	}
});

test("declaring a revealed coworker says so", () => {
	expect(reducer(start(DAY), { type: "already" }).message).toBe(
		"Already declared.",
	);
});

test("selecting moves the selection", () => {
	expect(reducer(start(DAY), { type: "selected", desk: "D5" }).selected).toBe(
		"D5",
	);
});

test("times are always mm:ss", () => {
	expect(formatTime(0)).toBe("00:00");
	expect(formatTime(-5)).toBe("00:00");
	expect(formatTime(283_999)).toBe("04:43");
	expect(formatTime(6_000_000)).toBe("100:00");
});

const progress = (masks: Desk[], hints: Progress["hints"] = {}): Progress => ({
	reveals: DESKS.map(reveal),
	masks,
	hints,
	dimmed: [],
	complaints: [],
	startedAt: 1_000,
	solvedAt: 284_000,
});

test("the verdict goes by how many coworkers are marked: none, 1 to 3, 4 or more", () => {
	const tier = (p: Progress) =>
		VERDICTS.findIndex((lines) =>
			(lines as readonly string[]).includes(verdict(p, DAY.date)),
		);

	expect(tier(progress([]))).toBe(0);
	// A coworker with a mask and a hint counts once.
	expect(tier(progress(["A1", "B1", "C1"], { A1: 2 }))).toBe(1);
	expect(tier(progress(["A1", "B1", "C1"], { D1: 1 }))).toBe(2);
	expect(verdict(progress([]), DAY.date)).toBe(verdict(progress([]), DAY.date));
});

test("a square shows the strongest mark: 🟠 over 🟡 over 😷 over 🟩", () => {
	const p = progress(["A1", "B1", "C1"], { A1: 2, B1: 1 });

	expect(["A1", "B1", "C1", "D1"].map((d) => square(p, d as Desk))).toEqual([
		"🟠",
		"🟡",
		"😷",
		"🟩",
	]);
});

test("the result has the day, difficulty, time, verdict, grid and link", () => {
	const p = progress(["B1", "D5"], { A2: 1, C3: 2 });

	expect(result(DAY, p, "https://lurgy.app")).toBe(
		[
			"Office Lurgy · Mon 19 Oct (Medium) · ⏱ 04:43",
			`"${verdict(p, DAY.date)}"`,
			"🟩😷🟩🟩",
			"🟡🟩🟩🟩",
			"🟩🟩🟠🟩",
			"🟩🟩🟩🟩",
			"🟩🟩🟩😷",
			"https://lurgy.app",
		].join("\n"),
	);
});

test("a day built before grading leaves the difficulty out", () => {
	const text = result({ ...DAY, difficulty: null }, progress([]), "https://x");

	expect(text.split("\n")[0]).toBe("Office Lurgy · Mon 19 Oct · ⏱ 04:43");
});

// The fixture day as Overtime.
const OVERTIME = { ...DAY, overtime: true };
const flavour = (desk: Desk) =>
	({ desk, state: "sick", kind: "flavour", text: "Hm." }) as const;
const well = (desk: Desk) =>
	({ desk, state: "well", kind: "clue", text: "Hi." }) as const;

test("calling BS goes in the declarations where it was made", () => {
	const p: Progress = {
		...start(OVERTIME).progress,
		reveals: [DAY.start, reveal("B1"), reveal("C1")],
		caught: { desk: "B1", after: 1 },
	};

	expect(declared(p)).toEqual([
		{ desk: "B1", state: "sick" },
		{ desk: "B1", state: "fibber" },
		{ desk: "C1", state: "sick" },
	]);
});

test("BS can be called only on a revealed sick coworker with a clue, on Overtime, until caught", () => {
	const p: Progress = {
		...start(OVERTIME).progress,
		reveals: [DAY.start, reveal("B1"), well("C1"), flavour("D1")],
	};

	expect(suspect(OVERTIME, p, "B1")).toBe(true);
	expect(suspect(DAY, p, "B1")).toBe(false); // a weekday
	expect(suspect(OVERTIME, p, "C1")).toBe(false); // well
	expect(suspect(OVERTIME, p, "D1")).toBe(false); // no clue
	expect(suspect(OVERTIME, p, "A2")).toBe(false); // not revealed
	const caught = { ...p, caught: { desk: "B1" as Desk, after: 1 } };
	expect(suspect(OVERTIME, caught, "B1")).toBe(false);
});

test("Overtime is solved once everyone is declared and BS is called", () => {
	const everyone = { ...start(OVERTIME).progress, reveals: DESKS.map(reveal) };

	expect(solved(DAY, everyone)).toBe(true);
	expect(solved(OVERTIME, everyone)).toBe(false);
	expect(
		solved(OVERTIME, { ...everyone, caught: { desk: "B1", after: 3 } }),
	).toBe(true);
});

test("calling BS on the fibber says so, closes a hint on them, and can solve the day", () => {
	let game = reducer(start(OVERTIME), { type: "sent", at: 0 });
	for (const desk of DESKS.slice(1)) {
		game = reducer(game, { type: "accepted", reveal: reveal(desk), at: 1 });
	}
	expect(game.progress.solvedAt).toBeUndefined();
	game = {
		...game,
		hint: { clues: ["B1"], coworker: "B1", explanations: [], presses: 2 },
	};

	game = reducer(game, { type: "caught", desk: "B1", at: 83_000 });

	expect(game.progress.caught).toEqual({ desk: "B1", after: 19 });
	expect(game.hint).toBeUndefined();
	expect(game.progress.solvedAt).toBe(83_000);
	expect(game.message).toBe(
		`BS called! NameB1 was the fibber: their clue was a lie. ${verdict(game.progress, DAY.date)} Office cleared in 01:23.`,
	);
});

test("a rejected BS call makes one complaint, which counts toward the verdict", () => {
	let game = reducer(start(OVERTIME), { type: "complained", desk: "B1" });
	expect(game.message).toBe(
		`Not enough evidence. NameB1 says: “${pick(COMPLAINTS, DAY.date, "B1", 0)}”`,
	);
	game = reducer(game, { type: "complained", desk: "B1" });

	expect(game.progress.complaints).toEqual(["B1"]);
	expect(game.progress.masks).toEqual([]);
	// One coworker marked: the middle tier.
	expect(VERDICTS[1] as readonly string[]).toContain(
		verdict(game.progress, DAY.date),
	);
});

test("an Overtime result says so, and sums up the fibber without any position", () => {
	const p = { ...progress([]), complaints: ["B1", "C2"] as Desk[] };
	const lines = result(OVERTIME, p, "https://lurgy.app").split("\n");

	expect(lines[0]).toBe(
		"Office Lurgy · Overtime · Mon 19 Oct (Medium) · ⏱ 04:43",
	);
	expect(lines.slice(2, 7)).toEqual(Array(5).fill("🟩🟩🟩🟩"));
	expect(lines[7]).toBe("🤥 Fibber caught · 💢 2 complaints");
	const one = result(OVERTIME, { ...p, complaints: ["B1"] }, "x").split("\n");
	expect(one[7]).toBe("🤥 Fibber caught · 💢 1 complaint");
});

test("a hint toward calling BS stays off the fibber's tile and square, but still counts", () => {
	let game = reducer(start(OVERTIME), {
		type: "accepted",
		reveal: reveal("B1"),
		at: 1,
	});
	const toBS = {
		clues: ["A1" as Desk],
		coworker: "B1" as Desk,
		explanations: [],
	};

	game = reducer(game, { type: "hinted", hint: toBS });
	expect(game.progress.hints).toEqual({});
	expect(game.progress.fibberHint).toBe(1);
	game = reducer(game, { type: "hinted-again" });
	expect(game.message).toMatch(/Those clues catch NameB1 lying\.$/);
	expect(game.progress.fibberHint).toBe(2);
	game = reducer(game, { type: "hinted", hint: toBS }); // keeps the stronger mark
	expect(game.progress.fibberHint).toBe(2);

	const p = { ...progress([]), fibberHint: 2 as const };
	expect(result(OVERTIME, p, "x").split("\n")[7]).toBe(
		"🤥 Fibber caught 🟠 · 💢 0 complaints",
	);
	expect(result(OVERTIME, { ...p, fibberHint: 1 }, "x").split("\n")[7]).toBe(
		"🤥 Fibber caught 🟡 · 💢 0 complaints",
	);
	expect(square(p, "B1")).toBe("🟩");
	expect(VERDICTS[1] as readonly string[]).toContain(verdict(p, DAY.date));
});

test("calling BS on someone who complained says it sticks this time", () => {
	let game = reducer(start(OVERTIME), { type: "complained", desk: "A1" });

	game = reducer(game, { type: "caught", desk: "A1", at: 1 });

	expect(game.message).toBe(
		"BS called again, and this time it sticks: NameA1 was the fibber.",
	);
	expect(game.progress.complaints).toEqual(["A1"]); // the complaint stays
});
