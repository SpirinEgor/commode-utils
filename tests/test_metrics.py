import unittest

import torch
from parameterized import parameterized

from commode_utils.metrics import SequentialF1Score, ClassificationMetrics


class TestMetrics(unittest.TestCase):
    def test_update(self):
        """Sequences and corresponding statistic:
        target     | predicted  | TP | FP | FN
        1, 2, 3, 4 | 2, 4, 1, 5 | 3  | 1  | 1
        1, 2, 3    | 4, 5, 6    | 0  | 3  | 3
        1, 2       | 1, 2, 3    | 2  | 0  | 1
        1          | -          | 0  | 1  | 0

        """
        target = torch.tensor([[1, 1, 1, 1], [2, 2, 2, 0], [3, 3, 0, -1], [4, 0, -1, -1]])
        predicted = torch.tensor([[2, 4, 1, 0], [4, 5, 2, 0], [1, 6, 3, 0], [5, -1, -1, -1]])

        metric = SequentialF1Score(pad_idx=-1, eos_idx=0)
        _ = metric(predicted, target)

        self.assertEqual(5, metric.true_positive)
        self.assertEqual(5, metric.false_positive)
        self.assertEqual(5, metric.false_negative)

    def test_computing_metrics(self):
        metric = SequentialF1Score(pad_idx=-1, eos_idx=0)
        metric.true_positive += 3
        metric.false_positive += 4
        metric.false_negative += 7

        classification_metrics: ClassificationMetrics = metric.compute()
        self.assertAlmostEqual(3 / 7, classification_metrics.precision.item())
        self.assertAlmostEqual(3 / 10, classification_metrics.recall.item())
        self.assertAlmostEqual(6 / 17, classification_metrics.f1_score.item())

    def test_computing_zero_metrics(self):
        metric = SequentialF1Score(pad_idx=-1, eos_idx=0)

        classification_metrics: ClassificationMetrics = metric.compute()
        self.assertAlmostEqual(0, classification_metrics.precision.item())
        self.assertAlmostEqual(0, classification_metrics.recall.item())
        self.assertAlmostEqual(0, classification_metrics.f1_score.item())

    def test_update_equal_tensors(self):
        predicted = torch.tensor([1, 2, 3, 4, 5, 0, -1]).view(-1, 1)
        target = torch.tensor([1, 2, 3, 4, 5, 0, -1]).view(-1, 1)

        metric = SequentialF1Score(pad_idx=-1, eos_idx=0)
        _ = metric(predicted, target)

        self.assertEqual(metric.true_positive, 5)
        self.assertEqual(metric.false_positive, 0)
        self.assertEqual(metric.false_negative, 0)

    @parameterized.expand(
        [
            (-1, 0),
            (0, -1),
        ]
    )
    def test_masking(self, pad_idx: int, eos_idx: int):
        tokens = torch.tensor([[1, 1, 1, 1], [1, 1, 1, -1], [1, 1, -1, 2], [1, -1, 2, 2]])
        true_mask = torch.tensor(
            [
                [False, False, False, False],
                [False, False, False, True],
                [False, False, True, True],
                [False, True, True, True],
            ],
            dtype=torch.bool,
        )

        metric = SequentialF1Score(pad_idx=pad_idx, eos_idx=eos_idx)
        pred_mask = metric._get_end_sequence_mask(tokens)

        torch.testing.assert_allclose(pred_mask, true_mask)

    def test_masking_combining(self):
        tokens = torch.tensor([[1, 1, 1, 1], [1, 1, 0, -1], [1, 0, -1, 2], [0, -1, 2, 2]])
        true_mask = torch.tensor(
            [
                [False, False, False, False],
                [False, False, True, True],
                [False, True, True, True],
                [True, True, True, True],
            ],
            dtype=torch.bool,
        )

        metric = SequentialF1Score(pad_idx=-1, eos_idx=0)
        pred_mask = metric._get_end_sequence_mask(tokens)

        torch.testing.assert_allclose(pred_mask, true_mask)

    def test_update_with_masking(self):
        target = torch.tensor([1, 2, 3, 6, 7, 8, 0, -1, -1]).view(-1, 1)
        predicted = torch.tensor([1, 2, 3, 4, 5, 0, 6, 0, 8]).view(-1, 1)

        metric = SequentialF1Score(pad_idx=-1, eos_idx=0)
        _ = metric(predicted, target)

        self.assertEqual(metric.true_positive, 3)
        self.assertEqual(metric.false_positive, 2)
        self.assertEqual(metric.false_negative, 3)

    def test_update_with_masking_long_sequence(self):
        target = torch.tensor([1, 2, 3, 6, 7, 8, 0, -1, -1]).view(-1, 1)
        predicted = torch.tensor([1, 2, 3, 4, 5, 6, 7, 8]).view(-1, 1)

        metric = SequentialF1Score(pad_idx=-1, eos_idx=0)
        _ = metric(predicted, target)

        self.assertEqual(metric.true_positive, 6)
        self.assertEqual(metric.false_positive, 2)
        self.assertEqual(metric.false_negative, 0)
