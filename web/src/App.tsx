import { useEffect, useState } from "react";
import { fetchDay } from "./api.ts";
import type { Day } from "./game.ts";
import { Play } from "./Play.tsx";

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

	if (day === undefined) return <p className="notice">Opening the office…</p>;
	if (day === "missing")
		return <p className="notice">No puzzle for that day yet.</p>;
	if (day === "offline")
		return <p className="notice">Couldn't reach the office, try again.</p>;
	return <Play day={day} />;
}
