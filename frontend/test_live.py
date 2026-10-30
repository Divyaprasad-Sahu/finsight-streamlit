import unittest
import numpy as np
import pandas as pd
from live import score_bars, Telemetry


class LiveTests(unittest.TestCase):
    def fixture(self):
        rng = np.random.default_rng(1)
        return pd.DataFrame({'Close': 100 * np.cumprod(1 + rng.normal(0, .002, 300)),
                             'Volume': rng.integers(0, 10000, 300)},
                            index=pd.date_range('2026-01-01', periods=300, freq='5min', tz='UTC'))

    def test_chronological_split_and_scores(self):
        frame = self.fixture()
        result, train, fit_seconds, inference_seconds = score_bars(frame)
        self.assertLess(train.index[-1], result.index[0])
        self.assertEqual(len(train) + len(result), len(frame) - 20)
        self.assertTrue(np.isfinite(result['Decision score']).all())
        self.assertTrue((result.Anomaly == (result['Decision score'] < 0)).all())
        self.assertGreaterEqual(fit_seconds, 0)
        self.assertGreaterEqual(inference_seconds, 0)

    def test_holdout_does_not_change_fitted_model(self):
        frame = self.fixture()
        original, _, _, _ = score_bars(frame)
        # Mutating the last holdout row must not alter earlier holdout scores.
        frame.iloc[-1, frame.columns.get_loc('Close')] *= 2
        changed, _, _, _ = score_bars(frame)
        np.testing.assert_array_equal(original['Decision score'].iloc[:-1], changed['Decision score'].iloc[:-1])

    def test_short_input_rejected(self):
        with self.assertRaises(ValueError):
            score_bars(self.fixture().iloc[:50])

    def test_metrics_exposition(self):
        state = Telemetry()
        state.increment('finsight_live_fetch_total')
        self.assertIn('finsight_live_fetch_total 1', state.exposition())


if __name__ == '__main__':
    unittest.main()
