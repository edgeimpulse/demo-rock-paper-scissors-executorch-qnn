# The gesture dataset

What the four classes need to contain, the consent record to create before
publishing anything trained on them, and the rules for anyone collecting more.

Neither the dataset nor a trained model is published in this repo. Both the CPU
and the NPU model come from your own training run, so this page is written for
whoever does that collecting. The only dataset-adjacent file here is
`labels.txt`, which only contains the four class names.


## What the dataset is

Four classes, one gesture per image, photographed against a plain background:

| Class | Contents |
|---|---|
| `Rock`, `Paper`, `Scissors` | A single hand making the gesture |
| `unknown` | Frames with **no hand** — including faces and upper bodies |

**`unknown` is the class that makes the demo work, and it is the one people get
wrong when they reproduce this.** A classifier has no "is there a hand?"
output, so without a fourth class softmax is forced to pick rock, paper or
scissors for every empty frame. `unknown` absorbs those.

What goes in it matters as much as that it exists. Most non-gesture frames
contain a **face, a torso, or someone walking past**, not an empty background.
So `unknown` is built from exactly that — people in frame with no hand raised.
An `unknown` class of blank walls trains a model that rejects empty rooms and
confidently misreads the first face it sees.

That is also what puts identifiable people in the training set, which is why
the next section matters.

Class names are stored in `labels.txt` in alphabetical order, which is the
order Edge Impulse builds its one-hot targets in.

## Consent, and why nothing here is published

The images were collected for this project; it is not a public dataset. The
record of who is depicted and what they agreed to is held with the project
owners, not in this repo.

Nothing derived from those images is published either: not the dataset, not
`model.pte`, not `model_qnn.pte`, and not the `X_split_test.npy` /
`Y_split_test.npy` arrays that `board/verify.sh` uses locally. A trained model
is a derivative of its training data, so shipping a `.pte` would mean shipping
something that the consent record governs. That is why we keep models out of
the repo altogether, and why `models/*.pte` is in `.gitignore`.

The same reasoning applies to anyone reproducing this. If your `unknown` class
contains identifiable people, and the section above is the argument that it
should, then whatever you agreed with them governs your `.pte` as well as your
images. That record is the thing to create before you publish a model rather
than after the fact.

## Collecting more data

`RPS_SAVE_FRAMES=<dir>` makes the running demo write the frames the model saw
to disk — raw material for a better `unknown` class. It is off by default, and
should stay off unless you mean to be collecting frames.

Those frames are camera captures of whoever is standing in front of the demo,
so they fall under the same record as the images above.

## Known weaknesses

These are from the original collection run. They are recorded here because they
shape what the next one should cover:

- Some scissors poses read as paper. More varied scissors data is the fix.
- `unknown` is under-trained; empty frames at odd angles still occasionally
  score as a gesture.
- The split is not stratified; best-epoch selection uses the test split rather
  than a held-out validation split.