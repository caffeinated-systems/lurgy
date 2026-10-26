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
import { App, localToday } from "./App.tsx";
import { DAY, DESKS } from "./fixture.ts";
import type { Reveal } from "./game.ts";

type Answer = Reveal | "rejected" | "down" | Promise<Response>;

/** Stubs fetch: the day comes back as given, each declaration takes the next answer. */
function serve(day: Response | Error, ...answers: Answer[]) {
	const fetch = vi.fn((url: string, _init?: RequestInit) => {
		if (url.startsWith("/api/days/"))
			return day instanceof Error ? Promise.reject(day) : Promise.resolve(day);
		const answer = answers.shift();
		if (answer instanceof Promise) return answer;
		if (answer === "down")
			return Promise.resolve(new Response(null, { status: 500 }));
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

const sick = (desk: (typeof DESKS)[number], text = "Hi."): Reveal => ({
	desk,
	state: "sick",
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

beforeEach(() => {
	localStorage.clear();
	history.replaceState(null, "", "/?day=2026-10-19");
});
afterEach(() => {
	cleanup();
	vi.useRealTimers();
});

test("the local date pads its month and day", () => {
	expect(localToday(new Date(2026, 0, 5))).toBe("2026-01-05");
});

test("with no ?day it asks for the player's local today", async () => {
	history.replaceState(null, "", "/");
	const fetch = serve(new Response(null, { status: 404 }));
	render(<App />);

	expect(screen.getByText("Opening the office…")).toBeDefined();
	expect(
		screen.getByRole("heading", { level: 1, name: "Office Lurgy" }),
	).toBeDefined();
	expect(await screen.findByText("No puzzle for that day yet.")).toBeDefined();
	expect(fetch).toHaveBeenCalledWith(`/api/days/${localToday()}`);
});

test("a day that isn't a date has no puzzle", async () => {
	serve(new Response(null, { status: 422 }));
	render(<App />);

	expect(await screen.findByText("No puzzle for that day yet.")).toBeDefined();
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
	expect(tile("B1").getAttribute("aria-selected")).toBe("true");
	expect(tile("B1").tabIndex).toBe(0);
	expect(tile("A1").tabIndex).toBe(-1);
	expect(screen.getByText("Two in my row.")).toBeDefined();
});

test("an accepted declaration reveals the coworker and posts what came before", async () => {
	const fetch = await open(sick("B1"), sick("C1", "Bye."));

	fireEvent.click(screen.getByRole("button", { name: "Declare NameB1 sick" }));
	await screen.findByText("NameB1 is sick. NameB1 says: Hi.");
	expect(tile("B1").getAttribute("aria-label")).toBe(
		"B1, NameB1, HR, sick, says: Hi.",
	);

	fireEvent.click(tile("C1"));
	fireEvent.click(screen.getByRole("button", { name: "Declare NameC1 well" }));
	await screen.findByText("NameC1 is sick. NameC1 says: Bye.");

	expect(JSON.parse(fetch.mock.calls[2]?.[1]?.body as string)).toEqual({
		date: "2026-10-19",
		declared: [{ desk: "B1", state: "sick" }],
		declaration: { desk: "C1", state: "well" },
	});
	const log = screen.getAllByRole("listitem").map((li) => li.textContent);
	expect(log).toEqual([
		"NameC1 · C1 · sickBye.",
		"NameB1 · B1 · sickHi.",
		"NameA1 · A1 · wellTwo in my row.",
	]);
});

test("a rejected declaration marks a mistake", async () => {
	await open("rejected");

	fireEvent.click(screen.getByRole("button", { name: "Declare NameB1 well" }));

	expect(await screen.findByText("Not enough evidence.")).toBeDefined();
	expect(tile("B1").getAttribute("aria-label")).toBe(
		"B1, NameB1, HR, unknown, one mistake",
	);
	expect(tile("B1").className).toContain("mistake");
});

test("a failed declaration says so and marks nothing", async () => {
	await open("down");

	fireEvent.click(screen.getByRole("button", { name: "Declare NameB1 sick" }));

	expect(
		await screen.findByText("Couldn't reach the office, try again."),
	).toBeDefined();
	expect(tile("B1").className).not.toContain("mistake");
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
	await screen.findByText("Not enough evidence.");

	expect(
		JSON.parse(fetch.mock.calls[2]?.[1]?.body as string).declaration,
	).toEqual({ desk: "C1", state: "well" });
});

test("flavour says it carries no clue", async () => {
	await open({ desk: "B1", state: "well", kind: "flavour", text: "My mug!" });

	fireEvent.click(screen.getByRole("button", { name: "Declare NameB1 well" }));

	expect(await screen.findByText("Flavour: no clue.")).toBeDefined();
});

test("the timer ticks, stops on the solve and stays stopped after a reload", async () => {
	vi.useFakeTimers({ shouldAdvanceTime: true, now: 0 });
	const answers = DESKS.slice(1).map((desk) => sick(desk));
	await open(...answers);
	const timer = screen.getByRole("timer");
	expect(timer.textContent).toBe("⏱ 00:00");

	await act(() => vi.advanceTimersByTimeAsync(65_000));
	expect(timer.textContent).toMatch(/⏱ 01:0[56]/);

	for (const desk of DESKS.slice(1)) {
		fireEvent.click(tile(desk));
		fireEvent.keyDown(tile(desk), { key: "s" });
		await waitFor(() =>
			expect(tile(desk).getAttribute("aria-label")).toContain("sick"),
		);
	}
	expect(screen.getByRole("status").textContent).toMatch(
		/Office cleared in 01:0[56]\.$/,
	);
	const stopped = timer.textContent;
	await act(() => vi.advanceTimersByTimeAsync(10_000));
	expect(timer.textContent).toBe(stopped);

	cleanup();
	await open();
	expect(screen.getByRole("timer").textContent).toBe(stopped);
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
	await screen.findByText("Not enough evidence.");

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
