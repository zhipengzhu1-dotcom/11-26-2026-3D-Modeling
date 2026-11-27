# Kept Results live outside the project folder and are backed up to a private repo

Code cannot remake her Kept Results (the downloaded originals, her Controllers, her Training Records, her memories of Live Sessions), and the licence keeps them out of this public repo, so they need a home and a backup of their own. They live in one folder outside the project folder, `~/Vodyanitsa/`, because the ignored folders inside the project can be erased by a Build or a git clean-up and cannot be seen from other working copies. That folder becomes the working copy of a private GitHub repo, which is both the backup and the way the RTX 5090 PC downloads an exact copy. The human chose this over an automatic copy to the PC with an encrypted copy in iCloud Drive.

## Consequences

- The private repo holds the model itself. It is never made public and never shared, and the same goes for the private Google Drive folder below; one wrong visibility setting would breach the licence.
- The human creates the private repo, from a written checklist, before the first long Training Run. Until then the downloaded originals exist only on the laptop, and that risk is accepted.
- A Kept Result too big for the private repo goes to a private Google Drive folder, and the private repo keeps a small note saying where it is with its fingerprint. Nothing lives in both places. This is decided the first time something is actually too big.
- Clips are left out of the backup and live only on the Mac. Losing the laptop loses the pictures of her progress, not her Controllers, scores or notes.
- Every Kept Result carries a note written when it is made: code version, date, machine, settings, and fingerprints of the Simulation Body and Fitted Motion used. A Controller also keeps beside it the exact Simulation Body and Fitted Motion it was trained on, because a later Build may not remake them identically and a Controller only works on the body it was trained on.
- A Training Run over about ten minutes starts only from committed code, so the code version in its note names code that really existed. Shorter trials may run from uncommitted code, are marked as such, and never count as a real Controller.
- The agent never deletes a Kept Result on its own. Each Training Run keeps its final Controller, its best one and a handful along the way; in-between saves are thinned only after the human has judged the run.
- A Guided Hand Fix that is only numbers (which points, which weights, how far) lives in this public repo beside the code that applies it. Only one that carries her actual shapes or texture pixels is a Kept Result.
- Once the private repo exists, the sync runs by itself at the end or pause of every Training Run and at least once a day during a long one, so at most a day of training can be lost. A failed sync warns and never stops training.
- A restore is proven when the private repo is set up, and again whenever the folder layout changes: a fresh download into a scratch folder, beside this code, must still play a kept Controller.
