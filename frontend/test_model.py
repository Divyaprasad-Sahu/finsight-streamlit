import json
import unittest
import numpy as np
from model import dashboard_data, render_dashboard


class ModelTests(unittest.TestCase):
    def test_reproducible_models(self):
        first = dashboard_data()
        dashboard_data.cache_clear()
        self.assertEqual(first, dashboard_data())

    def test_scores_and_flags(self):
        data = dashboard_data()
        self.assertEqual(len(data['stocks']), 6)
        self.assertEqual(sum(len(s['prices']) for s in data['stocks']), 720)
        for stock in data['stocks']:
            self.assertTrue(np.isfinite(stock['scores']).all())
            self.assertTrue(all(p > 0 for p in stock['prices']))
            self.assertEqual(stock['anomaly_count'], 6)
            # The deliberately injected extreme return must be detected.
            self.assertIn(92, stock['anomalies'])
            self.assertEqual([i for i, score in enumerate(stock['scores']) if score < 0], stock['anomalies'])

    def test_html_embeds_serializable_model_results(self):
        html = render_dashboard()
        self.assertNotIn('__DASHBOARD_DATA__', html)
        payload = html.split('const DATA=', 1)[1].split(';\nlet selected=', 1)[0]
        self.assertEqual(json.loads(payload), dashboard_data())


if __name__ == '__main__':
    unittest.main()
