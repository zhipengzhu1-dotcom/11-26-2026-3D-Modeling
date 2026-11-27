# Her Simulation Body follows her clothed outline where clothing is stiff or close-fitting

Her collision shapes are deliberately bulkier than her body. Where clothing is stiff or close-fitting (bodice, collar, sleeve cuffs, head ornaments), the Simulation Body follows the clothed outline, so her hands and limbs physically cannot enter those parts. This removes body-through-body 穿模 at its source instead of patching it in the picture afterwards. Loose parts (skirt, hair, hanging sleeve cloth) stay Secondary Physics.

## Consequences

- She is bulkier than the body her Reference Motion was made for. Where a dance asks for a pose her body cannot reach, she departs from it; physical validity outranks matching the Reference Motion.
- A trained controller is tied to the shapes it was trained on, so changing this outline later means retraining.
