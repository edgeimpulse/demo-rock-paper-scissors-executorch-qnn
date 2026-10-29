# Third-party components and licenses

The third-party components this project uses, and their licenses.

This project's own code is under The Clear BSD License ([LICENSE](LICENSE)).
Everything below is somebody else's and keeps its own terms.

Nothing listed is redistributed by this repository except where the "Shipped
here?" column says so — the rest is fetched by scripts at install time. If you
redistribute this project or build on it, check that column first: it is the
line between "we point at it" and "we ship it".

## Runtime and build dependencies

| Component | License | Shipped here? |
|---|---|---|
| `ExecuTorch`, `PyTorch`, `torchvision` | BSD-3-Clause | no — pip |
| `llama.cpp` (commentary engine) | MIT | no — built by `rps-amazing-hand/scripts/build-llama-hexagon.sh` |
| Piper (TTS engine, `piper-tts`) | **GPL-3.0-or-later** | no — pip, see below |
| Amazing Hand — software | Apache-2.0 | no |
| Amazing Hand — mechanical design | CC BY 4.0 | no — attribution required if you publish the CAD or photos of it |
| `rustypot` (servo driver) | Apache-2.0 | no — pip |
| `FastAPI`, `httpx`, `onnxruntime` | MIT | no — pip |
| `uvicorn`, `numpy` | BSD | no — pip |
| `opencv-python` | Apache-2.0 | no — pip |
| `Atkinson Hyperlegible`, `Barlow` (web fonts) | SIL OFL 1.1 | **yes** — `rps-amazing-hand/app/static/fonts/`, with the per-family license text alongside, as the OFL requires |
| Qualcomm®  QNN SDK / `libqnn1` | Qualcomm proprietary | no — Ubuntu IoT PPA |

## Models and data

| Artifact | License | Notes |
|---|---|---|
| Llama 3.2 1B Instruct (GGUF) | **Llama 3.2 Community License** | Not an OSI open-source license. Fetched by `rps-amazing-hand/scripts/fetch-llm-model.sh`; never redistributed here. See below. |
| Piper voice (`en_US-kristin-medium`) | public domain (LibriVox) | Fetched by `rps-amazing-hand/scripts/fetch-tts-voice.sh`. **The voice catalogue is mixed — see below.** |
| `model.pte` / `model_qnn.pte` | — | Not distributed here. You train them with the learning block in the example-executorch-qnn repository, fine-tuned from torchvision's ImageNet MobileNetV2 weights. |

## Worth reading before you build on this

### 1. Piper is GPL-3.0-or-later

It links espeak-ng for phonemization, which is why the license is copyleft.

This repository keeps it at arm's length rather than linking it:

- Piper runs as **its own process**, started by `start.sh`, behind its HTTP API.
- `rps-amazing-hand/app/speech.py` only ever POSTs to `127.0.0.1:5000` and
  parses the WAV that comes back. **No file in this repository imports Piper.**
- Its dependency lives in a separate
  [`requirements-speech.txt`](rps-amazing-hand/requirements-speech.txt),
  not in `requirements.txt`, and `SKIP_SPEECH=1 ./install.sh` omits it.
- The same arrangement is used for llama.cpp, which is MIT and needs no such
  care — the structure was chosen for both reasons.

Process isolation is also the faster option here — a per-clip CLI invocation
would reload the voice model every time — so nothing was traded away to get
this separation.

If you redistribute this project, satisfy yourself that the arrangement meets
your own requirements. `SKIP_SPEECH=1 ./install.sh` omits Piper entirely; the
demo then runs silently and nothing else changes.

### 2. Llama 3.2 is not open source

llama.cpp (the engine) is MIT. The **weights** are under Meta's Llama 3.2
Community License, which is source-available rather than OSI-approved. The
obligations that matter here:

- Attribution: products built with it should display **"Built with Llama"**.
- A copy of the license must accompany any redistribution of the weights.
- An Acceptable Use Policy applies.
- A separate license from Meta is required above 700 million monthly active
  users — not a concern for this project.

This repository never redistributes the weights;
`rps-amazing-hand/scripts/fetch-llm-model.sh` downloads them from Hugging Face
at install time, so the redistribution clause is not triggered. The attribution
requirement is met by the "Built with Llama" notice in [NOTICE](NOTICE), in the
top-level README and in that script.

### 3. Piper's voice catalogue mixes permissive and non-commercial

The voice name gives no hint. What binds is the license of the **training
dataset**, named in each voice's `MODEL_CARD` at
[huggingface.co/rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices).

| Voice | Dataset | License |
|---|---|---|
| `en_US-kristin-medium` (default) | LibriVox | public domain |
| `en_US-john-medium` | LibriVox | public domain |
| `en_GB-alba-medium` | Edinburgh DataShare | CC BY 4.0 — attribution |
| `en_US-lessac-medium` | Blizzard Challenge 2013 | **research only.** Its license excludes "the development, marketing, commercialisation, sale or licencing of voice synthesis or speech recognition products or services" |
| `en_US-ryan-medium` | RyanSpeech | **CC BY-NC-SA 4.0** |
| `en_US-hfc_female/male-medium` | Hi-Fi Captain | **CC BY-NC-SA 4.0** |

A trade-show demo is a commercial context, so the non-commercial voices are out
for this project even though the software is given away.
`rps-amazing-hand/app/config.py` repeats this list at the point of change so the
next person does not have to rediscover it.

## Training data

The gesture model is trained on images collected for this project. Their
provenance, the consent position, and the rules for collecting more are in
[docs/dataset.md](docs/dataset.md).

`RPS_SAVE_FRAMES` makes the running demo write camera frames to disk. It is off
by default. If you turn it on in front of other people, read that page first.

## The example repository

The model pipeline, the board runtime and the NPU service these applications
depend on live in **example-executorch-qnn**. That repository redistributes no
third-party files at all, so nothing on this page applies to it.
