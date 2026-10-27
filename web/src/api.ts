import type { components } from "./api/schema";
import type { Day, Hint, Reveal } from "./game.ts";

type Schemas = components["schemas"];

/** Over the API's limit for the minute: try again after `seconds`. */
export class Busy extends Error {
	readonly seconds: number;

	constructor(seconds: number) {
		super("Too many requests");
		this.seconds = seconds;
	}
}

async function ok(response: Response): Promise<Response> {
	// ponytail: Retry-After in seconds only; the API never sends an HTTP date.
	if (response.status === 429) {
		const seconds = Math.ceil(Number(response.headers.get("Retry-After")));
		throw new Busy(seconds > 0 ? seconds : 60);
	}
	if (!response.ok) throw new Error(`HTTP ${response.status}`);
	return response;
}

/** The day's board, or undefined when there's no puzzle for it (or it isn't a date). */
export async function fetchDay(date: string): Promise<Day | undefined> {
	const response = await fetch(`/api/days/${encodeURIComponent(date)}`);
	if (response.status === 404 || response.status === 422) return undefined;
	return (await ok(response)).json();
}

/** The newly revealed coworker, or undefined for "Not enough evidence". */
export async function declare(
	request: Schemas["DeclarationRequest"],
): Promise<Reveal | undefined> {
	const response = await fetch("/api/declarations", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(request),
		// A stalled request fails rather than blocking every later declaration.
		signal: AbortSignal.timeout(10_000),
	});
	const result: Schemas["Accepted"] | Schemas["Rejected"] = await (
		await ok(response)
	).json();
	return result.accepted ? result.reveal : undefined;
}

/** The fewest clues that force a coworker, and that coworker. */
export async function hint(request: Schemas["HintRequest"]): Promise<Hint> {
	const response = await fetch("/api/hints", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify(request),
		signal: AbortSignal.timeout(10_000),
	});
	return (await ok(response)).json();
}
