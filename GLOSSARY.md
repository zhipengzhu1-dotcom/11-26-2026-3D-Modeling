# Character Modeling

Bringing an existing anime character model to life: a body that dances and moves under real physics, a mind that decides and speaks in character, and a bright, clean anime look.

## Language

### Her body and movement

**Simulated Character**:
A character whose body is an articulated set of rigid parts with mass and joints, moved only by joint forces under gravity and contact, so it must balance and can fall.
_Avoid_: Ragdoll, physics character, robot

**Simulation Body**:
The simplified rigid parts and joints that stand in for the character inside the simulator; it is what the Simulated Character physically is.
_Avoid_: Collision mesh, proxy, skeleton

**Controller**:
The trained part of her that, moment by moment, turns what her body senses and the movement asked of her into joint forces. It is learned by training, never written by hand, and is kept, not remade by a Build. She has one Controller for all her movements, and it grows as she learns each new one.
_Avoid_: Policy, network, weights, model

**Visible Mesh**:
The character's drawn surface (skin, clothing, hair), which follows the Simulation Body's motion and takes no part in the simulation.
_Avoid_: Model, body mesh

**Secondary Physics**:
Simulation of the parts that trail the body (hair, skirt, ribbons, soft parts), driven by the body's motion and never driving it.
_Avoid_: MMD physics, cloth sim, jiggle

**Reference Motion**:
An authored or captured movement, such as a dance, a walk or a gesture, as its maker made it, usually for a different body; it is the source of the movement, not what she trains against directly.
_Avoid_: Animation, dance file

**Fitted Motion**:
A Reference Motion resized to her body and her heels with its choreography unchanged. It is the record of the choreography asked of her and what she is shown beside in an Eye Check, not the motion she is guaranteed to perform.
_Avoid_: Retargeted motion, adjusted dance, her version

**Sprung Motion**:
A Fitted Motion as her own soft upper body performs it with her hips carried: the same choreography with the overshoot and settle of her arms, head and chest in it, and her legs unchanged. It is what she trains against and what her straying is measured from, so her Q弹 is asked for and never counted as an error.
_Avoid_: Springy target, bouncy version, training target

**Movement Repertoire**:
The set of distinct movements the Simulated Character can perform on request, such as standing, walking, turning, gesturing and dancing.
_Avoid_: Skills, animations, moveset

**Practice Movement**:
A movement she learns under real physics on her way to the stage 1 dance, performed alone from a standing start and shown as a review clip, not a produced piece. It is not yet part of her Movement Repertoire, which is what she performs on request.
_Avoid_: Rung, warm-up, drill, milestone

**Anime Feel**:
How she moves in the picture when she reads as an anime character: alive (never perfectly still, reacting to her own movement), flexible (movement flowing through many joints and past a real person's range), Q弹 and 可爱. It is judged by an Eye Check, never by likeness to a real person.
_Avoid_: Realism, naturalness, style

**Q弹**:
Springiness in how she moves: a movement ends with a small overshoot and settle, a landing is soft and rebounds, and her soft and trailing parts bounce and settle. It belongs to her body's own movement and to her Secondary Physics alike.
_Avoid_: Bouncy, jiggle, elastic

**可爱**:
Lightness and smallness in how she moves: light on her feet, small quick movements, and poses that close in (knees together, hands near her face, a tilted head).
_Avoid_: Cute, kawaii, moe

### Her mind

**Mind**:
The part of the character that decides what she says and which movement from the Movement Repertoire she performs next.
_Avoid_: AI, brain, agent, controller

**Persona**:
The written account of who the character is (personality, speech habits, history, relationships) that the Mind acts from, drawn from her lore.
_Avoid_: Prompt, character sheet, personality model

**Lore Fidelity**:
How closely the character's words and choices match her established lore, as scored against a rubric derived from that lore.
_Avoid_: Accuracy, in-character score

### Her voice and song

**Voice**:
The one synthetic voice she speaks in, and sings in wherever no official recording of her singing exists. It is designed for her from a written description, never copied from a real person's recordings, and is fixed by kept clips of that one voice, so that she sounds the same every time.
_Avoid_: TTS, voicebank, clone, CV

**Singing Performance**:
She performs a whole song as its singer, standing in place, with the song carried by her singing, her mouth shapes and a singer's gestures. Her mouth following the song of a dance she is dancing is not a Singing Performance, and neither is a short piece from her Songbook.
_Avoid_: Lip sync, karaoke, song number

**Songbook**:
The songs and short pieces prepared ahead of time that she can choose to sing in a Live Session. A song is given as a Singing Performance; a short piece, such as a warm-up scale or one hummed line, is sung in passing. She chooses from it; she does not invent a melody on the spot.
_Avoid_: Playlist, setlist, repertoire

### Making and judging her

**Build**:
Making her parts from the downloaded model: her Simulation Body, her look, her Secondary Physics, her Fitted Motions and her Sprung Motions. A Build governs how she is made, never how she behaves.
_Avoid_: Script, pipeline run, export

**Kept Result**:
Something code cannot remake, which a Build never erases: a Controller, a Training Record, the clips that fix her Voice, her memories of Live Sessions, and the downloaded originals she is built from.
_Avoid_: Artifact, checkpoint, output, save

**Training Run**:
One attempt to train her Controller, from its start to the point it is stopped or judged, including any pauses. A run usually adds one new movement to the ones she already performs and rehearses those alongside it.
_Avoid_: Experiment, session, epoch

**Training Aid**:
Help she is given only inside a Training Run to get her started, such as a helping hand at her hips or an easier heel, which fades to nothing well before the run ends. She never performs with one: every try that counts and every clip shown as her performing is made without it.
_Avoid_: Assist, crutch, helper force, curriculum

**Training Record**:
What is kept from a Training Run so her progress can be read back later: what was trained, when, what it cost in time, and how she improved along the way.
_Avoid_: Logs, metrics, history

**Live Session**:
A stretch of time in which she runs in real time, deciding and moving for herself; nothing she does in it is written in advance.
_Avoid_: Runtime, playback, demo

**Eye Check**:
A judgement the human makes by looking at a still or a clip; where it disagrees with a Measured Check, it wins.
_Avoid_: Visual QA, sign-off, approval

**Ear Check**:
A judgement the human makes by listening to her speak or sing; where it disagrees with a Measured Check, it wins.
_Avoid_: Listening test, audio QA, sign-off

**Measured Check**:
A judgement made from numbers, which can be repeated identically after every Build.
_Avoid_: Test, metric, automated QA

**Guided Hand Fix**:
One manual edit the human makes from written instructions, recorded so that every later Build re-applies it.
_Avoid_: Manual tweak, touch-up, hand edit

**穿模**:
One part of her visibly passing through another part of her, or through the floor, in the picture. Like passing through like (hair through hair, one ruffle through the next) is not 穿模.
_Avoid_: Clipping, interpenetration, poke-through

**Overlap**:
Two parts of her occupying the same space beyond how they sit in her rest pose, whether or not anything shows in the picture. An Overlap is found by a Measured Check; 穿模 is found by an Eye Check.
_Avoid_: Collision, intersection, penetration

**浮空**:
One part of her visibly stopping short of what it should be touching in the picture: a hand hovering over her hip, a shoe hovering over the floor. It is the opposite of 穿模 and, like it, is found by an Eye Check.
_Avoid_: Floating, hovering, levitating

**Gap**:
Two parts of her whose Simulation Body shapes are touching while their drawn surfaces sit apart, whether or not anything shows in the picture. A Gap is found by a Measured Check; 浮空 is found by an Eye Check.
_Avoid_: Clearance, offset, float
