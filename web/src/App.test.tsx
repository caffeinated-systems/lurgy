import {
	act,
	cleanup,
	fireEvent,
	render,
	screen,
	waitFor,
	within,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { App, localToday, weekOf } from "./App.tsx";
import { DAY, DESKS } from "./fixture.ts";
import type { Hint, Reveal } from "./game.ts";

type Answer = Reveal | Hint | "rejected" | "down" | "busy" | Promise<Response>;

/** Stubs fetch: the day comes back as given, each declaration takes the next answer. */
function serve(day: Response | Error, ...answers: Answer[]) {
	const fetch = vi.fn((url: string, _init?: RequestInit) => {
		if (url.startsWith("/api/days/"))
			return day instanceof Error ? Promise.reject(day) : Promise.resolve(day);
		const answer = answers.shift();
		if (answer instanceof Promise) return answer;
		if (answer === "down")
			return Promise.resolve(new Response(null, { status: 500 }));
		if (answer === "busy") return Promise.resolve(busy());
		if (typeof answer === "object" && "coworker" in answer)
			return Promise.resolve(Response.json(answer));
		return Promise.resolve(
			Response.json(
				answer === "rejected"
					? { accepted: false }
					: { accepted: true, reveal: answer },
			),
		);
	});
	vi.stubGlobal("fetch", fetch);
	return fetch;
}

const busy = (headers: HeadersInit = { "Retry-After": "20" }) =>
	new Response(null, { status: 429, headers });

const sick = (desk: (typeof DESKS)[number], text = "Hi."): Reveal => ({
	desk,
	state: "sick",
	kind: "clue",
	text,
});

const well = (desk: (typeof DESKS)[number], text = "Hi."): Reveal => ({
	desk,
	state: "well",
	kind: "clue",
	text,
});

async function open(...answers: Answer[]) {
	const fetch = serve(Response.json(DAY), ...answers);
	render(<App />);
	await screen.findByRole("grid", { name: /office floor/i });
	return fetch;
}

const tile = (desk: string) =>
	within(screen.getByRole("grid")).getAllByRole("gridcell")[
		DESKS.indexOf(desk as (typeof DESKS)[number])
	] as HTMLElement;

// Noon on the fixture Monday, in the player's local time.
const MONDAY = new Date(2026, 9, 19, 12);

beforeEach(() => {
	vi.useFakeTimers({ toFake: ["Date"], now: MONDAY });
	localStorage.clear();
	history.replaceState(null, "", "/?day=2026-10-19");
});
afterEach(() => {
	cleanup();
	vi.useRealTimers();
	vi.unstubAllGlobals();
});

test("the local date pads its month and day", () => {
	expect(localToday(new Date(2026, 0, 5))).toBe("2026-01-05");
});

test.each([
	["Monday", "2026-10-19"],
	["Friday", "2026-10-23"],
	["Saturday", "2026-10-24"],
	["Sunday", "2026-10-25"],
])("on %s the Week is that Monday to Sunday", (_, date) => {
	expect(weekOf(date)).toEqual([
		"2026-10-19",
		"2026-10-20",
		"2026-10-21",
		"2026-10-22",
		"2026-10-23",
		"2026-10-24",
		"2026-10-25",
	]);
});

test("a Week can span two months", () => {
	expect(weekOf("2026-11-01")).toEqual([
		"2026-10-26",
		"2026-10-27",
		"2026-10-28",
		"2026-10-29",
		"2026-10-30",
		"2026-10-31",
		"2026-11-01",
	]);
});

test("the week strip links every day so far and marks the one open", async () => {
	vi.setSystemTime(new Date(2026, 9, 21, 12));
	serve(Response.json(DAY));
	render(<App />);

	const week = await screen.findByRole("navigation", {
		name: "The week's puzzles",
	});
	const links = within(week).getAllByRole("link");
	expect(links.map((a) => a.textContent)).toEqual(["Mon", "Tue", "Wed"]);
	expect(links[0]?.getAttribute("href")).toBe("?day=2026-10-19");
	expect(links[0]?.getAttribute("aria-current")).toBe("page");
	expect(links[2]?.getAttribute("aria-current")).toBeNull();
	expect(links[0]?.getAttribute("aria-label")).toBe("Mon 19 Oct");
	expect(week.textContent).toContain("Thu, not open yet");
});

test.each([
	["a later day this Week", "2026-10-20"],
	["a day in an older Week", "2026-10-12"],
])("%s is closed without asking the server", async (_, date) => {
	history.replaceState(null, "", `/?day=${date}`);
	const fetch = serve(Response.json(DAY));
	render(<App />);

	expect(screen.getByText(/^That day isn't open/)).toBeDefined();
	expect(fetch).not.toHaveBeenCalled();
});

test("at the weekend today's Overtime opens, with the weekend marked", async () => {
	vi.setSystemTime(new Date(2026, 9, 24, 12));
	history.replaceState(null, "", "/");
	const fetch = serve(
		Response.json({ ...DAY, date: "2026-10-24", overtime: true }),
	);
	render(<App />);

	await screen.findByRole("grid", { name: /office floor/i });
	expect(fetch).toHaveBeenCalledWith("/api/days/2026-10-24");
	const week = screen.getByRole("navigation", { name: "The week's puzzles" });
	const links = within(week).getAllByRole("link");
	expect(links).toHaveLength(6);
	expect(links[5]?.getAttribute("aria-label")).toBe("Sat 24 Oct, Overtime");
	expect(week.textContent).toContain("Sun, not open yet");
});

test("an earlier day stays playable at the weekend", async () => {
	vi.setSystemTime(new Date(2026, 9, 25, 12));
	await open();

	expect(screen.getByText("Mon 19 Oct")).toBeDefined();
});

test("with no ?day it asks for the player's local today", async () => {
	history.replaceState(null, "", "/");
	const fetch = serve(new Response(null, { status: 404 }));
	render(<App />);

	expect(screen.getByText("Opening the office…")).toBeDefined();
	expect(
		screen.getByRole("heading", { level: 1, name: "Office Lurgy" }),
	).toBeDefined();
	expect(
		await screen.findByText(/^No puzzle for that day: the office is closed/),
	).toBeDefined();
	expect(fetch).toHaveBeenCalledWith(`/api/days/${localToday()}`);
});

test("a day that isn't a date has no puzzle", async () => {
	serve(new Response(null, { status: 422 }));
	render(<App />);

	expect(
		await screen.findByText(/^No puzzle for that day: the office is closed/),
	).toBeDefined();
});

test.each([
	["a server error", new Response(null, { status: 500 })],
	["no network", new Error("offline")],
])("%s while loading says so", async (_, day) => {
	serve(day);
	render(<App />);

	expect(
		await screen.findByText("Couldn't reach the office, try again."),
	).toBeDefined();
});

test("the board shows the logo, the date, the starting coworker and the first hidden desk selected", async () => {
	await open();

	expect(
		screen.getByRole("heading", { level: 1, name: "Office Lurgy" }),
	).toBeDefined();
	expect(screen.getByText("Mon 19 Oct")).toBeDefined();
	expect(tile("A1").getAttribute("aria-label")).toBe(
		"A1, NameA1, HR, well, says: Two in my row.",
	);
	expect(within(tile("A1")).getByText("HR")).toBeDefined();
	// Declared tiles are washed in their state (App.css); the rest stay plain.
	expect(tile("A1").classList).toContain("st-well");
	expect(tile("B1").className).not.toMatch(/st-/);
	expect(tile("B1").getAttribute("aria-selected")).toBe("true");
	expect(tile("B1").tabIndex).toBe(0);
	expect(tile("A1").tabIndex).toBe(-1);
	expect(screen.getByText("Two in my row.")).toBeDefined();
});

test("a department the board doesn't know shows its first three letters", async () => {
	const coworkers = DAY.coworkers.map((c) => ({ ...c, department: "Payroll" }));
	serve(Response.json({ ...DAY, coworkers }));
	render(<App />);
	await screen.findByRole("grid", { name: /office floor/i });

	expect(within(tile("A1")).getByText("PAY")).toBeDefined();
});

test("an accepted declaration reveals the coworker and posts what came before", async () => {
	const fetch = await open(sick("B1"), sick("C1", "Bye."));

	fireEvent.click(screen.getByRole("button", { name: "Declare NameB1 sick" }));
	await screen.findByText("NameB1 is sick. NameB1 says: Hi.");
	expect(tile("B1").getAttribute("aria-label")).toBe(
		"B1, NameB1, HR, sick, says: Hi.",
	);
	expect(tile("B1").classList).toContain("st-sick");

	fireEvent.click(tile("C1"));
	fireEvent.click(screen.getByRole("button", { name: "Declare NameC1 well" }));
	await screen.findByText("NameC1 is sick. NameC1 says: Bye.");

	expect(JSON.parse(fetch.mock.calls[2]?.[1]?.body as string)).toEqual({
		date: "2026-10-19",
		declared: [{ desk: "B1", state: "sick" }],
		declaration: { desk: "C1", state: "well" },
	});
	const log = screen
		.getAllByRole("listitem")
		.map((li) => li.querySelector(".entry")?.textContent);
	expect(log).toEqual([
		"NameC1 · C1 · sickBye.",
		"NameB1 · B1 · sickHi.",
		"NameA1 · A1 · wellTwo in my row.",
	]);
});

test("a rejected declaration masks the coworker", async () => {
	await open("rejected");

	fireEvent.click(screen.getByRole("button", { name: "Declare NameB1 well" }));

	expect(
		await screen.findByText(/^Not enough evidence\. NameB1 says: “.+”$/),
	).toBeDefined();
	expect(tile("B1").getAttribute("aria-label")).toBe(
		"B1, NameB1, HR, unknown, wearing a mask",
	);
	expect(tile("B1").querySelector(".mask")).not.toBeNull();
});

test("a message can be dismissed until the next one", async () => {
	await open(sick("B1"), sick("C1"));
	expect(screen.queryByRole("button", { name: "Dismiss message" })).toBeNull();

	fireEvent.click(screen.getByRole("button", { name: "Declare NameB1 sick" }));
	await screen.findByText("NameB1 is sick. NameB1 says: Hi.");
	fireEvent.click(screen.getByRole("button", { name: "Dismiss message" }));
	expect(screen.getByRole("status").textContent).toBe("");
	expect(screen.queryByRole("button", { name: "Dismiss message" })).toBeNull();
	// Focus goes to the selected desk, not back to the page.
	expect(document.activeElement).toBe(tile("B1"));

	fireEvent.click(tile("C1"));
	fireEvent.click(screen.getByRole("button", { name: "Declare NameC1 sick" }));
	expect(
		await screen.findByRole("button", { name: "Dismiss message" }),
	).toBeDefined();
});

test("a failed declaration says so and marks nothing", async () => {
	await open("down");

	fireEvent.click(screen.getByRole("button", { name: "Declare NameB1 sick" }));

	expect(
		await screen.findByText("Couldn't reach the office, try again."),
	).toBeDefined();
	expect(tile("B1").querySelector(".mask")).toBeNull();
});

test("a revealed coworker can't be declared again", async () => {
	const fetch = await open();

	fireEvent.click(tile("A1"));

	expect(screen.getByText(/Already declared/)).toBeDefined();
	const declare = screen.getByRole("button", { name: "Declare NameA1 sick" });
	expect((declare as HTMLButtonElement).disabled).toBe(true);
	fireEvent.keyDown(tile("A1"), { key: "s" });
	expect(screen.getByRole("status").textContent).toBe("Already declared.");
	expect(fetch).toHaveBeenCalledTimes(1);
});

test("arrow keys move round the board and stop at its edges", async () => {
	await open();
	const press = (key: string) =>
		fireEvent.keyDown(document.activeElement as Element, { key });
	tile("B1").focus();

	press("ArrowUp");
	expect(document.activeElement).toBe(tile("B1"));
	press("ArrowRight");
	press("ArrowRight");
	press("ArrowRight");
	expect(document.activeElement).toBe(tile("D1"));
	press("ArrowDown");
	expect(document.activeElement).toBe(tile("D2"));
	expect(tile("D2").getAttribute("aria-selected")).toBe("true");
	expect(tile("D2").tabIndex).toBe(0);
	press("ArrowLeft");
	expect(document.activeElement).toBe(tile("C2"));
	press("ArrowUp");
	expect(document.activeElement).toBe(tile("C1"));
	for (const _ of [1, 2, 3, 4, 5]) press("ArrowDown");
	expect(document.activeElement).toBe(tile("C5"));
	press("ArrowLeft");
	press("ArrowLeft");
	press("ArrowLeft");
	expect(document.activeElement).toBe(tile("A5"));
	press("Enter");
	expect(document.activeElement).toBe(tile("A5"));
});

test("S and W declare the selected coworker; modified keys don't", async () => {
	const fetch = await open(sick("B1"), "rejected");

	fireEvent.keyDown(tile("B1"), { key: "s", ctrlKey: true });
	expect(fetch).toHaveBeenCalledTimes(1);

	fireEvent.keyDown(tile("B1"), { key: "S" });
	await screen.findByText("NameB1 is sick. NameB1 says: Hi.");
	fireEvent.keyDown(tile("B1"), { key: "ArrowRight" });
	fireEvent.keyDown(tile("C1"), { key: "w" });
	await screen.findByText(/^Not enough evidence\./);

	expect(
		JSON.parse(fetch.mock.calls[2]?.[1]?.body as string).declaration,
	).toEqual({ desk: "C1", state: "well" });
});

test("flavour says it carries no clue", async () => {
	await open({ desk: "B1", state: "well", kind: "flavour", text: "My mug!" });

	fireEvent.click(screen.getByRole("button", { name: "Declare NameB1 well" }));

	expect(await screen.findByText("Flavour: no clue.")).toBeDefined();
});

test("a joke follows its clue", async () => {
	await open({
		desk: "B1",
		state: "well",
		kind: "clue",
		text: "One in my row.",
		joke: "Not that I'm counting.",
	});

	fireEvent.click(screen.getByRole("button", { name: "Declare NameB1 well" }));

	expect(await screen.findByText("Not that I'm counting.")).toBeDefined();
});

test("a hint shows its clues, then on a second press its coworker", async () => {
	const fetch = await open({
		clues: ["A1"],
		coworker: "B3",
		explanations: [
			{
				desk: "A1",
				explanation:
					"Row 1 is NameA1, NameB1, NameC1 and NameD1: two are sick.",
				desks: ["A1", "B1", "C1", "D1"],
			},
		],
	});

	fireEvent.click(screen.getByRole("button", { name: "Hint" }));

	expect(await screen.findByText(/Look at what NameA1 said\.$/)).toBeDefined();
	expect(JSON.parse(fetch.mock.calls[1]?.[1]?.body as string)).toEqual({
		date: "2026-10-19",
		declared: [],
	});
	expect(tile("A1").getAttribute("aria-label")).toContain("hinted clue");
	expect(screen.getByText("Two in my row.").closest("li")?.className).toBe(
		"hinted",
	);
	expect(tile("B3").getAttribute("aria-label")).toContain("one hint");
	expect(tile("B3").textContent).toContain("🟡");

	fireEvent.click(screen.getByRole("button", { name: "Who do they settle?" }));

	expect(await screen.findByText(/Those clues settle NameB3\.$/)).toBeDefined();
	expect(tile("B3").getAttribute("aria-label")).toMatch(
		/two hints, the hint is about them$/,
	);
	expect(tile("B3").getAttribute("aria-selected")).toBe("true");
	expect(document.activeElement).toBe(tile("B3"));
	expect(
		screen.getByRole("button", { name: "Who do they settle?" }),
	).toHaveProperty("disabled", true);
	expect(fetch).toHaveBeenCalledTimes(2);
});

test("reading a clue marks who said it; only a hinted one is spelled out", async () => {
	await open({
		clues: ["A1"],
		coworker: "B3",
		explanations: [
			{
				desk: "A1",
				explanation: "Row 1 is NameA1 and NameB1: two are sick.",
				desks: ["A1", "B1"],
			},
		],
	});
	const entry = screen.getByRole("button", { name: /Two in my row\./ });

	fireEvent.click(entry);

	expect(entry.getAttribute("aria-pressed")).toBe("true");
	expect(tile("A1").getAttribute("aria-label")).toContain(
		"said the clue you're reading",
	);
	expect(screen.queryByText(/^Row 1 is/)).toBeNull();
	expect(tile("B1").getAttribute("aria-label")).not.toContain("in the clue");

	fireEvent.click(screen.getByRole("button", { name: "Hint" }));

	expect(await screen.findByText(/^Row 1 is/)).toBeDefined();
	expect(
		document.getElementById(entry.getAttribute("aria-describedby") ?? "")
			?.textContent,
	).toMatch(/^Row 1 is/);
	expect(tile("B1").getAttribute("aria-label")).toContain(
		"in the clue you're reading",
	);
	expect(tile("C1").getAttribute("aria-label")).not.toContain("in the clue");

	fireEvent.click(entry);

	expect(entry.getAttribute("aria-pressed")).toBe("false");
	expect(screen.queryByText(/^Row 1 is/)).toBeNull();
	expect(tile("A1").getAttribute("aria-label")).not.toContain("reading");
});

test("a dimmed clue stays dimmed after a reload, and undims", async () => {
	await open();
	const dim = () => screen.getByRole("button", { name: "Dim NameA1's clue" });

	fireEvent.click(dim());

	expect(dim().getAttribute("aria-pressed")).toBe("true");
	expect(dim().closest("li")?.className).toBe("dimmed");

	document.body.innerHTML = "";
	await open();

	expect(dim().closest("li")?.className).toBe("dimmed");
	fireEvent.click(dim());
	expect(dim().closest("li")?.className).toBe("");
});

test("flavour can be read and dimmed like a clue", async () => {
	await open({ ...sick("B1", "Nice weather."), kind: "flavour" });
	fireEvent.keyDown(tile("B1"), { key: "s" });
	await screen.findByText("Flavour: no clue.");

	const dim = screen.getByRole("button", { name: "Dim NameB1's message" });
	fireEvent.click(dim);
	expect(dim.closest("li")?.className).toBe("dimmed");
	fireEvent.click(screen.getByRole("button", { name: /Nice weather\./ }));
	expect(tile("B1").getAttribute("aria-label")).toContain(
		"said the clue you're reading",
	);
});

/** Opens a day that was already solved, with B1 masked. */
async function openSolved() {
	localStorage.setItem(
		"office-bug:2026-10-19",
		JSON.stringify({
			reveals: DESKS.map((desk) => sick(desk)),
			masks: ["B1"],
			hints: {},
			startedAt: 0,
			solvedAt: 1,
		}),
	);
	await open();
}

const RESULT =
	/^Office Lurgy · Mon 19 Oct \(Medium\) · ⏱ 00:00\n"[^"]+"\n🟩😷🟩🟩\n/;

test("a cleared office shows the result in place of the buttons", async () => {
	await openSolved();

	expect(screen.queryByRole("button", { name: "Hint" })).toBeNull();
	expect(screen.queryByRole("button", { name: /^Declare/ })).toBeNull();
	expect(screen.getByRole("button", { name: "Share" })).toBeDefined();
});

test("sharing uses the share sheet where there is one", async () => {
	const share = vi.fn(() => Promise.resolve());
	vi.stubGlobal("navigator", { share });
	await openSolved();

	fireEvent.click(screen.getByRole("button", { name: "Share" }));

	await waitFor(() => expect(share).toHaveBeenCalledTimes(1));
	expect(share.mock.calls[0]).toEqual([
		{ text: expect.stringMatching(RESULT) },
	]);
});

test("closing the share sheet does nothing", async () => {
	const writeText = vi.fn(() => Promise.resolve());
	const share = vi.fn(() =>
		Promise.reject(new DOMException("closed", "AbortError")),
	);
	vi.stubGlobal("navigator", { share, clipboard: { writeText } });
	await openSolved();

	fireEvent.click(screen.getByRole("button", { name: "Share" }));

	await waitFor(() => expect(share).toHaveBeenCalled());
	expect(writeText).not.toHaveBeenCalled();
});

test("without a share sheet the result is copied", async () => {
	const writeText = vi.fn(() => Promise.resolve());
	const share = vi.fn(() => Promise.reject(new Error("not allowed")));
	vi.stubGlobal("navigator", { share, clipboard: { writeText } });
	await openSolved();

	fireEvent.click(screen.getByRole("button", { name: "Share" }));

	expect(await screen.findByText("Result copied.")).toBeDefined();
	expect(writeText.mock.calls[0]).toEqual([expect.stringMatching(RESULT)]);
});

test("a result that can't be copied says so", async () => {
	vi.stubGlobal("navigator", {});
	await openSolved();

	fireEvent.click(screen.getByRole("button", { name: "Share" }));

	expect(await screen.findByText("Couldn't copy the result.")).toBeDefined();
});

test("no hint while a declaration is waiting", async () => {
	let respond = (_: Response) => {};
	const waiting = new Promise<Response>((resolve) => {
		respond = resolve;
	});
	await open(waiting);
	const button = () => screen.getByRole("button", { name: "Hint" });

	fireEvent.click(screen.getByRole("button", { name: "Declare NameB1 sick" }));
	expect(button()).toHaveProperty("disabled", true);
	respond(Response.json({ accepted: false }));
	await waitFor(() => expect(button()).toHaveProperty("disabled", false));
});

test.each([
	["a declaration", "Declare NameB1 sick"],
	["a hint", "Hint"],
])("%s over the limit asks the player to wait", async (_, button) => {
	await open("busy");

	fireEvent.click(screen.getByRole("button", { name: button }));

	expect(
		await screen.findByText(
			"Steady on, the whole office is asking at once. Try again in 20 seconds.",
		),
	).toBeDefined();
	expect(tile("B1").getAttribute("aria-label")).not.toContain("mask");
});

test.each<Record<string, string>>([
	{},
	{ "Retry-After": "-5" },
	{ "Retry-After": "soon" },
])(
	"loading a day over the limit asks the player to wait, a minute if it doesn't say (%o)",
	async (headers) => {
		serve(busy(headers));
		render(<App />);

		expect(
			await screen.findByText(
				"Steady on, the whole office is asking at once. Try again in 60 seconds.",
			),
		).toBeDefined();
	},
);

test("a hint that can't reach the office says so", async () => {
	await open("down");

	fireEvent.click(screen.getByRole("button", { name: "Hint" }));

	expect(
		await screen.findByText("Couldn't reach the office, try again."),
	).toBeDefined();
});

test("the timer waits for the first declaration, ticks, stops on the solve and stays stopped after a reload", async () => {
	vi.useFakeTimers({ shouldAdvanceTime: true, now: MONDAY });
	const answers = DESKS.slice(1).map((desk) => sick(desk));
	await open(...answers);
	const timer = screen.getByRole("timer");
	await act(() => vi.advanceTimersByTimeAsync(30_000));
	expect(timer.textContent).toBe("00:00");

	fireEvent.keyDown(tile("B1"), { key: "s" });
	await waitFor(() =>
		expect(tile("B1").getAttribute("aria-label")).toContain("sick"),
	);
	await act(() => vi.advanceTimersByTimeAsync(65_000));
	expect(timer.textContent).toMatch(/^01:0[56]$/);

	for (const desk of DESKS.slice(2)) {
		fireEvent.click(tile(desk));
		fireEvent.keyDown(tile(desk), { key: "s" });
		await waitFor(() =>
			expect(tile(desk).getAttribute("aria-label")).toContain("sick"),
		);
	}
	expect(screen.getByRole("status").textContent).toMatch(
		/Office cleared in 01:0[56]\.$/,
	);
	await waitFor(() =>
		expect(document.activeElement).toBe(
			screen.getByRole("button", { name: "Share" }),
		),
	);
	const stopped = timer.textContent;
	await act(() => vi.advanceTimersByTimeAsync(10_000));
	expect(timer.textContent).toBe(stopped);

	cleanup();
	await open();
	expect(screen.getByRole("timer").textContent).toBe(stopped);
	expect(document.activeElement).toBe(document.body);
});

test.each([
	[
		"a hint",
		{ clues: ["A1"], coworker: "B3", explanations: [] } as Hint,
		"Hint",
	],
	["a refused declaration", "rejected" as const, "Declare NameB1 well"],
])("%s also starts the timer", async (_, answer, button) => {
	vi.useFakeTimers({ shouldAdvanceTime: true, now: MONDAY });
	await open(answer);
	const timer = screen.getByRole("timer");
	await act(() => vi.advanceTimersByTimeAsync(30_000));
	expect(timer.textContent).toBe("00:00");

	fireEvent.click(screen.getByRole("button", { name: button }));
	await act(() => vi.advanceTimersByTimeAsync(5_000));

	expect(timer.textContent).not.toBe("00:00");
});

test("a reload rebuilds the board from the browser", async () => {
	const first = await open(sick("B1"));
	fireEvent.keyDown(tile("B1"), { key: "s" });
	await screen.findByText("NameB1 is sick. NameB1 says: Hi.");
	expect(first).toHaveBeenCalledTimes(2);

	document.body.innerHTML = "";
	const second = await open();

	expect(tile("B1").getAttribute("aria-label")).toContain("sick");
	expect(tile("C1").getAttribute("aria-selected")).toBe("true");
	expect(second).toHaveBeenCalledTimes(1);
});

test("a second declaration waits for the first one's answer", async () => {
	let reply: (response: Response) => void = () => {};
	const first = new Promise<Response>((resolve) => {
		reply = resolve;
	});
	const fetch = await open(first, "rejected");

	fireEvent.keyDown(tile("B1"), { key: "s" });
	fireEvent.click(tile("C1"));
	fireEvent.keyDown(tile("C1"), { key: "w" });
	expect(fetch).toHaveBeenCalledTimes(2);
	const well = screen.getByRole("button", { name: "Declare NameC1 well" });
	expect((well as HTMLButtonElement).disabled).toBe(true);

	reply(Response.json({ accepted: true, reveal: sick("B1") }));
	await screen.findByText("NameB1 is sick. NameB1 says: Hi.");
	fireEvent.keyDown(tile("C1"), { key: "w" });
	await screen.findByText(/^Not enough evidence\./);

	expect(JSON.parse(fetch.mock.calls[2]?.[1]?.body as string).declared).toEqual(
		[{ desk: "B1", state: "sick" }],
	);
});

test("the footer links to Caffeinated Systems and Wordis", async () => {
	await open();

	expect(
		screen
			.getByRole("link", { name: "Caffeinated Systems" })
			.getAttribute("href"),
	).toBe("https://caffeinated.systems");
	expect(
		screen.getByRole("link", { name: "Wordis" }).getAttribute("href"),
	).toBe("https://wordis.caffeinated.systems");
});

// jsdom has no showModal; the browser does the rest (Esc, the Close form).
HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
	this.open = true;
};

test("help opens how to play over the board", async () => {
	serve(Response.json(DAY));
	render(<App />);

	const help = await screen.findByRole("button", { name: "Help" });
	expect(screen.queryByRole("dialog")).toBeNull();
	fireEvent.click(help);
	const panel = screen.getByRole("dialog", { name: "How to play" });
	expect(within(panel).getByText("Reading the clues")).toBeDefined();
	expect(within(panel).getByText("Keys")).toBeDefined();
});

// The fixture day as Overtime, starting from a sick coworker with a clue.
const OVERTIME = {
	...DAY,
	overtime: true,
	start: { ...DAY.start, state: "sick" as const },
};

async function overtime(...answers: Answer[]) {
	const fetch = serve(Response.json(OVERTIME), ...answers);
	render(<App />);
	await screen.findByRole("grid", { name: /office floor/i });
	return fetch;
}

test("Overtime stamps the logo and says someone is lying; a weekday doesn't", async () => {
	await overtime();
	const logo = screen.getByRole("heading", { level: 1 });
	expect(within(logo).getByText("Overtime")).toBeDefined();
	expect(screen.getByText("One sick coworker is lying.")).toBeDefined();
	expect(tile("A1").getAttribute("aria-keyshortcuts")).toBe("S W B");
	cleanup();

	await open();
	expect(screen.queryByText("One sick coworker is lying.")).toBeNull();
	expect(tile("A1").getAttribute("aria-keyshortcuts")).toBe("S W");
});

test("on a revealed sick coworker, BS takes the place of Sick and Well", async () => {
	await overtime();

	fireEvent.click(tile("A1"));

	expect(
		screen.getByRole("button", { name: "Call BS on NameA1" }),
	).toBeDefined();
	expect(screen.queryByRole("button", { name: /^Declare NameA1/ })).toBeNull();
});

test("a rejected BS call makes a complaint, not a mask", async () => {
	await overtime("rejected");

	fireEvent.click(tile("A1"));
	fireEvent.click(screen.getByRole("button", { name: "Call BS on NameA1" }));

	await screen.findByText(/^Not enough evidence\. NameA1 says/);
	expect(tile("A1").getAttribute("aria-label")).toContain("made a complaint");
	expect(tile("A1").getAttribute("aria-label")).not.toContain("wearing a mask");
	expect(within(tile("A1")).getByText("💢")).toBeDefined();
});

test("calling BS on the fibber strikes out their clue and posts in order", async () => {
	const fetch = await overtime(sick("B1"), OVERTIME.start, well("C1"));
	fireEvent.click(screen.getByRole("button", { name: "Declare NameB1 sick" }));
	await screen.findByText("NameB1 is sick. NameB1 says: Hi.");

	fireEvent.click(tile("A1"));
	fireEvent.keyDown(tile("A1"), { key: "b" });
	await screen.findByText(/^BS called! NameA1 was the fibber/);
	fireEvent.click(tile("C1"));
	fireEvent.click(screen.getByRole("button", { name: "Declare NameC1 well" }));
	await screen.findByText("NameC1 is well. NameC1 says: Hi.");

	expect(JSON.parse(fetch.mock.calls[3]?.[1]?.body as string).declared).toEqual(
		[
			{ desk: "B1", state: "sick" },
			{ desk: "A1", state: "fibber" },
		],
	);
	const lie = screen.getAllByRole("listitem").at(-1) as HTMLElement;
	expect(lie.querySelector("s")?.textContent).toBe("Two in my row.");
	expect(within(lie).getByText("A lie: BS called.")).toBeDefined();
	// Caught: no more BS on them.
	fireEvent.click(tile("A1"));
	expect(
		screen.queryByRole("button", { name: "Call BS on NameA1" }),
	).toBeNull();
});

test("B does nothing on someone BS can't be called on", async () => {
	const fetch = await overtime();

	fireEvent.keyDown(tile("B1"), { key: "b" }); // not revealed
	expect(fetch).toHaveBeenCalledTimes(1); // only the day
	cleanup();

	const weekday = await open();
	fireEvent.click(tile("A1"));
	fireEvent.keyDown(tile("A1"), { key: "b" });
	expect(weekday).toHaveBeenCalledTimes(1);
});
