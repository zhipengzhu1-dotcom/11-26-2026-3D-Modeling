# One Controller for all her movements, shown the next moments of the motion

The standard recipe for following a motion (BeyondMimic's, as built into Isaac Lab) trains a separate Controller for each clip and shows it only the current moment of that clip. We train one Controller for all her movements instead: it is shown the next few moments of whichever movement is asked of her, and each Training Run adds a movement while rehearsing the ones she has already passed. We chose this because stage 2 needs one Controller that performs any movement on request, and separate Controllers would have to be merged then. The price is that a shared Controller can fail where a dedicated one succeeds, and that a Controller carried on to a new movement may learn it more slowly than a fresh one.

## Consequences

- Whether a run continues from the last kept Controller or starts from nothing on all movements so far is measured, not assumed. The double peace sign is trained both ways, and the faster way is how the walk and the dance start.
- A dance-only Controller trained from nothing is the one exception, made on the human's call once the shared run has stopped improving. The stage 1 video may be filmed with it, and stage 2 folds the dance back in by having it teach her one Controller.
- In stage 1, an earlier movement that fails after a later one is added is reported and does not hold the later one back. In stage 2 all her movements must pass together.
- Everything else copies Isaac Lab's built-in tracking task, so a Controller can move between the Mac and the RTX 5090 PC: she acts 50 times a second by moving the targets her joints' springs pull toward, and learns with the same learning library and the same size of Controller.
- Two further departures from that recipe are deliberate and are not to be "corrected": her own soft springs in place of its stiff ones (`0005-unseen-properties-tuned-for-anime-feel.md`), and the Sprung Motion as what she trains against (`0009-her-bounce-is-put-into-what-she-trains-against.md`).
- On the PC, Isaac Lab's task has to be adapted to show her the next moments of the motion.
