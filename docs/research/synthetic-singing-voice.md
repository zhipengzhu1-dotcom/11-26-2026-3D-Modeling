# A synthetic singing voice for Vodyanitsa

Research for issue #21, "Her singing: what she performs and with whose voice". The question: can she sing with a synthetic voice of her own, a soprano worthy of a prima donna (首席女高音), rather than performing to someone else's recording? And if so, can the same voice also carry her speech in stage 3, and can the singing drive her mouth shapes (あ い う え お ん)?

Researched 2026-11-27. Fixed constraints from the issue: no cloning of her official voice actors; nothing rented (no cloud GPUs); the machines are an Apple Silicon MacBook Pro (M4 Max, 36 GB) and a Windows 11 PC with an RTX 5090; prices are reported, and paying is the human's call.

## How far to trust this

| Label | Meaning |
|---|---|
| **P** | Read this session on the owner's own page, manual, API reference or source code |
| **S** | Read only in a secondary source (a review, a retailer, a wiki, search-result summaries) |
| **U** | Not verified this session (from memory or inference); treat as a lead to check |

Some sites refuse automated fetches (dreamtonics.com, store.dreamtonics.com, voisona.com). Those were read in a real browser instead, so they still count as **P**. Prices change often. Many shown below were Black Friday prices on 2026-11-27.

Nothing in this study was rendered or timed on the project's machines. **Every render time below is unmeasured.** The first Measured Check of any route should be "render one three-minute song on each machine and time it".

## Summary

1. **No tool ships a Mandarin operatic soprano.** Classical soprano voices exist, but each was recorded in another language and sings Mandarin cross-lingually:
   - Synthesizer V: **GALENAIA**, a third-party voice from Eclipsed Sounds made from an opera soprano. Spanish is its native language. **P**
   - Synthesizer V: **Felicia**, an English voice with an "operatic" vocal mode. **P/S**
   - ACE Studio: **Karolyn**, an "Opera female voice, soprano", plus an "Opera" (bel canto) control. **P**
2. **ACE Studio needs the internet.** Rendering runs in the vendor's cloud unless the optional Turbo Mode moves the heavy steps to the local GPU, and it is a subscription (rent-to-own) product. That collides with "nothing is rented". **P**
3. **Synthesizer V Studio 2 Pro runs fully offline on both machines with no GPU.** It costs $99 one time (Black Friday $79) plus about $79 to $100 per voice. **P**. Its voice terms forbid distributing works "under a different name than the original name for the voice database". **P** That bears directly on presenting a Synthesizer V voice as Vodyanitsa (see Usage terms).
4. **Exact sung-phoneme timings come only from the open tools.**
   - VOICEVOX's song API returns every phoneme with its frame length. **P**
   - DiffSinger produces phoneme durations as part of its own pipeline. **P/U**
   - Synthesizer V's script API gives note timings and phoneme symbols but **no phoneme durations**. **P**
   - ACE Studio shows phoneme durations in its editor and exports MIDI with phonemes. Whether that MIDI carries phoneme durations was not verified. **P/U**
   - For any closed tool, the dependable fallback is forced alignment of the rendered vocal against the known lyrics. **U**
5. **One voice for speech and song is easiest as a designed timbre laid over both.** Dreamtonics **Vocoflex** turns speaking or singing into a voice you build from imported samples or generate yourself (X/Y gender pad, random "hue"). It runs in real time on the local CPU and costs $199 (Black Friday $139). **P** The free and open alternative is RVC, with a real-time GUI and support for RTX 50-series cards. **P** No product found sells a matching *Mandarin* talk voice and song voice from one provider.
6. **Live singing is not realistic.** A Live Session can play a song rendered ahead of time, but every route renders the song first. The Mind can *choose* to sing; it cannot improvise a newly sung melody. The real-time pieces found are voice changers (Vocoflex, RVC at 90 to 170 ms latency), not score-to-song synthesizers. **P**

## 1. The tools, one by one

### Synthesizer V Studio 2 Pro (Dreamtonics)

**Runs on.** macOS, Windows and Linux. **U** for the exact OS list; the manual's download and plugin pages show Windows and Mac installers. **P**
- It is fully local. It "renders up to 300% faster than its predecessor ... without requiring a dedicated GPU or acceleration hardware, allowing for seamless offline use." **P** [sv2 manual, Changes Since Version 1](https://sv2.docs.dreamtonics.com/en/prev-version-changes)
- An offline license is available. The editor can be used on **one device at a time**; you can move it between devices by logging in on the new one. **P** [Editor Installation and Activation](https://sv2.docs.dreamtonics.com/en/install)

**Price.** On the [Dreamtonics store](https://store.dreamtonics.com/), 2026-11-27: **P**

| Item | Price | Black Friday |
|---|---|---|
| Editor | $99 | $79 |
| Editor plus one voice | $149 | from $129 |
| Each Dreamtonics voice | $79 | $63 |
| Vocoflex (voice changer, see section 3) | $199 | $139 |
| Synthesizer V plus Vocoflex bundle | $299 | $199 |

A 14-day editor trial and a 7-day voice trial are offered. **P**

**Input.** MIDI, MusicXML "and other singing data formats". MusicXML imports lyrics more accurately than MIDI. **P** [Project Management](https://sv2.docs.dreamtonics.com/en/project)

**Languages.** Cross-lingual synthesis lets any voice sing English, Japanese, Mandarin, Cantonese, Spanish and Korean.
- Korean was added in version 2. **P** [Changes Since Version 1](https://sv2.docs.dreamtonics.com/en/prev-version-changes)
- The rest of the list comes from the Felicia store text and a Dreamtonics statement in search results. **S**
- Italian, Latin and wordless vocalise are not supported languages. Latin or Italian would have to be spelled out phonetically in a supported language. **U**
- Sound On Sound warns that results are best in the voice's original language. **S** [SOS Felicia review](https://www.soundonsound.com/reviews/dreamtonics-felicia)

**Classical or operatic voices.**
- **GALENAIA** (Eclipsed Sounds, third party). "An operatic Spanish-native soprano ... based on the vocals of professional opera singer Laura Gómez", recommended range C3 to D6, six vocal modes (Stable, Supported, Rounded, Throaty, Warm, Nasal). $99.99. **P** [product page](https://eclipsedsounds.com/products/galenaia-synthv2-digital), [voice page](https://eclipsedsounds.com/pages/tc/galenaia)
  - Sound On Sound gave it 5/5 and called it "impressive stuff" for opera or classical music. **S** [SOS review, Aug 2025](https://www.soundonsound.com/reviews/eclipsed-sounds-galenaia-hxvoc)
  - Demo: [SOS audio example](https://soundcloud.com/soundonsound/eclipsed-sounds-galenaia-audio-example-jw-01-1). The product page also has an audio player.
- **Felicia 2** (Dreamtonics). Native English, with vocal modes airy, bright, musical, operatic and powerful. **S** [SOS review, Feb 2025](https://www.soundonsound.com/reviews/dreamtonics-felicia). The store text "Operatic, Powerful" and the opera/classical genre tag also come from secondary sources. **S**
- **Choir Voice Collection 2.** Soprano, mezzo, tenor and baritone voices "with classical, operatic, and cinematic scoring in mind". These are choir voices, not soloists. Collections cost $179 to $537 (Black Friday $139 to $249). **P** for the price, **S** for the description.
- **Cheng Xiao** is aimed at Peking opera, not Western soprano. **S**

**Phoneme timings for lip sync.** The editor has a Phoneme Timing Panel for editing phoneme timing by hand. **P**
- The script API ([reference](https://resource.dreamtonics.com/scripting/)) gives each note's onset and duration (`Note.getOnset`, `Note.getDuration`) and the phoneme symbols the engine chose (`SV.getPhonemesForGroup`). **P**
- `SV.getComputedAttributesForGroup` (since 2.1.1) returns per-phoneme `symbol`, `language`, `activity` and `position`. The last two are described only as consonant activity and position, with no units, and **no phoneme start or end times are exposed**. **P** [SV class reference](https://resource.dreamtonics.com/scripting/SV.html)
- So a script can write note-level timings plus phoneme lists. Vowel boundaries inside a note would have to be estimated, or recovered by forced alignment of the exported WAV. **P/U**
- Scripts run only inside the editor (JavaScript or Lua). **S**
- There is no headless or command-line render. **U**: none was found in the manual's table of contents.

**Live or prepared.** Prepared. It is a desktop editor; nothing found offers an API another program could call for a Live Session. **U**

### ACE Studio 2 (ACE Studio / Timedomain)

**Runs on.** Windows 10 or 11 (22H2 or later) and macOS 13 or later. **P**
- "ACE Studio requires an Internet connection to run." **P**
- Rendering is in the cloud by default. Turbo Mode "offloads the heavy synthesis steps of V2 models to your local CPU/GPU" on an RTX 2060 or newer, or an M1 Max, M2 or newer. **P** [docs export](https://docs.acestudio.ai/llms-full.txt), sections "System Requirements" and "Local Rendering"
- Even with Turbo Mode the app needs to be online. **P** It is a cloud-tied subscription, which conflicts with the "nothing rented" rule unless the human decides a software subscription is not "renting".

**Price.** [pricing page](https://acestudio.ai/pricing), 2026-11-27: **P**

| Plan | Price | Includes |
|---|---|---|
| Artist (rent-to-own) | $16.58 a month (20% off $20.73) | 160+ voices, 1 voice-cloning slot for singing, 1 for the voice changer, 2,500 credits a month |
| Artist Pro (rent-to-own) | $22 a month (20% off $27.50) | 5 voice-cloning slots for singing, 10 for the voice changer, 5,000 credits a month |

- The page labels both prices "billed yearly". **P**
- Rent-to-own "automatically convert[s] into a lifetime license" after the subscription term. A perpetual license comes from 2 years' subscription or a purchase. **P**
- The December 2025 launch lifetime prices of $398 (Artist) and $528 (Artist Pro) come from secondary sources. **S**

**Input.** MIDI and MusicXML (.mxl or .musicxml), with lyrics, plus audio-to-MIDI. **P**

**Languages.** The Verse 2.7 model sings English, Spanish, Italian, French, Portuguese, Korean, Chinese and Japanese. **P** Italian is the notable extra for opera. Latin is not listed. **P**

**Classical or operatic voices.**
- The docs recommend "Karolyn - Opera female voice, soprano", with Aaron (opera tenor) and Robert (opera baritone). **P**
- Voices that support it get an "Opera" control that "injects classical bel canto singing techniques into the voice ... adds brilliant vibrato and dramatic tone". It is "ideal for singing classical arias". **P**
- There is also a "Chinese Opera" control. **P**
- No public Karolyn demo link was found. **U**

**Phoneme timings.** The Breath & Phoneme tab "splits every note into its phonemes, so you can see and adjust exactly how long each sound lasts". **P**
- MIDI export can "include lyrics and phonemes". **P** Whether phoneme durations survive in that MIDI or in the `.ufdata` export is not documented. **U**
- No public API was found. **P**: none mentioned in the docs.

**Speech.** ACE's "Speech Generator" is a third-party service, "performed by ElevenLabs or by SeedAudio". It does not use the same voice as the singing. **P**

**Live or prepared.** Prepared. With pre-rendering on, local rendering "operates in real-time (after changes)" inside the editor. That is an editing convenience, not a live API. **P**

### VOCALOID 6 and VOCALOID 7 (Yamaha)

- **VOCALOID7 replaced VOCALOID6** on 2026-11-11. Sales of VOCALOID6 stopped: "With the release of the new VOCALOID7, sales of previous versions have been discontinued." **P** [VOCALOID6 specs](https://www.vocaloid.com/en/vocaloid6/specs/)
- The VOCALOID7 Editor costs $129. Upgrades cost $69, or $39 until 2026-12-20. **S** (consistent across several news reports; Yamaha's English release was not read)
- **Languages:** Japanese, English and Chinese. **P** (V6 specs), **S** (V7)
- **OS (V6):** macOS 14, 15 or 26, with Apple Silicon listed; Windows 11 22H2 or later. **P**
- **Input (V6):** VPR, VSQX and MIDI. MusicXML is not listed. **P**
- **Voices:** the VOCALOID7 voicebanks shown are LUCI, NurseRobot_TypeT, GekiyakuV, KazehikiV and AI Megpoid. None is a classical or operatic soprano. **P** [vocaloid.com](https://www.vocaloid.com/en)
- **Verdict:** pop and character voices only. Not a soprano candidate.
- Phoneme-timing export and API were not researched further. **U**

### CeVIO AI and VoiSona (Techno-Speech)

- **VoiSona (song) and VoiSona Talk** are free editors for Windows and macOS (song also on iOS), with paid voice libraries. **P** [voisona.com/song](https://voisona.com/song/), [voisona.com/talk](https://voisona.com/talk/)
- The song editor takes MIDI and MusicXML. Both editors let you "shift the starting time line of each phoneme". **P**
- The song voice list is long and mostly pop or character voices. None is labelled classical. **P**
- CeVIO AI handles both song and talk. **S**
- The same character is sometimes sold as talk only or song only, so a matched pair is not guaranteed. **S**
- Prices, Mandarin support, and whether VoiSona Talk exposes phoneme timings through an API were not verified. **U**
- **Verdict:** a possible source of a matched talk and song pair in Japanese, not a soprano candidate.

### VOICEVOX (song feature)

- Free, "商用・非商用問わず無料" (free for commercial and non-commercial use) subject to each character's own terms. Runs on Windows, Mac and Linux. Version 0.26.x. **P** [voicevox.hiroshiba.jp](https://voicevox.hiroshiba.jp/)
- **Best timing data of any tool found.** The local HTTP engine's `/sing_frame_audio_query` takes notes (MIDI key, frame length, lyric) and returns a `FrameAudioQuery`. Its `phonemes` list gives each phoneme with its `frame_length` and `note_id`, at 93.75 frames per second by default. **P** ([engine README](https://github.com/VOICEVOX/voicevox_engine), [model.py](https://github.com/VOICEVOX/voicevox_engine/blob/master/voicevox_engine/tts_pipeline/model.py))
  - Talk queries also return consonant and vowel lengths per mora. **P**
  - Any talk voice can sing through the "humming" route, using a singing-teacher style for the query and a `frame_decode` style for the sound. **P**
- **Languages:** Japanese, one mora of kana per note. **P/U**
- **Verdict:** the voices are anime and pop characters, not a soprano. It is useful as a free, fully local prototype of the lip-sync pipeline, because the timings come straight out of the API.

### NEUTRINO

- Free AI singing from MusicXML. The voices are Japanese character libraries (Zundamon, Tohoku Kiritan, No.7 and others). None is described as classical. **P** [studio-neutrino.com](https://studio-neutrino.com/)
- **Desktop downloads are suspended** "for the time being" while the developer reviews security. Only the browser version (Neutrino Orbit) remains. **P** [notice, 2026-11-22](https://studio-neutrino.com/news/software-distribution-suspension/)
- NEUTRINO has historically written timing label files. **U**
- **Verdict:** ruled out for now. It cannot be installed locally, and it has no soprano.

### OpenUtau with DiffSinger voicebanks

- **OpenUtau** is MIT licensed. Release 0.1.576 came out on 2026-10-20 with builds for `osx-arm64`, `win-x64` and others. **P** [GitHub](https://github.com/stakira/OpenUtau)
  - It imports MusicXML, MIDI, UST, VSQx, SVP and ufdata. **P** (source `OpenUtau.Core/Format/`)
  - It runs DiffSinger through ONNX Runtime: DirectML on Windows (which covers the RTX 5090), CUDA on Linux, CoreML or WebGPU on macOS. **P** (source `Util/Onnx.cs`)
- **DiffSinger** (OpenVPI) is Apache-2.0, version 2.5.1, and its repository was still active in November 2026. **P** [GitHub](https://github.com/openvpi/DiffSinger)
  - It ships a Mandarin dictionary. Community voicebanks exist for Mandarin, Japanese, English and more. **S**
- **No classical, operatic or bel canto DiffSinger voicebank was found.** **S** (several searches)
  - Training one means recording a consenting soprano, or licensing a dataset, then labelling it. That is a project in itself. **U**
  - Recording a real singer is cloning a real person, which is allowed only with that person's consent. It is not one of the official voice actors.
- **Phoneme timings.** DiffSinger predicts a duration for each phoneme as an explicit step (`ph_dur` in its `.ds` files). Running it from Python or ONNX outside OpenUtau would give exact vowel start and end times for the mouth shapes. **U** (from knowledge of the project; not re-read this session)
  - OpenUtau itself has no `.lab` export. **P**: none in source, except for the older ENUNU path.
- **Live or prepared.** Fully local and scriptable, so it is the only singing synthesizer here that a Live Session could call directly. Faster-than-real-time rendering on the RTX 5090 is likely but **unmeasured**.

### Newer open models

- **SoulX-Singer** (Soul AI Lab, Apache-2.0). A zero-shot singing synthesizer driven by "score-conditioned (MIDI notes)" or melody (F0) input. Trained on 42,000+ hours of Mandarin, English and Cantonese. **P** [GitHub](https://github.com/Soul-AILab/SoulX-Singer)
  - It clones the timbre of a reference clip. **P** A *designed* (non-cloned) reference timbre would be needed to stay within the rules.
  - Easy MIDI input is still on its to-do list. **P**
  - Demo: [soul-ailab.github.io/soulx-singer](https://soul-ailab.github.io/soulx-singer/). Classical soprano quality is unknown. **U**
- **ACE-Step 1.5** (MIT) is a generative song model. It writes whole songs from a text prompt and lyrics in 50+ languages. It does **not** follow a given score. Its "LRC" output gives lyric timestamps, not phonemes. **P** [GitHub](https://github.com/ace-step/ACE-Step-1.5)
  - **Verdict:** not suitable when she must sing a set melody. Cloud song generators (Suno and similar) were not researched; they break the no-rent rule anyway.

## 2. Phoneme and note timings

| Tool | Timing she can get | Source |
|---|---|---|
| VOICEVOX | Exact: every phoneme with frame length (93.75 fps), from a local HTTP API | **P** |
| DiffSinger (run directly) | Exact: predicted phoneme durations | **U** |
| ACE Studio | Visible and editable per phoneme. MIDI export "with phonemes", durations unclear. No API | **P/U** |
| Synthesizer V | Note onsets and durations plus phoneme symbols through scripts. No phoneme durations | **P** |
| VoiSona | Editable per-phoneme start lines in the editor. Export or API not checked | **P/U** |
| Any tool | Forced alignment of the rendered vocal against the known lyrics and phonemes (for example the Montreal Forced Aligner) | **U** |

Mapping onto her mouth shapes is straightforward once vowels have times: Mandarin finals and Japanese kana reduce to あ い う え お, and closed or nasal codas to ん. **U** Sustained operatic vowels make this easier than speech, since vowels dominate.

## 3. One voice for speech and song

- **No single-provider pair for Mandarin was found.**
  - VoiSona and CeVIO sell some talk and song voices of the same character, mostly Japanese. **P/S**
  - VOICEVOX characters both talk and hum, Japanese only. **P**
  - ACE Studio's speech comes from ElevenLabs or SeedAudio, a different voice from the singing. **P**
- **Designed timbre over both (the strongest option):**
  - **Vocoflex (Dreamtonics).**
    - It is a "Real-Time AI Voice Changer & Creator Plugin" with "local CPU real-time processing". **P** [dreamtonics.com/vocoflex](https://dreamtonics.com/vocoflex/)
    - It changes voices as you "start speaking or singing". **P**
    - You can import voice samples, blend 40 licensed presets, set gender on an X/Y pad, and "change the timbre by randomizing the hue". **P** That is a way to make a timbre that belongs to no single real person.
    - Price: $199 (Black Friday $139). **P**
    - It runs as a plugin, so a Live Session would need a plugin host. **U**
  - **RVC** (MIT). Version 2.3.260718, July 2026. It has a real-time GUI with "an end-to-end latency of 170ms", or 90 ms with ASIO. There is an install path for the RTX 50 series (CUDA 12.8); macOS is CPU only, or DirectML on Windows. **P** [GitHub](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)
    - It needs a target voice to train on. Whose recordings those are is the whole rights question (section 6).
  - **so-vits-svc** and **Seed-VC** are archived on GitHub. **P** Not recommended.
- **Mandarin talk side.** Qwen3-TTS (Apache-2.0) has a 1.7B "VoiceDesign" model that makes a voice from a written description. Chinese is among its 10 languages. **P** for the licence (repository), **S** for the feature details.
  - This is a route to a designed Mandarin speaking voice. Turning it into a singing voice still needs one of: voice conversion trained on that designed voice, or SoulX-Singer prompted with it. Both are **U** for quality.
- **Watch the Synthesizer V terms here.** Training any machine-learning model on Synthesizer V output is forbidden (see section 4). So "render her songs in GALENAIA, then train RVC on them to get her talk voice" is not allowed.

## 4. Usage terms

**Dreamtonics' own voice databases** (Felicia, Natalie and so on): **P** [dreamtonics.com/terms](https://dreamtonics.com/terms)
- "Use this voice database however you want for private use."
- "Distribute or publish works created with this voice database for commercial or non-commercial purposes, with no limitation on the revenue." A fan video is fine.
- You cannot "Distribute works created with this voice database under a different name than the original name for the voice database."
  - This is the key clause for character use. Publishing a song credited as Vodyanitsa singing, with Felicia's voice, appears to conflict. Private use is unrestricted.
  - Whether crediting "voice: Felicia (Synthesizer V)" in the description satisfies it is a question for Dreamtonics. **U**
- You cannot "Train machine-learning systems using audio generated from this voice."
- "Voice databases from our licensed partners are distributed under different terms." GALENAIA is a partner voice, and its own licence was not found online. The Eclipsed Sounds shop terms are generic retail terms. **P/U**

**ACE Studio:** **P** [docs, "License & Copyright"](https://docs.acestudio.ai/llms-full.txt)
- "ACE Studio does not claim copyright ownership over outputs generated by users."
- "You may use outputs created with ACE Studio in commercial or non-commercial projects, unless a specific feature, model, voice, instrument, or third-party service states otherwise."
- Most pre-made voices are royalty-free. A few Vsinger voices (Luo Tianyi and others) and one Nylis voice need a third-party licence for commercial use.
- **No clause about presenting a voice as a different character was found** in the docs. That is not proof none exists in the full Terms of Service, which were not read. **U**

**VOICEVOX:** free for commercial and non-commercial use, but "each character's terms" apply. **P** Per-character credit and character-use rules were not read. **U**

**VOCALOID, VoiSona and CeVIO:** per-voicebank character guidelines exist (search results show per-voice guideline PDFs on voisona.com) but were not read. **U**

## 5. Live or prepared, and render times

- **Prepared is the realistic plan.** The Mind can decide in a Live Session to sing one of her prepared songs. The song itself is rendered in advance and kept as a Kept Result, with its timing file.
- **Near-live singing synthesis** is possible only with the local, scriptable models (DiffSinger, VOICEVOX, SoulX-Singer), and only from a score the Mind already has. **U**
- **Real-time voice conversion** (Vocoflex, RVC) can re-voice audio as it plays. That would let a prepared vocal, or her live TTS speech, be re-timbred on the fly. **P**
- **Render times for a three-minute song:**
  - ACE-Step claims under 10 seconds per full song on an RTX 3090, but that is song generation, not score singing. **P** (vendor claim)
  - Synthesizer V claims "up to 300% faster" than version 1, with no absolute figures. **P** (vendor claim)
  - No tool's three-minute render time on an M4 Max or an RTX 5090 was found. **U**

## 6. Singing voice conversion (the third route)

- **What it needs:**
  - An isolated vocal from the recording. Stem separation such as the MSST models bundled with RVC can extract it. **P**
  - A conversion model of the target timbre. RVC trains on minutes of clean voice. **U** on the exact amount
  - The RTX 5090 for training. Conversion itself can run on either machine. **P/U**
  - Alternatives: SoulX-Singer-SVC converts zero-shot from a reference clip, without lyrics or MIDI. **P** Vocoflex converts in real time from a built timbre. **P**
- **Quality for a classical soprano:** the result keeps the original singer's phrasing, vibrato and breath, which is the point. Weak spots are the sustained high register and operatic vibrato, where these models tend to buzz or lose pitch. **U** No benchmark of these models on operatic singing was found.
- **Rights:**
  - Converting a commercial recording still uses (a) the composition and lyrics and (b) the performer's and label's recording, minus only the timbre.
  - Private listening is the least exposed use. Posting a fan video re-uses the recording and performance, just as posting the original would. **U** (not legal advice)
  - The target timbre must not be the official voice actors' or any non-consenting person's. Training on Synthesizer V output is banned by its terms. **P**
  - Some VOICEVOX and VoiSona character terms are also likely to restrict this. **U**
  - The cleanest version of this route is a recording the project owns or has permission to use: the human singing, or a commissioned singer.

## The routes that remain

| Route | Classical soprano | Mandarin | Local, no rent | Timings for the mouth | Use as Vodyanitsa | Cost |
|---|---|---|---|---|---|---|
| **A. Synthesizer V 2 + GALENAIA (or Felicia)**, Vocoflex for the speech match | Best found (a real opera soprano's voice) | Cross-lingual from Spanish or English | Yes, offline, CPU | Notes via script; vowels by forced alignment | Dreamtonics voices: published works must keep the voice's name. GALENAIA: terms not found | $99 + $99.99 (+ $199 Vocoflex), before sales |
| **B. ACE Studio 2 + Karolyn and the Opera control** | Good on paper (an opera soprano voice plus a bel canto control) | Yes, plus Italian | **No**: needs the internet; cloud rendering unless Turbo Mode | Editable per phoneme; export unclear | No character clause found | About $199 to $264 a year, rent-to-own |
| **C. Open stack: DiffSinger or SoulX-Singer + RVC or Vocoflex** | Unproven; no operatic voicebank exists | Yes | Yes | Exact (DiffSinger) | MIT or Apache code; the voice's rights depend on whose data | Free, but a big build |
| **D. Perform to a human recording**, optionally re-voiced | Real singer | Whatever the recording is | Yes | Forced alignment | The recording's rights remain | Free |

## Open questions to check before deciding

1. GALENAIA's own end-user licence: private use, fan videos, and use under a character name.
2. Whether ACE Studio's Turbo Mode can render with the network down after login. The docs say the app needs the internet; this was not tested.
3. Whether an ACE Studio MIDI or ufdata export contains phoneme durations.
4. Real Mandarin quality of GALENAIA, Felicia and Karolyn. That needs an Eye Check by ear: render the same Mandarin phrase in each during the free trials (Synthesizer V 14 days; ACE Studio has a free tier).
5. The three-minute render time on the M4 Max and the RTX 5090, as a Measured Check.
