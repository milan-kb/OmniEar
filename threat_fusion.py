"""Fuse the custom OmniEar head with YAMNet's pretrained event scores.

The custom head is good at the project's five broad classes.  YAMNet's native
521 labels are useful independent evidence for YouTube/demo audio, where a
short event can otherwise disappear inside a clip-level average.
"""

import numpy as np


# Exact names from YAMNet's bundled AudioSet class map.  Exact matching avoids
# accidents such as treating a goose "Honk" as a traffic siren.
YAMNET_LABEL_GROUPS = {
    "scream_distress": (
        "Shout",
        "Yell",
        "Children shouting",
        "Screaming",
        "Crying, sobbing",
        "Whimper",
        "Wail, moan",
    ),
    "explosion": (
        "Explosion",
        "Artillery fire",
        "Fireworks",
        "Firecracker",
        "Burst, pop",
        "Eruption",
        "Boom",
    ),
    "impact_crash": (
        "Gunshot, gunfire",
        "Machine gun",
        "Fusillade",
        "Cap gun",
        "Slam",
        "Glass",
        "Shatter",
        "Thump, thud",
        "Thunk",
        "Bang",
        "Smash, crash",
        "Breaking",
        "Crushing",
    ),
    "siren_traffic": (
        "Vehicle horn, car horn, honking",
        "Car alarm",
        "Air horn, truck horn",
        "Emergency vehicle",
        "Police car (siren)",
        "Ambulance (siren)",
        "Fire engine, fire truck (siren)",
        "Siren",
        "Civil defense siren",
    ),
}


def build_yamnet_index_groups(class_names):
    """Map each OmniEar class to indices in YAMNet's current class map."""
    name_to_index = {str(name).strip(): i for i, name in enumerate(class_names)}
    return {
        label: tuple(name_to_index[name] for name in names if name in name_to_index)
        for label, names in YAMNET_LABEL_GROUPS.items()
    }


def _top_k_mean(values, k=2):
    values = np.asarray(values, dtype=np.float32).reshape(-1)
    if values.size == 0:
        return 0.0
    k = min(k, values.size)
    return float(np.mean(np.partition(values, values.size - k)[-k:]))


def aggregate_yamnet_evidence(yamnet_scores, index_groups, classes):
    """Convert per-frame 521-way YAMNet scores to four project-class scores."""
    scores = np.asarray(yamnet_scores, dtype=np.float32)
    evidence = np.zeros(len(classes), dtype=np.float32)
    if scores.ndim != 2 or scores.shape[0] == 0:
        return evidence

    for label, indices in index_groups.items():
        if label not in classes or not indices:
            continue
        valid = [index for index in indices if 0 <= index < scores.shape[1]]
        if not valid:
            continue
        per_frame = np.max(scores[:, valid], axis=1)
        # A peak matters for a gunshot; top-two support makes sustained screams
        # and sirens more stable.  Both are deliberately retained.
        evidence[classes.index(label)] = (
            0.70 * float(np.max(per_frame)) + 0.30 * _top_k_mean(per_frame, k=2)
        )
    return evidence


def fuse_predictions(clip_probs, frame_probs, yamnet_evidence, classes):
    """Return fused probabilities plus useful diagnostics.

    Direct YAMNet evidence never overrides a background decision. Held-out
    calibration showed it is useful only for reinforcing agreement or as a
    high-margin tie-breaker between two threat classes.
    """
    clip_probs = np.asarray(clip_probs, dtype=np.float32).reshape(-1)
    if clip_probs.size != len(classes):
        raise ValueError("Classifier output size does not match classes.json")

    learned = clip_probs.copy()
    if frame_probs is not None:
        per_frame = np.asarray(frame_probs, dtype=np.float32)
        if per_frame.ndim == 2 and per_frame.shape[1] == len(classes) and per_frame.shape[0]:
            transient = np.array(
                [_top_k_mean(per_frame[:, i], k=2) for i in range(len(classes))],
                dtype=np.float32,
            )
            if "background" in classes:
                transient[classes.index("background")] = clip_probs[classes.index("background")]
            learned = 0.65 * clip_probs + 0.35 * transient

    learned = np.maximum(learned, 0.0)
    learned /= max(float(np.sum(learned)), 1e-8)

    evidence = np.asarray(yamnet_evidence, dtype=np.float32).reshape(-1)
    if evidence.size != len(classes) or not np.any(evidence > 0):
        return learned, {
            "learned": learned,
            "yamnet_evidence": np.zeros_like(learned),
            "yamnet_weight": 0.0,
        }

    semantic = np.maximum(evidence, 0.0)
    strength = float(np.max(semantic))
    semantic_top = int(np.argmax(semantic))
    learned_top = int(np.argmax(learned))
    weight = 0.0
    fused = learned.copy()

    if semantic_top == learned_top and strength >= 0.35:
        # Agreement is safe to use as a modest confidence reinforcement.
        semantic_distribution = semantic / max(float(np.sum(semantic)), 1e-8)
        weight = min(0.20, strength * 0.20)
        fused = (1.0 - weight) * learned + weight * semantic_distribution
    elif (
        classes[learned_top] != "background"
        and classes[semantic_top] != "background"
        and strength >= 0.35
        and learned[learned_top] - learned[semantic_top] <= 0.40
        and evidence[semantic_top] - evidence[learned_top] >= 0.30
    ):
        # Validation showed that direct YAMNet evidence is useful as a
        # high-margin tie-breaker *between threat classes*, but aggressively
        # rescuing background creates many false alerts on loud hard negatives.
        # Swap the two probabilities so the semantic class wins without
        # inventing an overconfident score.
        fused[semantic_top], fused[learned_top] = (
            learned[learned_top],
            learned[semantic_top],
        )
        weight = 1.0

    fused /= max(float(np.sum(fused)), 1e-8)
    return fused, {
        "learned": learned,
        "yamnet_evidence": evidence,
        "yamnet_weight": weight,
    }
