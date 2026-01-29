"""
L9 Calibration Methods

Implements:
- Temperature Scaling (Guo et al. 2017)
- Ensemble Averaging (Lakshminarayanan et al. 2017)
- MC-Dropout (Gal & Ghahramani 2016)

Reference: L9-Calibration-Implementation-Roadmap.md §B.2
"""

import numpy as np
from typing import Optional


def temperature_scaling(
    logits: np.ndarray,
    temperature: float = 1.0,
) -> np.ndarray:
    """
    Apply temperature scaling: P = softmax(logits / T).

    Args:
        logits: Raw network outputs, shape (batch, num_classes)
        temperature: Scaling factor (T=1 is uncalibrated, T>1 flattens)

    Returns:
        Calibrated probabilities, shape (batch, num_classes), sum to 1.0 per sample

    Reference: Guo et al. "On Calibration of Modern Neural Networks" (ICML 2017)
    """
    if temperature <= 0:
        raise ValueError(f"Temperature must be positive, got {temperature}")

    logits = np.asarray(logits, dtype=np.float32)

    # Numerical stability: subtract max before exp
    scaled = logits / temperature
    max_per_batch = np.max(scaled, axis=1, keepdims=True)
    exp = np.exp(scaled - max_per_batch)

    # Normalize to get probabilities
    probs = exp / np.sum(exp, axis=1, keepdims=True)

    return probs.astype(np.float32)


def ensemble_calibration(
    predictions: list[np.ndarray],
    aggregation: str = "mean",
) -> np.ndarray:
    """
    Average predictions across ensemble members.

    Args:
        predictions: List of M predictions, each shape (batch, num_classes)
        aggregation: "mean" | "median" | "max"

    Returns:
        Aggregated probabilities, shape (batch, num_classes), normalized

    Reference: Lakshminarayanan et al. "Simple and Scalable Predictive Uncertainty" (NIPS 2017)
    """
    if not predictions:
        raise ValueError("predictions list is empty")

    stack = np.stack([np.asarray(p, dtype=np.float32) for p in predictions], axis=0)
    # stack shape: (num_models, batch, num_classes)

    if aggregation == "mean":
        result = np.mean(stack, axis=0)
    elif aggregation == "median":
        result = np.median(stack, axis=0)
    elif aggregation == "max":
        result = np.max(stack, axis=0)
    else:
        raise ValueError(f"Unknown aggregation: {aggregation}")

    # Normalize
    result = result / np.sum(result, axis=1, keepdims=True)

    return result.astype(np.float32)


def mc_dropout_calibration(
    mc_samples: list[np.ndarray],
    aggregation: str = "mean",
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calibrate using MC-Dropout samples (Bayesian approximation).

    Args:
        mc_samples: List of M forward passes with dropout enabled, each (batch, num_classes)
        aggregation: How to combine samples

    Returns:
        (mean_predictions, variance_estimates) both shape (batch, num_classes)

    Reference: Gal & Ghahramani "Dropout as a Bayesian Approximation" (ICML 2016)
    """
    if not mc_samples:
        raise ValueError("mc_samples list is empty")

    stack = np.stack([np.asarray(s, dtype=np.float32) for s in mc_samples], axis=0)
    # stack shape: (num_samples, batch, num_classes)

    # Mean across MC samples (calibrated prediction)
    mean_pred = np.mean(stack, axis=0)

    # Variance across MC samples (epistemic uncertainty)
    variance = np.var(stack, axis=0)

    # Normalize mean to probability distribution
    mean_pred = mean_pred / np.sum(mean_pred, axis=1, keepdims=True)

    return mean_pred.astype(np.float32), variance.astype(np.float32)


def evidential_calibration(
    alpha: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calibrate using Evidential Deep Learning (Dirichlet posterior).

    Args:
        alpha: Concentration parameters from Dirichlet head, shape (batch, num_classes)

    Returns:
        (probabilities, uncertainty) both shape (batch, num_classes)

    Reference: Malinin & Grangier "Predictive Uncertainty via Evidential DL" (NeurIPS 2018)
    """
    alpha = np.asarray(alpha, dtype=np.float32)

    # Ensure positive concentration
    alpha = np.maximum(alpha, 1e-6)

    # Dirichlet posterior: P = alpha / sum(alpha)
    S = np.sum(alpha, axis=1, keepdims=True)
    probabilities = alpha / S

    # Uncertainty: variance of Dirichlet
    # Var[X_i] = (alpha_i * (S - alpha_i)) / (S^2 * (S + 1))
    uncertainty = (alpha * (S - alpha)) / (S**2 * (S + 1))

    return probabilities.astype(np.float32), uncertainty.astype(np.float32)


def conformal_calibration(
    probabilities: np.ndarray,
    calibration_scores: Optional[np.ndarray] = None,
    confidence_level: float = 0.9,
) -> np.ndarray:
    """
    Conformal prediction: return confidence sets.

    Args:
        probabilities: (batch, num_classes)
        calibration_scores: Optional (calib_batch,) scores for threshold
        confidence_level: Desired coverage (default 90%)

    Returns:
        Confidence-set size per sample, shape (batch,)
    """
    probabilities = np.asarray(probabilities, dtype=np.float32)

    # Placeholder: full conformal requires calibration dataset; for now, pass-through
    return np.ones(probabilities.shape[0]).astype(np.float32)
