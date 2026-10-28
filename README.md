# Rock-paper-scissors on ExecuTorch: two demo applications

Two demos build on the ExecuTorch artifacts produced by
[**example-executorch-qnn**](https://github.com/edgeimpulse/example-executorch-qnn).
A single training run there produces a portable CPU model and an NPU model. The
web demo can use either one, while the Android app runs the portable model on a
phone.

| Demo | What it is | Runs on |
|---|---|---|
| [`rps-amazing-hand/`](rps-amazing-hand/) | A web game that uses a camera, a gesture classifier, and a robotic hand. It can also add on-device LLM commentary and speech. | Any Linux machine with a webcam. The NPU path needs an IQ-9075 EVK. |
| [`rps-android/`](rps-android/) | An Android app that plays the same game with the phone camera. | An Android phone (arm64, Android 8.0+) |

The Android app runs `model.pte` — the same file the Linux demo falls back to.
It prints the model hash so you can verify it yourself. The IQ-9075 demo also
uses `model_qnn.pte` through the NPU service. That file is compiled for Hexagon
v73 and is not meant to run anywhere else.

## What you need from the example repository

This repository contains the demo apps, not the model pipeline. The shared pieces
come from [example-executorch-qnn](https://github.com/edgeimpulse/example-executorch-qnn):

**The models:** no trained model is checked in here, so training one is the first
step. A single run of the repo's [learning block](https://github.com/edgeimpulse/example-executorch-qnn/tree/main/blocks/learning-image-classifier)
produces everything the demos need: the portable `model.pte` and its matching
`labels.txt` for the CPU path, plus `model_qnn.pte` and `export_report.json` for
the NPU path. Copy `model.pte` and `labels.txt` into
`rps-amazing-hand/models/` before you start the web demo. Training on your own
images is also how the classifier learns your hands and your lighting.

**The NPU service** is only needed for the IQ-9075 path. `board/setup.sh` in the
example repo builds ExecuTorch with the QNN backend and installs `npu_server` as
the `rps-npu` systemd service. This demo talks to it over a UNIX socket at
`/run/rps-npu/npu.sock`. Without that service, the app falls back to the CPU.

`rps-amazing-hand/app/npu_client.py` is this repo's copy of that client. The
example repo keeps its own version at `board/steps/npu_client.py`, so each
project can evolve independently.

## Quick start

**Web game** on any Linux machine with a webcam. 
Train a model first, then put
`model.pte` and `labels.txt` in `rps-amazing-hand/models/`:

```bash
cd rps-amazing-hand
./install.sh
./start.sh                     # pick the camera, then open http://localhost:8000
```

The web demo uses the CPU model you placed in `rps-amazing-hand/models/`. 
On an IQ-9075, with the `rps-npu` service running, it switches to the NPU and logs
`detector: NPU ACTIVE`. 
Details can be found in: [rps-amazing-hand/README.md](rps-amazing-hand/README.md).

**Android app:** copy `model.pte` and `labels.txt` into
`rps-android/app/src/main/assets/`, open `rps-android` in Android Studio, and
press Run with your phone plugged in. The app includes a parity check that
compares the phone's scores with Python's for the same photo. Details:
[rps-android/README.md](rps-android/README.md).

## Adding the NPU, the hand, and the voice

The web game can be extended in a few different ways. If one piece is missing,
the app still runs, and the log tells you what to install:

- **The NPU** — needs the `rps-npu` service from the example repo.
- **The Amazing Hand** — a serial servo hand on USB, with the user in the `dialout` group.
- **LLM commentary** — llama.cpp with the Hexagon backend, plus a Q4_0 GGUF model.
- **Spoken commentary** — Piper text-to-speech on the CPU.

```bash
./scripts/fetch-llm-model.sh                   # commentary model (Q4_0 GGUF)
./scripts/fetch-tts-voice.sh                   # speech voice (Piper)

./scripts/check-llama-hexagon.sh models/Llama-3.2-1B-Instruct-Q4_0.gguf   # is the LLM on the NPU?
./scripts/check-audio.sh                                                  # can this board speak?
.venv/bin/python scripts/test-hand.py                                     # does the hand move?
```

Speech runs on the CPU because the NPU is already handling vision and the LLM.
You can read more about that choice and the audio player logic in
[docs/speech-and-actuation.md](docs/speech-and-actuation.md).

The sidebar's **Artifacts** panel shows which `.pte` is answering while the game
runs, along with its SHA-256, the input resolution, the delegate inside it, and
any CPU fallback. If you stop `rps-npu` mid-match, the badge flips to
`CPU fallback` while the game keeps running
([details](rps-amazing-hand/README.md#artifact-panel)).

## Repository map

| Path | What it is |
|---|---|
| [`rps-amazing-hand/`](rps-amazing-hand/) | The web game: FastAPI server, camera loop, NPU-first inference with per-frame CPU fallback, the hand actuator, LLM commentary, and speech |
| [`rps-android/`](rps-android/) | The Android app: Kotlin, Compose UI, ExecuTorch Android runtime, with golden tests proving the Kotlin preprocessing matches Python's |
| [`docs/`](docs/) | The full pipeline, design decisions, troubleshooting notes, speech and actuation details, and the dataset provenance |

## License and credits

This project is licensed under **The Clear BSD License** — see
[LICENSE](LICENSE). Every source file owned by this project carries a
copyright line and the SPDX identifier `BSD-3-Clause-Clear` in its header.

### What is shipped and what is fetched

**Shipped in this repository:** this project's own source, a UI screenshot, the
synthetic Android test fixtures, and two web font families with their OFL
license text. The fonts are the only third-party files redistributed here.

**Not shipped at all:** the trained models. You produce `model.pte` and
`model_qnn.pte` from your own training run, so no model weights and no training
images are published here.

**Not shipped — fetched at install time:** ExecuTorch and PyTorch, llama.cpp,
the Llama 3.2 weights, Piper and its voice, and the rest of the pip
dependencies.

[NOTICE](NOTICE) is the authoritative record of the split and the attribution
obligations for each component. [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)
covers the same ground in more detail, and [docs/binary-provenance.md](docs/binary-provenance.md)
tracks every shipped binary and document file.

### Credits

- The model pipeline and the NPU runtime come from [example-executorch-qnn](https://github.com/edgeimpulse/example-executorch-qnn).
- The [Amazing Hand](https://github.com/pollen-robotics/AmazingHand) is by Pollen Robotics: Apache-2.0 for the software and CC BY 4.0 for the mechanical design.

**Built with Llama.** The optional spoken commentary uses Meta's
Llama 3.2 1B Instruct under the
[Llama 3.2 Community License](https://www.llama.com/llama3_2/license/). The
model is downloaded at install time and is not redistributed here.

The dataset provenance and the rules for collecting more images are in
[docs/dataset.md](docs/dataset.md).
