import unittest

import numpy as np

from threat_fusion import (
    aggregate_yamnet_evidence,
    build_yamnet_index_groups,
    fuse_predictions,
)


CLASSES = ["background", "explosion", "impact_crash", "scream_distress", "siren_traffic"]


class ThreatFusionTests(unittest.TestCase):
    def test_exact_mapping_does_not_treat_goose_honk_as_traffic(self):
        names = ["Honk", "Vehicle horn, car horn, honking", "Screaming"]
        groups = build_yamnet_index_groups(names)
        self.assertEqual(groups["siren_traffic"], (1,))
        self.assertEqual(groups["scream_distress"], (2,))

    def test_yamnet_does_not_override_background_prediction(self):
        clip = np.array([0.72, 0.05, 0.05, 0.13, 0.05], dtype=np.float32)
        frame = np.array(
            [
                [0.75, 0.04, 0.04, 0.12, 0.05],
                [0.15, 0.03, 0.02, 0.77, 0.03],
                [0.45, 0.03, 0.03, 0.44, 0.05],
            ],
            dtype=np.float32,
        )
        evidence = np.array([0.0, 0.0, 0.0, 0.45, 0.0], dtype=np.float32)
        fused, details = fuse_predictions(clip, frame, evidence, CLASSES)
        self.assertEqual(CLASSES[int(np.argmax(fused))], "background")
        self.assertEqual(details["yamnet_weight"], 0.0)

    def test_strong_semantic_evidence_corrects_wrong_threat_category(self):
        clip = np.array([0.08, 0.58, 0.25, 0.04, 0.05], dtype=np.float32)
        evidence = np.array([0.0, 0.05, 0.68, 0.0, 0.0], dtype=np.float32)
        fused, _ = fuse_predictions(clip, None, evidence, CLASSES)
        self.assertEqual(CLASSES[int(np.argmax(fused))], "impact_crash")

    def test_weak_evidence_does_not_override_background(self):
        clip = np.array([0.75, 0.08, 0.06, 0.06, 0.05], dtype=np.float32)
        evidence = np.array([0.0, 0.0, 0.0, 0.09, 0.0], dtype=np.float32)
        fused, _ = fuse_predictions(clip, None, evidence, CLASSES)
        self.assertEqual(CLASSES[int(np.argmax(fused))], "background")

    def test_yamnet_scores_are_aggregated_per_project_class(self):
        names = ["Speech", "Screaming", "Explosion", "Siren"]
        groups = build_yamnet_index_groups(names)
        scores = np.array([[0.9, 0.1, 0.2, 0.05], [0.8, 0.7, 0.1, 0.1]])
        evidence = aggregate_yamnet_evidence(scores, groups, CLASSES)
        self.assertGreater(evidence[CLASSES.index("scream_distress")], 0.5)
        self.assertEqual(evidence[CLASSES.index("background")], 0.0)


if __name__ == "__main__":
    unittest.main()
