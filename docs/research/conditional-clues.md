# Conditional clues in Clues by Sam

Research for [#19](https://github.com/da-mask/sam_game/issues/19). Checked against cluesbysam.com and its archived daily bundles on 2026-10-24.

The original game says **suspect**, **criminal** / **innocent** and **profession**. In our terms (see `GLOSSARY.md`) these are **coworker**, **sick** / **well** and **department**. Quotes keep the original's words. Desk numbers are 0-based and row-major on the 4 × 5 grid (0 = A1, 4 = A2, …). In the DSL, `unit(between,pair(a,b))` is **inclusive** of a and b. The client renders it as "in between" the desks one step *outside* the pair (`xe=V-width`, `W=P+width` in the `#BETWEEN` renderer), or as "above/below/in column …" when it reaches an edge.

## Answer in brief

- **Forms.** Conditionals are always about **one coworker's state implying another's**:
  - "If X is criminal, then so is Y"
  - "If X is innocent then so is Y"
  - "If X is criminal then Y is innocent"
  - "If I'm a criminal then X is not innocent"
  - one "only if" variant whose consequent is a group: "X is innocent only if all other singers are innocent"

  None conditions on a count, parity or any other group statement.
- **They have no DSL predicate.** Every conditional is hand-written in the displayed `hint` text over an ordinary `orig_hint` predicate. In the first two (August 2025), `orig_hint` is a different true clue the author rewrote. From 2025-09-16 on, it is the **consequence the clue gives at the point it is used** (for example `has_trait(6,criminal)` behind "If Hazel is innocent then so is Gus"). The conditional itself never appears in the DSL.
- **They are rare and short-lived.** There are 7 conditional clues in 366 archived dailies (4,520 clues, 0.15 %). All of them fall between 2025-08-22 and 2025-10-21, a period with 40 dailies. None appear in the 265 dailies after that.
- **Difficulty does not matter.** They appear at every level from Easy to Evil. The difficulty comes from the context, not the clue. As displayed, each is usable in a one-clue step, because the antecedent or the negated consequent is already known (modus ponens or contraposition).
- **We can support them.** For the numpy mask solver a conditional costs one line, `~A | B`, over masks we already build. The wording fits the existing rules with one addition: "if" is one-way.
- **Recommendation: keep them out of the launch spec.** If we add them, add only the narrow coworker → coworker form, as one more statement family, generated rarely. Details in [Recommendation](#recommendation).

## Sources

| Tag | Source | Trust |
|---|---|---|
| [help] | "How to play" text on the [cluesbysam.com](https://cluesbysam.com/) home page | Primary |
| [client] | The live client bundle `https://cluesbysam.com/assets/index-B0lUpotk.js` (2026-10-24 daily) | Primary (the code is the behaviour) |
| [archive] | 404 archived copies of the daily bundle `https://cluesbysam.com/assets/index-*.js` from the [Wayback Machine](https://web.archive.org/cdx/search/cdx?url=cluesbysam.com/assets/&matchType=prefix) (CDX index, fetched with `id_` raw mode). 401 parsed, giving **366 distinct dailies from 2025-04-28 to 2026-10-17** (365 dates; 2026-01-18 has two puzzles), about two thirds of all days in that span | Primary: the game's own shipped data. The sample is whatever the archive happened to capture |
| [cbs-bench] | [Syps/cbs-bench](https://github.com/Syps/cbs-bench) `syntax.dsl` and `cbs_bench/generate/hint_dsl_functions.py` | Secondary, reverse-engineered |

Each bundle embeds that day's puzzle: per card `criminal`, `name`, `profession`, `orig_hint` (DSL), `hint` (displayed text) and `paths`. Since autumn 2025 the bundle also carries `hints: [{flipped, clues, reveals}]`, the precomputed hint table. I extracted these with regexes and never ran the bundles. The extraction and analysis scripts live outside the repo.

## What the help text and client say

- [help] defines the semantics, with no example clue:
  > "If A then B" does NOT mean the same as "If and only if A then B". Therefore it does NOT mean "If not A then not B". But please note that, due to how logic works, it DOES mean "If not B then not A". (It's called the contraposition.)
- [client] The Inspect tips table (`Dy`) has **no "if" entry**. The nearest entry is **"any"**: *"Any doesn't tell you anything about the number. Zero is allowed. It means 'if there are any, then...'"*. That entry is about a vacuous "all/any" quantifier, not a conditional clue.
- [client] Whether a card shows as a clue or as flavour depends only on whether it has `orig_hint`. The class function (`uy`) gives cards with `orig_hint` the class `hint`, and everything else the italic/dimmed/hidden `flavour` classes. Inspect tips are attached only to cards with `orig_hint` (`e2`). So a hand-written conditional needs *some* `orig_hint` to be styled as a clue, whatever its value.
- [client] No solver runs at play time. A declaration is accepted when it is correct and one of the card's precomputed `paths` is fully revealed (see the [rules research](https://github.com/da-mask/sam_game/blob/research/clues-by-sam-rules/docs/research/clues-by-sam-rules.md)). A hand-written clue is therefore as sound as the author's check of it.
- [cbs-bench] The DSL catalogue and its z3 implementation of the predicates contain no conditional predicate. The only `Implies` in the code is the internals of "connected".

## Every conditional clue found

Each row: date, weekday, the puzzle's `difficulty` label, the speaker, the displayed text with names resolved, the `orig_hint`, and how the clue is used (from `hints` where present, otherwise from the reveal order in `paths`). C = criminal (sick), i = innocent (well), in the solution.

| Date | Day / label | Speaker | Displayed clue | `orig_hint` | How it is used |
|---|---|---|---|---|---|
| 2025-08-22 | Fri / Hard | Tyler (i) | "If Logan is a criminal, then so is Hilda" | `all_traits_are_neighbors_in_unit(unit(between,pair(2,10)),criminal)`: "all criminals in C1–C3 are connected", a different true clue (Debra, Hilda and Logan are all criminal) | Logan is already revealed criminal, so the displayed conditional alone forces Hilda (modus ponens). The hint table, though, lists clues [Tyler, Zoe] → Hilda. That is the **`orig_hint`'s** reasoning: Zoe says Logan is one of ≥2 criminals in column C, Ruby and Xia are revealed innocent, so Debra or Hilda is criminal, and connectivity makes it Hilda either way |
| 2025-08-25 | Mon / Easy | Wally (C) | "If Paula is criminal, then so is Xavi" | `both_traits_are_neighbors_in_unit(unit(between,pair(5,13)),criminal)`: "both criminals in B2–B4 are connected", a different true clue (Floyd and Katie criminal, Paula innocent) | Hint: clues [Wally] → Paula. Xavi is the initially revealed innocent, so contraposition gives Paula innocent. The `orig_hint` gives the same result (Floyd and Katie are revealed criminals, so Paula is innocent). One clue |
| 2025-09-16 | Tue / Medium | Freya (C) | "If Henry is criminal then Jason is innocent" | `name_has_trait(jason,innocent)` | Henry and Freya are revealed together, Henry criminal. Hint: clues [Freya] → Jason. Modus ponens, one clue |
| 2025-09-21 | Sun / Evil | Sofia (i) | "If Isaac is innocent then so is Alice" | `name_has_trait(isaac,criminal)` | Alice is the initially revealed criminal. Hint: clues [Sofia] → Isaac. Contraposition, one clue |
| 2025-09-23 | Tue / (no label) | Noah (C) | "Isaac is innocent only if all other singers are innocent" | `has_trait(8,criminal)` (Isaac) | The other singers, Logan and Mary, are revealed criminals. Hint: clues [Noah] → Isaac. Contraposition, one clue |
| 2025-10-20 | Mon / Easy | Logan (C) | "If Hazel is innocent then so is Gus" | `has_trait(6,criminal)` (Hazel) | Gus is revealed criminal in the same step as Logan. Hint: clues [Logan] → Hazel. Contraposition, one clue |
| 2025-10-21 | Tue / Medium | Logan (C) | "If I'm a criminal then Julie is not innocent" | `has_trait(8,criminal)` (Julie) | The speaker is revealed, and revealed criminal. Modus ponens, one clue |

The same weeks also had conditional **flavour**: cards with no `orig_hint`, shown as flavour:
- 2025-10-20, Anna (C): "If I'm a criminal then I'm not innocent". A tautology.
- 2025-10-21, Julie (C): "If I'm innocent then so is Wally". Vacuously true, because the speaker is criminal.
- Later jokes in the same vein, e.g. 2026-08-03: "If I wasn't a criminal, I'd be innocent".

Near misses that are *not* conditionals: two hand-reworded single-coworker clues, "I'd be lying if I told you Mary is a criminal" (2025-06-21) and "Will you let me go if I tell you Olivia is a criminal? Well, she is!" (2025-07-05). Like the conditionals, their `orig_hint` doesn't match the displayed text. This confirms the author hand-edits clue text over the generated `orig_hint`.

## Frequency and difficulty

- **7 of 4,520 clues (0.15 %), in 7 of 366 dailies (1.9 %).** All fall in a two-month run, 2025-08-22 to 2025-10-21, where they were 7 of 40 dailies. None appear in the 265 archived dailies since. The run looks like an experiment that was dropped, or became a rare treat. The archive covers about two thirds of days, so a few more may exist uncaptured.
- **Levels:** Easy ×2, Medium ×2, unlabelled Tuesday ×1, Hard ×1, Evil ×1. They don't track difficulty. All seven are usable in a one-clue step as displayed. The game's own hint table counts the Hard Friday one as a two-clue step, because it reasons from the `orig_hint`.
- **Context:** the author always places the conditional so that one side is already settled when it matters: the antecedent is known (modus ponens) or the consequent is known false (contraposition). The contraposition cases (4 of 7) are what the help text warns about. On an Easy Monday the trick is noticing that the revealed coworker *is* the consequent.
- **Antecedent false in the solution:** in 4 of 7, "A" is false in the solution (e.g. "If Isaac is innocent…" where Isaac is criminal), so the clue is true *vacuously*. That is exactly why it is useful: it works by contraposition.

For context, the most common predicates in the same corpus were `number_of_traits_in_unit` (498), `unit_shares_n_out_of_n_traits_with_unit` (406), `is_one_of_n_traits_in_unit` (347) and `odd_number_of_traits_in_unit` (282). Even rare families like `max_number_of_traits_in_neighbors_in_unit` (15) are twice as common as conditionals.

## Can our solver and wording support them?

**Solver ([#7](https://github.com/da-mask/sam_game/issues/7)): yes, trivially.** Every statement is already a boolean mask over the 2^20 boards, so "if A then B" is `~A | B`, and "A only if B" is the same thing. Nothing else changes:
- The forced check ANDs this mask in like any other clue.
- Hardness grading counts it as one clue. The Easy Monday case grades as Easy because a single clue forces a coworker.
- Hints (fewest forcing clues) and the generator's "true of the solution, preferably creates a new forced move" rule apply unchanged. That rule already filters out the useless conditionals (true but forcing nothing).

Since A and B can be any existing statement, the general form would let A and B be counts over groups. The original never does that, and it would make far harder clues than anything else in the game. The narrow form only needs `A = (desk d is sick/well)`, `B = (desk e is sick/well)`, or B = "every member of a group (minus d) is sick/well" for the "only if" case.

**Wording ([#5](https://github.com/da-mask/sam_game/issues/5), [#6](https://github.com/da-mask/sam_game/issues/6)): yes, with one new rule.**
- Our rules already say "sick"/"well" plainly and use the first person for the speaker. "If Hazel is well, then so is Gus", "If I'm sick, then Julie is sick" and "If Ben is sick, then Ana is well" all read naturally.
- New wording rule: **"if" is one-way**: it never means "if and only if", and the contrapositive holds. The explanation shown on tapping the clue should say so concretely: "If Gus is sick, Hazel must be sick too."
- Avoid "only if" and "not innocent". The original uses both once each. They are the hardest phrasings to read, and "not well" breaks our "say sick/well plainly" rule.
- **Vacuous conditionals as flavour** (the "If I'm a criminal then I'm not innocent" jokes) clash with our rule that flavour never carries or suggests logic. A conditional-shaped line reads like logic. Keep them out of flavour.

**Design tension.** The original's conditionals are hand-written. Their `orig_hint` is either another clue or just the consequence, never the conditional. Our map says logic is code-owned and AI may only write wording. So for us a conditional would be a generated statement whose mask *is* the conditional. That is cleaner than the original, but it means the generator decides where to place one. Placement is where the original's craft lies: one side is already settled, often the starting coworker.

## Recommendation

1. **Keep conditionals out of the launch spec**, as #5 decided. They are rare in the original (0.15 % of clues, none for a year), and no difficulty tier depends on them.
2. If we want them later, they are a small, contained addition:
   - one statement family, **"if coworker X is sick/well, then coworker Y is sick/well"**: mask `~A | B`, at most one per puzzle, and only when it creates a new forced move;
   - the wording rule "if is one-way; the contrapositive holds", plus a concrete explanation;
   - no "only if", no group antecedents, no conditional flavour.
3. No change is needed to the solver design, the grading or the hint search.

## Open uncertainties

- **Coverage:** the archive has about 68 % of days from 2025-04-28 to 2026-10-17, with nothing before late April 2025. Uncaptured dailies, the paid packs and the weekly bonus puzzles weren't checked, and packs may use conditionals more.
- **Why they stopped** after 2025-10-21 is unknown. No first-party statement was found. Web searches for discussion turned up nothing relevant.
- **How the author checks them.** The August `orig_hint`s are unrelated generated clues and the later ones are the consequence, which suggests the conditional text is edited by hand after generation. The 2025-08-22 hint table follows the `orig_hint`'s logic, not the conditional's, so the generator never saw that conditional. The author evidently swaps in a conditional that yields the same consequence in context. The client can't show whether later ones were machine-checked.
- **Side finding for #3's open question:** the dailies do use **Brutal** (5) and **Evil** (7) labels, all on Sundays, plus one **Beginner** Monday. 52 early dailies carry no label.
