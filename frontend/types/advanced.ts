/* Phase 2/3 types */

export interface ExplanationFactor {
  feature: string;
  label: string;
  importance: number;
  direction: string;
  explanation_text?: string;
}

export interface ExplanationPayload {
  success: boolean;
  prediction: {
    id: string;
    predicted_score: number;
    risk_probability: number;
    risk_level: string;
    model_name: string;
    model_version: string;
    model_type: string;
  };
  shap: ExplanationFactor[];
  lime: ExplanationFactor[];
  gradient: ExplanationFactor[];
  summary: string;
  factors: ExplanationFactor[];
  disclaimer: string;
}

export interface PredictionAdvanced {
  success: boolean;
  student_id: string;
  course_id: string | null;
  predicted_score: number;
  risk_probability: number;
  risk_level: string;
  model_name: string;
  model_version: string;
  model_type: string;
  prediction_id: string;
  latency_ms: number;
  explanation?: ExplanationPayload | null;
  recommendations_created?: number | null;
}

export interface Recommendation {
  id: string;
  student_id: string;
  course_id: string | null;
  prediction_id: string | null;
  recommendation_type: string;
  title: string;
  description: string;
  reason: string;
  priority: number;
  confidence: number;
  score: number;
  status: "PENDING" | "IN_PROGRESS" | "COMPLETED" | "DISMISSED";
  resource_id: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface LearningResource {
  id: string;
  course_id: string | null;
  title: string;
  description: string | null;
  resource_type: string;
  topic: string;
  difficulty: string;
  url: string;
  estimated_minutes: number;
}

export interface LearningProgress {
  success: boolean;
  learning_hours: number;
  practice_questions: number;
  recommendations_completed: number;
  recommendations_in_progress: number;
  recommendations_total: number;
  by_status: Record<string, number>;
}

export interface ModelVersionRecord {
  id: string;
  model_name: string;
  model_type: "BASELINE" | "TRANSFORMER" | "HYBRID";
  version: string;
  dataset_version: string;
  feature_version: string;
  training_date: string;
  metrics: Record<string, number>;
  hyperparameters: Record<string, unknown>;
  artifact_location: string;
  status: string;
  notes: string | null;
}

export interface ExperimentRecord {
  id: string;
  experiment_name: string;
  model_type: string;
  dataset_version: string;
  hyperparameters: Record<string, unknown>;
  metrics: {
    validation?: Record<string, number>;
    test?: Record<string, number>;
  };
  training_duration_seconds: number | null;
  notes: string | null;
  created_at: string;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  notification_type: string;
  link: string | null;
  is_read: boolean;
  created_at: string;
}

export interface BatchJob {
  id: string;
  scope: string;
  scope_id: string | null;
  model_type: string;
  status: string;
  total_items: number;
  processed_items: number;
  failed_items: number;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  result: Record<string, unknown>;
}

export interface DriftFeature {
  feature: string;
  psi: number;
  status: string;
  training_mean: number | null;
  live_mean: number | null;
}

export interface MonitoringPayload {
  success: boolean;
  summary: {
    total_predictions: number;
    average_predicted_score: number | null;
    predictions_by_model_type: Record<string, number>;
    risk_distribution: Record<string, number>;
    failed_batch_jobs: number;
    latency: { count: number; avg_ms: number | null; p95_ms: number | null };
  };
  drift: {
    status: string;
    features: DriftFeature[];
    latency?: Record<string, unknown>;
    message: string;
  };
}
