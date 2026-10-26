import { useEffect, useState } from "react";
import { fetchDay } from "./api.ts";
import type { Day } from "./game.ts";
import { Logo, Play } from "./Play.tsx";

/** The player's local date as YYYY-MM-DD. */
export function localToday(now = new Date()): string {
	const pad = (n: number) => String(n).padStart(2, "0");
	return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

export function App() {
	const [day, setDay] = useState<Day | "missing" | "offline">();

	useEffect(() => {
		// ponytail: ?day= stands in for the weekly schedule until #32.
		const date =
			new URLSearchParams(location.search).get("day") ?? localToday();
		fetchDay(date).then(
			(found) => setDay(found ?? "missing"),
			() => setDay("offline"),
		);
	}, []);

	return (
		<>
			{day === undefined ? (
				<Notice>Opening the office…</Notice>
			) : day === "missing" ? (
				<Notice>
					No puzzle for that day: the office is closed for a deep clean. Back
					soon.
				</Notice>
			) : day === "offline" ? (
				<Notice>Couldn't reach the office, try again.</Notice>
			) : (
				<Play day={day} />
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

function Notice({ children }: { children: string }) {
	return (
		<main className="notice">
			<Logo />
			<p>{children}</p>
		</main>
	);
}
