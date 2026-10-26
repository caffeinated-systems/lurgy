import { type KeyboardEvent, useEffect, useReducer, useState } from "react";
import { hint as askForHint, declare as post } from "./api.ts";
import {
	type Day,
	type Desk,
	declared,
	elapsed,
	formatTime,
	type Progress,
	reducer,
	revealOf,
	type State,
	save,
	start,
} from "./game.ts";
import "./App.css";

const COLUMNS = 4;

/** The tile an arrow key moves to from tile i, or undefined at an edge. */
function move(i: number, key: string, count: number): number | undefined {
	const column = i % COLUMNS;
	if (key === "ArrowLeft" && column > 0) return i - 1;
	if (key === "ArrowRight" && column < COLUMNS - 1) return i + 1;
	if (key === "ArrowUp" && i >= COLUMNS) return i - COLUMNS;
	if (key === "ArrowDown" && i < count - COLUMNS) return i + COLUMNS;
	return undefined;
}

export function Logo() {
	return (
		<h1 className="logo">
			<img src="/logo.svg" alt="Office Lurgy" width="262" height="148" />
		</h1>
	);
}

function Timer({ progress }: { progress: Progress }) {
	const [now, setNow] = useState(Date.now);

	useEffect(() => {
		if (progress.solvedAt !== undefined) return;
		const id = setInterval(() => setNow(Date.now()), 1000);
		return () => clearInterval(id);
	}, [progress.solvedAt]);

	return <span role="timer">⏱ {formatTime(elapsed(progress, now))}</span>;
}

export function Play({ day }: { day: Day }) {
	const [game, dispatch] = useReducer(reducer, day, (d) =>
		start(d, Date.now()),
	);
	const { progress, selected } = game;
	const coworkers = day.coworkers;
	const index = coworkers.findIndex((c) => c.desk === selected);
	const chosen = coworkers[index];

	useEffect(() => save(day.date, progress), [day.date, progress]);

	async function declare(desk: Desk, state: State) {
		if (revealOf(progress, desk)) return dispatch({ type: "already" });
		if (game.pending) return;
		dispatch({ type: "sent" });
		try {
			const reveal = await post({
				date: day.date,
				declared: declared(progress),
				declaration: { desk, state },
			});
			dispatch(
				reveal
					? { type: "accepted", reveal, at: Date.now() }
					: { type: "rejected", desk, state },
			);
		} catch {
			dispatch({ type: "failed" });
		}
	}

	async function hint() {
		if (game.hint) {
			dispatch({ type: "hinted-again" });
			// The button disables itself, so focus goes to the coworker, ready for S or W.
			document
				.querySelector<HTMLElement>(`[data-desk="${game.hint.coworker}"]`)
				?.focus();
			return;
		}
		dispatch({ type: "sent" });
		try {
			dispatch({
				type: "hinted",
				hint: await askForHint({
					date: day.date,
					declared: declared(progress),
				}),
			});
		} catch {
			dispatch({ type: "failed" });
		}
	}

	function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
		if (event.ctrlKey || event.metaKey || event.altKey) return;
		const key = event.key.toLowerCase();
		if (key === "s" || key === "w") {
			event.preventDefault();
			declare(selected, key === "s" ? "sick" : "well");
			return;
		}
		const next = coworkers[move(index, event.key, coworkers.length) ?? -1];
		if (!next) return;
		event.preventDefault();
		dispatch({ type: "selected", desk: next.desk });
		event.currentTarget
			.querySelector<HTMLElement>(`[data-desk="${next.desk}"]`)
			?.focus();
	}

	const rows = Array.from({ length: coworkers.length / COLUMNS }, (_, r) =>
		coworkers.slice(r * COLUMNS, (r + 1) * COLUMNS),
	);
	const nameOf = (desk: Desk) => coworkers.find((c) => c.desk === desk)?.name;

	return (
		<main>
			<header>
				<Logo />
				<div className="today">
					<p className="date">
						{new Date(`${day.date}T00:00`).toLocaleDateString("en-GB", {
							weekday: "short",
							day: "numeric",
							month: "short",
						})}
					</p>
					<Timer progress={progress} />
				</div>
			</header>

			{/* biome-ignore lint/a11y/useSemanticElements: an ARIA grid, not a data table, so screen readers pass arrows and S/W to the page */}
			<div
				className="board"
				role="grid"
				aria-label="Office floor, 4 desks across, 5 rows"
				onKeyDown={onKeyDown}
			>
				{rows.map((row) => (
					// biome-ignore lint/a11y/useSemanticElements: a row of the ARIA grid above
					// biome-ignore lint/a11y/useFocusableInteractive: a grid row only groups its cells
					<div role="row" className="row" key={row[0]?.desk}>
						{row.map((c) => {
							const reveal = revealOf(progress, c.desk);
							const masked = progress.masks.includes(c.desk);
							const hints = progress.hints[c.desk];
							const lit = game.hint?.clues.includes(c.desk);
							const named =
								game.hint?.presses === 2 && game.hint.coworker === c.desk;
							const label = [
								c.desk,
								c.name,
								c.department,
								reveal?.state ?? "unknown",
								...(masked ? ["wearing a mask"] : []),
								...(hints ? [hints === 1 ? "one hint" : "two hints"] : []),
								...(lit ? ["hinted clue"] : []),
								...(named ? ["the hint is about them"] : []),
								...(reveal ? [`says: ${reveal.text}`] : []),
							].join(", ");
							return (
								// biome-ignore lint/a11y/useSemanticElements: a cell of the ARIA grid above
								<button
									type="button"
									key={c.desk}
									data-desk={c.desk}
									className={`tile ${reveal ? `st-${reveal.state}` : ""} ${lit ? "hint-clue" : ""} ${named ? "hint-named" : ""}`}
									tabIndex={c.desk === selected ? 0 : -1}
									role="gridcell"
									aria-keyshortcuts="S W"
									aria-selected={c.desk === selected}
									aria-label={label}
									onClick={() => dispatch({ type: "selected", desk: c.desk })}
								>
									<span className="coord">{c.desk}</span>
									<span className="nm">{c.name}</span>
									{reveal && <span className="state">{reveal.state}</span>}
									{masked && (
										<span className="mask" aria-hidden="true">
											😷
										</span>
									)}
									{hints && (
										<span className="mark" aria-hidden="true">
											{hints === 1 ? "🟡" : "🟠"}
										</span>
									)}
								</button>
							);
						})}
					</div>
				))}
			</div>

			<h2 className="log-title">Clues, newest first</h2>
			<ul className="log">
				{progress.reveals.toReversed().map((r) => (
					<li
						key={r.desk}
						className={game.hint?.clues.includes(r.desk) ? "hinted" : undefined}
					>
						<span className="who">
							{nameOf(r.desk)} · {r.desk} · {r.state}
						</span>
						<span>{r.text}</span>
						{r.joke && <span className="joke">{r.joke}</span>}
						{r.kind === "flavour" && (
							<span className="plain">Flavour: no clue.</span>
						)}
					</li>
				))}
			</ul>

			<div className="thumb">
				<p className="toast" role="status">
					<span key={game.said}>{game.message}</span>
				</p>
				{chosen && (
					<>
						<span className="who">
							{chosen.desk} · {chosen.name} · {chosen.department}
							{revealOf(progress, chosen.desk) && " · Already declared"}
						</span>
						<div className="big">
							{(["sick", "well"] as const).map((state) => (
								<button
									type="button"
									key={state}
									className={`btn-${state}`}
									disabled={game.pending || !!revealOf(progress, chosen.desk)}
									aria-label={`Declare ${chosen.name} ${state}`}
									onClick={() => declare(chosen.desk, state)}
								>
									{state === "sick" ? "Sick" : "Well"}
								</button>
							))}
						</div>
					</>
				)}
				<button
					type="button"
					className="btn-hint"
					disabled={
						game.pending ||
						progress.solvedAt !== undefined ||
						game.hint?.presses === 2
					}
					onClick={hint}
				>
					{game.hint ? "Who do they settle?" : "Hint"}
				</button>
			</div>
		</main>
	);
}
