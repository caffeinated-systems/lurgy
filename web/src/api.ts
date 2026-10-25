import type { components } from "./api/schema";
import type { Day, Reveal } from "./game.ts";

type Schemas = components["schemas"];

async function ok(response: Response): Promise<Response> {
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
	});
	const result: Schemas["Accepted"] | Schemas["Rejected"] = await (
		await ok(response)
	).json();
	return result.accepted ? result.reveal : undefined;
}
