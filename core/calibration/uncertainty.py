"""
L9 Uncertainty Decomposition

Aleatoric (data/environment noise) vs Epistemic (model/knowledge scarcity).

Methods:
- Heteroscedastic regression head (aleatoric from σ² output)
- Ensemble disagreement (epistemic from model variance)
- MC-Dropout variance
- Hybrid (combine multiple sources)

Reference: L9-Calibration-Implementation-Roadmap.md §B.3
"""

import numpy as np
from typing import Optional, Tuple


def decompose_uncertainty_heteroscedastic(
    mean_prediction: np.ndarray,
    variance: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Decompose using heteroscedastic head output.

    Aleatoric = variance from auxiliary σ² head
    Epistemic = entropy / spread of mean prediction

    Args:
        mean_prediction: Model prediction, shape (batch, num_classes)
        variance: σ² from heteroscedastic head, shape (batch,) or (batch, num_classes)

    Returns:
        (aleatoric_unc, epistemic_unc) each shape (batch,)
    """
    mean_prediction = np.asarray(mean_prediction, dtype=np.float32)
    variance = np.asarray(variance, dtype=np.float32)

    # Aleatoric: directly from variance
    if variance.ndim == 1:
        aleatoric = np.sqrt(variance)
    else:
        aleatoric = np.sqrt(np.mean(variance, axis=1))

    # Epistemic: entropy of mean prediction (how spread out?)
    entropy = -np.sum(mean_prediction * np.log(mean_prediction + 1e-10), axis=1)
    max_entropy = np.log(mean_prediction.shape[1])
    epistemic = entropy / max_entropy

    # Normalize to [0, 1]
    aleatoric = np.clip(aleatoric, 0.0, 1.0)
    epistemic = np.clip(epistemic, 0.0, 1.0)

    return aleatoric.astype(np.float32), epistemic.astype(np.float32)


def decompose_uncertainty_ensemble(
    predictions: list[np.ndarray],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Decompose using ensemble disagreement.

    Epistemic = std dev across ensemble members (model variance)
    Aleatoric = mean entropy of individual predictions (data noise)

    Args:
        predictions: List of M predictions, each shape (batch, num_classes)

    Returns:
        (aleatoric_unc, epistemic_unc) each shape (batch,)
    """
    if not predictions:
        raise ValueError("predictions list is empty")

    stack = np.stack([np.asarray(p, dtype=np.float32) for p in predictions], axis=0)
    # (num_models, batch, num_classes)

    # Epistemic: disagreement across ensemble
    mean_pred = np.mean(stack, axis=0)
    variance = np.mean((stack - mean_pred) ** 2, axis=0)
    epistemic = np.sqrt(np.mean(variance, axis=1))

    # Aleatoric: entropy of mean prediction
    entropy = -np.sum(mean_pred * np.log(mean_pred + 1e-10), axis=1)
    max_entropy = np.log(mean_pred.shape[1])
    aleatoric = entropy / max_entropy

    # Normalize
    epistemic = np.clip(epistemic, 0.0, 1.0)
    aleatoric = np.clip(aleatoric, 0.0, 1.0)

    return aleatoric.astype(np.float32), epistemic.astype(np.float32)


def decompose_uncertainty_mc_dropout(
    mc_samples: list[np.ndarray],
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Decompose using MC-Dropout variance.

    Epistemic = variance across MC samples (model uncertainty)
    Aleatoric = entropy of mean sample (data noise)

    Args:
        mc_samples: List of M forward passes, each (batch, num_classes)

    Returns:
        (aleatoric_unc, epistemic_unc) each shape (batch,)
    """
    if not mc_samples:
        raise ValueError("mc_samples list is empty")

    stack = np.stack([np.asarray(s, dtype=np.float32) for s in mc_samples], axis=0)
    # (num_samples, batch, num_classes)

    # Epistemic: variance across MC samples
    mean_pred = np.mean(stack, axis=0)
    variance = np.var(stack, axis=0)
    epistemic = np.sqrt(np.mean(variance, axis=1))

    # Aleatoric: entropy of mean prediction
    entropy = -np.sum(mean_pred * np.log(mean_pred + 1e-10), axis=1)
    max_entropy = np.log(mean_pred.shape[1])
    aleatoric = entropy / max_entropy

    # Normalize
    epistemic = np.clip(epistemic, 0.0, 1.0)
    aleatoric = np.clip(aleatoric, 0.0, 1.0)

    return aleatoric.astype(np.float32), epistemic.astype(np.float32)


def decompose_uncertainty_hybrid(
    mean_prediction: np.ndarray,
    ensemble_predictions: Optional[list[np.ndarray]] = None,
    mc_samples: Optional[list[np.ndarray]] = None,
    heteroscedastic_variance: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Hybrid decomposition using all available sources.

    Combines:
    - Aleatoric: heteroscedastic head (if available), else entropy
    - Epistemic: ensemble/MC variance (if available), else entropy spread

    Args:
        mean_prediction: Base prediction, shape (batch, num_classes)
        ensemble_predictions: Optional, list of ensemble preds
        mc_samples: Optional, list of MC samples
        heteroscedastic_variance: Optional, σ² from auxiliary head

    Returns:
        (aleatoric_unc, epistemic_unc) each shape (batch,)
    """
    mean_prediction = np.asarray(mean_prediction, dtype=np.float32)

    # Aleatoric: prefer heteroscedastic, fallback to entropy
    if heteroscedastic_variance is not None:
        aleatoric = np.sqrt(np.asarray(heteroscedastic_variance))
    else:
        entropy = -np.sum(mean_prediction * np.log(mean_prediction + 1e-10), axis=1)
        aleatoric = entropy / np.log(mean_prediction.shape[1])

    # Epistemic: prefer ensemble/MC, fallback to entropy
    if ensemble_predictions is not None and ensemble_predictions:
        _, epistemic = decompose_uncertainty_ensemble(ensemble_predictions)
    elif mc_samples is not None and mc_samples:
        _, epistemic = decompose_uncertainty_mc_dropout(mc_samples)
    else:
        entropy = -np.sum(mean_prediction * np.log(mean_prediction + 1e-10), axis=1)
        epistemic = entropy / np.log(mean_prediction.shape[1])

    # Normalize to [0, 1]
    aleatoric = np.clip(aleatoric, 0.0, 1.0)
    epistemic = np.clip(epistemic, 0.0, 1.0)

    return aleatoric.astype(np.float32), epistemic.astype(np.float32)
