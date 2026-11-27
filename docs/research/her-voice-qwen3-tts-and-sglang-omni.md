# Her voice: Qwen3-TTS and SGLang-Omni

The question: her voice should come closer to her Chinese in-game voice, built with **Qwen3-TTS**, and **SGLang-Omni** should be explored. What does each Qwen3-TTS mode take as input (the standing rule: no cloning of her official voice actors), where does it run on the project's two machines and how fast, what is SGLang-Omni, and how can the same voice carry her songs, including her Russian, lyric-coloratura soprano aria?

Researched 2026-11-27. Builds on `docs/research/synthetic-singing-voice.md` (branch `research/synthetic-singing-voice`), `docs/research/songs-and-their-terms.md` and `docs/research/vodyanitsa-lore.md`, and does not repeat them. Machines: MacBook Pro M4 Max, 36 GB; Windows 11 PC with an RTX 5090 (32 GB VRAM), 64 GB RAM. Nothing rented.

## How far to trust this

| Label | Meaning |
|---|---|
| **P** | Read this session on the owner's own page: repository README, model card, paper, official docs, the maintainers' own replies in their issue tracker, a court's own site |
| **S** | Read only in a secondary source (news, a blog, a third party's benchmark) |
| **U** | Not verified this session (memory or guesswork); a lead to check |
| **I** | My own inference from what was read |

A third-party benchmark is labelled **S** even when it is the only measurement there is. Nothing in this study was run or timed on the project's machines. **Every speed figure below is somebody else's measurement.**

## Summary

1. **Qwen3-TTS has three modes, and only one of them takes a recording.** VoiceDesign takes text plus a written description of the voice. CustomVoice takes text, one of nine preset speakers, and (1.7B only) a style instruction. Base (cloning) takes a reference recording plus its transcript. **P**
2. **A designed voice is made reusable through the cloning mode.** The official README's own workflow: design a short clip with VoiceDesign, turn that clip into a reusable `voice_clone_prompt` with the Base model, and generate every later line from that prompt. The only recording ever cloned is the project's own synthetic clip. **P** That clip is a Kept Result: it *is* her voice.
3. **Russian is one of the ten languages** (Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian). The paper's Russian word error rate is 3.2% against 0.9% for Chinese. **P**
4. **No timings, no singing.** Qwen3-TTS returns audio only, with no word or phoneme timestamps. The companion **Qwen3-ForcedAligner-0.6B** (Apache-2.0) gives word or character timestamps in 11 languages, Chinese and Russian included. **P** Nothing official says Qwen3-TTS can sing or hum. **P** (absence)
5. **Speed depends entirely on the serving code.** The plain `qwen-tts` package is a demo and batch tool without audio streaming, and is slower than real time even on an RTX 5090 under Windows. **P** (maintainers and issue reports). Optimised stacks reach about 50 ms to first sound on an RTX 5090 (vLLM-Omni, Linux) and run several times faster than real time. **S**. On Apple Silicon, MLX ports run faster than real time. **S**
6. **SGLang-Omni** is the SGLang project's (sgl-project, LMSYS) serving runtime for speech and omni models, started January 2026, v0.2.0 on 2026-10-27. It serves Qwen3-TTS in all three modes with streaming over an OpenAI-style API, plus Qwen3-Omni, MiniCPM-o 4.5 and a ready-made ASR → LLM → TTS voice-assistant cascade whose voice is a **Qwen3-TTS Base clone prompt**. **P** It targets **Linux with an NVIDIA GPU**; Windows and WSL2 are not mentioned; on a Mac it runs only ASR models. **P**
7. **Speech-in, speech-out models are not a better route to her voice.** Qwen3-Omni offers three preset voices only and needs about 79 GB of GPU memory in BF16. **P** MiniCPM-o 4.5 can clone a voice from a reference clip (so it could be fed her designed clip), but speaks only Chinese and English. **P**
8. **One voice for speech and song** still means: sing with a synthesiser or a real singer, then convert the timbre to her designed voice (RVC trained on Qwen3-TTS output, SoulX-Singer-SVC, or Vocoflex), or prompt SoulX-Singer with a clip of her voice. No source tested any of these on sustained high operatic soprano notes. **P** (absence) / **U**
9. **Russian singing:** no commercial synthesiser from the earlier study sings Russian (Synthesizer V 2, ACE Studio 2, VOCALOID, SoulX-Singer). OpenUtau has a built-in DiffSinger Russian phonemizer, so Russian DiffSinger voicebanks are supported, but no operatic one was found. **P/S**
10. **Law:** the Shanghai Pudong court (reported 2026-09-10) held that the voices of 63 Genshin characters, *cloned from about a minute of game audio*, are commercial identifiers of the game, and awarded miHoYo ¥750,000 under unfair-competition law. **S**. The Supreme People's Court's opinion of 2026-09-07 protects a natural person against a synthetic voice made *by using their voice as training material* that can identify them. **P** Neither text addresses a voice designed from words that merely ends up sounding similar.

## 1. Qwen3-TTS, precisely

Released 2026-01-22 by Alibaba's Qwen team. Repository [QwenLM/Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS); paper [arXiv 2601.15621](https://arxiv.org/abs/2601.15621). The repository's last commit was 2026-03-17 ("fix finetuning bug"); no newer open model was found. **P** (GitHub API)

### Released models

All six were published on Hugging Face on 2026-01-21. **P** (Hugging Face API)

| Model | Mode | Instruction control | Notes |
|---|---|---|---|
| Qwen3-TTS-12Hz-1.7B-VoiceDesign | Voice from a written description | Yes | Card shows about 2B parameters (BF16) |
| Qwen3-TTS-12Hz-1.7B-CustomVoice | Nine preset speakers + style instruction | Yes | |
| Qwen3-TTS-12Hz-0.6B-CustomVoice | Nine preset speakers | **No** | |
| Qwen3-TTS-12Hz-1.7B-Base | Clone from a reference recording; base for fine-tuning | No | |
| Qwen3-TTS-12Hz-0.6B-Base | Same, smaller | No | |
| Qwen3-TTS-Tokenizer-12Hz | Speech codec (encode/decode) | n/a | |

Source: README model table. **P**

- The paper also describes **25 Hz** models (1.7B Base, VoiceEditing, CustomVoice; 0.6B Base, CustomVoice) and says "we release both tokenizers and models under the Apache 2.0 license". **P** (paper). **No 25 Hz model is on Hugging Face** under the Qwen organisation. **P** (API listing). Third-party coverage says Qwen called it "forthcoming". **S**
- The hosted Qwen3-TTS-Flash and -Realtime models in Alibaba Cloud Model Studio are separate, paid, cloud-only products. **S** Out of scope under the no-rent rule.

### What each mode takes as input

From the README's code and text. **P**

| Mode | Call | Inputs | Cloning? |
|---|---|---|---|
| **VoiceDesign** | `generate_voice_design` | `text`, `language`, `instruct` (a free-text description of the voice). README example: 「体现撒娇稚嫩的萝莉女声，音调偏高且起伏明显，营造出黏人、做作又刻意卖萌的听觉效果。」 | No recording at all |
| **CustomVoice** | `generate_custom_voice` | `text`, `language`, `speaker` (one of the presets), optional `instruct` (1.7B only), e.g. 「用特别愤怒的语气说」 or "Very happy." | No recording |
| **Base (voice clone)** | `generate_voice_clone`, `create_voice_clone_prompt` | `ref_audio` (file, URL, base64, or array) **and** `ref_text`, its transcript. With `x_vector_only_mode=True` only a speaker embedding is used and no transcript is needed, "but cloning quality may be reduced" | **Yes**: this mode copies the voice in whatever recording it is given |

- The README's feature list says "3-second rapid voice clone"; no minimum or recommended reference length is stated. **P**
- The nine presets (CustomVoice): Vivian ("Bright, slightly edgy young female voice", Chinese), Serena ("Warm, gentle young female voice", Chinese), Uncle_Fu, Dylan (Beijing dialect), Eric (Sichuan dialect), Ryan, Aiden (English), Ono_Anna ("Playful female voice with a light, nimble timbre", Japanese), Sohee (Korean). Any speaker may speak any supported language; the native language is recommended. **P**
- **What this means for the rule.** VoiceDesign and CustomVoice never see a human recording. Base copies whoever is in `ref_audio`. Fed one of her official lines, it would clone her voice actor, which the rule forbids. Fed a clip the project made with VoiceDesign, it clones a synthetic voice that belongs to no one. **I**

### Making her sound the same every time

- The README describes exactly this case: "If you want a designed voice that you can reuse like a cloned speaker... (1) use the VoiceDesign model to synthesize a short reference clip that matches your target persona, (2) feed that clip into `create_voice_clone_prompt` to build a reusable prompt, and then (3) call `generate_voice_clone` with `voice_clone_prompt`... This is especially useful when you want a consistent character voice across many lines." **P**
- The README does not say whether VoiceDesign gives the same voice twice for the same description. Its recommending the clip-and-clone route suggests it does not. **U**
- So the designed reference clip (and the saved prompt built from it) is a **Kept Result**: lose it and her voice is gone. **I**
- Fine-tuning a Base model on a larger set of her designed lines is also possible (`finetuning/` folder). **P**
- One limitation: the Base (clone) models have **no instruction control**. **P** Style then comes from the text and from the reference clip itself. A maintainer recommends cloning "audio with the desired style" for this reason. **P** ([issue #16](https://github.com/QwenLM/Qwen3-TTS/issues/16)) A second reference clip in a different mood (teasing, cool, triumphant) would give the Mind a second prompt to choose. **U**

### Languages and quality

- Ten languages, as listed in the summary, plus "multiple dialectal voice profiles". **P**
- From the paper's multilingual table (Base models, word error rate and speaker similarity): **P**

| Language | 12Hz-1.7B WER | 12Hz-1.7B SIM | MiniMax WER | ElevenLabs WER |
|---|---|---|---|---|
| Chinese | 0.928 | 0.799 | 2.252 | 16.026 |
| Russian | 3.212 | 0.792 | 4.281 | 3.878 |

- Chinese is its strongest language (Seed-TTS test-zh WER 0.77 for 1.7B-Base). **P** Russian speech is about three times less accurate by this measure but still ahead of the two commercial systems in the table. **P**
- Voice design scores (InstructTTSEval, 12Hz-1.7B-VD, APS / DSD / RP): Chinese 85.2 / 81.1 / 65.1, English 82.9 / 82.4 / 68.4, which the paper calls "new state-of-the-art among open-source models". **P**
- A known issue: a Base model given a Japanese reference read Mandarin with Japanese-like pronunciation ([issue #401](https://github.com/QwenLM/Qwen3-TTS/issues/401), open). **P** Her reference clip should be in Mandarin. **I**

### Emotion, laughter and her way of speaking

- Instructions control "timbre, emotion, and prosody". **P**
- **Laughter comes from instructions.** A maintainer, answering why "very happy" output contained laughs: "the model simulates natural human speech behavior by incorporating laughter. If you prefer the model not to generate laughter, you can try refining the instruction". **P** ([issue #16](https://github.com/QwenLM/Qwen3-TTS/issues/16))
- Whether written 嘻嘻 or 哼 in the text are voiced as laughs or read as syllables is **not documented**. **U** Another user in the same thread could not get onomatopoeia (sighs, tongue clicks) reliably. **P** (user report)
- Her Persona's laugh palette (嘻嘻 mischievous, 呵 wry, 哼 mock pique, from `vodyanitsa-lore.md`) is a good first Eye Check script (by ear). **I**

### Streaming and delay

- README: "can output the first audio packet immediately after a single character is input, with end-to-end synthesis latency as low as 97ms." **P**
- The paper's latency table (internal vLLM engine, unnamed GPU, concurrency 1): 12Hz-0.6B 97 ms, RTF 0.288; 12Hz-1.7B 101 ms, RTF 0.313. **P**
- **The official `qwen-tts` package does not stream audio.** Maintainer: "our `qwen-tts` package primarily focuses on enabling quick demos, rapid prototyping, and batch offline inference. For text-level and speech-level streaming capabilities, ongoing development... will be mainly driven by the **vLLM-Omni** community." **P** ([issue #10](https://github.com/QwenLM/Qwen3-TTS/issues/10))
- The README says vLLM-Omni had day-0 support, at first "only offline inference". **P** (That note dates from January; a later third-party post used vLLM-Omni streaming, see section 2.)

### Timings for lip sync

- Qwen3-TTS returns waveforms only; no word or phoneme timestamps in the README or paper. **P** (absence)
- **Qwen3-ForcedAligner-0.6B** (released 2026-01-29 with Qwen3-ASR): "timestamp prediction for arbitrary units within up to 5 minutes of speech", word or character level, 11 languages including Chinese and Russian. Its authors report 42.9 ms mean alignment error against 129.8 (NFA) and 133.2 (WhisperX). **P** ([QwenLM/Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR))
- So the mouth-shape route is: synthesise → align against the known text → map characters to あ い う え お ん. In a Live Session that adds one more model call after each sentence. **U** for its delay.

### Singing or humming

- Not mentioned anywhere in the README, model cards or paper. **P** (absence) Training data is described as "over 5 million hours of speech data spanning 10 languages". **P** Expect it not to sing a set melody. **U**

### Licence

- Apache-2.0 on the code and on each model card; the paper says the models are released under Apache 2.0. No extra use restrictions on the cards. **P**
- Note: the licence covers the weights. It says nothing about whose voice is put into the cloning mode; that is the law question in section 7.

## 2. Where Qwen3-TTS runs, and how fast

| Machine / stack | First sound | Speed | Source |
|---|---|---|---|
| RTX 5090, **Windows 11**, plain `qwen-tts` | not given | "10 times slower than realtime", GPU at 4-5% | **P** (user report, [issue #89](https://github.com/QwenLM/Qwen3-TTS/issues/89)) |
| RTX 5090, plain transformers path | 2.3-2.5 s | RTF 1.85 (slower than real time) | **S** [storminthecastle, 2026-10-07](https://www.storminthecastle.com/posts/qwen_tts_latency/) |
| RTX 5090, **vLLM-Omni 0.30.0**, streaming, probably Linux | median 47-51 ms (0.6B CustomVoice); p50 61 ms (0.6B Base clone, precomputed prompt) | about 13× real time | **S** same post |
| RTX 5090, community fork with torch.compile and CUDA graphs | about 80 ms | RTF < 0.25 | **P** (user report, issue #89) |
| RTX 4090, faster-qwen3-tts (CUDA graphs), streaming | 156 ms (0.6B), 174 ms (1.7B) | 4.78× / 4.22× real time | **S** [faster-qwen3-tts](https://github.com/andimarafioti/faster-qwen3-tts) |
| RTX 4060, **Windows**, faster-qwen3-tts | 413 ms / 460 ms | 2.26× / 1.83× real time | **S** same |
| Apple Silicon, MLX Swift, 0.6B (pruned 4-bit) | not given | RTF 0.68, peak 2.1 GB | **S** [AtomGradient](https://atomgradient.github.io/swift-qwen3-tts) |
| M2 Max, MLX | not given | RTF about 0.55 | **S** (soniqo.audio guide, search result only) |

Notes:
- **RTF conventions differ.** The paper and most posts use RTF = compute time ÷ audio time (lower is faster). faster-qwen3-tts uses the inverse ("RTF > 1.0 = faster than real-time"). The table converts the latter to "× real time".
- **Windows on the 5090.** vLLM "does not support Windows natively"; it runs under WSL. **P** ([vLLM docs](https://docs.vllm.ai/en/latest/getting_started/installation/gpu.html)). faster-qwen3-tts ships a native Windows setup (`setup_windows.bat`) and supports VoiceDesign, CustomVoice and cloning. **S** No one was found who measured it on an RTX 5090 under Windows.
- **Apple Silicon.** `mlx-audio` (MIT) lists Qwen3-TTS VoiceDesign (1.7B bf16) and CustomVoice (0.6B, bf16 and 8-bit) and says it supports cloning. **S** (its README). The official package also runs on MPS (`qwen-tts-demo --device mps --no-flash-attn` in [issue #16](https://github.com/QwenLM/Qwen3-TTS/issues/16)) **P**, but one M4 Pro user's CPU run hung for 20 minutes ([issue #69](https://github.com/QwenLM/Qwen3-TTS/issues/69)). **P** faster-qwen3-tts offers a Metal (GGML) backend on macOS 14+. **S** No official Apple port exists. **P** (absence)
- **First Measured Check:** time-to-first-sound and RTF for one sentence on each machine, with her designed clone prompt.

## 3. SGLang-Omni

### What it is

- **Owner:** `sgl-project`, the organisation behind SGLang (the LMSYS serving framework). Repository [sgl-project/sglang-omni](https://github.com/sgl-project/sglang-omni), Apache-2.0, created 2026-01-07, about 1,950 stars, pushed to on 2026-11-27. **P** (GitHub API)
- **Releases:** v0.1.8 (2026-10-12), v0.1.9 (2026-10-21), **v0.2.0 (2026-10-27)** on PyPI. The repo also publishes frequent "voxt" app releases (latest v2.1.4, 2026-11-26). **P**
- **Relation to SGLang:** a separate runtime that "composes with SGLang for autoregressive scheduling". It splits a model into stages (encoders, thinker, talker, vocoder...) and moves tensors between them. **P** (README)
- **The name covers two things in one repo.** (a) The **server runtime** (`sglang-omni`, `sgl-omni serve`). (b) **Voxt**, a Mac app for voice input, translation and a local assistant, running ASR on Apple Silicon. **P** Both are from sgl-project. Qwen3-Omni support inside the main SGLang repository was not checked. **U**

### Which models it serves

From the README. **P**
- **Speech generation** (`/v1/audio/speech`): Qwen3-TTS, Higgs Audio v3, MOSS-TTS, Fish Audio Drama 3, Fish Speech S2-Pro, Fun-CosyVoice3, Voxtral TTS, Ming-Omni-TTS and others.
- **Omni chat with speech:** Qwen3-Omni, MiniCPM-o 4.5, Ming-Omni.
- **Full duplex** (listens while it speaks, `/v1/realtime`): MiniCPM-o 4.5, PersonaPlex, Nemotron VoiceChat.
- **Cascaded voice assistant:** ASR → LLM → TTS with voice-activity detection, conversation history, turn-taking and interruption.
- **Transcription:** Qwen3-ASR, Whisper (experimental) and others.

### What it adds over plain model code

- **Qwen3-TTS in all three modes**, through an OpenAI-compatible endpoint: `voice` picks a preset, `instructions` carries the style or the voice description, Base takes "reference audio or a precomputed speaker embedding". "All three voice modes support streaming", with raw PCM, SSE and WebSocket examples. **P** ([Qwen3-TTS cookbook](https://sgl-project.github.io/sglang-omni/cookbook/qwen3_tts.html))
- **A ready-made Live Session loop.** The cascade profiles pair Qwen3-ASR-1.7B, an LLM and **Qwen3-TTS-12Hz-1.7B-Base**, which "clone a reference voice". **P** ([Full-Duplex Guide](https://sgl-project.github.io/sglang-omni/developer_reference/full_duplex_guide.html)) That is exactly the shape of her Mind speaking: her designed clip goes in as the reference voice. **I**
- Batching, scheduling and stage placement across GPUs. **P**

### Hardware and operating systems

- **CUDA install: "Install SGLang-Omni on Linux with an NVIDIA GPU"**, glibc 2.34 or newer; Docker with the NVIDIA Container Toolkit recommended. **Windows and WSL are not mentioned.** Blackwell / RTX 50-series is not listed, and "Precompiled coverage is not available for every NVIDIA GPU or kernel variant." **P** ([installation](https://sgl-project.github.io/sglang-omni/get_started/installation.html))
- **Apple Silicon:** the Torch MPS path runs "Qwen3-ASR and Fun-ASR" on macOS 14+; **Qwen3-TTS is not listed for Mac**. The README calls Apple Silicon support experimental. **P** ([Apple Silicon guide](https://sgl-project.github.io/sglang-omni/other_platforms/installation_apple_silicon.html))
- Other backends: Intel XPU, Intel CPU, Ascend NPU, Moore Threads. **P**
- **For these two machines:** not on the Mac (for TTS). On the 5090 PC only under Linux, which in practice means WSL2 with GPU passthrough or a Linux install. Running it under WSL2 is **untested by anyone found**. **U**
- **The documented GPUs are data-centre cards.** Full-duplex MiniCPM-o: "one GPU with at least 80 GB (H100 or H200)". Qwen3-Omni: "2 H100 or 1 H200". Cascade: 1 or 2 GPUs depending on profile. **P** A 1.7B TTS plus a 1.7B ASR should fit on 32 GB, but the LLM part of the cascade may not. **U**

### Maturity

- Fast-moving and young: v0.2.0 a month old, some setups pin an unmerged SGLang pull request, first start "can spend about nine minutes JIT-compiling", some features answer `not_supported`. **P** (Full-Duplex Guide)
- CUDA is the primary backend; Apple Silicon and Whisper are experimental. **P**

## 4. Qwen3-Omni and similar speech-in, speech-out models

| Model | Output voice | Languages spoken | Local needs | Source |
|---|---|---|---|---|
| **Qwen3-Omni-30B-A3B-Instruct** (2025-09, Apache-2.0) | **Three presets only**: Ethan, Chelsie, Aiden, chosen with `speaker`. No custom, cloned or designed voice | 10, Russian and Chinese included | BF16 minimum 78.85 GB (15 s video input). In SGLang-Omni: weights about 60 GB BF16, 40 GB FP8, 30 GB INT4 (only the thinker quantised) | **P** [QwenLM/Qwen3-Omni](https://github.com/QwenLM/Qwen3-Omni), SGLang-Omni cookbook |
| **Qwen3.5-Omni** (announced 2026-03-30) | Voice cloning listed among features | 36+ | **No weights** under the Qwen Hugging Face organisation; API service | **P** (HF API, absence); **S** (news) |
| **MiniCPM-o 4.5** (OpenBMB, 9B, Apache-2.0) | "cloning new voices and role play in inference time" from a reference clip | **Chinese and English only** | ≥28 GB GPU (PyTorch demo), ≥12 GB (llama.cpp-omni); full duplex on Mac needs M4 Max with ≥24 GB | **P** [model card](https://huggingface.co/openbmb/MiniCPM-o-4_5) |

- Qwen3-Omni cannot speak in her designed voice, and does not fit the RTX 5090 (32 GB) even at FP8. **P/I**
- MiniCPM-o 4.5 is the one that could: give it her designed Qwen3-TTS clip as the voice reference. It also runs on the M4 Max (36 GB) in full duplex, per its card. **P** Whether it holds a voice cloned from a synthetic clip as well as Qwen3-TTS does is **U**. It cannot speak Russian. **P**
- Using an omni model also makes it the Mind's language model, so the Persona would live in a 9B or 30B model rather than a stronger separate LLM. The cascade (ASR → LLM → Qwen3-TTS) keeps the Mind's LLM free. **I**

## 5. Carrying one voice into song

Starting point: her designed Qwen3-TTS speaking voice (section 1). Qwen3-TTS itself cannot sing (section 1). The routes:

| Route | What it needs | Status | Evidence on high sustained soprano notes |
|---|---|---|---|
| **A. Sing with a synthesiser (GALENAIA, Felicia, Karolyn, DiffSinger) or a consenting singer, then convert to her timbre with RVC** | An RVC model trained on her voice: generate tens of minutes of her **Qwen3-TTS speech** as training data. RVC: MIT, active (last push 2026-08-04) | **P** (RVC repo) | None found. A model trained only on *speech* has never heard her sing high; how it extrapolates to C6 is **U** |
| **B. Same, converting with SoulX-Singer-SVC** (released 2026-03-16) | Source singing plus a short prompt clip of the target timbre; zero-shot, no training | **P** (repo) | The paper's prompts are all *singing*; speech prompts are not described. No range or opera evaluation. **P** (absence) |
| **C. Same, converting with Vocoflex** | A timbre built from imported samples (her clips) or the X/Y pad; real time, CPU | **P** (earlier study) | None found |
| **D. Zero-shot singing: SoulX-Singer prompted with her voice** | Score (MIDI/F0) + lyrics + prompt audio | **P** | Mandarin, English, Cantonese only; prompts in the paper are singing. **P** |
| **E. Seed-VC** | | **Archived** 2025-04-20, GPL-3.0 | Its own eval has a "Soprano (Female)" source but only aggregate figures. **S** |

- **The licence trap from the earlier study still applies:** Synthesizer V's terms forbid training any machine-learning model on its output. **P** (earlier study) Converting a Synthesizer V render *at inference time* with an RVC model trained on Qwen3-TTS speech does not train on Synthesizer V output. Whether "distributed under a different name" then applies is the open question already noted. **U**
- **The clean training data is her own speech.** Qwen3-TTS output is Apache-2.0 model output of a voice no human owns. **I**
- **Weak spot common to A-D:** the converter learns her timbre from speech (100-400 Hz) and is asked to reproduce it at soprano pitch (up to about 1,000-1,400 Hz). No public benchmark tests this. **U** The practical test is a Measured Check plus an Eye Check (by ear): convert one sustained high phrase and listen for buzzing, pitch loss and timbre collapse.
- A middle path worth trying: design a second Qwen3-TTS reference in a *high, bright, head-voice* register (the description can say so), and add it to the RVC training set so the converter has seen her higher range. **U**

## 6. Singing in Russian

| Tool | Russian | How | Source |
|---|---|---|---|
| Synthesizer V Studio 2 | **No** | Singing languages: English, Japanese, Mandarin, Cantonese, Spanish, Korean (French and German in beta). Russian only as an interface language. A forum user posted a Russian-sounding demo by phonetic workaround | **S** (Wikipedia, Plugin Boutique, KVR) |
| ACE Studio 2 | **No** | English, Spanish, Italian, French, Portuguese, Korean, Chinese, Japanese | **P** (earlier study) |
| VOCALOID 6/7 | **No** | Japanese, English, Chinese | **P/S** (earlier study) |
| SoulX-Singer | **No** | Mandarin, English, Cantonese (cross-lingual tested Mandarin → English only) | **P** |
| **OpenUtau + DiffSinger** | **Yes, supported** | Built-in `DiffSinger Russian Phonemizer` (`dsdict-ru.yaml`) and a Russian G2P (`g2p-ru`) in OpenUtau's source; a Russian or multilingual DiffSinger voicebank is needed | **P** (source tree) |
| Russian DiffSinger voicebanks | **Not found** | None found, operatic or otherwise | **S** (absence) |
| Voice conversion (RVC, SoulX-Singer-SVC, Vocoflex) | **Language-free** | They change timbre, not words, so a Russian sung source (a real singer, or a DiffSinger Russian render) carries over | **P/I** |

- So a Russian aria in her voice realistically means: a Russian sung source (a consenting human soprano, or a DiffSinger Russian voicebank if one is found) → timbre conversion to her designed voice. **I**
- The official aria and its recording belong to HoYoverse and an uncredited singer; converting that recording is the "re-voicing" route whose rights were covered in `songs-and-their-terms.md`.

## 7. Law and rules on a voice that resembles a real voice actor

Facts only; not legal advice.

### The Shanghai ruling (reported 2026-09-10)

Source: IT之家, citing the WeChat account 《案件聚焦》 ([ithome.com/1/000/573.htm](https://www.ithome.com/1/000/573.htm)); consistent reports in 网易, 腾讯新闻, Game Developer and AUTOMATON. **S** (no court document or case number was found).
- Court: 上海市浦东新区人民法院. Plaintiff: miHoYo. Defendant: the operator of an AI voice-changer app selling paid voice packs for **63 Genshin characters**, using character images to attract users.
- The defendant admitted using about **one minute of Genshin character audio** without authorisation, mixed with other material, to train its model. A voiceprint appraisal found the app's samples and the game voices "倾向认定同一" (tend to be the same).
- The defendant argued that voice rights belong to the voice actors. The court instead held that a character's timbre is largely set by the character's preset attributes, so hearing it brings the game and its operator to mind: it works as a **商业标识** (commercial identifier).
- Held: unfair competition. Ordered to stop, and to pay **¥750,000**. Secondary reports say an appeal was filed and withdrawn. **S**
- The case was about **cloning from game audio, commercially**. It did not consider a voice designed without the game audio.

### China's rules on a synthetic voice imitating an identifiable person

- **Supreme People's Court, 《关于依法审理涉人工智能纠纷案件的意见》, 法发〔2026〕10号, 2026-09-07, paragraph (四):** "除法律另有规定的外，未经自然人同意，使用自然人的声音作为训练语料，模仿该自然人的音色、语调和发音风格等生成能够识别该自然人的合成人声，该自然人主张行为人侵害其声音权益的，人民法院依法予以支持。" Also: using a synthetic voice that identifies a person to say false things that lower their reputation is defamation. **P** ([court.gov.cn](https://www.court.gov.cn/zixun/xiangqing/511101.html)). Game characters are not mentioned. **P**
- **Deep Synthesis Provisions (互联网信息服务深度合成管理规定, in force 2023-01-10), Art. 14:** a *service provider* offering editing of biometric information such as 人声 must prompt users to inform the person and obtain their separate consent. **S** (quoted from gov.cn via search; not opened). Labelling of synthetic voices is required of services (Arts. 16-17). **S**
- Civil Code Art. 1023 (voice protected by analogy to portrait rights). **U** (not opened this session)

### HoYoverse's rules

- Global Legal FAQ: "character voice-overs/character music, game music or voice samples" are "limited to personal non-commercial use", and "if voice-over personnel are involved", you must get their confirmation yourself. **P** (read in `songs-and-their-terms.md`)
- A March 2026 statement from miHoYo's voice studio: AI use of its voice actors' voices needs written authorisation from both the company and the actor, even non-commercially. **S** (news only; original statement not found)
- Mainland 米哈游 fan-work rules on voice: not found. **S** (absence)

### Cloning versus designing

- Every text above turns on **using the person's or the game's recordings** (as training material, as source audio, or as editable biometric data) and on the result being **recognisable**.
- Designing a voice from a written description uses no recording. None of these texts addresses a voice that ends up sounding similar without using recordings. **P** (absence)
- But the Shanghai court's test was whether users *associate* the timbre with the game. A designed voice deliberately tuned to sound like her in-game voice, presented as Vodyanitsa, would invite the same association question. **I**
- Using any official line as a Qwen3-TTS Base `ref_audio` is cloning in every sense above, and breaks the project rule.

## What could not be verified

1. Whether VoiceDesign returns the same voice for the same description (seeding).
2. Whether written 嘻嘻 / 哼 are voiced as laughs.
3. Any measurement on an RTX 5090 **under Windows** with an optimised stack, or on an **M4 Max**.
4. Whether SGLang-Omni runs under WSL2, and whether it builds for Blackwell (sm_120).
5. How a converter trained on speech holds sustained soprano notes; no benchmark exists.
6. Whether any Russian DiffSinger voicebank exists.
7. The Shanghai judgment itself (case number, date, full reasoning); only press reports were read.
8. The 25 Hz Qwen3-TTS models: described in the paper as released, but absent from Hugging Face.
