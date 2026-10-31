import {
	type KeyboardEvent,
	type ReactNode,
	useEffect,
	useReducer,
	useRef,
	useState,
} from "react";
import { hint as askForHint, declare as post } from "./api.ts";
import {
	type Call,
	type Day,
	type Desk,
	dayLabel,
	declared,
	elapsed,
	formatTime,
	type Progress,
	reducer,
	result,
	revealOf,
	save,
	start,
	suspect,
	verdict,
} from "./game.ts";
import { HowToPlay } from "./HowToPlay.tsx";
import "./App.css";

const COLUMNS = 4;

/** Each department's code on a tile, and its lanyard colour in the portraits. */
const DEPARTMENTS: Record<string, [code: string, colour: string]> = {
	"Customer Services": ["CS", "#C77DFF"],
	Facilities: ["FAC", "#FFB703"],
	Finance: ["FIN", "#F4A261"],
	HR: ["HR", "#2EC4B6"],
	IT: ["IT", "#00E5FF"],
	Legal: ["LGL", "#9D4EDD"],
	Marketing: ["MKT", "#FF5A5F"],
	Procurement: ["PRO", "#FB8500"],
	Reception: ["REC", "#52B788"],
	Sales: ["SAL", "#E63946"],
};

/** The tile an arrow key moves to from tile i, or undefined at an edge. */
function move(i: number, key: string, count: number): number | undefined {
	const column = i % COLUMNS;
	if (key === "ArrowLeft" && column > 0) return i - 1;
	if (key === "ArrowRight" && column < COLUMNS - 1) return i + 1;
	if (key === "ArrowUp" && i >= COLUMNS) return i - COLUMNS;
	if (key === "ArrowDown" && i < count - COLUMNS) return i + COLUMNS;
	return undefined;
}

export function Logo({ overtime = false }: { overtime?: boolean }) {
	return (
		<h1 className="logo">
			<img src="/logo.svg" alt="Office Lurgy" width="262" height="148" />
			{overtime && <span className="stamp">Overtime</span>}
		</h1>
	);
}

function Timer({ progress }: { progress: Progress }) {
	const [now, setNow] = useState(Date.now);

	// Ticks in step with the start, so the display never lags a second behind.
	useEffect(() => {
		if (progress.startedAt === undefined || progress.solvedAt !== undefined)
			return;
		const id = setInterval(() => setNow(Date.now()), 1000);
		return () => clearInterval(id);
	}, [progress.startedAt, progress.solvedAt]);

	return <span role="timer">{formatTime(elapsed(progress, now))}</span>;
}

export function Play({ day, week }: { day: Day; week: ReactNode }) {
	const [game, dispatch] = useReducer(reducer, day, start);
	const { progress, selected } = game;
	const coworkers = day.coworkers;
	const index = coworkers.findIndex((c) => c.desk === selected);
	const chosen = coworkers[index];

	useEffect(() => save(day.date, progress), [day.date, progress]);

	// The solving move unmounts the Sick/Well buttons; hand focus to Share so it
	// isn't dropped. Not on reloading a solved day.
	const shareButton = useRef<HTMLButtonElement>(null);
	const wasSolved = useRef(progress.solvedAt !== undefined);
	const board = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (progress.solvedAt === undefined || wasSolved.current) return;
		wasSolved.current = true;
		shareButton.current?.focus();
	}, [progress.solvedAt]);

	async function declare(desk: Desk, call: Call) {
		const bs = call === "fibber";
		if (bs && !suspect(day, progress, desk)) return;
		if (!bs && revealOf(progress, desk)) return dispatch({ type: "already" });
		if (game.pending) return;
		dispatch({ type: "sent", at: Date.now() });
		try {
			const reveal = await post({
				date: day.date,
				declared: declared(progress),
				declaration: { desk, state: call },
			});
			const at = Date.now();
			dispatch(
				call === "fibber"
					? reveal
						? { type: "caught", desk, at }
						: { type: "complained", desk }
					: reveal
						? { type: "accepted", reveal, at }
						: { type: "rejected", desk, state: call },
			);
		} catch (error) {
			dispatch({ type: "failed", error });
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
		dispatch({ type: "sent", at: Date.now() });
		try {
			dispatch({
				type: "hinted",
				hint: await askForHint({
					date: day.date,
					declared: declared(progress),
				}),
			});
		} catch (error) {
			dispatch({ type: "failed", error });
		}
	}

	async function share() {
		const text = result(day, progress, location.origin);
		if (navigator.share) {
			try {
				return await navigator.share({ text });
			} catch (error) {
				// Closing the share sheet isn't a failure; anything else falls back to copying.
				// ponytail: Safari may refuse the copy once the share has failed; show the
				// text to copy by hand if players hit it.
				if (error instanceof DOMException && error.name === "AbortError")
					return;
			}
		}
		try {
			await navigator.clipboard.writeText(text);
			dispatch({ type: "shared", copied: true });
		} catch {
			dispatch({ type: "shared", copied: false });
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
		if (key === "b" && day.overtime) {
			event.preventDefault();
			declare(selected, "fibber");
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
	// They complained at an early call: calling BS on them again is still allowed.
	const again = !!chosen && progress.complaints.includes(chosen.desk);
	// Only a clue the open hint points to is spelled out, with its desks outlined.
	const explained = game.hint?.explanations.find(
		(e) => e.desk === game.reading,
	);

	return (
		<main>
			<header>
				<Logo overtime={day.overtime} />
				<div className="today">
					<p className="date">{dayLabel(day.date)}</p>
					<Timer progress={progress} />
					<HowToPlay />
				</div>
				{week}
				{day.overtime && <p className="lying">One sick coworker is lying.</p>}
			</header>

			{/* biome-ignore lint/a11y/useSemanticElements: an ARIA grid, not a data table, so screen readers pass arrows and S/W to the page */}
			<div
				ref={board}
				className="board"
				role="grid"
				aria-label="Office floor, 4 desks across, 5 rows"
				onKeyDown={onKeyDown}
			>
				{/* Column letters and row numbers sit on the edges, so tiles show faces, not coordinates. */}
				<div className="axis" aria-hidden="true">
					<span />
					{rows[0]?.map((c) => (
						<span key={c.desk}>{c.desk[0]}</span>
					))}
				</div>
				{rows.map((row) => (
					// biome-ignore lint/a11y/useSemanticElements: a row of the ARIA grid above
					// biome-ignore lint/a11y/useFocusableInteractive: a grid row only groups its cells
					<div role="row" className="row" key={row[0]?.desk}>
						<span className="axis" aria-hidden="true">
							{row[0]?.desk.slice(1)}
						</span>
						{row.map((c) => {
							const reveal = revealOf(progress, c.desk);
							const masked = progress.masks.includes(c.desk);
							const complained = progress.complaints.includes(c.desk);
							const caught = progress.caught?.desk === c.desk;
							const hints = progress.hints[c.desk];
							const lit = game.hint?.clues.includes(c.desk);
							const named =
								game.hint?.presses === 2 && game.hint.coworker === c.desk;
							const speaker = game.reading === c.desk;
							const inClue = explained?.desks.includes(c.desk);
							const [code, colour] = DEPARTMENTS[c.department] ?? [
								c.department.slice(0, 3).toUpperCase(),
								"var(--line)",
							];
							const label = [
								c.desk,
								c.name,
								c.department,
								reveal?.state ?? "unknown",
								...(masked ? ["wearing a mask"] : []),
								...(complained ? ["made a complaint"] : []),
								...(caught ? ["caught as the fibber"] : []),
								...(hints ? [hints === 1 ? "one hint" : "two hints"] : []),
								...(lit ? ["hinted clue"] : []),
								...(named ? ["the hint is about them"] : []),
								...(speaker ? ["said the clue you're reading"] : []),
								...(inClue ? ["in the clue you're reading"] : []),
								...(reveal ? [`says: ${reveal.text}`] : []),
							].join(", ");
							return (
								// biome-ignore lint/a11y/useSemanticElements: a cell of the ARIA grid above
								<button
									type="button"
									key={c.desk}
									data-desk={c.desk}
									className={`tile ${reveal ? `st-${reveal.state}` : ""} ${complained ? "complained" : ""} ${lit ? "hint-clue" : ""} ${named ? "hint-named" : ""} ${speaker ? "speaker" : ""} ${inClue ? "in-clue" : ""}`}
									tabIndex={c.desk === selected ? 0 : -1}
									role="gridcell"
									aria-keyshortcuts={day.overtime ? "S W B" : "S W"}
									aria-selected={c.desk === selected}
									aria-label={label}
									onClick={() => dispatch({ type: "selected", desk: c.desk })}
								>
									<img
										className="portrait"
										src={`/portraits/${c.name.toLowerCase()}.svg`}
										alt=""
									/>
									{/* A complaint flushes the face red, under any mask. */}
									{complained && <span className="flush" aria-hidden="true" />}
									{masked && (
										<img
											className="portrait mask"
											src="/portraits/mask.svg"
											alt=""
										/>
									)}
									{caught && (
										<span className="stamp" aria-hidden="true">
											BS
										</span>
									)}
									<span className="nm" style={{ borderColor: colour }}>
										<span className="name">{c.name}</span>
										<span className="dept">{code}</span>
									</span>
									{reveal && <span className="state">{reveal.state}</span>}
									{hints && (
										<span className="marks" aria-hidden="true">
											<span className="mark">{hints === 1 ? "🟡" : "🟠"}</span>
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
				{progress.reveals.toReversed().map((r) => {
					const dimmed = progress.dimmed.includes(r.desk);
					const lie = progress.caught?.desk === r.desk;
					const classes = [
						game.hint?.clues.includes(r.desk) && "hinted",
						game.reading === r.desk && "reading",
						dimmed && "dimmed",
						lie && "lie",
					].filter(Boolean);
					return (
						<li key={r.desk} className={classes.join(" ") || undefined}>
							<button
								type="button"
								className="entry"
								aria-pressed={game.reading === r.desk}
								aria-describedby={
									explained?.desk === r.desk && explained.explanation
										? `explain-${r.desk}`
										: undefined
								}
								onClick={() => dispatch({ type: "read", desk: r.desk })}
							>
								<span className="who">
									{nameOf(r.desk)} · {r.desk} · {r.state}
								</span>
								{lie ? (
									<>
										<s>{r.text}</s>
										<span className="plain">A lie: BS called.</span>
									</>
								) : (
									<span>{r.text}</span>
								)}
								{r.joke && <span className="joke">{r.joke}</span>}
								{r.kind === "flavour" && (
									<span className="plain">Flavour: no clue.</span>
								)}
							</button>
							<button
								type="button"
								className="dim"
								aria-pressed={dimmed}
								aria-label={`Dim ${nameOf(r.desk)}'s ${r.kind === "clue" ? "clue" : "message"}`}
								onClick={() => dispatch({ type: "dimmed", desk: r.desk })}
							>
								Dim
							</button>
							{explained?.desk === r.desk && explained.explanation && (
								<p className="explain" id={`explain-${r.desk}`}>
									{explained.explanation}
								</p>
							)}
						</li>
					);
				})}
			</ul>

			<div className="thumb">
				<div className="message">
					<p className="toast" role="status">
						<span key={game.said}>{game.message}</span>
					</p>
					{/* Outside the live region, so it isn't read out with every message. */}
					{game.message && (
						<button
							type="button"
							className="dismiss"
							aria-label="Dismiss message"
							onClick={() => {
								dispatch({ type: "dismissed" });
								// The button goes with the message; focus the selected desk, not the page.
								board.current
									?.querySelector<HTMLElement>('[tabindex="0"]')
									?.focus();
							}}
						>
							×
						</button>
					)}
				</div>
				{progress.solvedAt !== undefined ? (
					<div className="result">
						<p className="verdict">{verdict(progress, day.date)}</p>
						<button
							type="button"
							className="btn-share"
							ref={shareButton}
							onClick={share}
						>
							Share
						</button>
					</div>
				) : (
					<>
						{chosen && (
							<span className="who">
								{chosen.desk} · {chosen.name} · {chosen.department}
								{revealOf(progress, chosen.desk) && " · Already declared"}
							</span>
						)}
						{/* Beside the chosen coworker, so the bar is two rows and the log gets the room. */}
						<button
							type="button"
							className="btn-hint"
							disabled={game.pending || game.hint?.presses === 2}
							onClick={hint}
						>
							{game.hint ? "Who do they settle?" : "Hint"}
						</button>
						{chosen && suspect(day, progress, chosen.desk) && (
							<div className="big">
								{/* In place of the spent Sick and Well: calling BS on them. */}
								<button
									type="button"
									className="btn-bs"
									disabled={game.pending}
									aria-label={`Call BS ${again ? "again " : ""}on ${chosen.name}`}
									aria-keyshortcuts="B"
									onClick={() => declare(chosen.desk, "fibber")}
								>
									{again ? "BS again" : "BS"}
								</button>
							</div>
						)}
						{chosen && !suspect(day, progress, chosen.desk) && (
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
						)}
					</>
				)}
			</div>
		</main>
	);
}
