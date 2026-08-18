"""
OmniEar Stage 2, step 2: train a lightweight classifier on top of the
cached YAMNet embeddings (data/embeddings.npz).

Uses capped class weighting to help the smaller classes without making the
classifier over-predict them. Augmented siblings are always kept in the same
split, and the final report includes a second score on untouched originals.

Run: python train_classifier.py
Output: models/classifier.keras, models/classes.json
"""

import os
import json
import numpy as np
import tensorflow as tf
from sklearn.model_selection import GroupShuffleSplit, StratifiedGroupKFold
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix

EMBEDDINGS_PATH = "data/embeddings.npz"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "classifier.keras")
CLASSES_PATH = os.path.join(MODEL_DIR, "classes.json")
RANDOM_SEED = 42


def print_evaluation(title, y_true, y_pred, classes):
    """Print a consistent per-class report and confusion matrix."""
    label_ids = np.arange(len(classes))
    print(f"\n--- {title} ---")
    print(
        classification_report(
            y_true,
            y_pred,
            labels=label_ids,
            target_names=classes,
            zero_division=0,
        )
    )
    print("Confusion matrix (rows=true, cols=predicted):")
    print(classes)
    print(confusion_matrix(y_true, y_pred, labels=label_ids))


def build_model(input_dim, num_classes):
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(input_dim,)),
        tf.keras.layers.BatchNormalization(),
        tf.keras.layers.Dense(
            256,
            activation="relu",
            kernel_regularizer=tf.keras.regularizers.l2(1e-4),
        ),
        tf.keras.layers.Dropout(0.35),
        tf.keras.layers.Dense(
            96,
            activation="relu",
            kernel_regularizer=tf.keras.regularizers.l2(1e-4),
        ),
        tf.keras.layers.Dropout(0.25),
        tf.keras.layers.Dense(num_classes, activation="softmax"),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def split_by_stratified_groups(X, y, groups):
    """Create class-balanced splits without separating augmented siblings."""
    try:
        # 1/6 test, then 1/5 of the remainder for validation: approximately
        # 67/17/17. Stratification matters because every group belongs to one
        # class and some project classes have far fewer original recordings.
        outer = StratifiedGroupKFold(n_splits=6, shuffle=True, random_state=42)
        train_val_idx, test_idx = next(outer.split(X, y, groups))

        inner = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=43)
        inner_train, inner_val = next(
            inner.split(X[train_val_idx], y[train_val_idx], groups[train_val_idx])
        )
        train_idx = train_val_idx[inner_train]
        val_idx = train_val_idx[inner_val]
        return train_idx, val_idx, test_idx
    except ValueError as exc:
        # Very small hand-built datasets may not have six original clips in
        # every class. Preserve group isolation even when stratification is
        # mathematically impossible.
        print(f"Stratified group split unavailable ({exc}); using group-only split.")
        outer = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=42)
        train_idx, temp_idx = next(outer.split(X, y, groups=groups))
        inner = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=43)
        val_local, test_local = next(
            inner.split(X[temp_idx], y[temp_idx], groups=groups[temp_idx])
        )
        return train_idx, temp_idx[val_local], temp_idx[test_local]


def main():
    # Keep model selection and reported demo metrics reproducible.
    np.random.seed(RANDOM_SEED)
    tf.keras.utils.set_random_seed(RANDOM_SEED)

    print("Loading cached embeddings...")
    data = np.load(EMBEDDINGS_PATH, allow_pickle=True)
    X = data["X"]
    y = data["y"]
    classes = list(data["classes"])

    if "groups" not in data:
        raise RuntimeError(
            "embeddings.npz has no 'groups' array -- re-run extract_embeddings.py "
            "with the updated script before training, or augmented clips may leak "
            "across train/test splits and inflate your metrics."
        )
    groups = data["groups"]

    print(f"X shape: {X.shape}, y shape: {y.shape}")
    print(f"Classes: {classes}")
    print(f"Unique groups (original clips): {len(set(groups))}")
    print("\nClass distribution:")
    for i, cls in enumerate(classes):
        print(f"  {cls}: {np.sum(y == i)}")

    # All augmented variants remain with their original, while stratification
    # keeps rare classes represented in train/validation/test.
    train_idx, val_idx, test_idx = split_by_stratified_groups(X, y, groups)
    X_train, y_train, groups_train = X[train_idx], y[train_idx], groups[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]
    X_test, y_test = X[test_idx], y[test_idx]

    # Sanity check: confirm no group overlaps between splits
    train_groups = set(groups_train)
    val_groups = set(groups[val_idx])
    test_groups = set(groups[test_idx])
    assert not (train_groups & val_groups), "Group leak between train and val!"
    assert not (train_groups & test_groups), "Group leak between train and test!"
    assert not (val_groups & test_groups), "Group leak between val and test!"
    print("\nGroup-split sanity check passed: no original clip appears in more than one split.")

    print(f"\nTrain: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    # Class weights to counter imbalance
    balanced_weights = compute_class_weight(
        class_weight="balanced", classes=np.unique(y_train), y=y_train
    )
    # Full inverse-frequency weighting tends to make a small head overpredict
    # rare classes. Square-root weighting still helps recall without sacrificing
    # as much category precision.
    class_weights_arr = np.clip(np.sqrt(balanced_weights), 0.8, 1.5)
    # Screams have by far the fewest distinct source recordings. A modest
    # extra recall bias is appropriate for this P0 class and is validated
    # against the untouched-original split below.
    if "scream_distress" in classes:
        class_weights_arr[classes.index("scream_distress")] = 2.0
    class_weight_dict = {i: float(w) for i, w in enumerate(class_weights_arr)}
    print("\nClass weights (higher = rarer class, more emphasis):")
    for i, cls in enumerate(classes):
        print(f"  {cls}: {class_weight_dict.get(i, 'N/A'):.2f}")

    model = build_model(input_dim=X.shape[1], num_classes=len(classes))
    model.summary()

    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=10, restore_best_weights=True
    )
    reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
        monitor="val_loss", factor=0.5, patience=4, min_lr=1e-5, verbose=1
    )

    print("\nTraining...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=50,
        batch_size=32,
        class_weight=class_weight_dict,
        callbacks=[early_stop, reduce_lr],
        verbose=2,
    )

    print("\nEvaluating held-out test data...")
    y_pred_probs = model.predict(X_test)
    y_pred = np.argmax(y_pred_probs, axis=1)
    print_evaluation("Test set (originals + augmentations)", y_test, y_pred, classes)

    if "paths" in data:
        # Augmented clips are useful domain variants, but scoring them can make
        # the headline result look better than the real-world generalization.
        # Report the untouched originals separately for an honest demo metric.
        paths = data["paths"]
        original_test_idx = np.array(
            [
                index
                for index in test_idx
                if not os.path.basename(str(paths[index])).startswith("aug_")
            ],
            dtype=np.int64,
        )
        original_probs = model.predict(X[original_test_idx])
        original_pred = np.argmax(original_probs, axis=1)
        print_evaluation(
            "Test set (untouched originals only)",
            y[original_test_idx],
            original_pred,
            classes,
        )
    else:
        print(
            "\nNo paths array found; re-run extract_embeddings.py to enable "
            "the untouched-original evaluation."
        )

    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save(MODEL_PATH)
    with open(CLASSES_PATH, "w") as f:
        json.dump(classes, f)

    print(f"\nModel saved to {MODEL_PATH}")
    print(f"Classes saved to {CLASSES_PATH}")


if __name__ == "__main__":
    main()
