# Solving and generating 20-desk deduction puzzles in Python

Research for [#4](https://github.com/da-mask/sam_game/issues/4). Laid out as trade-offs, not a decision.

## The problem

- A board has 20 coworkers on a 4x5 grid of desks. Each coworker is sick or well, so there are 2^20 = 1,048,576 possible boards.
- A **revealed state** is a set of declared coworkers together with the clues of the revealed coworkers. Each clue is a constraint over the 20 booleans.
- **(1) Forced check.** A declaration "X is sick" is forced when no assignment that satisfies every constraint has X well. That is one co-NP-style query per declaration. At this size it is either a full enumeration or one unsatisfiability call.
- **(2) Generation.** The generator picks a solution and a clue for each coworker such that, starting from the first revealed coworker, repeatedly declaring every forced coworker eventually declares all 20. If the chain completes, the solution is unique: every desk was forced.
- **(3) Grading.** Difficulty should follow how hard each forced step is for a person to find, not how hard it is for the machine.

Almost every clue type in scope is a **cardinality constraint**: "exactly, at least or at most k sick" among a set of desks (a row, a column, a coworker's neighbours or a department). The others are:

- **Parity** (odd/even): an XOR over a set of desks.
- **Comparisons** ("more sick in A than in B"): a linear constraint, count(A) - count(B) >= 1.
- **Connected** ("the sick in row 3 are connected"): a pattern constraint over one line, or a graph-connectivity constraint if it covers the whole board.

## How it was measured

All timings come from scratch scripts that are not committed. The setup:

- **Machine:** Intel i7-1165G7 under WSL2, CPython 3.12.3, run single-threaded.
- **Libraries:** numpy 2.5.4, python-sat 1.9.dev17, ortools 9.15.6755, z3-solver 5.3.1.0, python-constraint2 2.7.3, all installed from PyPI wheels into a fresh venv.
- **Model:**
  - Bit i of an integer means "desk i is sick".
  - Clues were random true cardinality clues about a random solution, drawn from 5 rows, 4 columns, 20 neighbour sets (diagonals included) and 4 random 5-desk departments.
  - Operators were `==`, `>=` and `<=`.
- **Reporting:** each figure is the median of 3 to 5 runs.
- **Typical state:** 4 declared coworkers and 6 clues, leaving 480 consistent boards.
- **Hard case for enumeration:** no declared coworkers and 12 clues.
- **Early-game case:** 1 declared coworker and 2 clues, leaving 65,536 consistent boards.

## (1) Checking whether a declaration is forced

### Approaches compared

| Approach | Typical state (4 declared, 6 clues) | Other cases | Notes |
|---|---|---|---|
| **Pure Python**: enumerate `range(2**20)` and test with `int.bit_count()`; AND/OR the survivors to get every forced desk at once | 98 ms | 142 ms (12 clues, nothing declared); 226 ms (early game). A bare loop over 2^20 with one popcount test takes 66 ms | No dependencies. Any clue that can be written as a Python predicate works. Too slow for a generator that runs thousands of checks; fine for checking a single declaration. |
| **numpy**: `np.arange(2**20, dtype=np.uint32)`, `np.bitwise_count(a & mask)`, boolean masks, then `bitwise_and.reduce` / `bitwise_or.reduce` | 10 ms full pass; 2.4 ms when the surviving candidates are filtered clue by clue | 13 ms (12 clues); 2 ms (early game) | `np.bitwise_count` needs numpy 2.0 or later. The candidate array is 4 MB. Any clue that can be vectorised, or turned into a lookup table, works (see below). |
| **PySAT** (CaDiCaL 1.9.5, MiniSat 2.2, Glucose 4): cardinality clues encoded with `CardEnc` (sequential counter), then 2 `solve(assumptions=[±x])` calls per undeclared desk | 0.4 ms for all 16 undeclared desks (32 calls; Glucose 0.6 ms) | 0.5 ms (early game). Enumerating all 480 models with blocking clauses takes 5.5 ms | Fastest by a wide margin, and the cost does not depend on how many boards remain consistent. Each clue type needs a CNF encoding. |
| **OR-Tools CP-SAT**: native `sum(x) == k` constraints, clone the model and fix one desk, 2 solves per desk, `num_workers=1` | 20 ms (32 solves; about 0.8 ms per solve) | 22 ms (early game) | Expresses linear, XOR and boolean constraints natively. Each solve has a fixed setup cost; `add_assumptions` exists and would avoid cloning the model. |
| **z3**: `PbEq`/`PbGe`/`PbLe`, `check(assumption)` | 3.6 ms | 9.4 ms (early game) | The most expressive option (integer arithmetic and more). The Python API adds overhead on every call. |
| **python-constraint2**: backtracking CSP with `ExactSumConstraint` and related constraints, calling `getSolutions()` | 4.2 ms (480 solutions) | **117 ms** (65,536 solutions, early game) | Finds forced desks only by listing every solution, so the cost grows with the number of consistent boards. |

Process start plus import time (median of 5 runs, against 9 ms for a bare interpreter):

| Package | Start + import |
|---|---|
| pysat | 33 ms |
| python-constraint2 | 40 ms |
| z3 | 67 ms |
| numpy | 75 ms |
| ortools | 346 ms |

This matters for a CLI or for serverless cold starts, not for a long-running server.

### Clues that are not plain counts

- **Connected within a row or column.** Use a lookup table indexed by the line's bits: 16 entries for a 4-desk row, 32 for a 5-desk column. In numpy one table lookup over all 2^20 boards takes 2.6 ms. In CNF the encoding is small: for every i < j < k on the line, add the clause (¬x_i ∨ x_j ∨ ¬x_k).
- **Connected across the whole board.** Use a table precomputed once over all 2^20 boards and cached:
  - Pure Python, one flood fill per board: 2.0 s.
  - numpy, a bit-parallel flood fill over all boards at once: 106 ms. It found 116,167 connected boards.

  This clue is awkward for SAT and CP-SAT, which need a reachability or flow encoding, and easy for enumeration.
- **Odd/even.** In numpy, `bitwise_count(...) & 1`. CP-SAT has `add_bool_xor`. In CNF, an XOR over 4 or 5 desks needs 8 or 16 clauses.
- **Comparisons.** count(A) > count(B) is the same as count(A) + count(¬B) ≥ |B| + 1, so it reuses `CardEnc.atleast` over mixed literals. Overlapping A and B need care. CP-SAT and z3 take the linear form directly. PySAT's `pysat.pb` also offers pseudo-Boolean encodings through the optional `pindakaas` extra, listed in python-sat's `requires_dist` on PyPI.

**The trade-off:** enumeration makes every new clue type a few lines of Python, whatever its shape. Solvers make every check almost free, but each clue type needs its own encoding, and that encoding is a new place for bugs.

### Scaling

The figures above depend on the board staying at 20 desks. A 25-desk (5x5) board means 33.5M boards: a 134 MB uint32 array and roughly 30 times the numpy time. Pure Python would be out of the question. SAT timings would barely change. If board size might grow, that favours a solver.

### Packaging and typing

Checked against PyPI JSON metadata on 2026-10-24, and by running `mypy --strict` on a file that imports each package.

| Package | Latest | Wheels | Typing | Maintenance and notes |
|---|---|---|---|---|
| `numpy` | 2.5.4 (2026-10-10) | 65, `requires_python >=3.12` | `py.typed` with full stubs | Production/Stable |
| `python-sat` (import `pysat`) | 1.9.dev17 (2026-10-20) | 51 (CPython × Linux/macOS/Windows) | No `py.typed` and no stubs package; mypy reports `import-untyped` and `solve()` returns `Any` | Very active, but PyPI carries **only `.devN` versions** (1.8.devN, then 1.9.devN), so pins name a dev release. Bundles 21 solvers, including CaDiCaL 1.0.3 to 3.0.0, Glucose, MiniSat, Lingeling and Kissat. Depends only on `six`. |
| `ortools` | 9.15.6755 (2026-01-14) | 34 | `ortools/sat/python/py.typed` plus a `.pyi` for the C++ helper; mypy resolves `new_bool_var` to `IntVar` | Production/Stable, from Google. Heavy: pulls in numpy, **pandas**, protobuf (pinned `<6.34`), absl-py and immutabledict. The ortools and pandas trees take about 80 MB each. |
| `z3-solver` | 5.3.1.0 (2026-10-15) | 9 (`py3-none`, per platform) | No `py.typed` and no stubs on PyPI; `import-untyped` | Active (Microsoft Research). About 56 MB installed. |
| `python-constraint2` | 2.7.3 (2026-08-18) | 40, `requires_python >=3.11` | No `py.typed`; `import-untyped` | The maintained successor. The original `python-constraint` stopped at 1.4.0 in 2018, and its README says "must be installed with `pip install python-constraint2`, as the original pip release will not be updated". Compiled with Cython. |
| `pycosat` | 0.6.6 (2023-10-03) | **none, sdist only** | none | Wraps PicoSAT 965. `pip install` on CPython 3.12 **failed to build** here, so it is effectively conda-only. Not a practical choice. |

With mypy strict, any of the untyped solvers would sit behind a small typed module of our own, with a per-module `ignore_missing_imports` override. That module would be the only place solver-shaped `Any` leaks in.

## (2) Generating boards with a forced chain

[Simon Tatham's developer guide](https://www.chiark.greenend.org.uk/~sgtatham/puzzles/devel/writing.html#writing-generation) ("Puzzle generation", from `devel.but` in the 20260923 source tarball) sets out the strategies that use a solver. Each is mapped to this game below.

**Strategy 1: generate at random and test.** Pattern and Dominosa work this way. Tatham warns it "tends not to scale well" as uniquely soluble instances get rarer. For us this means choosing all 20 clues blind and then checking. Probably a poor fit: one useless clue breaks the chain.

**Strategy 2: generate, then tweak where the solver gets stuck.** Mines and Net work this way. The method fits when the solver "get[s] stuck in an easily localised spot". It also needs a re-check from scratch afterwards, because a tweak can break earlier steps.

**Strategy 3: start full and remove clues while the puzzle stays soluble.** Solo and Slant work this way. Tatham notes it "*cannot* fail". The direct analogue here does not exist, because every revealed coworker has exactly one clue. The near-analogue is to start each coworker with a strong clue and **weaken** it ("exactly 2" becomes "at least 1", a neighbour count becomes a department count) for as long as the chain still completes.

**Strategy 4: run the solver during construction.** Rectangles works this way. Tatham's point: if it "finishes successfully at all, then it has definitely produced a uniquely soluble puzzle", with no re-check needed.

This is the natural fit for a reveal-driven game. The loop:

1. Pick a solution and a starting coworker.
2. Whenever a coworker is revealed, pick their clue from the true clues about the solution, preferring clues that create at least one new forced move.
3. Declare the forced coworkers.
4. Repeat until all 20 are declared.
5. If the solver gets stuck, restart.

**Measured prototype of strategy 4.** It used numpy candidate filtering, greedy clue choice from up to 12 random true cardinality clues per reveal, and declared every forced coworker each round. Over 200 attempts:

- 97 succeeded (49%).
- Each attempt took a median of 10.4 ms (maximum 18.7 ms).
- The expected time per usable board is about 21 ms.
- A successful attempt took a median of 6 rounds of forced declarations.

Tatham's rule of thumb applies: divide attempt time by success rate. Even a far smarter generator (backtracking over clue choices, difficulty targeting) has orders of magnitude of headroom. A daily puzzle can also be generated offline and stored, so generator speed is not critical.

**Targeting a difficulty.** Tatham's generators keep a candidate only if the solver succeeds at the target level and fails at the level below:

- `towers.c` says: "See if the game can be solved at the specified difficulty level, but not at the one below… if (ret != diff) continue".
- `solo.c` does the same with `dlev.diff == dlev.maxdiff`.

Hitting *at most* a level is easy. Hitting *at least* a level often means throwing the attempt away and starting again. The guide shows the same thing for Solo: removing one number can take a grid "from Trivial straight to Ambiguous".

The levels are an ordered list of solver functions (`DIFFLIST`: Easy → Hard → Extreme → Unreasonable). Unreasonable "may require guessing and backtracking", which this game rules out.

**The closest existing design is Tatham's Mines.** It is Minesweeper with "Ensure solubility" on by default, so that "you never need to *guess* where a mine is". Its solver reasons about local sets of squares with mine counts, takes set differences ("wings") between overlapping sets, and only "when all localised deductions have failed" falls back to "global deduction based on the total mine count … computationally expensive". That is almost exactly what neighbour-count clues are, and it suggests a two-tier solver:

- a cheap local solver that is human-like and gives the grade;
- an exhaustive check (enumeration or SAT) that is authoritative.

The server's rule ("is this declaration forced?") should always use the exhaustive check. Otherwise a player who makes a valid deduction the local solver does not know would be wrongly refused.

## (3) Grading difficulty the way a person deduces

### How existing raters work

- **Tatham.** The difficulty is the weakest solver tier that completes the puzzle. Tiers are hand-written families of techniques.
- **[HoDoKu](https://hodoku.sourceforge.net/en/docs_cre.php) (Sudoku).** Each technique has a *level* (Easy, Medium, Hard, Unfair, Extreme) and a *score*. "The score of all steps in the solution is simply summed up". The level "cannot be smaller than the level of the hardest step", and a high total score can push it higher. The generator discards candidates that come out too easy. HoDoKu itself points to Sudoku Explainer for "a stable difficulty rating".
- **Sudoku Explainer (SE rating).** The rating is the *maximum* difficulty of any technique used, out of about 20 techniques. This description comes from Pelánek, below.
- **[Pelánek, *Difficulty Rating of Sudoku Puzzles by a Computational Model*](https://www.fi.muni.cz/~xpelanek/publications/flairs-sudoku.pdf) (FLAIRS 2011).** This is the empirical paper. Puzzle ratings were compared against thousands of hours of human solving times on more than 2,000 puzzles. The paper identifies "two sources of problem difficulty: complexity of individual steps … and structure of dependency among steps". The **dependency** metric is the mean number of places a simple step could be applied, over the first k steps (k = 20 to 30 for 9x9 Sudoku). It worked where max-technique ratings failed: on simple puzzles, the correlation with solving time was 0.73 to 0.78 against SE's 0.28 to 0.55. A combination of the metrics reached 0.95. Number of givens correlated at only about 0.25. The author expects the approach to carry over to other constraint puzzles.

### What the measurable signals are here

1. **Clues per step.** For each forced declaration, find the smallest set of revealed clues that forces it. This is the analogue of a technique tier: one clue alone ("0 sick among X's neighbours"), two clues combined (Mines-style wings), three or more, or global reasoning. Both tools compute it:
   - **SAT cores.** Add a selector literal to each clue, assume all selectors plus the negated declaration, and read `get_core()`; then shrink the core greedily. For a 12-clue state, finding and minimising a core for every forced desk took **0.9 ms** in total. The 14 forced desk values needed between 2 and 6 clues. Greedy shrinking gives an *irreducible* set, not always the *smallest*. An exact minimum would need a minimal-unsatisfiable-subset (MUS) or optimisation search, which PySAT also supports.
   - **numpy subsets.** Keep one boolean table per clue (1 MB each) and test every subset of up to 3 of the 12 clues (298 subsets): **194 ms**. Restricting enumeration to the desks a subset mentions would cut this a lot, and also reads as "what a person looks at".
2. **Clue-type weight.** "Connected", parity and comparisons are probably harder to use than "exactly k". As in HoDoKu, these would be per-type scores, tunable later.
3. **Dependency (branching).** Count how many forced declarations are available at each step. A chain with a single forced move at a time is harder than one offering five (Pelánek). Logging how long players take per step would allow fitting the weights, as Pelánek did.
4. **Aggregation.** The options are max (Tatham, SE), sum with a floor at the hardest step (HoDoKu), or a weighted mix of max step, sum and branching (Pelánek's combined metric).

## Trade-offs

**Which looks strongest:**

- **For checking declarations on the server.** Three candidates:
  - **numpy enumeration:** 2 to 13 ms. Any clue type is a predicate or a table, and it is easy to test against a pure-Python reference.
  - **PySAT:** under 1 ms. It also gives explanations through unsat cores, but needs CNF encodings and has untyped, dev-only releases.
  - **Pure Python:** about 0.1 to 0.2 s with no dependencies. Acceptable for a single declaration.

  CP-SAT works but is the heaviest dependency (pandas, protobuf, 346 ms import) for the least benefit at this size. z3 is more expressive than the clues need. python-constraint2 slows down sharply early in the game. pycosat does not install.
- **For generation.** A solver run during construction (Tatham's Rectangles style), restarting on failure, looks strongest. Prototyped at about 21 ms per usable board. Difficulty targeting would follow Tatham's "at this tier, not the tier below" rule.
- **For grading.** Combine tiers based on clues per step (from SAT cores or numpy clue subsets) with a dependency or branching term. Pelánek's data suggest this tracks people better than "hardest technique" alone.

**Open questions:**

- Will clue types ever include board-wide constraints such as whole-board connectivity? That favours enumeration.
- Might the board ever grow beyond 20 desks? That favours SAT.
- How much does a light dependency stack matter against the typed-API gap?

These belong in [#5](https://github.com/da-mask/sam_game/issues/5) (clue types) and [#7](https://github.com/da-mask/sam_game/issues/7) (solver and generator design).

## Sources

- Simon Tatham's Portable Puzzle Collection, source tarball `puzzles-20260923.616da16`: `devel.but` §"Puzzle generation" (also published at <https://www.chiark.greenend.org.uk/~sgtatham/puzzles/devel/>), `towers.c` (`DIFFLIST`, generator loop), `solo.c` (difficulty enum, `dlev.maxdiff`), `mines.c` (set store, `setwings`, global deduction), `puzzles.but` (Mines "Ensure solubility", "Unreasonable" mode). <https://www.chiark.greenend.org.uk/~sgtatham/puzzles/>
- HoDoKu, Chapter 4 "Creating Sudokus": <https://hodoku.sourceforge.net/en/docs_cre.php>
- R. Pelánek, "Difficulty Rating of Sudoku Puzzles by a Computational Model", FLAIRS 2011: <https://www.fi.muni.cz/~xpelanek/publications/flairs-sudoku.pdf>
- PyPI JSON API (versions, upload dates, wheels, classifiers, `requires_dist`): `https://pypi.org/pypi/<name>/json` for numpy, python-sat, ortools, z3-solver, python-constraint2, python-constraint and pycosat.
- PySAT: <https://pysathq.github.io/> (assumption-based incremental interface, `get_core`, cardinality encodings), plus the installed `pysat.solvers.SolverNames`.
- OR-Tools CP-SAT Python API: installed `ortools/sat/python/cp_model.py` (`add_assumptions`, `enumerate_all_solutions`, `py.typed`).
- python-constraint README: <https://github.com/python-constraint/python-constraint>
- pycosat: <https://github.com/conda/pycosat> (PicoSAT 965).
- numpy `bitwise_count`: <https://numpy.org/doc/stable/reference/generated/numpy.bitwise_count.html>
