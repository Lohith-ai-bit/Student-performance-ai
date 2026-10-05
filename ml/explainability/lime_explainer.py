"""LIME local explanations for individual predictions (§20)."""
import numpy as np
import pandas as pd

from ml.explainability.labels import describe_factor, label_for


class LimeTabularExplainer:
    """LIME-style local linear explanation around one prediction."""

    def __init__(self, training_data: pd.DataFrame, feature_names: list[str], mode: str = "regression", seed: int = 42):
        from lime.lime_tabular import LimeTabularExplainer as _Lime

        self.feature_names = feature_names
        self.training = training_data.to_numpy(dtype=float)
        self.explainer = _Lime(
            self.training,
            feature_names=feature_names,
            mode=mode,
            discretize_continuous=False,
            random_state=seed,
        )

    def local(self, predict_fn, features: pd.DataFrame, num_features: int = 8) -> list[dict]:
        row = features.to_numpy(dtype=float).reshape(1, -1)
        explanation = self.explainer.explain_instance(
            row[0], lambda X: np.asarray(predict_fn(pd.DataFrame(X, columns=self.feature_names))).reshape(-1, 1)[:, 0],
            num_features=num_features,
        )
        factors = []
        for feature_idx, weight in explanation.as_list():
            name = self.feature_names[feature_idx] if isinstance(feature_idx, (int, np.integer)) else str(feature_idx)
            factors.append(
                {
                    "feature": name,
                    "label": label_for(name),
                    "importance": round(float(weight), 4),
                    "direction": "positive" if weight >= 0 else "negative",
                }
            )
        for f in factors:
            f["explanation_text"] = describe_factor(f["label"], f["importance"], f["direction"])
        return factors
