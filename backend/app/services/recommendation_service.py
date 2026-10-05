"""Personalized recommendation engine (§23-§28).

Pipeline: prediction + explanations + weak-area detection -> resource matching
-> rule-based candidate generation -> configurable ranking -> persistence.

Recommendations are decision support for the student; they never imply
automatic academic consequences.
"""
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.recommendation_config import (
    DIFFICULTY_ORDER,
    LOW_RISK_PROBABILITY,
    MAX_RECOMMENDATIONS,
    RANKING_WEIGHTS,
)
from app.models import Assessment, Course, LearningActivity, LearningResource, Recommendation
from app.models.advanced_enums import RecommendationType, ResourceType


@dataclass
class WeakArea:
    kind: str            # "course" | "assessment_type" | "behaviour" | "attendance"
    label: str           # human-readable, e.g. "Operating Systems quizzes"
    severity: float      # 0..1
    reason: str
    course_id: str | None = None
    suggested_resource_type: ResourceType | None = None

    def candidates(self) -> list[dict]:
        """Rule-based recommendation candidates derived from the weak area."""
        base: list[dict] = []
        if self.kind == "attendance":
            base.append(
                {
                    "recommendation_type": RecommendationType.ATTENDANCE,
                    "title": f"Attend upcoming sessions for {self.label}",
                    "description": (
                        f"Attendance in {self.label} is below the level associated with comfortable "
                        "performance. Aim to attend upcoming classes consistently."
                    ),
                    "reason": self.reason,
                    "suggested_resource_type": None,
                }
            )
            return base
        if self.kind == "behaviour":
            base.append(
                {
                    "recommendation_type": RecommendationType.TIME_MANAGEMENT,
                    "title": f"Build a steadier study routine for {self.label}",
                    "description": (
                        "Short, regular study sessions tend to help more than long infrequent ones. "
                        "Try scheduling focused practice time each week."
                    ),
                    "reason": self.reason,
                    "suggested_resource_type": ResourceType.PRACTICE,
                }
            )
            return base

        if self.suggested_resource_type in (ResourceType.QUIZ, ResourceType.ASSIGNMENT, None):
            base.append(
                {
                    "recommendation_type": RecommendationType.ASSESSMENT,
                    "title": f"Complete pending {self.label} assessments",
                    "description": f"Recent {self.label} results are below your historical average. Completing outstanding assessments can lift your standing.",
                    "reason": self.reason,
                    "suggested_resource_type": ResourceType.ASSIGNMENT,
                }
            )
        base.append(
            {
                "recommendation_type": RecommendationType.REVISION,
                "title": f"Review {self.label} fundamentals",
                "description": f"Revise the core ideas behind {self.label} — the model identified this as a relative weak spot.",
                "reason": self.reason,
                "suggested_resource_type": ResourceType.VIDEO,
            }
        )
        base.append(
            {
                "recommendation_type": RecommendationType.PRACTICE,
                "title": f"Practice {self.label} questions",
                "description": f"Work through a {self.label} practice set to build confidence.",
                "reason": self.reason,
                "suggested_resource_type": ResourceType.PRACTICE,
            }
        )
        return base


# ----------------------------------------------------------------- weak areas (§24)
def detect_weak_areas(db: Session, student, prediction, explanations: list[dict] | None = None) -> list[WeakArea]:
    areas: list[WeakArea] = []
    risk_probability = float(prediction.risk_probability)

    assessments = db.query(Assessment).filter(Assessment.student_id == student.id).all()
    course_ids = {a.course_id for a in assessments}
    courses = {c.id: c for c in db.query(Course).filter(Course.id.in_(course_ids)).all()} if course_ids else {}

    # 1) weak course: lowest in-progress average
    by_course: dict[uuid.UUID, list[float]] = {}
    for a in assessments:
        if a.assessment_type.value != "ENDTERM":
            by_course.setdefault(a.course_id, []).append(a.score / a.maximum_score * 100.0)
    if by_course:
        averages = {cid: sum(v) / len(v) for cid, v in by_course.items()}
        worst_cid = min(averages, key=averages.get)
        course = courses.get(worst_cid)
        if course and averages[worst_cid] < 65:
            areas.append(
                WeakArea(
                    kind="course",
                    label=course.course_name,
                    severity=max(0.0, min(1.0, (65 - averages[worst_cid]) / 40.0)),
                    reason="Recent assessment performance below the historical average.",
                    course_id=str(course.id),
                    suggested_resource_type=ResourceType.VIDEO,
                )
            )

    # 2) weak assessment type within the weakest course
    if by_course:
        worst_cid = min(by_course, key=lambda c: sum(by_course[c]) / len(by_course[c]))
        by_type: dict[str, list[float]] = {}
        for a in assessments:
            if a.course_id == worst_cid and a.assessment_type.value != "ENDTERM":
                by_type.setdefault(a.assessment_type.value, []).append(a.score / a.maximum_score * 100.0)
        if len(by_type) >= 2:
            worst_type = min(by_type, key=lambda t: sum(by_type[t]) / len(by_type[t]))
            course = courses.get(worst_cid)
            areas.append(
                WeakArea(
                    kind="assessment_type",
                    label=f"{course.course_name} {worst_type.lower()}s" if course else worst_type.lower() + "s",
                    severity=max(0.0, min(1.0, (65 - sum(by_type[worst_type]) / len(by_type[worst_type])) / 40.0)),
                    reason="This assessment type is the weakest within the course.",
                    course_id=str(worst_cid),
                    suggested_resource_type=ResourceType.PRACTICE,
                )
            )

    # 3) attendance weakness
    from app.models import Attendance

    att = db.query(Attendance).filter(Attendance.student_id == student.id).order_by(Attendance.date.desc()).limit(50).all()
    if att:
        conducted = sum(a.classes_conducted for a in att)
        attended = sum(a.classes_attended for a in att)
        if conducted > 0:
            pct = attended / conducted * 100.0
            if pct < 80:
                label = courses[att[0].course_id].course_code if att[0].course_id in courses else "your courses"
                areas.append(
                    WeakArea(
                        kind="attendance",
                        label=label,
                        severity=min(1.0, (80 - pct) / 50.0),
                        reason=f"Overall attendance is {pct:.0f}%.",
                        course_id=str(att[0].course_id) if att[0].course_id in courses else None,
                    )
                )

    # 4) behaviour weakness (lowest engagement sub-signal from the latest activities)
    acts = (
        db.query(LearningActivity)
        .filter(LearningActivity.student_id == student.id)
        .order_by(LearningActivity.activity_date.desc())
        .limit(40)
        .all()
    )
    if acts:
        watched = sum(a.videos_watched for a in acts)
        completed = sum(a.videos_completed for a in acts)
        submitted = sum(a.assignments_submitted for a in acts)
        late = sum(a.late_submissions for a in acts)
        practice = sum(a.practice_questions_attempted for a in acts)
        if watched >= 10 and completed / max(1, watched) < 0.6:
            areas.append(
                WeakArea(
                    kind="behaviour",
                    label="video learning",
                    severity=1.0 - completed / max(1, watched),
                    reason="Video completion rate is low.",
                    suggested_resource_type=ResourceType.VIDEO,
                )
            )
        if practice < 40:
            areas.append(
                WeakArea(
                    kind="behaviour",
                    label="practice questions",
                    severity=0.5,
                    reason="Few practice questions attempted recently.",
                    suggested_resource_type=ResourceType.PRACTICE,
                )
            )
        if submitted >= 5 and late / max(1, submitted) > 0.3:
            areas.append(
                WeakArea(
                    kind="behaviour",
                    label="assignment timeliness",
                    severity=late / max(1, submitted),
                    reason="Many recent submissions were late.",
                    suggested_resource_type=ResourceType.ASSIGNMENT,
                )
            )

    # incorporate explanation factors as severity modifiers when available
    if explanations:
        negative_features = {f.get("feature") for f in explanations if f.get("direction") == "negative"}
        for area in areas:
            if area.kind == "attendance" and "attendance_percentage" in negative_features:
                area.severity = min(1.0, area.severity + 0.15)
            if area.kind == "behaviour" and any(x in negative_features for x in ("engagement_score", "video_completion_rate")):
                area.severity = min(1.0, area.severity + 0.1)

    return areas


# ----------------------------------------------------------------- resources (§27)
def match_resource(db: Session, area: WeakArea) -> LearningResource | None:
    query = db.query(LearningResource)
    if area.course_id:
        query = query.filter(LearningResource.course_id == uuid.UUID(area.course_id))
    if area.suggested_resource_type:
        matched = query.filter(LearningResource.resource_type == area.suggested_resource_type.value).first()
        if matched:
            return matched
    return query.first()


# ----------------------------------------------------------------- ranking (§26)
def rank_candidate(candidate: dict, area: WeakArea, risk_probability: float, resource: LearningResource | None) -> float:
    w = RANKING_WEIGHTS
    recent_decline = 1.0 if "below" in area.reason or "decline" in area.reason else 0.4
    resource_relevance = 0.8 if resource is not None else 0.2
    difficulty_fit = 0.6
    if resource is not None:
        try:
            difficulty_fit = 1.0 - abs(DIFFICULTY_ORDER.index(resource.difficulty) - 1) / 2.0
        except ValueError:
            difficulty_fit = 0.5
    score = (
        w["risk"] * min(1.0, risk_probability / 0.9)
        + w["severity"] * area.severity
        + w["recent_decline"] * recent_decline
        + w["resource_relevance"] * resource_relevance
        + w["difficulty_fit"] * difficulty_fit
        + w["feedback"] * 0.5  # neutral until feedback exists
    )
    return round(score, 4)


# ----------------------------------------------------------------- generation (§25)
def generate_for_prediction(db: Session, student, prediction, explanations: list[dict] | None = None) -> int:
    """Generate + persist ranked recommendations for one prediction. Returns count."""
    risk_probability = float(prediction.risk_probability)
    existing = (
        db.query(Recommendation.id)
        .filter(Recommendation.prediction_id == prediction.id)
        .count()
    )
    if existing:
        return 0

    areas = detect_weak_areas(db, student, prediction, explanations)
    candidates: list[tuple[float, dict, WeakArea, LearningResource | None]] = []
    for area in areas:
        for cand in area.candidates():
            resource = match_resource(db, area)
            score = rank_candidate(cand, area, risk_probability, resource)
            candidates.append((score, cand, area, resource))

    candidates.sort(key=lambda t: t[0], reverse=True)

    # light-touch behaviour for genuinely low-risk students
    limit = MAX_RECOMMENDATIONS if risk_probability >= LOW_RISK_PROBABILITY else 2

    priority_map = lambda score: max(1, min(5, int(round(6 - score * 5))))
    created = 0
    for score, cand, area, resource in candidates[:limit]:
        db.add(
            Recommendation(
                student_id=student.id,
                course_id=uuid.UUID(area.course_id) if area.course_id else None,
                prediction_id=prediction.id,
                recommendation_type=cand["recommendation_type"].value,
                title=cand["title"],
                description=cand["description"],
                reason=cand["reason"],
                priority=priority_map(score),
                confidence=round(min(1.0, 0.4 + area.severity * 0.6), 3),
                score=score,
                status="PENDING",
                resource_id=resource.id if resource else None,
            )
        )
        created += 1
    db.commit()
    return created


def latest_explanations(db: Session, prediction_id) -> list[dict]:
    from app.models import PredictionExplanation

    rows = db.query(PredictionExplanation).filter(PredictionExplanation.prediction_id == prediction_id).all()
    return [{"feature": r.feature, "direction": r.direction, "importance": r.importance} for r in rows]
