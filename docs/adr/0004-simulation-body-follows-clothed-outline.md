# Her Simulation Body follows her clothed outline where clothing is stiff or close-fitting

Her collision shapes are deliberately bulkier than her body. Where clothing is stiff or close-fitting (bodice, collar, sleeve cuffs), the Simulation Body follows the clothed outline, so her hands and limbs physically cannot enter those parts. This removes body-through-body 穿模 at its source instead of patching it in the picture afterwards. Loose parts (skirt, hair, hanging sleeve cloth) stay Secondary Physics.

A part is loose or stiff by what it is, not by which bone the model binds it to. Hair, skirt and hanging sleeve cloth get no collision shape even where the model binds them rigidly to her head, hips or forearms, and the ornaments that sit on her hair get none either: her head's shape is her skull and face. The first look at her Simulation Body tried the other reading, a shape for everything bound to a body bone; it wrapped her head in her hair and her forearms in her sleeves, and her own shapes shoved her off the motion.

## Consequences

- She is bulkier than the body her Reference Motion was made for. Where a dance asks for a pose her body cannot reach, she departs from it; physical validity outranks matching the Reference Motion.
- A trained controller is tied to the shapes it was trained on, so changing this outline later means retraining.
- Her hands can pass through her hair and the ornaments on it in the picture. That is left to her Secondary Physics and to the 穿模 checks, not to her Simulation Body.
