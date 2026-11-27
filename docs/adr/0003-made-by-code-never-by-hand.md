# Everything that makes her is code or written text; nothing is hand-edited

This is a Blender project with no Blender file in it. Everything that makes the character is either code or written text in this repo, and a Build remakes her parts from a local copy of the model whenever needed; no change is made by editing a Blender file by hand. We chose this over a hand-edited master file because the model and everything derived from it cannot enter git, so code is the only part of the work that can be versioned and recovered; because she must eventually run in a Live Session outside Blender, where hand edits would stay trapped; and because one change to her Simulation Body forces everything after it to be redone.

Two things are kept and never erased by a Build, because code cannot remake them: her trained controllers (training takes hours to days and never comes out identical twice) and her memories of Live Sessions. Both stay out of this public repo; where they live and how they are backed up is in `0006-kept-results-live-outside-and-are-backed-up-privately.md`.

## Consequences

- Fixes an artist would make with a brush are made by script first, hidden second, and only as a last resort made as a Guided Hand Fix, which is recorded as data the Build re-applies.
- The human reviews results and does not operate Blender; an open Blender window is for looking only.
- The principle governs how she is made, not how she behaves: nothing she does in a Live Session is written in advance.
