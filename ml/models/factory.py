"""Model factory: the four baseline model families (§25).

All estimators get fixed random_state for reproducibility. Tree ensembles do
not require scaled inputs but share the same preprocessing pipeline anyway,
which keeps the comparison consistent across linear and non-linear models.
"""
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression

from ml.config import RANDOM_SEED


def get_regression_models() -> dict:
    models: dict = {"LinearRegression": LinearRegression()}
    try:
        from xgboost import XGBRegressor

        models["XGBoost"] = XGBRegressor(
            n_estimators=300, max_depth=5, learning_rate=0.08,
            random_state=RANDOM_SEED, n_jobs=-1, verbosity=0,
        )
    except ImportError:
        pass
    try:
        from lightgbm import LGBMRegressor

        models["LightGBM"] = LGBMRegressor(
            n_estimators=300, max_depth=5, learning_rate=0.08,
            random_state=RANDOM_SEED, n_jobs=-1, verbosity=-1,
        )
    except ImportError:
        pass
    models["RandomForest"] = RandomForestRegressor(
        n_estimators=300, max_depth=12, random_state=RANDOM_SEED, n_jobs=-1
    )
    return models


def get_classification_models() -> dict:
    models: dict = {
        "LogisticRegression": LogisticRegression(max_iter=2000, random_state=RANDOM_SEED)
    }
    try:
        from xgboost import XGBClassifier

        models["XGBoost"] = XGBClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.08,
            random_state=RANDOM_SEED, n_jobs=-1, verbosity=0, eval_metric="logloss",
        )
    except ImportError:
        pass
    try:
        from lightgbm import LGBMClassifier

        models["LightGBM"] = LGBMClassifier(
            n_estimators=300, max_depth=5, learning_rate=0.08,
            random_state=RANDOM_SEED, n_jobs=-1, verbosity=-1,
        )
    except ImportError:
        pass
    models["RandomForest"] = RandomForestClassifier(
        n_estimators=300, max_depth=12, random_state=RANDOM_SEED, n_jobs=-1
    )
    return models
