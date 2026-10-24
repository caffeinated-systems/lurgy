"""PROTOTYPE, throwaway: builds one solvable office-bug board so the sample's wording sits on real logic.

Run: python3 prototype/office-bug-voice/check.py [seed]
No numpy: a set of boards is one 2^20-bit int (bit b set = board b is in the set), and board b has
desk i sick when b's bit i is set. Clues become bitwise ops over all million boards at once.
"""

import random
import sys
from functools import cache
from itertools import combinations

W, H = 4, 5
N = W * H
ALL = (1 << (1 << N)) - 1
NAMES = ["Aisha", "Barry", "Carol", "Dev", "Erin", "Fergus", "Gemma", "Hamid", "Imogen", "Jas",
         "Kev", "Linda", "Mo", "Nadia", "Ollie", "Priya", "Quentin", "Rosa", "Steve", "Tariq"]
DEPTS = ["Sales", "IT", "HR", "Finance", "Marketing", "Facilities"]
SIZES = [4, 4, 3, 3, 3, 3]


def desk_set(i):
    # boards where desk i is sick: runs of 2^i absent then 2^i present, repeated
    if i < 3:
        byte = [0xAA, 0xCC, 0xF0][i]
        return int.from_bytes(bytes([byte]) * ((1 << N) // 8), "little")
    run = (1 << i) // 8
    return int.from_bytes((b"\x00" * run + b"\xff" * run) * ((1 << N) // (16 * run)), "little")


SICK = [desk_set(i) for i in range(N)]


def rc(i):
    return divmod(i, W)


def neighbours(i):
    r, c = rc(i)
    return [rr * W + cc for rr in range(r - 1, r + 2) for cc in range(c - 1, c + 2)
            if 0 <= rr < H and 0 <= cc < W and (rr, cc) != (r, c)]


ROWS = {f"row {r + 1}": [r * W + c for c in range(W)] for r in range(H)}
COLS = {f"column {'ABCD'[c]}": [r * W + c for r in range(H)] for c in range(W)}
CORNERS = [0, W - 1, N - W, N - 1]
EDGES = [i for i in range(N) if rc(i)[0] in (0, H - 1) or rc(i)[1] in (0, W - 1)]


def directional(i):
    r, c = rc(i)
    return {"above": [rr * W + c for rr in range(r)], "below": [rr * W + c for rr in range(r + 1, H)],
            "left of": [r * W + cc for cc in range(c)], "right of": [r * W + cc for cc in range(c + 1, W)]}


def between(i, j):
    (r1, c1), (r2, c2) = rc(i), rc(j)
    if r1 == r2:
        return [r1 * W + c for c in range(min(c1, c2) + 1, max(c1, c2))]
    if c1 == c2:
        return [r * W + c1 for r in range(min(r1, r2) + 1, max(r1, r2))]
    return []


def counter(group):
    return _counter(tuple(group))


@cache
def _counter(group):
    # bit-sliced binary counter: digit j is the set of boards whose sick count in group has bit j set
    digits = [0] * 5
    for i in group:
        carry = SICK[i]
        for j in range(5):
            digits[j], carry = digits[j] ^ carry, digits[j] & carry
    return digits


def exactly(group, k):
    out = ALL
    for j, d in enumerate(counter(group)):
        out &= d if k >> j & 1 else ~d
    return out & ALL


def more(g1, g2):
    a, b = counter(g1), counter(g2)
    gt, eq = 0, ALL
    for j in reversed(range(5)):
        gt |= eq & a[j] & ~b[j]
        eq &= ~(a[j] ^ b[j])
    return gt & ALL, eq & ALL


def connected(line):
    # the sick in this line form one unbroken run, at least one of them
    out = 0
    for s, e in combinations(range(len(line) + 1), 2):
        run = ALL
        for k, i in enumerate(line):
            run &= SICK[i] if s <= k < e else ~SICK[i]
        out |= run
    return out & ALL


def candidate_clues(speaker, dept_of):
    """Every clue a speaker could give, as (plain explanation, set of boards where it's true)."""
    dept = lambda d: [i for i in range(N) if dept_of[i] == d]
    r, c = rc(speaker)
    groups = {"my neighbours": neighbours(speaker), "my row": ROWS[f"row {r + 1}"],
              "my column": COLS[f"column {'ABCD'[c]}"], f"{DEPTS[dept_of[speaker]]} (my department)": dept(dept_of[speaker]),
              "the corners": CORNERS, "the edges": EDGES}
    groups |= {f"everyone {k} me": v for k, v in directional(speaker).items()}
    groups |= ROWS | COLS | {d: dept(k) for k, d in enumerate(DEPTS)}
    groups |= {f"between me and {NAMES[j]}": between(speaker, j) for j in range(N)}
    groups = {k: v for k, v in groups.items() if v}

    for name, g in groups.items():
        for k in range(len(g) + 1):
            yield f"exactly {k} sick in {name}", lambda g=g, k=k: exactly(g, k)
        yield f"an odd number sick in {name}", lambda g=g: counter(g)[0]
        yield f"an even number sick in {name}", lambda g=g: ~counter(g)[0] & ALL
    for name, line in (ROWS | COLS).items():
        yield f"all sick in {name} are connected", lambda line=line: connected(line)
    for (n1, g1), (n2, g2) in combinations(groups.items(), 2):
        yield f"more sick in {n1} than in {n2}", lambda g1=g1, g2=g2: more(g1, g2)[0]
        yield f"more sick in {n2} than in {n1}", lambda g1=g1, g2=g2: more(g2, g1)[0]
        yield f"as many sick in {n1} as in {n2}", lambda g1=g1, g2=g2: more(g1, g2)[1]


def forced(boards, known):
    return {i: not boards & ~SICK[i] for i in range(N)
            if i not in known and (not boards & ~SICK[i] or not boards & SICK[i])}


def declare(boards, i, sick):
    return boards & (SICK[i] if sick else ~SICK[i])


def generate(rng):
    dept_of = [d for d, s in enumerate(SIZES) for _ in range(s)]
    rng.shuffle(dept_of)
    solution = sum(1 << i for i in rng.sample(range(N), rng.randint(8, 11)))
    start = rng.randrange(N)
    known = {start: bool(solution >> start & 1)}
    boards = declare(ALL, start, known[start])
    clues, order, queue = {}, [start], [start]
    while queue:
        speaker = queue.pop(0)
        # flavour once the board is solved, or sometimes while others are still to speak (restart if it stalls)
        if len(known) == N or queue and len(known) > 3 and rng.random() < 0.3:
            clues[speaker] = None
        else:
            options = list(candidate_clues(speaker, dept_of))
            rng.shuffle(options)
            best = None
            for text, make in options:
                truth = make()
                if not truth >> solution & 1:
                    continue
                gain = len(forced(boards & truth, known))
                # prefer a small step forward: one new forced coworker
                # then favour the clue shapes Clues by Sam uses most: plain counts over comparisons and "between"
                weight = (3 if text.startswith("exactly") else 2 if "connected" in text else 1) / (3 if "between" in text else 1)
                score = (gain > 0, -abs(gain - 1), rng.random() * weight)
                if best is None or score > best[0]:
                    best = (score, text, truth)
            if not best[0][0] and not queue:
                return None
            _, text, truth = best
            clues[speaker] = text
            boards &= truth
        for i, sick in forced(boards, known).items():
            known[i] = sick
            boards = declare(boards, i, sick)
            order.append(i)
            queue.append(i)
    return (dept_of, solution, start, order, clues) if len(known) == N else None


def main():
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    while (result := generate(rng)) is None:
        print("restart", file=sys.stderr)
    dept_of, solution, start, order, clues = result
    for r in range(H):
        print("  ".join(f"{NAMES[r * W + c]:>8} {DEPTS[dept_of[r * W + c]][:5]:<5} {'SICK' if solution >> (r * W + c) & 1 else 'well'}"
                        for c in range(W)))
    print(f"\nstarts revealed: {NAMES[start]}\n")
    for i in order:
        print(f"{NAMES[i]:>8} ({'sick' if solution >> i & 1 else 'well'}): {clues[i] or '<flavour>'}")


if __name__ == "__main__":
    main()
