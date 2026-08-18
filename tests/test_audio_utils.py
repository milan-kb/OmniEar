import unittest

import numpy as np

from audio_utils import extract_loudest_window, get_group_id, pool_embedding_frames


class AudioUtilsTests(unittest.TestCase):
    def test_legacy_augmentation_names_map_to_original(self):
        originals = {
            "aug_pitch_up_clip.wav",
            "aug_pitch_down_clip.wav",
            "aug_stretch_fast_clip.wav",
            "aug_stretch_slow_clip.wav",
            "aug_noise_clip.wav",
            "aug_playback_clip.wav",
        }
        self.assertEqual({get_group_id(name) for name in originals}, {"clip.wav"})

    def test_double_underscore_augmentation_name_is_unambiguous(self):
        self.assertEqual(get_group_id("aug__room_echo__my_clip.wav"), "my_clip.wav")

    def test_loudest_window_contains_transient(self):
        waveform = np.zeros(8000, dtype=np.float32)
        waveform[6100:6200] = 1.0
        selected = extract_loudest_window(waveform, window_samples=2000, sample_rate=1000)
        self.assertEqual(len(selected), 2000)
        self.assertGreater(float(np.max(selected)), 0.9)

    def test_pooling_supports_old_and_new_model_dimensions(self):
        frames = np.array([[1.0, 2.0], [3.0, 6.0]], dtype=np.float32)
        np.testing.assert_allclose(pool_embedding_frames(frames, output_dim=2), [2.0, 4.0])
        np.testing.assert_allclose(
            pool_embedding_frames(frames, output_dim=6),
            [2.0, 4.0, 3.0, 6.0, 1.0, 2.0],
        )


if __name__ == "__main__":
    unittest.main()
