"""ML configuration. Kept separate from code so thresholds/weights are auditable."""
from pathlib import Path

# Paths
ML_ROOT = Path(__file__).resolve().parent                 # <project>/ml/
ARTIFACTS_DIR = ML_ROOT / "artifacts"
DATA_RAW_DIR = ML_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = ML_ROOT / "data" / "processed"

DATASET_FILE = DATA_PROCESSED_DIR / "dataset.csv"
EXPERIMENTS_REGRESSION_FILE = DATA_PROCESSED_DIR / "experiments_regression.csv"
EXPERIMENTS_CLASSIFICATION_FILE = DATA_PROCESSED_DIR / "experiments_classification.csv"
METADATA_FILE = ARTIFACTS_DIR / "metadata.json"
MODEL_REGRESSION_FILE = ARTIFACTS_DIR / "model_regression.joblib"
MODEL_CLASSIFICATION_FILE = ARTIFACTS_DIR / "model_classification.joblib"

# Reproducibility
RANDOM_SEED = 42

# Train / validation / test split (§24)
TRAIN_FRACTION = 0.70
VALIDATION_FRACTION = 0.15
TEST_FRACTION = 0.15

# Classification target: a student is "at risk" if final (ENDTERM) percentage
# falls below this threshold. Configurable — not presented as validated.
RISK_SCORE_THRESHOLD = 50.0

# Feature set version — bump when feature engineering changes.
FEATURE_VERSION = "v1"

# Model metadata defaults
MODEL_VERSION = "1.0"
DATASET_VERSION = "v1"

# ---------------------------------------------------------------------------
# Phase 2/3: temporal sequence + Transformer configuration (§8/§9).
# All architecture hyperparameters live here — not scattered through the code.
# ---------------------------------------------------------------------------
SEQUENCE_LENGTH = 12          # weeks of history per example

SEQUENCE_FEATURES = [
    "attendance_percentage",
    "quiz_average",
    "assignment_average",
    "midterm_score",
    "session_duration",
    "video_completion_rate",
    "quiz_attempts",
    "assignment_submission_rate",
    "practice_questions",
    "login_frequency",
    "engagement_score",
    "performance_trend",
    "attendance_trend",
]

# feature groups used by ablation studies (§16/§53)
FEATURE_GROUPS = {
    "attendance": ["attendance_percentage", "attendance_trend"],
    "behaviour": [
        "session_duration", "video_completion_rate", "quiz_attempts",
        "assignment_submission_rate", "practice_questions", "login_frequency",
        "engagement_score",
    ],
    "academic": ["quiz_average", "assignment_average", "midterm_score", "performance_trend"],
}


class TransformerConfig:
    """Architecture hyperparameters for the Transformer and Hybrid models."""

    def __init__(
        self,
        sequence_length: int = SEQUENCE_LENGTH,
        n_features: int = len(SEQUENCE_FEATURES),
        embedding_dimension: int = 64,
        attention_heads: int = 4,
        encoder_layers: int = 2,
        feedforward_dimension: int = 128,
        dropout: float = 0.1,
        fusion: str = "learned",  # "concat" | "weighted" | "learned"
    ):
        self.sequence_length = sequence_length
        self.n_features = n_features
        self.embedding_dimension = embedding_dimension
        self.attention_heads = attention_heads
        self.encoder_layers = encoder_layers
        self.feedforward_dimension = feedforward_dimension
        self.dropout = dropout
        self.fusion = fusion

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, data: dict) -> "TransformerConfig":
        return cls(**data)


SEQUENCES_FILE = DATA_PROCESSED_DIR / "sequences.npz"
SEQUENCES_INDEX_FILE = DATA_PROCESSED_DIR / "sequences_index.json"
TRANSFORMER_FILE = ARTIFACTS_DIR / "model_transformer.pt"
HYBRID_FILE = ARTIFACTS_DIR / "model_hybrid.pt"
HYBRID_PREPROCESSOR_FILE = ARTIFACTS_DIR / "hybrid_preprocessor.joblib"
TRANSFORMER_METADATA_FILE = ARTIFACTS_DIR / "transformer_metadata.json"
HYBRID_METADATA_FILE = ARTIFACTS_DIR / "hybrid_metadata.json"
SEQUENCE_STATS_FILE = ARTIFACTS_DIR / "sequence_stats.json"
