export type Role = "STUDENT" | "FACULTY" | "ADMIN";

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface AuthSession {
  access_token: string;
  refresh_token: string;
  user: User;
}

export interface StudentProfile {
  id: string;
  name: string;
  email: string;
  roll_number: string;
  department: string;
  branch: string;
  year: number;
  semester: number;
  section: string;
  admission_year: number;
}

export interface CourseInfo {
  id: string;
  course_code: string;
  course_name: string;
  credits: number;
  department_id: string | null;
  semester: number;
}

export interface Assessment {
  id: string;
  student_id: string;
  course_id: string;
  assessment_type: string;
  score: number;
  maximum_score: number;
  assessment_date: string;
  created_at: string;
}

export interface Attendance {
  id: string;
  student_id: string;
  course_id: string;
  classes_conducted: number;
  classes_attended: number;
  attendance_percentage: number;
  date: string;
  created_at: string;
}

export interface LearningActivity {
  id: string;
  student_id: string;
  course_id: string;
  activity_date: string;
  session_duration: number;
  videos_watched: number;
  videos_completed: number;
  documents_opened: number;
  quiz_attempts: number;
  assignments_submitted: number;
  late_submissions: number;
  practice_questions_attempted: number;
  login_count: number;
  created_at: string;
}

export interface PredictionRecord {
  id: string;
  student_id: string;
  course_id: string | null;
  model_name: string;
  model_version: string;
  predicted_score: number;
  risk_probability: number;
  risk_level: RiskLevel;
  prediction_date: string;
  created_at: string;
}

export interface PredictionResult {
  success: boolean;
  student_id: string;
  course_id: string | null;
  predicted_score: number;
  risk_probability: number;
  risk_level: RiskLevel;
  model_name: string;
  model_version: string;
  prediction_id: string;
  per_course?: { course_id: string; predicted_score: number; risk_probability: number }[];
}

export interface ModelInfo {
  model_name: string;
  model_version: string;
  task: string;
  trained_at: string | null;
  dataset_version: string | null;
  feature_version: string | null;
  metrics: { validation?: Record<string, number>; test?: Record<string, number> };
  selected: boolean;
}

export interface EvaluationRow {
  model_name: string;
  task: string;
  metrics: Record<string, number | null>;
}

export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface FacultyStudentRow {
  student_id: string;
  name: string;
  email: string;
  roll_number: string;
  department: string;
  branch: string;
  year: number;
  semester: number;
  section: string;
  risk_level: RiskLevel | null;
  predicted_score: number | null;
  prediction_date: string | null;
}

export interface StudentDashboard {
  success: boolean;
  student: {
    id: string;
    name: string | null;
    roll_number: string;
    department: string;
    branch: string;
    year: number;
    semester: number;
    section: string;
  };
  summary: {
    gpa: number | null;
    predicted_score: number | null;
    attendance_percentage: number | null;
    engagement_score: number | null;
    risk_level: RiskLevel | null;
  };
  performance: {
    course_id: string;
    course_code: string;
    current_average: number | null;
    final_average: number | null;
  }[];
  performance_trend: {
    course_code: string;
    previous: number | null;
    current: number | null;
    predicted: number | null;
  }[];
  attendance: {
    course_id: string;
    course_code: string;
    percentage: number | null;
    classes_conducted: number;
    classes_attended: number;
  }[];
  latest_prediction: PredictionRecord | null;
}

export interface FacultyDashboard {
  success: boolean;
  faculty_name: string;
  totals: {
    students: number;
    avg_performance: number | null;
    avg_attendance: number | null;
    high_risk: number;
    medium_risk: number;
    low_risk: number;
    critical_risk?: number;
  };
  performance_distribution: { bucket: string; count: number }[];
  risk_distribution: { level: RiskLevel; count: number }[];
  attendance_distribution: { bucket: string; count: number }[];
}

export interface AdminDashboard {
  success: boolean;
  totals: {
    students: number;
    faculty: number;
    courses: number;
    departments: number;
    avg_performance: number | null;
    at_risk: number;
  };
  performance_by_department: { department: string; avg_performance: number }[];
  risk_distribution: { level: RiskLevel; count: number }[];
  attendance_distribution: { bucket: string; count: number }[];
  year_wise_performance: { year: string; avg_performance: number }[];
}

export interface ImportReport {
  success: boolean;
  file_name: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  inserted: number;
  skipped_duplicates: number;
  errors: { row: number; field: string; message: string; raw: string }[];
  message: string;
}

export interface FacultyStudentDetail {
  success: boolean;
  student: {
    student_id: string;
    name: string;
    email: string;
    roll_number: string;
    department: string;
    branch: string;
    year: number;
    semester: number;
    section: string;
  };
  assessments: Assessment[];
  attendance: Attendance[];
  activities: LearningActivity[];
  predictions: PredictionRecord[];
}

export interface ApiError {
  success: false;
  error: { code: string; message: string };
}
