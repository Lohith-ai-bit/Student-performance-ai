"""Model registry (§17/§59): versioned models in the DB; only VALIDATED models may
be promoted to PRODUCTION. Artifacts stay on disk — the DB stores locations."""
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.models import ModelExperiment, ModelVersion
from app.models.advanced_enums import ModelStatus, ModelType
from pathlib import Path


def _artifact_dir() -> Path:
    return Path(settings.ML_ARTIFACTS_DIR)


def sync_from_artifacts(db: Session) -> list[ModelVersion]:
    """Register models found in ml/artifacts (idempotent by name+type+version)."""
    registered: list[ModelVersion] = []

    def _register(name: str, mtype: str, version: str, metadata: dict, metrics: dict, artifact: str, hyp: dict):
        exists = (
            db.query(ModelVersion)
            .filter(ModelVersion.model_name == name, ModelVersion.model_type == mtype, ModelVersion.version == version)
            .first()
        )
        if exists:
            registered.append(exists)
            return exists
        row = ModelVersion(
            model_name=name,
            model_type=mtype,
            version=version,
            dataset_version=metadata.get("dataset_version", "v1"),
            feature_version=metadata.get("feature_version", "v1"),
            training_date=datetime.fromisoformat(metadata["trained_at"]) if metadata.get("trained_at") else datetime.now(timezone.utc),
            metrics=metrics,
            hyperparameters=hyp,
            artifact_location=artifact,
            status=ModelStatus.VALIDATED.value if metadata.get("test_metrics") else ModelStatus.TRAINING.value,
        )
        db.add(row)
        registered.append(row)
        return row

    base_file = _artifact_dir() / "metadata.json"
    if base_file.exists():
        m = json.loads(base_file.read_text(encoding="utf-8"))
        for task, info in m.get("models", {}).items():
            _register(
                name=f"Baseline{info['model_name']}",
                mtype=ModelType.BASELINE.value,
                version=str(info.get("model_version", "1.0")),
                metadata=m,
                metrics=info.get("test_metrics", {}),
                artifact=str(base_file.parent / ("model_regression.joblib" if task == "regression" else "model_classification.joblib")),
                hyp={"task": task},
            )

    for meta_file, mtype, default_name, artifact in [
        ("transformer_metadata.json", ModelType.TRANSFORMER.value, "TemporalTransformer", "model_transformer.pt"),
        ("hybrid_metadata.json", ModelType.HYBRID.value, "HybridMLTransformer", "model_hybrid.pt"),
    ]:
        f = _artifact_dir() / meta_file
        if f.exists():
            m = json.loads(f.read_text(encoding="utf-8"))
            _register(
                name=m.get("model_name", default_name),
                mtype=mtype,
                version=str(m.get("model_version", "1.0")),
                metadata=m,
                metrics=m.get("test_metrics", {}),
                artifact=str(_artifact_dir() / artifact),
                hyp=m.get("hyperparameters", {}),
            )

    db.commit()
    return registered


def get_production_model(db: Session, model_type: str) -> ModelVersion | None:
    return (
        db.query(ModelVersion)
        .filter(ModelVersion.model_type == model_type.upper(), ModelVersion.status == ModelStatus.PRODUCTION.value)
        .order_by(ModelVersion.training_date.desc())
        .first()
    )


def promote(db: Session, model_id: uuid.UUID, notes: str | None = None) -> ModelVersion:
    """VALIDATED -> PRODUCTION; demotes the previous production model of the same type."""
    row = db.get(ModelVersion, model_id)
    if row is None:
        raise NotFoundError("Model version could not be found.", code="MODEL_NOT_FOUND")
    if row.status not in (ModelStatus.VALIDATED.value, ModelStatus.PRODUCTION.value):
        raise ValidationError(
            f"Only validated models may be promoted to production (current status: {row.status}).",
            code="MODEL_NOT_VALIDATED",
        )
    current = get_production_model(db, row.model_type)
    if current and current.id != row.id:
        current.status = ModelStatus.ARCHIVED.value
    row.status = ModelStatus.PRODUCTION.value
    if notes:
        row.notes = notes
    db.commit()
    db.refresh(row)
    return row


def list_models(db: Session) -> list[ModelVersion]:
    return db.query(ModelVersion).order_by(ModelVersion.training_date.desc()).all()


def list_experiments(db: Session, limit: int = 200) -> list[ModelExperiment]:
    return db.query(ModelExperiment).order_by(ModelExperiment.created_at.desc()).limit(limit).all()


def record_experiment(db: Session, name: str, model_type: str, hyperparameters: dict, metrics: dict, duration: float, notes: str = "") -> ModelExperiment:
    row = ModelExperiment(
        experiment_name=name,
        model_type=model_type,
        dataset_version="v1",
        hyperparameters=hyperparameters,
        metrics=metrics,
        training_duration_seconds=duration,
        notes=notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def import_experiment_report(db: Session) -> int:
    """Load ml/data/processed/experiment_report.json into model_experiments (§15/§16)."""
    from ml.config import DATA_PROCESSED_DIR

    report_file = DATA_PROCESSED_DIR / "experiment_report.json"
    if not report_file.exists():
        raise NotFoundError("No experiment report found. Run `python -m ml.training.compare_models` first.", code="NO_EXPERIMENT_REPORT")
    report = json.loads(report_file.read_text(encoding="utf-8"))
    count = 0
    for exp in report.get("experiments", []):
        exists = (
            db.query(ModelExperiment.id)
            .filter(ModelExperiment.experiment_name == exp["experiment_name"])
            .first()
        )
        if exists:
            continue
        db.add(
            ModelExperiment(
                experiment_name=exp["experiment_name"],
                model_type=exp["model_type"],
                dataset_version=exp.get("dataset_version", "v1"),
                hyperparameters=exp.get("hyperparameters", {}),
                metrics=exp.get("metrics", {}),
                training_duration_seconds=exp.get("training_duration_seconds"),
                notes=exp.get("notes", ""),
            )
        )
        count += 1
    db.commit()
    return count
