import { type ReactNode, useEffect, useState } from "react";
import { fetchDay } from "./api.ts";
import type { Day } from "./game.ts";
import { Logo, Play } from "./Play.tsx";

/** The player's local date as YYYY-MM-DD. */
export function localToday(now = new Date()): string {
	const pad = (n: number) => String(n).padStart(2, "0");
	return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** Monday to Friday of the Week a date is in; at the weekend, the Week just ended. */
export function weekOf(date: string): string[] {
	const [year = 0, month = 1, day = 1] = date.split("-").map(Number);
	const monday = day - ((new Date(year, month - 1, day).getDay() + 6) % 7);
	return [0, 1, 2, 3, 4].map((i) =>
		localToday(new Date(year, month - 1, monday + i)),
	);
}

/** Local midnight at the start of the coming Monday (only asked at the weekend). */
export function nextMonday(now: Date): Date {
	const days = (8 - now.getDay()) % 7;
	return new Date(now.getFullYear(), now.getMonth(), now.getDate() + days);
}

/** "47:59:59": hours, minutes and seconds left, rounded up. */
export function countdown(ms: number): string {
	const seconds = Math.max(0, Math.ceil(ms / 1000));
	const pad = (n: number) => String(n).padStart(2, "0");
	return `${pad(Math.floor(seconds / 3600))}:${pad(Math.floor(seconds / 60) % 60)}:${pad(seconds % 60)}`;
}

export function App() {
	const [now, setNow] = useState(() => new Date());
	const [day, setDay] = useState<Day | "missing" | "offline">();
	const today = localToday(now);
	const days = weekOf(today);
	const asked = new URLSearchParams(location.search).get("day");
	const date = asked ?? today;
	// Only the Week of the player's own date, up to today: the server allows a day
	// either side for timezones, so a later day may exist without being open here.
	const open = days.includes(date) && date <= today;
	const weekend = asked === null && !days.includes(today);

	useEffect(() => {
		if (!open) return;
		fetchDay(date).then(
			(found) => setDay(found ?? "missing"),
			() => setDay("offline"),
		);
	}, [date, open]);

	const week = <Week days={days} today={today} current={date} />;
	return (
		<>
			{weekend ? (
				<Closed week={week} onOpen={() => setNow(new Date())} />
			) : !open || day === "missing" ? (
				<Notice week={week}>
					No puzzle for that day: the office is closed for a deep clean. Back
					soon.
				</Notice>
			) : day === undefined ? (
				<Notice week={week}>Opening the office…</Notice>
			) : day === "offline" ? (
				<Notice week={week}>Couldn't reach the office, try again.</Notice>
			) : (
				<Play day={day} week={week} />
			)}
			<footer>
				Built with{" "}
				<span role="img" aria-label="love">
					♥
				</span>{" "}
				by <a href="https://caffeinated.systems">Caffeinated Systems</a>
				<span aria-hidden="true"> · </span>
				Also from Caffeinated Systems:{" "}
				<a href="https://wordis.caffeinated.systems">Wordis</a>
			</footer>
		</>
	);
}

/** Monday to Friday, each a link once it has started. */
function Week({
	days,
	today,
	current,
}: {
	days: string[];
	today: string;
	current: string;
}) {
	return (
		<nav className="week" aria-label="This week">
			{days.map((d) => {
				const name = new Date(`${d}T00:00`).toLocaleDateString("en-GB", {
					weekday: "short",
				});
				return d <= today ? (
					<a
						key={d}
						href={`?day=${d}`}
						aria-current={d === current ? "page" : undefined}
					>
						{name}
					</a>
				) : (
					<span key={d} aria-disabled="true">
						{name}
					</span>
				);
			})}
		</nav>
	);
}

/** The weekend: a countdown to Monday, then onOpen. */
function Closed({ week, onOpen }: { week: ReactNode; onOpen: () => void }) {
	const [opens] = useState(() => nextMonday(new Date()).getTime());
	const [now, setNow] = useState(Date.now);

	useEffect(() => {
		const id = setInterval(() => {
			const at = Date.now();
			setNow(at);
			if (at >= opens) onOpen();
		}, 1000);
		return () => clearInterval(id);
	}, [opens, onOpen]);

	return (
		<main className="notice">
			<Logo />
			<p>
				Office closed for the weekend. Missed a day? This week's puzzles are
				still on the desk.
			</p>
			{week}
			<p>
				Back Monday in <span role="timer">{countdown(opens - now)}</span>
			</p>
		</main>
	);
}

function Notice({ children, week }: { children: string; week: ReactNode }) {
	return (
		<main className="notice">
			<Logo />
			<p>{children}</p>
			{week}
		</main>
	);
}
