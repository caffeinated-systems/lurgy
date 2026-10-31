import { useRef } from "react";

/** A Help button and the panel it opens over whatever is on screen. */
export function HowToPlay() {
	const dialog = useRef<HTMLDialogElement>(null);
	return (
		<>
			<button
				type="button"
				className="btn-help"
				onClick={() => dialog.current?.showModal()}
			>
				Help
			</button>
			<dialog ref={dialog} className="help" aria-labelledby="help-title">
				{/* A dialog form closes the dialog natively, as Esc does. */}
				<form method="dialog">
					<button type="submit" className="btn-hint">
						Close
					</button>
				</form>
				<h2 id="help-title">How to play</h2>
				<div className="help-columns">
					<section>
						<p>
							Something's going round the office. As office manager, work out
							who's caught the lurgy and who's fine, using only what your
							coworkers let slip. A new puzzle every day, and the week's puzzles
							stay on the desk till Sunday.
						</p>
						<ul>
							<li>Pick a coworker and declare them Sick or Well.</li>
							<li>
								A declaration only goes through when the clues so far force it:
								every board that fits what you know agrees. Otherwise it's "Not
								enough evidence" and they put on a mask, whether you were wrong
								or just early.
							</li>
							<li>
								Each coworker you declare says something: a clue, or just chat
								marked "Flavour: no clue". Every clue is true, whoever says it,
								except on Overtime.
							</li>
							<li>
								Tap a clue to see who said it. Dim a clue once you've used it
								up.
							</li>
							<li>
								Stuck? Hint shows the fewest clues that settle someone; press
								again to see who.
							</li>
							<li>
								The timer starts at your first declaration or hint. Masks and
								hints show in your result.
							</li>
							<li>
								Each tile shows the coworker's department code and colour.
							</li>
						</ul>

						<h3>Overtime</h3>
						<p>
							At the weekend the office does overtime, and one sick coworker has
							come in anyway for the double pay: the fibber. Their clue is
							false; everyone else, sick or well, tells the truth. Until you
							catch them, any sick coworker's clue could be the lie.
						</p>
						<ul>
							<li>
								Once the clues prove which sick coworker is lying, pick them and
								call BS. Call it too soon, or on the wrong person, and they make
								a complaint instead.
							</li>
							<li>
								The puzzle is solved when everyone is declared and you've called
								BS on the fibber. Your result counts complaints but never says
								who.
							</li>
						</ul>

						<h3>Keys</h3>
						<p>
							Arrow keys move between desks. S declares sick, W declares well,
							and on Overtime B calls BS.
						</p>

						<h3>About</h3>
						<p>
							Your progress stays in this browser; there are no accounts. Fonts:
							Poppins and DSEG7, both under the SIL Open Font License.
						</p>
					</section>
					<section>
						<h3>Reading the clues</h3>
						<dl>
							<dt>Row, column</dt>
							<dd>
								Rows are numbered 1 to 5 down the side, columns A to D along the
								top.
							</dd>
							<dt>Neighbours</dt>
							<dd>
								The desks touching theirs, diagonals included: up to eight.
							</dd>
							<dt>Between</dt>
							<dd>
								The desks in a straight line between two coworkers, not counting
								the two themselves.
							</dd>
							<dt>Above, below, left, right</dt>
							<dd>
								Anywhere in that column or row as you look at the board, not
								just next door. "Directly" means only the next desk.
							</dd>
							<dt>Corners, edges</dt>
							<dd>
								The four corner desks; every desk round the outside, corners
								included.
							</dd>
							<dt>Department</dt>
							<dd>Everyone with that department's code and colour.</dd>
							<dt>Connected</dt>
							<dd>
								One unbroken chain of desks touching side to side, never
								diagonally. A single coworker counts as connected.
							</dd>
							<dt>Most</dt>
							<dd>
								More than every other row, column or department, with no ties.
							</dd>
							<dt>One of the</dt>
							<dd>
								That coworker and at least one other. With a number, "one of two
								sick people", exactly that many, them included.
							</dd>
						</dl>
						<p>
							For example, if B2 says "Two people among my neighbours are sick",
							then of A1, B1, C1, A2, C2, A3, B3 and C3, exactly two are sick
							and six are well.
						</p>
					</section>
				</div>
			</dialog>
		</>
	);
}
