import type { components } from "./api/schema";
import { Busy } from "./api.ts";

type Schemas = components["schemas"];
export type Desk = Schemas["Desk"];
export type State = Schemas["State"];
export type Call = Schemas["Call"];
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
	// Clues the player has dimmed, by who said them.
	dimmed: Desk[];
	// Overtime: who made a complaint at being wrongly called a liar.
	complaints: Desk[];
	// Overtime: BS called on the fibber, after that many declarations.
	caught?: { desk: Desk; after: number };
	// Overtime: hints that pointed at calling BS. Kept off the fibber's tile and
	// square, where they would give the fibber away in a shared result.
	fibberHint?: 1 | 2;
	// Set by the first declaration or hint; the clock holds at 00:00 until then.
	startedAt?: number;
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
	// The log entry being read, by who said it: their tile is highlighted.
	reading?: Desk;
};

export type Action =
	| { type: "selected"; desk: Desk }
	| { type: "sent"; at: number }
	| { type: "accepted"; reveal: Reveal; at: number }
	| { type: "rejected"; desk: Desk; state: State }
	| { type: "caught"; desk: Desk; at: number }
	| { type: "complained"; desk: Desk }
	| { type: "hinted"; hint: Hint }
	| { type: "hinted-again" }
	| { type: "read"; desk: Desk }
	| { type: "dimmed"; desk: Desk }
	| { type: "failed"; error: unknown }
	| { type: "already" }
	| { type: "dismissed" }
	| { type: "shared"; copied: boolean };

const key = (date: string) => `office-bug:${date}`;

export function load(day: Day): Progress | undefined {
	try {
		const saved = JSON.parse(localStorage.getItem(key(day.date)) ?? "null");
		// Saved before hints, dimming or complaints existed: none of them yet.
		const hints = saved?.hints ?? {};
		const dimmed = saved?.dimmed ?? [];
		const complaints = saved?.complaints ?? [];
		// ponytail: shape check only; a full schema check if Progress ever changes shape.
		const fits =
			saved?.reveals?.[0]?.desk === day.start.desk &&
			Array.isArray(saved.masks) &&
			(saved.startedAt === undefined || typeof saved.startedAt === "number") &&
			typeof hints === "object" &&
			!Array.isArray(hints) &&
			Array.isArray(dimmed) &&
			Array.isArray(complaints);
		return fits ? { ...saved, hints, dimmed, complaints } : undefined;
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

export function start(day: Day): Game {
	const progress = load(day) ?? {
		reveals: [day.start],
		masks: [],
		hints: {},
		dimmed: [],
		complaints: [],
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
	const steps: Declaration[] = progress.reveals
		.slice(1)
		.map(({ desk, state }) => ({ desk, state }));
	const { caught } = progress;
	if (caught)
		steps.splice(caught.after, 0, { desk: caught.desk, state: "fibber" });
	return steps;
}

/** Everyone declared and, on Overtime, BS called on the fibber. */
export function solved(day: Day, progress: Progress): boolean {
	const everyone = progress.reveals.length === day.coworkers.length;
	return everyone && (!day.overtime || progress.caught !== undefined);
}

/** Who BS can be called on: a revealed sick coworker who gave a clue, on Overtime,
 * while the fibber is still at large. */
export function suspect(day: Day, progress: Progress, desk: Desk): boolean {
	const reveal = revealOf(progress, desk);
	return (
		day.overtime &&
		!progress.caught &&
		reveal?.state === "sick" &&
		reveal.kind === "clue"
	);
}

export function elapsed(progress: Progress, now: number): number {
	if (progress.startedAt === undefined) return 0;
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

// What a coworker says back when BS is called on them too soon or wrongly: put out,
// but never a denial, since an early call on the real fibber gets one too. Like a
// remark, it never hints whether the call was wrong or only early.
// Drafted with AI, edited by a human.
export const COMPLAINTS = [
	"Prove it.",
	"You'll need more than that.",
	"Bold accusation. Got anything to back it up?",
	"I'm putting in a formal complaint.",
	"Come back when you've done your homework.",
	"That's a serious thing to say without evidence.",
	"I'll be speaking to HR about this.",
	"On a weekend, and with no evidence. Charming.",
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

/** Every coworker who wears a mask, made a complaint or carries a hint, and any
 * hint toward calling BS. */
function marks(progress: Progress): Set<string> {
	return new Set([
		...progress.masks,
		...progress.complaints,
		...Object.keys(progress.hints),
		...(progress.fibberHint ? ["BS"] : []),
	]);
}

/** A hint's mark, keeping the stronger: on the coworker, or, when it points at
 * calling BS on someone already revealed, off the board. */
function marked(progress: Progress, desk: Desk, presses: 1 | 2): Progress {
	if (revealOf(progress, desk)) {
		return {
			...progress,
			fibberHint: Math.max(progress.fibberHint ?? 0, presses) as 1 | 2,
		};
	}
	const hints = {
		...progress.hints,
		[desk]: Math.max(progress.hints[desk] ?? 0, presses) as 1 | 2,
	};
	return { ...progress, hints };
}

export function verdict(progress: Progress, date: string): string {
	const n = marks(progress).size;
	const tier = n === 0 ? 0 : n <= 3 ? 1 : 2;
	return pick([...VERDICTS[tier]], date, tier);
}

// A complaint, in the result and on the tile.
export const COMPLAINT = "💢";

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
	const overtime = day.overtime ? " · Overtime" : "";
	const time = formatTime(elapsed(progress, 0));
	const squares = day.coworkers.map((c) => square(progress, c.desk));
	const rows = Array.from({ length: squares.length / 4 }, (_, r) =>
		squares.slice(r * 4, (r + 1) * 4).join(""),
	);
	// The fibber and complaints never go in the grid: BS is only called on someone
	// sick, so a square would give the day away.
	const n = progress.complaints.length;
	const hinted =
		progress.fibberHint === 2 ? " 🟠" : progress.fibberHint ? " 🟡" : "";
	const fibber = `🤥 Fibber caught${hinted} · ${COMPLAINT} ${n} complaint${n === 1 ? "" : "s"}`;
	return [
		`Office Lurgy${overtime} · ${dayLabel(day.date)}${difficulty} · ⏱ ${time}`,
		`"${verdict(progress, day.date)}"`,
		...rows,
		...(day.overtime ? [fibber] : []),
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

/** What the office says when a request fails: wait if it was over the limit. */
export function failure(error: unknown): string {
	if (!(error instanceof Busy)) return "Couldn't reach the office, try again.";
	const wait = `${error.seconds} second${error.seconds === 1 ? "" : "s"}`;
	return `Steady on, the whole office is asking at once. Try again in ${wait}.`;
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
		case "read":
			return {
				...game,
				reading: game.reading === action.desk ? undefined : action.desk,
			};
		case "dimmed": {
			const { desk } = action;
			const dimmed = progress.dimmed.includes(desk)
				? progress.dimmed.filter((d) => d !== desk)
				: [...progress.dimmed, desk];
			return { ...game, progress: { ...progress, dimmed } };
		}
		case "sent":
			return {
				...game,
				progress: { ...progress, startedAt: progress.startedAt ?? action.at },
				pending: true,
			};
		case "accepted": {
			const { reveal, at } = action;
			const reveals = [...progress.reveals, reveal];
			const name = nameOf(game, reveal.desk);
			const line = `${name} is ${reveal.state}. ${name} says: ${reveal.text}`;
			return finish(game, { ...progress, reveals }, reveal.desk, line, at);
		}
		case "caught": {
			const { desk, at } = action;
			const caught = { desk, after: progress.reveals.length - 1 };
			const name = nameOf(game, desk);
			const line = progress.complaints.includes(desk)
				? `BS called again, and this time it sticks: ${name} was the fibber.`
				: `BS called! ${name} was the fibber: their clue was a lie.`;
			return finish(game, { ...progress, caught }, desk, line, at);
		}
		case "complained": {
			const { desk } = action;
			const complaints = progress.complaints.includes(desk)
				? progress.complaints
				: [...progress.complaints, desk];
			const complaint = pick(COMPLAINTS, game.day.date, desk, game.said);
			return answer(
				{ ...game, progress: { ...progress, complaints } },
				`Not enough evidence. ${nameOf(game, desk)} says: “${complaint}”`,
			);
		}
		case "rejected": {
			const { desk, state } = action;
			const masks = progress.masks.includes(desk)
				? progress.masks
				: [...progress.masks, desk];
			// Only what the player did goes into the hash, never whether it was wrong.
			// `said` moves on with every move, so trying again gets a new remark.
			const remark = pick(REMARKS, game.day.date, desk, state, game.said);
			return answer(
				{ ...game, progress: { ...progress, masks } },
				`Not enough evidence. ${nameOf(game, desk)} says: “${remark}”`,
			);
		}
		case "hinted": {
			const { hint } = action;
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
					progress: marked(progress, hint.coworker, 1),
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
					progress: marked(progress, hint.coworker, 2),
				},
				revealOf(progress, hint.coworker)
					? `${taunt} Those clues catch ${nameOf(game, hint.coworker)} lying.`
					: `${taunt} Those clues settle ${nameOf(game, hint.coworker)}.`,
			);
		}
		case "failed":
			return answer(game, failure(action.error));
		case "dismissed":
			return { ...game, message: "" };
		case "already":
			return say(game, "Already declared.");
		case "shared":
			return say(
				game,
				action.copied ? "Result copied." : "Couldn't copy the result.",
			);
	}
}

/** An accepted move: say it, close any hint about them, and stop the clock if
 * that solved the day. */
function finish(
	game: Game,
	progress: Progress,
	desk: Desk,
	line: string,
	at: number,
): Game {
	const done = solved(game.day, progress);
	const next = done ? { ...progress, solvedAt: at } : progress;
	const hint = game.hint?.coworker === desk ? undefined : game.hint;
	return answer(
		{ ...game, progress: next, hint },
		done
			? `${line} ${verdict(next, game.day.date)} Office cleared in ${formatTime(elapsed(next, at))}.`
			: line,
	);
}

function nameOf(game: Game, desk: Desk): string | undefined {
	return game.day.coworkers.find((c) => c.desk === desk)?.name;
}
