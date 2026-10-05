"""Sklearn preprocessing pipeline. Fitted ONLY on training data (inside the model
Pipeline) so no information leaks from validation/test sets (§23/§24)."""
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.features.build_features import FEATURE_COLUMNS_CATEGORICAL, FEATURE_COLUMNS_NUMERIC


def build_preprocessor() -> ColumnTransformer:
    numeric = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric, FEATURE_COLUMNS_NUMERIC),
            ("categorical", categorical, FEATURE_COLUMNS_CATEGORICAL),
        ],
        remainder="drop",
    )
