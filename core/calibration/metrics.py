"""
L9 Calibration Metrics

Measures of calibration quality:
- ECE: Expected Calibration Error
- MCE: Max Calibration Error
- Brier Score: Mean squared error of probabilities
- Reliability Diagram: Visual inspection

Reference: L9-Calibration-Implementation-Roadmap.md §B.4, Spec §4.1
"""

import numpy as np
from typing import Tuple


def compute_ece(
    predicted_probs: np.ndarray,
    true_labels: np.ndarray,
    num_bins: int = 10,
) -> float:
    """
    Expected Calibration Error (ECE).

    ECE = average |P(correct) - accuracy| across confidence bins.
    Gold standard metric for calibration quality.

    Args:
        predicted_probs: (N, K) predicted probabilities
        true_labels: (N,) true class labels
        num_bins: Number of confidence bins (default 10)

    Returns:
        ECE score (0.0 = perfectly calibrated, lower is better)
        Target: < 0.05
    """
    predicted_probs = np.asarray(predicted_probs, dtype=np.float32)
    true_labels = np.asarray(true_labels, dtype=np.int32)

    predicted_class = np.argmax(predicted_probs, axis=1)
    max_prob = np.max(predicted_probs, axis=1)

    correct = (predicted_class == true_labels).astype(np.float32)

    bin_edges = np.linspace(0.0, 1.0, num_bins + 1)
    bin_indices = np.digitize(max_prob, bin_edges) - 1
    bin_indices = np.clip(bin_indices, 0, num_bins - 1)

    ece = 0.0
    for bin_idx in range(num_bins):
        mask = bin_indices == bin_idx
        if np.sum(mask) > 0:
            bin_confidence = np.mean(max_prob[mask])
            bin_accuracy = np.mean(correct[mask])
            bin_size = np.sum(mask)

            ece += (bin_size / len(predicted_probs)) * abs(
                bin_confidence - bin_accuracy
            )

    return float(ece)


def compute_mce(
    predicted_probs: np.ndarray,
    true_labels: np.ndarray,
    num_bins: int = 10,
) -> float:
    """
    Max Calibration Error (MCE).

    MCE = maximum |P(correct) - accuracy| across bins.
    Worst-case calibration error.

    Args:
        predicted_probs: (N, K) predicted probabilities
        true_labels: (N,) true labels
        num_bins: Number of bins

    Returns:
        MCE score (lower is better)
        Target: < 0.10
    """
    predicted_probs = np.asarray(predicted_probs, dtype=np.float32)
    true_labels = np.asarray(true_labels, dtype=np.int32)

    predicted_class = np.argmax(predicted_probs, axis=1)
    max_prob = np.max(predicted_probs, axis=1)
    correct = (predicted_class == true_labels).astype(np.float32)

    bin_edges = np.linspace(0.0, 1.0, num_bins + 1)
    bin_indices = np.digitize(max_prob, bin_edges) - 1
    bin_indices = np.clip(bin_indices, 0, num_bins - 1)

    mce = 0.0
    for bin_idx in range(num_bins):
        mask = bin_indices == bin_idx
        if np.sum(mask) > 0:
            bin_confidence = np.mean(max_prob[mask])
            bin_accuracy = np.mean(correct[mask])
            mce = max(mce, abs(bin_confidence - bin_accuracy))

    return float(mce)


def compute_brier(
    predicted_probs: np.ndarray,
    true_labels: np.ndarray,
) -> float:
    """
    Brier Score: Mean squared error of probabilities.

    Brier = (1/N) * sum(P_i(k) - Y_i(k))^2
    Penalizes both accuracy and calibration.

    Args:
        predicted_probs: (N, K) predicted probabilities
        true_labels: (N,) true labels or (N, K) one-hot

    Returns:
        Brier score (0.0 = perfect, lower is better)
        Target: < 0.10
    """
    predicted_probs = np.asarray(predicted_probs, dtype=np.float32)
    true_labels = np.asarray(true_labels, dtype=np.int32)

    if true_labels.ndim == 1:
        num_classes = predicted_probs.shape[1]
        one_hot = np.zeros((len(true_labels), num_classes))
        one_hot[np.arange(len(true_labels)), true_labels] = 1.0
        true_labels = one_hot

    brier = np.mean((predicted_probs - true_labels) ** 2)

    return float(brier)


def compute_reliability_diagram(
    predicted_probs: np.ndarray,
    true_labels: np.ndarray,
    num_bins: int = 10,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute reliability diagram points.

    Returns: (bin_confidences, bin_accuracies)
    Perfect calibration is a 45° diagonal line (confidence = accuracy).

    Args:
        predicted_probs: (N, K) predicted probabilities
        true_labels: (N,) true labels
        num_bins: Number of bins

    Returns:
        (confidences, accuracies) each shape (num_bins,)
    """
    predicted_probs = np.asarray(predicted_probs, dtype=np.float32)
    true_labels = np.asarray(true_labels, dtype=np.int32)

    predicted_class = np.argmax(predicted_probs, axis=1)
    max_prob = np.max(predicted_probs, axis=1)
    correct = (predicted_class == true_labels).astype(np.float32)

    bin_edges = np.linspace(0.0, 1.0, num_bins + 1)
    bin_indices = np.digitize(max_prob, bin_edges) - 1
    bin_indices = np.clip(bin_indices, 0, num_bins - 1)

    confidences: list[float] = []
    accuracies: list[float] = []

    for bin_idx in range(num_bins):
        mask = bin_indices == bin_idx
        if np.sum(mask) > 0:
            confidences.append(float(np.mean(max_prob[mask])))
            accuracies.append(float(np.mean(correct[mask])))
        else:
            confidences.append(float(bin_edges[bin_idx]))
            accuracies.append(float("nan"))

    return np.array(confidences), np.array(accuracies)


def compute_uncertainty_quality(
    aleatoric_unc: np.ndarray,
    epistemic_unc: np.ndarray,
    prediction_entropy: np.ndarray,
    ensemble_disagreement: np.ndarray,
) -> Tuple[float, float]:
    """
    Compute how well uncertainty estimates capture actual properties.

    Returns:
        (aleatoric_quality, epistemic_quality)
        where each is Pearson correlation coefficient [0, 1]

    Target:
        - aleatoric_quality > 0.65 (correlates with entropy)
        - epistemic_quality > 0.75 (correlates with ensemble disagreement)
    """
    aleatoric_unc = np.asarray(aleatoric_unc).flatten()
    epistemic_unc = np.asarray(epistemic_unc).flatten()
    prediction_entropy = np.asarray(prediction_entropy).flatten()
    ensemble_disagreement = np.asarray(ensemble_disagreement).flatten()

    aleatoric_quality = float(np.corrcoef(aleatoric_unc, prediction_entropy)[0, 1])
    epistemic_quality = float(np.corrcoef(epistemic_unc, ensemble_disagreement)[0, 1])

    if np.isnan(aleatoric_quality):
        aleatoric_quality = 0.0
    if np.isnan(epistemic_quality):
        epistemic_quality = 0.0

    aleatoric_quality = max(0.0, aleatoric_quality)
    epistemic_quality = max(0.0, epistemic_quality)

    return aleatoric_quality, epistemic_quality


def compute_selective_accuracy(
    predicted_probs: np.ndarray,
    true_labels: np.ndarray,
    confidence_threshold: float = 0.7,
) -> Tuple[float, float]:
    """
    Selective Prediction: accuracy when deferring low-confidence cases.

    Returns:
        (coverage, accuracy)
        - coverage: fraction of samples kept (> threshold)
        - accuracy: accuracy on kept samples
    """
    predicted_probs = np.asarray(predicted_probs, dtype=np.float32)
    true_labels = np.asarray(true_labels, dtype=np.int32)

    predicted_class = np.argmax(predicted_probs, axis=1)
    max_prob = np.max(predicted_probs, axis=1)

    mask = max_prob >= confidence_threshold

    if np.sum(mask) == 0:
        return 0.0, 0.0

    coverage = float(np.sum(mask) / len(predicted_probs))
    selected_accuracy = float(np.mean(predicted_class[mask] == true_labels[mask]))

    return coverage, selected_accuracy
