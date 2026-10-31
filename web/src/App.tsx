import { type ReactNode, useEffect, useState } from "react";
import { fetchDay } from "./api.ts";
import { type Day, dayLabel, failure } from "./game.ts";
import { Logo, Play } from "./Play.tsx";

/** The player's local date as YYYY-MM-DD. */
export function localToday(now = new Date()): string {
	const pad = (n: number) => String(n).padStart(2, "0");
	return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** Monday to Sunday of the Week a date is in: Saturday and Sunday are Overtime. */
export function weekOf(date: string): string[] {
	const [year = 0, month = 1, day = 1] = date.split("-").map(Number);
	const monday = day - ((new Date(year, month - 1, day).getDay() + 6) % 7);
	return [0, 1, 2, 3, 4, 5, 6].map((i) =>
		localToday(new Date(year, month - 1, monday + i)),
	);
}

export function App() {
	// ponytail: a tab left open past midnight keeps yesterday's strip until
	// reloaded; add a midnight timeout if players notice.
	const [now] = useState(() => new Date());
	const [day, setDay] = useState<Day | "missing" | { failed: string }>();
	const today = localToday(now);
	const days = weekOf(today);
	const asked = new URLSearchParams(location.search).get("day");
	const date = asked ?? today;
	// Only the Week of the player's own date, up to today: the server allows a day
	// either side for timezones, so a later day may exist without being open here.
	const open = days.includes(date) && date <= today;

	useEffect(() => {
		if (!open) return;
		fetchDay(date).then(
			(found) => setDay(found ?? "missing"),
			(error) => setDay({ failed: failure(error) }),
		);
	}, [date, open]);

	const week = <Week days={days} today={today} current={date} />;
	return (
		<>
			{!open ? (
				<Notice week={week}>
					That day isn't open: the office only does this week's puzzles, up to
					today.
				</Notice>
			) : day === "missing" ? (
				<Notice week={week}>
					No puzzle for that day: the office is closed for a deep clean. Back
					soon.
				</Notice>
			) : day === undefined ? (
				<Notice week={week}>Opening the office…</Notice>
			) : "failed" in day ? (
				<Notice week={week}>{day.failed}</Notice>
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

/** Monday to Sunday, each a link once it has started; the weekend is Overtime. */
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
		<nav className="week" aria-label="The week's puzzles">
			{days.map((d, i) => {
				const name = new Date(`${d}T00:00`).toLocaleDateString("en-GB", {
					weekday: "short",
				});
				const overtime = i >= 5 ? "overtime" : undefined;
				return d <= today ? (
					<a
						key={d}
						href={`?day=${d}`}
						className={overtime}
						aria-label={`${dayLabel(d)}${overtime ? ", Overtime" : ""}`}
						aria-current={d === current ? "page" : undefined}
					>
						{name}
					</a>
				) : (
					<span
						key={d}
						className={["later", overtime].filter(Boolean).join(" ")}
					>
						{name}
						<span className="sr-only">, not open yet</span>
					</span>
				);
			})}
		</nav>
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
