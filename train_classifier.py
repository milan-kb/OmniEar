"""
OmniEar Stage 2, step 2: train a lightweight classifier on top of the
cached YAMNet embeddings (data/embeddings.npz).

Uses class weighting to handle the imbalanced dataset (background: 4705
vs impact_crash: 141) rather than discarding data via subsampling --
keeps all the data, tells the loss function to pay more attention to
underrepresented classes.

Run: python train_classifier.py
Output: models/classifier.keras, models/classes.json
"""

import os
import json
import numpy as np
import tensorflow as tf
from sklearn.model_selection import GroupShuffleSplit
from sklearn.utils.class_weight import compute_class_weight
from sklearn.metrics import classification_report, confusion_matrix

EMBEDDINGS_PATH = "data/embeddings.npz"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "classifier.keras")
CLASSES_PATH = os.path.join(MODEL_DIR, "classes.json")


def build_model(input_dim, num_classes):
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(input_dim,)),
        tf.keras.layers.Dense(256, activation="relu"),
        tf.keras.layers.Dropout(0.3),
        tf.keras.layers.Dense(64, activation="relu"),
        tf.keras.layers.Dropout(0.2),
        tf.keras.layers.Dense(num_classes, activation="softmax"),
    ])
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def main():
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

    # Group-aware split: all augmented variants of a clip stay together with
    # their original in the same split, so the model is never tested on a
    # pitch-shifted/time-stretched copy of something it trained on.
    gss1 = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=42)
    train_idx, temp_idx = next(gss1.split(X, y, groups=groups))
    X_train, y_train, groups_train = X[train_idx], y[train_idx], groups[train_idx]
    X_temp, y_temp, groups_temp = X[temp_idx], y[temp_idx], groups[temp_idx]

    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=42)
    val_idx, test_idx = next(gss2.split(X_temp, y_temp, groups=groups_temp))
    X_val, y_val = X_temp[val_idx], y_temp[val_idx]
    X_test, y_test = X_temp[test_idx], y_temp[test_idx]

    # Sanity check: confirm no group overlaps between splits
    train_groups = set(groups_train)
    val_groups = set(groups_temp[val_idx])
    test_groups = set(groups_temp[test_idx])
    assert not (train_groups & val_groups), "Group leak between train and val!"
    assert not (train_groups & test_groups), "Group leak between train and test!"
    assert not (val_groups & test_groups), "Group leak between val and test!"
    print("\nGroup-split sanity check passed: no original clip appears in more than one split.")

    print(f"\nTrain: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    # Class weights to counter imbalance
    class_weights_arr = compute_class_weight(
        class_weight="balanced", classes=np.unique(y_train), y=y_train
    )
    class_weight_dict = {i: w for i, w in enumerate(class_weights_arr)}
    print("\nClass weights (higher = rarer class, more emphasis):")
    for i, cls in enumerate(classes):
        print(f"  {cls}: {class_weight_dict.get(i, 'N/A'):.2f}")

    model = build_model(input_dim=X.shape[1], num_classes=len(classes))
    model.summary()

    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=8, restore_best_weights=True
    )

    print("\nTraining...")
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=50,
        batch_size=32,
        class_weight=class_weight_dict,
        callbacks=[early_stop],
        verbose=2,
    )

    print("\n--- Test set evaluation ---")
    y_pred_probs = model.predict(X_test)
    y_pred = np.argmax(y_pred_probs, axis=1)

    print(classification_report(y_test, y_pred, target_names=classes))
    print("Confusion matrix (rows=true, cols=predicted):")
    print(classes)
    print(confusion_matrix(y_test, y_pred))

    os.makedirs(MODEL_DIR, exist_ok=True)
    model.save(MODEL_PATH)
    with open(CLASSES_PATH, "w") as f:
        json.dump(classes, f)

    print(f"\nModel saved to {MODEL_PATH}")
    print(f"Classes saved to {CLASSES_PATH}")


if __name__ == "__main__":
    main()
