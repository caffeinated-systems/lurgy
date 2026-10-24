# How Clues by Sam plays

Research for [#3](https://github.com/da-mask/sam_game/issues/3). Checked against cluesbysam.com on 2026-10-24.

The original game talks about **suspects**, who are **criminal** or **innocent** and have a **profession**. Our equivalents (see `GLOSSARY.md`) are **coworker**, **sick** / **well** and **department**. This note uses the original's terms, with ours in brackets where it helps.

## Sources and confidence

| Tag | Source | Trust |
|---|---|---|
| [help] | The "How to play" text on the [cluesbysam.com](https://cluesbysam.com/) home page and in the [tutorial](https://cluesbysam.com/s/tutorial/) | Primary |
| [client] | The game's shipped JavaScript bundle (`/assets/index-*.js`). Each day's puzzle is compiled into it: grid size, cards, clue text, a clue DSL, deduction paths and hints. I read the 2026-10-23 daily and three older archive/help puzzles ([1](https://cluesbysam.com/help/827da9815a12), [2](https://cluesbysam.com/archive/04ca9487cc93/), [3](https://cluesbysam.com/help/8d9719c8dbd6)) | Primary (the code is the behaviour) |
| [packs] | [cluesbysam.com/s/packs.html](https://cluesbysam.com/s/packs.html) | Primary |
| [cbs-bench] | [Syps/cbs-bench `syntax.dsl`](https://github.com/Syps/cbs-bench/blob/main/syntax.dsl), a third-party benchmark that scrapes daily puzzles and documents the clue DSL it finds | Secondary, reverse-engineered |
| [players] | Shared results on [belgae.social](https://belgae.social/post/1989614) and lemmy.world, plus search-engine summaries of Wikipedia/EverybodyWiki (both pages were unreachable directly: 404/403) | Tertiary |

"Confirmed" means read in [help] or [client]. "Inferred" is marked as such.

## Board

- **20 suspects on a 4 × 5 grid**: 4 columns, 5 rows (`width:4,height:5` in [client]). Rows are numbered 1–5 top to bottom and columns lettered A–D left to right [help]. Some articles say "5 × 5"; that is wrong.
- **Ordered alphabetically by name**, row-major from the top left [help: "People are in alphabetical order by name"; client: alex, berat, dana, emily…]. The order is a convention that makes a name easy to find. It does not encode anything. Names are unique, so from a hint's point of view position is effectively the only identifier.
- Each card shows an emoji face, a first name and a profession [client]. A puzzle reuses a handful of professions: the 2026-10-23 puzzle has 7 across 20 cards, with 2–4 people each. The emoji table includes office-ish jobs (coder, clerk, cop, cook, judge, painter, builder, doctor, teacher, pilot…) plus seasonal/special ones (santa, witch, zombie, animals). The help text notes that "person" covers "animals and other non-humans in some special puzzles".
- **One suspect starts revealed** (`initial_reveals:[2]` in the 2026-10-23 daily), with their clue showing [client]. Player write-ups agree.
- The number of criminals varies by puzzle (6 of 20 on 2026-10-23; another puzzle's clue says "11 innocents on the edges"). It is not announced up front, though some clues give a total.

## Core loop

1. Tap an unrevealed suspect and choose **innocent** or **criminal** [help].
2. If the choice is accepted, the card flips. It shows its status and usually a new clue ("They might reveal a new clue"), along with a short reaction line: criminals say things like "You got me!", innocents "Thanks for clearing me!" [client].
3. Repeat until all 20 are identified. Then the result screen opens [client].

### Rules the help text states

- Everyone is exactly one of criminal or innocent.
- **Everyone tells the truth, criminals included.** Clues are never lies.
- Professions mean nothing unless a clue says so ("A cop is as criminal as an accountant until proven otherwise").
- **You cannot guess.** "There is always a logical next choice." The game accepts a choice only when it follows logically from the clues currently revealed.

### Wrong vs correct-but-not-yet-provable

This is the key detail, and it is confirmed in [client]. A choice is accepted only if **both** of these hold:

```
accepted = (chosen trait == true trait)
           && some precomputed deduction path for this card is fully revealed
```

Each card carries `paths`: lists of card indices whose revealed clues are enough to deduce it. The game runs no solver at play time. Validity was worked out offline by the author's generator.

The game treats **a factually wrong choice and a right-but-unprovable choice exactly the same**:

- The card does **not** flip and nothing is revealed.
- A modal opens: **"⚠️ Not enough evidence!"** followed by "*{Name}* can't be logically identified as *{criminal/innocent}* from the available info." and "This means there exists at least one other logical scenario where *{Name}* could be *{the other trait}*." It offers "Share scenario" and "Continue".
- That card gets an `error` mark (at most one per card), which shows as 🟨 in the share grid. The attempt count goes up and the timer keeps running.
- There is no lives limit, no game over and no reveal of the answer. Mistakes only show up in the share grid.

The modal never says whether your guess was actually wrong, so it never leaks the answer. The help text frames this as "the game prevents you from making mistakes". The share legend still calls a 🟨 "made at least one mistake identifying the person".

## Timer, hints and result

- **Timer**: runs from the first move. It shows as `mm:ss` when the solve takes 6 minutes or less, otherwise as "less than N minutes" [client, help]. Pause/Resume is available. Restarting clears progress, and "your result after restarting won't be included in global statistics" [client].
- **Hints** [help, client]: a 💡 button below the grid. The first press ("Show hint") highlights the clue(s) to look at. The second press ("Show more") also highlights the person(s) you can now identify. Hints are precomputed per puzzle (`hints: [{flipped, clues, reveals}]`). The game picks the entry that applies to the current board, preferring the fewest clues, then the fewest reveals. The *next correct* identification after a hint is marked 🟡 (one press) or 🟠 (two presses). Hints are unlimited and can be turned off in Settings.
- **Inspect** (🔎): tap it, then a revealed card, to get an explanation of the terms in that card's clue [help].
- **Player aids** [help]: colour tags on two card corners (tap top right; long-press for more colours; long-press the bottom half for the second corner), tapping a clue to dim it, and highlighting of referenced names/professions (they bounce if you tap repeatedly). "Share scenario" copies a link that restores the current board state, for asking others for help.
- **Score**: there are no points. The result is time plus a per-card 4 × 5 emoji grid. Each cell shows its worst mark in the priority 🟠 second hint > 🟡 hint > 🟨 error > 🟩 clean [client].
- **Share text** [client], exactly:

  ```
  I solved the daily #CluesBySam, Oct 23rd 2026 (Hard), in 04:43
  🟩🟩🟩🟩
  🟩🟩🟨🟩
  🟩🟩🟩🟩
  🟩🟩🟩🟩
  🟩🟩🟩🟩
  https://cluesbysam.com
  ```

  (Time over 6 minutes reads "in less than 9 minutes".) There is a "Copy Text" button, a native "Share Text" button and an image share. The image is a canvas reading "SOLVED", the date and the same grid, with an optional "identity clue" theme line for the day (e.g. "One criminal is responsible for a lot of headaches").
- **Stats** [help]: after solving, you are told if you are in the top 1/5/10/25/50 % by speed, and how many others solved it perfectly. This is hidden for the very first solvers.
- **New puzzle** at midnight America/New_York, with a countdown on the result screen [client].

## Difficulty across the week

- The help text only says "Puzzles get harder throughout the week!". The puzzle data carries a `difficulty` label that appears on the start screen, the result screen and the share text [client].
- Labels seen: **Easy, Medium, Tricky, Hard** (confirmed in [client] and [players]). Search summaries of the Wikipedia article add **Brutal** and **Evil**, and say Monday is Easy and Tuesday Medium, NYT-crossword style. I could not open that article to check.
- Player-shared results:

  | Date | Day | Label |
  |---|---|---|
  | 2026-07-20 | Mon | Easy |
  | 2026-05-26, 2026-07-07 | Tue | Medium |
  | 2026-07-29 | Wed | Tricky |
  | 2026-07-16, 2026-07-30 | Thu | Tricky |
  | 2026-07-31 | Fri | Tricky |
  | 2026-10-23 | Fri | Hard (also confirmed in [client]) |
  | 2026-07-18 | Sat | Hard |

  **Inference**: the label belongs to each puzzle and only roughly follows the weekday. Monday is Easy and Tuesday Medium, then Tricky/Hard later in the week; Friday has been both Tricky and Hard. I found no Sunday data point. The client's day picker shows Mon–Sun, so there is a puzzle every day.
- Difficulty also seems to show in clue *types*. Harder puzzles use nested clues ("Exactly 2 of the 3 criminals in between X and Y are Z's neighbors"), while Monday-style ones use direct counts. This is inferred from the samples, not stated anywhere.

## Clue catalogue

Every clue card has `hint` (the displayed text) and, for real clues, `orig_hint`: a DSL expression the generator checks [client]. Cards with no `orig_hint` are **flavour text**: jokes, storyline, banter ("How can a weekend be stolen, anyway?"). Settings can show them normally, in italics, dimmed or hidden [client]. The author sometimes hand-edits `hint` so it no longer matches `orig_hint` word for word, presumably for voice. Flavour text also carries a light running story across the week. There is no evidence that flavour text ever carries logic.

### Units (the groups clues talk about)

The DSL's `unit(type, selector)` takes these types [client, cbs-bench]:

| Unit | DSL | Displayed as | Defined in [help] |
|---|---|---|---|
| Row | `unit(row,n)` | "row 3" | Rows go sideways, numbered 1–5 |
| Column | `unit(col,n)` | "column C" (`#C:3` renders as a letter) | Columns go up/down, lettered A–D |
| Neighbors | `unit(neighbor,i)` | "neighboring X", "X's neighbors", "innocent neighbors" | Always includes diagonals, up to 8 |
| Between | `unit(between,pair(a,b))` | "in between A and B", "above/below/to the left/right of X", or "in row n"/"in column X" when the pair spans the whole line | Excludes the two endpoints |
| Corners | `unit(corner,void)` | "in the corners" | The four corners |
| Edges | `unit(edge,void)` | "on the edges" | The 14 people around the border, corners included |
| Profession | `unit(profession,p)` | "#PROFS:builder" renders as "builders" | Profession group |

Row and column numbers in the DSL are 1-based: a neighbour of cell 6 (row 2) is said to be "in row 3", and `#C:3` renders as "C". The cbs-bench doc says they are 0-based, which conflicts with this evidence.

The renderer [client] turns a `between` pair into the most natural phrase. A pair spanning a whole row becomes "in row 2". A pair starting at the left edge becomes "to the left of X", and one ending at the right edge "to the right of X" (likewise "above X" / "below X"). Otherwise it reads "in between X and Y". When the speaker is one of the people named, the text switches to the first person: "I", "me", "my", "I am", "I have", "neighboring me", "X and I". "exactly 0" is rewritten to "no".

### Clue types (DSL predicate → example wording)

From the four puzzles I read in [client], plus the cbs-bench catalogue (marked †):

**Counts**
- `number_of_traits_in_unit` → "X has exactly 6 innocent neighbors", "There are exactly 2 innocents in between X and Y"
- `number_of_traits(trait,n)` † → "There are exactly N criminals" (whole board)
- `min_number_of_traits_in_unit` † → "There are at least 7 criminals on the edges"
- `all_units_have_at_least_n_traits(col,…)` → "Each column has at least 2 innocents"
- `total_number_of_traits_in_units` → "X and Y have 6 innocent neighbors in total"
- `max_number_of_traits_in_neighbors_in_unit` → "No one in the corners has more than one criminal neighbor"

**Parity**
- `odd_number_of_traits_in_unit` → "There's an odd number of innocents neighboring X"
- `even_number_of_traits_in_unit` → "There's an even number of innocent builders"
- `units_share_odd_n_traits` † → "An odd number of innocents on the edges are neighbors of X"

**Comparisons**
- `equal_number_of_traits_in_units` → "There's an equal number of innocents in columns C and D"
- `equal_traits_and_traits_in_unit` → "There are as many criminals as innocents in between X and Y"
- `more_traits_in_unit_than_unit` → "There are more criminal doctors than criminal farmers", "X has more innocent neighbors than Y"
- `more_traits_than_traits_in_unit` † → "X has more criminal than innocent neighbors"
- `has_most_traits` † → "Column D has the most innocents" ("the most" always means *uniquely* the most)

**Uniqueness**
- `only_one_unit_has_exactly_n_traits` † → "Only one column has exactly 1 innocent"
- `only_unit_has_exactly_n_traits` † → "X is the only one with exactly 1 innocent neighbor"
- `only_one_person_in_unit_has_exactly_n_trait_neighbors` → "Only one person in row 3 has exactly 4 innocent neighbors"

**About one person**
- `has_trait` † → "X is innocent"
- `is_one_of_n_traits_in_unit` → "X is one of 5 criminals on the edges", "X is one of Y's 3 criminal neighbors"
- `is_not_only_trait_in_unit` → "X is one of the criminals in between A and B" ("one of the…" implies at least two)

**Overlaps between two groups**
- `units_share_n_traits` → "X and Y have 2 innocent neighbors in common", "3 of the innocents in between X and Y are neighboring Z", "2 of X's innocent neighbors are in row 3"
- `unit_shares_n_out_of_n_traits_with_unit` → "Only 1 of the 3 criminals neighboring X is Y's neighbor"
- `only_trait_in_unit_is_in_unit` → "The only innocent in between X and Y is Z's neighbor"
- `both_traits_in_unit_are_in_unit` → "Both criminals in between X and Y are Z's neighbors"
- `all_traits_in_unit_are_in_unit` → "All criminals neighboring X are in column C"

**Connectivity**
- `all_traits_are_neighbors_in_unit` → "All innocents in between X and Y are connected"
- `both_traits_are_neighbors_in_unit` → "Both criminals above X are connected"

**Direction and profession**
- `every_profession_has_a_trait_in_dir(p,trait,dx,dy)` → "Every clerk has an innocent directly below them"
- `n_professions_have_trait_in_dir` † → "No singer has a criminal directly above them", "Exactly 2 teachers have an innocent directly to their right"
- `n_in_unit_have_trait_in_dir` → "4 persons on the edges have a criminal directly below them"

The help text also mentions **conditional clues** ("If A then B", not "if and only if", contrapositive valid) and **"share"** phrasing ("share an odd number of innocent neighbors"). I did not see their DSL names. This is not a complete list: the DSL is the author's and unpublished, and cbs-bench only catalogues what it has scraped.

### Wording conventions (help text, condensed)

- **Numbers are exact** unless stated ("2 criminal coders" means exactly 2). "Both" means exactly 2.
- **"All"** means at least one. **"One of the / one of several"** means at least two.
- **"Connected"** means a chain of orthogonal adjacency. One person counts as connected.
- **"Above/below"** means anywhere in the same column. **"Left/right"** means anywhere in the same row, from the player's view. **"Directly …"** means the adjacent cell only.
- **"In between"** (or just "between") excludes the two named people.
- **"Common neighbors"** means neighbours of both, not counting the two people themselves.
- **"In total"** means the sum across the groups (1 cop + 1 cook, or 0 + 2, …).
- **"More"** does not require any in the lesser group. **"The most"** means uniquely the most.
- **Even** includes 0.
- **"Person"** can include animals and non-humans in special puzzles.

## Around the core loop

- **Free account** (`/s/home`): keeps your result history, gives access to the current and previous weeks' puzzles ("Log in for last week's puzzles"), and lets you subscribe to the newsletter for **weekly bonus puzzles** and stats [help].
- **Archive / help links**: older puzzles are served at `/archive/<id>/` and `/help/<id>?state=…` (shared-scenario links) [client].
- **Paid puzzle packs** [packs]: 50 puzzles each, "ranging from easy to evil". Pack #1 is pay-what-you-want (minimum $1). Pack #2 costs a fixed €5.00 and is harder ("Easy" there ≈ daily Medium). They are delivered by email or link.
- **Tutorial**: three interactive tutorial puzzles at `/s/tutorial/`, plus linked YouTube walkthroughs [help].
- **Settings**: theme, light/dark, font, which side the colour picker is on (left-handed mode), auto-clearing tags on reveal, how flavour clues show, hints on/off, stats display, undimming clues at the end [client].
- **Community**: r/CluesBySamHelp and Bluesky for help. r/puzzles only for archived puzzles or yesterday's. Bug reports by email [help].
- Made by **Ad Artis Oy** (Finland), the same company behind Games by Sam, SudokuGen and Cluehound [help footer]. Search summaries of Wikipedia name the designer as Johannes Ahvenniemi, with a daily launch in May 2025. I could not verify this first-hand.

## Open questions

- The exact weekday → label mapping for Fri–Sun, and whether "Brutal" and "Evil" ever appear in dailies or only in packs. I found no first-party statement and only a few data points.
- The full clue DSL. Conditional ("if … then …") clues and some "share" variants were not seen in the sample.
- How puzzles are generated and how difficulty is rated (secondary sources mention an internal solver plus playtesting; unverified).
