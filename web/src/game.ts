import type { components } from "./api/schema";

type Schemas = components["schemas"];
export type Desk = Schemas["Desk"];
export type State = Schemas["State"];
export type Declaration = Schemas["Declaration"];
export type Reveal = Schemas["RevealedCoworker"];
export type Day = Schemas["DayResponse"];
export type Hint = Schemas["Hint"];

/** What the browser keeps for a day: enough to rebuild the board and the timer. */
export type Progress = {
	reveals: Reveal[];
	masks: Desk[];
	// How many times each hinted coworker's hint was pressed: 🟡 once, 🟠 twice.
	hints: Partial<Record<Desk, 1 | 2>>;
	startedAt: number;
	solvedAt?: number;
};

export type Game = {
	day: Day;
	progress: Progress;
	selected: Desk;
	message: string;
	// Bumped on every message, so the live region re-announces a repeated one.
	said: number;
	// A declaration is awaiting its answer: the next one's `declared` must include it.
	pending: boolean;
	// The open hint: it stays on its coworker until they're declared.
	hint?: Hint & { presses: 1 | 2 };
};

export type Action =
	| { type: "selected"; desk: Desk }
	| { type: "sent" }
	| { type: "accepted"; reveal: Reveal; at: number }
	| { type: "rejected"; desk: Desk; state: State }
	| { type: "hinted"; hint: Hint }
	| { type: "hinted-again" }
	| { type: "failed" }
	| { type: "already" }
	| { type: "shared"; copied: boolean };

const key = (date: string) => `office-bug:${date}`;

export function load(day: Day): Progress | undefined {
	try {
		const saved = JSON.parse(localStorage.getItem(key(day.date)) ?? "null");
		// Saved before hints existed: none were taken.
		const hints = saved?.hints ?? {};
		// ponytail: shape check only; a full schema check if Progress ever changes shape.
		const fits =
			saved?.reveals?.[0]?.desk === day.start.desk &&
			Array.isArray(saved.masks) &&
			typeof saved.startedAt === "number" &&
			typeof hints === "object" &&
			!Array.isArray(hints);
		return fits ? { ...saved, hints } : undefined;
	} catch {
		return undefined;
	}
}

// ponytail: last write wins across tabs; listen for the `storage` event if players
// really do play one day in two tabs at once.
export function save(date: string, progress: Progress): void {
	try {
		localStorage.setItem(key(date), JSON.stringify(progress));
	} catch {
		// Storage blocked or full: the game still plays, it just won't survive a reload.
	}
}

export function start(day: Day, now: number): Game {
	const progress = load(day) ?? {
		reveals: [day.start],
		masks: [],
		hints: {},
		startedAt: now,
	};
	const hidden = day.coworkers.find((c) => !revealOf(progress, c.desk));
	return {
		day,
		progress,
		selected: hidden?.desk ?? day.start.desk,
		message: "",
		said: 0,
		pending: false,
	};
}

export function revealOf(progress: Progress, desk: Desk): Reveal | undefined {
	return progress.reveals.find((r) => r.desk === desk);
}

/** Every accepted declaration, in order, not counting the starting coworker. */
export function declared(progress: Progress): Declaration[] {
	return progress.reveals.slice(1).map(({ desk, state }) => ({ desk, state }));
}

export function elapsed(progress: Progress, now: number): number {
	return (progress.solvedAt ?? now) - progress.startedAt;
}

export function formatTime(ms: number): string {
	const seconds = Math.max(0, Math.floor(ms / 1000));
	const pad = (n: number) => String(n).padStart(2, "0");
	return `${pad(Math.floor(seconds / 60))}:${pad(seconds % 60)}`;
}

// The game's jab after a hint. Drafted with AI, edited by a human.
export const HINT_TAUNTS = [
	"Stuck already? The kettle hasn't even boiled.",
	"Asking for help. Bold. HR will want to hear about this.",
	"A hint, is it. I'll note that in your appraisal.",
	"Fine. But I'm telling the whole office.",
	"Here's a clue about the clues: read them.",
	"Even Gary the plant got this one.",
	"Help is on its way. Slowly, and with a sigh.",
	"Have you tried turning your brain off and on again?",
];

// What a coworker says back when they get a mask. Never a hint of sick or well,
// since a wrong declaration and an unforced one must sound the same.
// Drafted with AI, edited by a human.
export const REMARKS = [
	"What are you basing that on?!",
	"Evidence. Look it up.",
	"I'd like that in writing, please.",
	"Is this about the stapler?",
	"Fine. Mask on. Under protest.",
	"You can't just say things.",
	"I'll be speaking to my union rep.",
	"Have you even read what people said?",
	"Great, now I look like a dentist.",
	"Wow. In front of everyone.",
	"Noted. Passive-aggressively.",
	"I'll remember this at my leaving do.",
];

// The taunt on solving, by how many coworkers wear a mask or carry a hint:
// none, 1 to 3, or 4 or more. Drafted with AI, edited by a human.
export const VERDICTS = [
	[
		"Flawless. Have a biscuit, you've earned it.",
		"Not one mask. HR are framing your appraisal.",
		"Clean sweep. The kettle's on for you.",
		"Perfect. Even Gary the plant is impressed.",
	],
	[
		"Got there, with a few smudges. Nothing a biscuit won't fix.",
		"Not bad. Not good either. But not bad.",
		"Done, with only a little help and a little panic.",
		"Solved. We'll call the masks a fashion choice.",
	],
	[
		"Solved, eventually. The office looks like a hospital ward.",
		"Cleared. But at what cost?",
		"You got there, mostly by asking everyone.",
		"Done. I've seen tidier fire drills.",
	],
] as const;

/** Every coworker who wears a mask or carries a hint. */
function marked(progress: Progress): Set<string> {
	return new Set([...progress.masks, ...Object.keys(progress.hints)]);
}

export function verdict(progress: Progress, date: string): string {
	const n = marked(progress).size;
	const tier = n === 0 ? 0 : n <= 3 ? 1 : 2;
	return pick([...VERDICTS[tier]], date, tier);
}

/** A coworker's square in the result: the strongest of 🟠 > 🟡 > 😷 > 🟩. */
export function square(progress: Progress, desk: Desk): string {
	const hints = progress.hints[desk];
	if (hints) return hints === 2 ? "🟠" : "🟡";
	return progress.masks.includes(desk) ? "😷" : "🟩";
}

/** "Wed 28 Oct" */
export function dayLabel(date: string): string {
	return new Date(`${date}T00:00`).toLocaleDateString("en-GB", {
		weekday: "short",
		day: "numeric",
		month: "short",
	});
}

/** What a solved day shares: time, verdict, grid and where to play. */
export function result(day: Day, progress: Progress, url: string): string {
	const difficulty = day.difficulty ? ` (${day.difficulty})` : "";
	const time = formatTime(elapsed(progress, 0));
	const squares = day.coworkers.map((c) => square(progress, c.desk));
	const rows = Array.from({ length: squares.length / 4 }, (_, r) =>
		squares.slice(r * 4, (r + 1) * 4).join(""),
	);
	return [
		`Office Lurgy · ${dayLabel(day.date)}${difficulty} · ⏱ ${time}`,
		`"${verdict(progress, day.date)}"`,
		...rows,
		url,
	].join("\n");
}

/** A line from the list, the same one for the same game state on every reload. */
export function pick(lines: string[], ...state: (string | number)[]): string {
	let hash = 0;
	for (const char of state.join(":")) {
		hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
	}
	return lines[hash % lines.length] ?? "";
}

function say(game: Game, message: string): Game {
	return { ...game, message, said: game.said + 1 };
}

/** An answer to the pending declaration: say it and allow the next one. */
function answer(game: Game, message: string): Game {
	return { ...say(game, message), pending: false };
}

export function reducer(game: Game, action: Action): Game {
	const { progress } = game;
	switch (action.type) {
		case "selected":
			return { ...game, selected: action.desk };
		case "sent":
			return { ...game, pending: true };
		case "accepted": {
			const { reveal, at } = action;
			const reveals = [...progress.reveals, reveal];
			const solved = reveals.length === game.day.coworkers.length;
			const next = {
				...progress,
				reveals,
				...(solved && { solvedAt: at }),
			};
			const name = nameOf(game, reveal.desk);
			const hint = game.hint?.coworker === reveal.desk ? undefined : game.hint;
			const line = `${name} is ${reveal.state}. ${name} says: ${reveal.text}`;
			return answer(
				{ ...game, progress: next, hint },
				solved
					? `${line} ${verdict(next, game.day.date)} Office cleared in ${formatTime(elapsed(next, at))}.`
					: line,
			);
		}
		case "rejected": {
			const { desk, state } = action;
			const masks = progress.masks.includes(desk)
				? progress.masks
				: [...progress.masks, desk];
			// Only what the player did goes into the hash, never whether it was wrong.
			const remark = pick(
				REMARKS,
				game.day.date,
				desk,
				state,
				progress.reveals.length,
			);
			return answer(
				{ ...game, progress: { ...progress, masks } },
				`Not enough evidence. ${nameOf(game, desk)} says: “${remark}”`,
			);
		}
		case "hinted": {
			const { hint } = action;
			const hints = {
				...progress.hints,
				[hint.coworker]: progress.hints[hint.coworker] ?? 1,
			};
			const taunt = pick(
				HINT_TAUNTS,
				game.day.date,
				progress.reveals.length,
				1,
			);
			const names = new Intl.ListFormat("en-GB").format(
				game.day.coworkers
					.filter((c) => hint.clues.includes(c.desk))
					.map((c) => c.name),
			);
			return answer(
				{
					...game,
					hint: { ...hint, presses: 1 },
					progress: { ...progress, hints },
				},
				`${taunt} Look at what ${names} said.`,
			);
		}
		case "hinted-again": {
			const { hint } = game;
			if (!hint) return game;
			const taunt = pick(
				HINT_TAUNTS,
				game.day.date,
				progress.reveals.length,
				2,
			);
			return say(
				{
					...game,
					hint: { ...hint, presses: 2 },
					selected: hint.coworker,
					progress: {
						...progress,
						hints: { ...progress.hints, [hint.coworker]: 2 },
					},
				},
				`${taunt} Those clues settle ${nameOf(game, hint.coworker)}.`,
			);
		}
		case "failed":
			return answer(game, "Couldn't reach the office, try again.");
		case "already":
			return say(game, "Already declared.");
		case "shared":
			return say(
				game,
				action.copied ? "Result copied." : "Couldn't copy the result.",
			);
	}
}

function nameOf(game: Game, desk: Desk): string | undefined {
	return game.day.coworkers.find((c) => c.desk === desk)?.name;
}
