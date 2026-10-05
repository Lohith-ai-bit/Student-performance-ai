"""Evaluation metrics for regression and classification (§27)."""
import numpy as np
from sklearn import metrics

REGRESSION_METRICS = ["MAE", "RMSE", "R2"]
CLASSIFICATION_METRICS = ["Accuracy", "Precision", "Recall", "F1", "ROC_AUC"]


def regression_metrics(y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "MAE": round(float(metrics.mean_absolute_error(y_true, y_pred)), 4),
        "RMSE": round(float(np.sqrt(metrics.mean_squared_error(y_true, y_pred))), 4),
        "R2": round(float(metrics.r2_score(y_true, y_pred)), 4),
    }


def classification_metrics(y_true, y_pred, y_proba=None) -> dict:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    result = {
        "Accuracy": round(float(metrics.accuracy_score(y_true, y_pred)), 4),
        "Precision": round(float(metrics.precision_score(y_true, y_pred, zero_division=0)), 4),
        "Recall": round(float(metrics.recall_score(y_true, y_pred, zero_division=0)), 4),
        "F1": round(float(metrics.f1_score(y_true, y_pred, zero_division=0)), 4),
    }
    if y_proba is not None and len(np.unique(y_true)) > 1:
        result["ROC_AUC"] = round(float(metrics.roc_auc_score(y_true, np.asarray(y_proba))), 4)
    else:
        result["ROC_AUC"] = None
    return result
