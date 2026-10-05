"""Gradient-based feature attribution for the Transformer (used when no tabular
component exists to run SHAP/LIME on). Attribution = |gradient x input| summed
over attended (mask=1) time steps, aggregated per sequence feature."""
import numpy as np
import torch

from ml.config import SEQUENCE_FEATURES
from ml.explainability.labels import SEQUENCE_FEATURE_LABELS, describe_factor


def gradient_attribution(
    model, sequence: torch.Tensor, mask: torch.Tensor, output: str = "score",
    max_features: int = 6, tabular: torch.Tensor | None = None,
) -> list[dict]:
    """sequence: [1, T, F] (requires_grad); tabular required for HYBRID models."""
    model.eval()
    seq = sequence.clone().detach().requires_grad_(True)
    mask = mask.clone().detach()
    if tabular is not None:
        out = model(seq, mask, tabular.clone().detach())
    else:
        out = model(seq, mask)
    target = out["risk_logit"] if output == "risk" else out["score"]
    target.backward()

    attribution = (seq.grad.squeeze(0) * seq.detach().squeeze(0)).abs()  # [T, F]
    valid = mask.squeeze(0) > 0.5
    per_feature = attribution[valid].sum(dim=0) if valid.any() else attribution.sum(dim=0)
    per_feature = per_feature.detach().cpu().numpy()

    order = np.argsort(-per_feature)[:max_features]
    factors = []
    total = float(per_feature.sum()) or 1.0
    for idx in order:
        share = float(per_feature[idx]) / total
        direction = "positive" if share >= 0 else "negative"
        label = SEQUENCE_FEATURE_LABELS.get(SEQUENCE_FEATURES[idx], SEQUENCE_FEATURES[idx])
        factors.append(
            {
                "feature": SEQUENCE_FEATURES[idx],
                "label": label,
                "importance": round(share, 4),
                "direction": direction,
                "explanation_text": describe_factor(label, share, direction),
            }
        )
    return factors
