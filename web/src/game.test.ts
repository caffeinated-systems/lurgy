import { beforeEach, expect, test, vi } from "vitest";
import { DAY, DESKS } from "./fixture.ts";
import {
	declared,
	elapsed,
	formatTime,
	load,
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
		mistakes: [],
		startedAt: 1000,
	});
	expect(game.selected).toBe("B1");
});

test("a saved day resumes where it left off", () => {
	const progress = {
		reveals: [DAY.start, reveal("B1")],
		mistakes: ["C1" as const],
		startedAt: 5,
	};
	save(DAY.date, progress);

	const game = start(DAY, 1000);

	expect(game.progress).toEqual(progress);
	expect(game.selected).toBe("C1");
});

test("broken or foreign storage starts the day afresh", () => {
	localStorage.setItem("office-bug:2026-10-19", "{not json");
	expect(load(DAY.date)).toBeUndefined();

	localStorage.setItem("office-bug:2026-10-19", '{"reveals": 3}');
	expect(load(DAY.date)).toBeUndefined();
});

test("blocked storage neither loads nor throws", () => {
	vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
		throw new Error("blocked");
	});
	vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
		throw new Error("blocked");
	});

	expect(load(DAY.date)).toBeUndefined();
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

test("accepting an already revealed coworker changes nothing", () => {
	const game = reducer(start(DAY, 0), {
		type: "accepted",
		reveal: DAY.start,
		at: 1,
	});

	expect(game).toEqual(start(DAY, 0));
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

test("a rejection marks one mistake per coworker and repeats its message", () => {
	let game = reducer(start(DAY, 0), { type: "rejected", desk: "B1" });
	game = reducer(game, { type: "rejected", desk: "B1" });

	expect(game.progress.mistakes).toEqual(["B1"]);
	expect(game.message).toBe("Not enough evidence.");
	expect(game.said).toBe(2);
});

test("a network failure says so without a mistake", () => {
	const game = reducer(start(DAY, 0), { type: "failed" });

	expect(game.progress.mistakes).toEqual([]);
	expect(game.message).toBe("Couldn't reach the office, try again.");
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
