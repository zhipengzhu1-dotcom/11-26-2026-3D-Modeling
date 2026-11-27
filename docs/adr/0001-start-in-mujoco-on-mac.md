# Start in MuJoCo on the Mac instead of Isaac Sim / Isaac Lab

The project was inspired by NVIDIA's Isaac stack (Omniverse, Isaac Sim, Isaac Lab), which needs an NVIDIA RTX GPU on Linux or Windows and does not run on macOS. The working machine is an Apple Silicon MacBook Pro (M4 Max, 36 GB); a personal Windows PC with an RTX 5090, which could run Isaac from the start, is also available. We still train her Controller in MuJoCo on the Mac first. The Mac is where she is built, judged and filmed, so a Controller has to perform in the Mac's MuJoCo whatever trained it; training there first gives early results and Training Records and measures how far the Mac can go; and Isaac Lab's default engine is MuJoCo's own GPU edition, so starting in MuJoCo does not turn away from Isaac. The PC is held back for complete training in Omniverse once the Mac's limit is reached, and nothing is rented.

## Consequences

- A Controller counts only once she performs on the Mac in ordinary MuJoCo, wherever it was trained.
- There is no fixed limit on how long a Training Run on the Mac may take. The human declares the Mac's limit from the Training Records, and that is the point at which complete training moves to the PC.
- Her Simulation Body stays in MuJoCo's own file format and avoids what Isaac Lab's import step drops (ellipsoid shapes, collision filtering by `contype`/`conaffinity`, per-pair contact overrides), so the same body can be taken into Omniverse later.
- What she senses, how she acts, how often she acts and how strong her joints are get written down explicitly, so training in Isaac Lab can be set up to match what was trained on the Mac.
- No released Isaac Lab runs the Mac's MuJoCo 4.0 yet. Which version both machines share is decided when complete training in Omniverse is planned.
