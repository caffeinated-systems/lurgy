# PROTOTYPE: one office-bug puzzle in full

Throwaway sample to react to: the wording, personalities and humour. The board and its logic come from `check.py`, seed 4, and every clue is true and checked. Only the wording here is written by hand.

**Monday · Easy**

> Someone brought a bug back from the weekend. Work out who's sick and send them home before it reaches the kitchen.

## The floor

|       | A                      | B                    | C                     | D                      |
| ----- | ---------------------- | -------------------- | --------------------- | ---------------------- |
| **1** | Aisha · Facilities     | Barry · Facilities   | Carol · HR            | Dev · Marketing        |
| **2** | Erin · IT              | Fergus · Facilities  | Gemma · Marketing     | Hamid · Finance        |
| **3** | Imogen · IT            | **Jas · HR** (well)  | Kev · IT              | Linda · Sales          |
| **4** | Mo · Finance           | Nadia · Sales        | Ollie · Sales         | Priya · Marketing      |
| **5** | Quentin · Finance      | Rosa · Sales         | Steve · HR            | Tariq · IT             |

Jas starts revealed. Six departments, 3 or 4 coworkers each; 8 of the 20 are sick.

## Clues

In the order an office manager who never slips would reveal them. The first line is what the coworker says, and the line under it is the plain explanation.

| Coworker | Says | Plain explanation |
| --- | --- | --- |
| **Jas** · HR · well | "My row has more sick people than the sick people to my right. I've logged it. Formally." | More sick in row 3 than sick to the right of Jas. |
| **Imogen** · IT · sick | "Nobody between me and Quentin is sick. Have you tried turning me off and on again?" | 0 sick between Imogen and Quentin. |
| **Mo** · Finance · well | "Exactly one person below me is sick. I've done the numbers twice." | 1 sick below Mo. |
| **Quentin** · Finance · sick | "Only one of us in Finance is sick. Don't tell anyone I came in." | 1 sick in Finance. |
| **Hamid** · Finance · well | "Exactly one person above me is sick. They sneezed on my monitor." | 1 sick above Hamid. |
| **Dev** · Marketing · sick | "Nobody between me and Priya is sick. Think of me as a soft launch." | 0 sick between Dev and Priya. |
| **Linda** · Sales · well | "Just one person in my row is sick. I'm keeping my distance. Two metres, minimum." | 1 sick in row 3. |
| **Kev** · IT · well | "One sick person between me and Carol. Sounds like a you problem, boss." | 1 sick between Kev and Carol. |
| **Gemma** · Marketing · sick | "Two of us in Marketing are sick. We're calling it engagement." | 2 sick in Marketing. |
| **Priya** · Marketing · well | "Two people in my column are sick. I've drafted a strongly worded email." | 2 sick in column D. |
| **Tariq** · IT · sick | "All four corners are sick. I'm in one. Obviously." | 4 sick in the corners. |
| **Aisha** · Facilities · sick | "Four people in my column are sick. I did wipe the door handles. Once." | 4 sick in column A. |
| **Erin** · IT · sick | "One person to my right is sick. It's not a bug, it's a feature." | 1 sick to the right of Erin. |
| **Fergus** · Facilities · well | "Only one of us in Facilities is sick. I'll get the mop." | 1 sick in Facilities. |
| **Barry** · Facilities · well | "Three people in row 1 are sick. I'm working from the stairwell today." | 3 sick in row 1. |
| **Carol** · HR · sick | "Only one person in HR is sick. I'll need that in writing." | 1 sick in HR. |
| **Steve** · HR · well | "Two people in my row are sick. I can't say who. Policy." | 2 sick in row 5. |
| **Rosa** · Sales · well | "Two people in column C are sick. Not me. I'm made of sterner stuff." | 2 sick in column C. |
| **Ollie** · Sales · well | "One of my neighbours is sick. One out of eight. I like those odds." | 1 sick among Ollie's neighbours. |
| **Nadia** · Sales · well | "Has anyone seen my mug? WORLD'S BEST CLOSER. Someone's been drinking out of it." | Flavour: no clue (and a thread for the week's story). |

<details><summary>Solution (spoiler)</summary>

Sick: Aisha, Carol, Dev, Erin, Gemma, Imogen, Quentin, Tariq. Everyone else is well.

</details>

## The game's own voice (Wordis-style)

The coworkers are characters; the game itself is the one taunting the player, as in Wordis.

- **Not enough evidence** (wrong, or right but not yet forced): "Not enough evidence. Wild accusations are HR's job." · "On what grounds? Vibes?" · "Not enough evidence. Sit down."
- **Hint**: "Fine. Look at Kev. Don't make a habit of this."
- **Solved**: "Everyone sick has been sent home. Took you long enough." · "Office cleared. Have a biscuit."

## Choices this sample makes (react to these)

1. **"Sick" and "well" are always said plainly** in the part that carries logic; the joke goes around them, never instead of them ("coughing", "under the weather" would be ambiguous).
2. **A bare number means exactly that many** ("Two people in my column are sick" means exactly two), explained once in How to play.
3. **Each clue is one sentence of logic plus at most one short joke**, the joke coming from the coworker's department or personality.
4. **Coworkers are mildly cheeky to the office manager; the real taunting belongs to the game**, as in Wordis.
5. **A comparison says "sick" on both sides** ("more sick people than the sick people to my right"), so it never reads as a count of desks.
6. **Flavour can seed the weekly story** (Nadia's mug), but never carries logic.
7. **Names run A to T across the floor**, one per letter, as in the original's alphabetical grid.
