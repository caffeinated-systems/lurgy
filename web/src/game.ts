import type { components } from "./api/schema";

type Schemas = components["schemas"];
export type Desk = Schemas["Desk"];
export type State = Schemas["State"];
export type Declaration = Schemas["Declaration"];
export type Reveal = Schemas["RevealedCoworker"];
export type Day = Schemas["DayResponse"];

/** What the browser keeps for a day: enough to rebuild the board and the timer. */
export type Progress = {
	reveals: Reveal[];
	mistakes: Desk[];
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
};

export type Action =
	| { type: "selected"; desk: Desk }
	| { type: "accepted"; reveal: Reveal; at: number }
	| { type: "rejected"; desk: Desk }
	| { type: "failed" };

const key = (date: string) => `office-bug:${date}`;

export function load(date: string): Progress | undefined {
	try {
		const saved = JSON.parse(localStorage.getItem(key(date)) ?? "null");
		// ponytail: shape check only; a full schema check if Progress ever changes shape.
		return Array.isArray(saved?.reveals) ? saved : undefined;
	} catch {
		return undefined;
	}
}

export function save(date: string, progress: Progress): void {
	try {
		localStorage.setItem(key(date), JSON.stringify(progress));
	} catch {
		// Storage blocked or full: the game still plays, it just won't survive a reload.
	}
}

export function start(day: Day, now: number): Game {
	const progress = load(day.date) ?? {
		reveals: [day.start],
		mistakes: [],
		startedAt: now,
	};
	const hidden = day.coworkers.find((c) => !revealOf(progress, c.desk));
	return {
		day,
		progress,
		selected: hidden?.desk ?? day.start.desk,
		message: "",
		said: 0,
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

function say(game: Game, message: string): Game {
	return { ...game, message, said: game.said + 1 };
}

export function reducer(game: Game, action: Action): Game {
	const { progress } = game;
	switch (action.type) {
		case "selected":
			return { ...game, selected: action.desk };
		case "accepted": {
			const { reveal, at } = action;
			if (revealOf(progress, reveal.desk)) return game;
			const reveals = [...progress.reveals, reveal];
			const solved = reveals.length === game.day.coworkers.length;
			const next = {
				...progress,
				reveals,
				...(solved && { solvedAt: at }),
			};
			const name = game.day.coworkers.find((c) => c.desk === reveal.desk)?.name;
			const line = `${name} is ${reveal.state}. ${name} says: ${reveal.text}`;
			return say(
				{ ...game, progress: next },
				solved
					? `${line} Office cleared in ${formatTime(elapsed(next, at))}.`
					: line,
			);
		}
		case "rejected": {
			const mistakes = progress.mistakes.includes(action.desk)
				? progress.mistakes
				: [...progress.mistakes, action.desk];
			return say(
				{ ...game, progress: { ...progress, mistakes } },
				"Not enough evidence.",
			);
		}
		case "failed":
			return say(game, "Couldn't reach the office, try again.");
	}
}
