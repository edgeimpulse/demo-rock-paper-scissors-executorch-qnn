# Rock-paper-scissors Demos with ExecuTorch Models

This repo contains two separate rock-paper-scissors demos. One version is a web app that runs on any Linux machine. The other is an Android version that runs on a mobile phone. 

The demos use the ExecuTorch artifacts produced by
[example-executorch-qnn](https://github.com/edgeimpulse/example-executorch-qnn) for classication of the human gesture. A single training run using that repo produces a portable CPU model (`model.pte`) and an NPU model (`model_qnn.pte`). 

The web app demo can use the CPU model  or, if you are using a Qualcomm® Dragonwing™ IQ-9075 SoC, the NPU model. The NPU model is compiled for the Hexagon™ v73 and is not meant to run anywhere else. The Android app uses the CPU model.

| Demo | What it is | Runs on |
|---|---|---|
| [`rps-amazing-hand/`](rps-amazing-hand/) | A web app that uses a camera and a gesture classifier. It can also add a robotic hand, on-device LLM commentary, and/or speech. | Any Linux machine with a webcam. The NPU path needs an IQ-9075 SoC. |
| [`rps-android/`](rps-android/) | An Android app that uses the phone camera and a gesture classifier. | An Android phone (arm64, Android 8.0+). |

## Before you run these demos

This repository contains the demo apps without the gesture classification models. You will first need to generate the gesture classification models. If you are using the NPU model, you will also need to set up the NPU service. 

### Models

Training a gesture classification model is the first step. A single run of the `example-executorch-qnn`'s [custom learning block](https://github.com/edgeimpulse/example-executorch-qnn/tree/main/blocks/learning-image-classifier) in Edge Impulse Studio produces everything the demos need. 

The artifacts produced include a portable `model.pte` and its matching `labels.txt` for the CPU path, plus `model_qnn.pte` and `export_report.json` for the NPU path. 

Training on your own images is how the classifier learns your hands and your lighting.

### NPU Service

> [!NOTE]
> The NPU service is only needed for the IQ-9075 SoC path. 

`board/setup.sh` in the `example-executorch-qnn` repo builds ExecuTorch with the QNN backend and installs `npu_server` as the `rps-npu` systemd service. The `rps-amazing-hand` demo talks to it over a UNIX socket at `/run/rps-npu/npu.sock`. Without that service, the app falls back to the CPU.

`rps-amazing-hand/app/npu_client.py` is this repo's copy of that client. The example repo keeps its own version at `board/steps/npu_client.py`, so each project can evolve independently.

## Quick start

### Web app

Place `model.pte` and `labels.txt` in `rps-amazing-hand/models/`. Place `model_qnn.pte` in `/opt/rps-npu/model_qnn.pte`. 

Then run:

```bash
cd rps-amazing-hand
./install.sh
./start.sh                     
# pick the camera, then open http://localhost:8000
```

On an IQ-9075, with the `rps-npu` service running, it switches to the NPU and logs `detector: NPU ACTIVE`. Details can be found in: [rps-amazing-hand/README.md](rps-amazing-hand/README.md).

### Android app

Copy `model.pte` and `labels.txt` into `rps-android/app/src/main/assets/`, open `rps-android` in Android Studio, and press Run with your phone plugged in. 

The app includes a parity check that compares the phone's scores with Python's for the same photo. Details can be found in: [rps-android/README.md](rps-android/README.md).

## Extending the web app 

The web app demo can be extended by running the gesture classification on the NPU or by adding a robotic hand (the Amazing Hand), LLM commentary, or speech commentary. If one piece is missing, the app still runs, and the log tells you what to install.

- **The NPU** — needs the `rps-npu` service from the example repo.
- **The Amazing Hand** — a serial servo hand on USB, with the user in the `dialout` group.
- **LLM commentary** — llama.cpp with the Hexagon backend, plus a Q4_0 GGUF model.
- **Spoken commentary** — Piper text-to-speech on the CPU.

Scripts to test functionality and retrieve necessary additional assets are shown below:

```bash
# is the LLM on the NPU?
./scripts/check-llama-hexagon.sh models/Llama-3.2-1B-Instruct-Q4_0.gguf

# does the hand move?
.venv/bin/python scripts/test-hand.py 

# commentary model (Q4_0 GGUF)
./scripts/fetch-llm-model.sh

# speech voice (Piper)
./scripts/fetch-tts-voice.sh          

# can this board speak?
./scripts/check-audio.sh
```

Speech runs on the CPU because the NPU is already handling vision and the LLM. You can read more about that choice and the audio player logic in
[docs/speech-and-actuation.md](docs/speech-and-actuation.md).

The web app left hand sidebar's **Artifacts** panel shows which `.pte` is being used while the game runs, along with its SHA-256, the input resolution, the delegate inside it, and any CPU fallback. If you stop `rps-npu` mid-match, the badge flips to `CPU fallback` while the game keeps running ([details](rps-amazing-hand/README.md#artifact-panel)).

## Repository map

| Path | What it is |
|---|---|
| [`rps-amazing-hand/`](rps-amazing-hand/) | The web app: FastAPI server, camera loop, NPU-first inference with per-frame CPU fallback, the hand actuator, LLM commentary, and speech. |
| [`rps-android/`](rps-android/) | The Android app: Kotlin, Compose UI, ExecuTorch Android runtime, with golden tests proving the Kotlin preprocessing matches Python's. |
| [`docs/`](docs/) | The full pipeline, design decisions, troubleshooting notes, speech and actuation details, and the dataset provenance. |

## License and credits

This project is licensed under **The Clear BSD License** — see
[LICENSE](LICENSE). Every source file owned by this project carries a
copyright line and the SPDX identifier `BSD-3-Clause-Clear` in its header.

### What is shipped and what is fetched

**Shipped in this repository:** this project's own source, a UI screenshot, the
synthetic Android test fixtures, and two web font families with their OFL
license text. The fonts are the only third-party files redistributed here.

**Not shipped at all:** the trained gesture classification models. You produce `model.pte` and `model_qnn.pte` from your own training run, so no model weights and no training images are published here.

**Not shipped — fetched at install time:** ExecuTorch and PyTorch, llama.cpp, the Llama 3.2 weights, Piper and its voice, and the rest of the pip
dependencies.

[NOTICE](NOTICE) is the authoritative record of the split and the attribution obligations for each component. [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) covers the same ground in more detail, and [docs/binary-provenance.md](docs/binary-provenance.md) tracks every shipped binary and document file.

The dataset provenance and the rules for collecting more images are in
[docs/dataset.md](docs/dataset.md).

### Credits

- The model pipeline and the NPU runtime come from [example-executorch-qnn](https://github.com/edgeimpulse/example-executorch-qnn).
- The [Amazing Hand](https://github.com/pollen-robotics/AmazingHand) is by Pollen Robotics: Apache-2.0 for the software and CC BY 4.0 for the mechanical design.
- Built with Llama. The optional LLM commentary uses Meta's
Llama 3.2 1B Instruct under the [Llama 3.2 Community License](https://www.llama.com/llama3_2/license/).
- The original web app demo, *Rock Paper Scissors: The Amazing Hand* (gesture object detection without ExecuTorch), was developed by [@bmcfads](https://github.com/bmcfads).
