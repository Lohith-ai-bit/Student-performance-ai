"""Phase 2/3 seed extension: learning sessions + learning resources.

Adds temporal-session telemetry (derived from existing learning activities) and
a resource catalogue per course. Never touches or deletes Phase 1 data.

Run from backend/:
    python -m app.seed_phase23
"""
import random
from datetime import date, time, timedelta

from app.core.database import SessionLocal
from app.models import Course, LearningActivity, LearningSession, LearningResource
from app.models.advanced_enums import ResourceType, SessionActivityType

random.seed(1337)

SYNTHETIC_NOTICE = "SYNTHETIC SEED DATA"

# topic templates per course: [topic, difficulty] pairs
def _topics_for(course_code: str, course_name: str) -> list[tuple[str, str]]:
    base = course_name.split("(")[0].strip()
    return [
        (f"{base} Fundamentals", "BEGINNER"),
        (f"{base} Core Concepts", "BEGINNER"),
        (f"{base} Problem Solving", "INTERMEDIATE"),
        (f"{base} Advanced Topics", "ADVANCED"),
        (f"{base} Revision", "BEGINNER"),
        (f"{base} Practice Set", "INTERMEDIATE"),
    ]


RESOURCE_TEMPLATES = [
    (ResourceType.VIDEO, "{topic} — Video Lecture", 35),
    (ResourceType.VIDEO, "{topic} — Worked Examples", 28),
    (ResourceType.DOCUMENT, "{topic} — Quick Notes", 20),
    (ResourceType.ARTICLE, "{topic} — Deep Dive Article", 25),
    (ResourceType.PRACTICE, "{topic} — Practice Question Set", 40),
    (ResourceType.QUIZ, "{topic} — Self-Assessment Quiz", 15),
    (ResourceType.ASSIGNMENT, "{topic} — Guided Assignment", 60),
]


def seed_sessions() -> int:
    """Derive 1-2 learning sessions per activity row (deterministic mapping)."""
    created = 0
    with SessionLocal() as db:
        existing = db.query(LearningSession.id).count()
        if existing > 0:
            print(f"learning_sessions already populated ({existing} rows). Skipping.")
            return 0

        activities = db.query(LearningActivity).all()
        for act in activities:
            intensity = min(1.0, act.session_duration / 75.0) if act.session_duration else 0.4
            n_sessions = 2 if act.session_duration >= 60 else 1
            remaining = act.session_duration
            for i in range(n_sessions):
                duration = max(10, int(remaining / (n_sessions - i)))
                remaining -= duration
                hour = 9 + (i * 5 + hash(str(act.id)) % 6) % 12
                start = time(hour, 15)
                end = time(hour, (15 + duration) % 60)
                # pick activity type from the day's telemetry
                if act.videos_watched and i == 0:
                    a_type = SessionActivityType.VIDEO
                elif act.quiz_attempts and i == 1:
                    a_type = SessionActivityType.QUIZ
                elif act.practice_questions_attempted:
                    a_type = SessionActivityType.PRACTICE
                elif act.documents_opened:
                    a_type = SessionActivityType.DOCUMENT
                elif act.assignments_submitted:
                    a_type = SessionActivityType.ASSIGNMENT
                else:
                    a_type = SessionActivityType.OTHER
                db.add(
                    LearningSession(
                        student_id=act.student_id,
                        course_id=act.course_id,
                        session_date=act.activity_date,
                        start_time=start,
                        end_time=end,
                        duration_minutes=duration,
                        activity_type=a_type,
                    )
                )
                created += 1
                if created % 2000 == 0:
                    db.commit()
        db.commit()
    return created


def seed_resources() -> int:
    created = 0
    with SessionLocal() as db:
        existing = db.query(LearningResource.id).count()
        if existing > 0:
            print(f"learning_resources already populated ({existing} rows). Skipping.")
            return 0

        courses = db.query(Course).all()
        for course in courses:
            topics = _topics_for(course.course_code, course.course_name)
            for topic, difficulty in topics:
                for r_type, title_tpl, minutes in RESOURCE_TEMPLATES[: random.choice([5, 6, 7])]:
                    db.add(
                        LearningResource(
                            course_id=course.id,
                            title=title_tpl.format(topic=topic),
                            description=f"[{SYNTHETIC_NOTICE}] Self-study material for {topic}.",
                            resource_type=r_type,
                            topic=topic,
                            difficulty=difficulty,
                            url=f"https://resources.university.example/{course.course_code.lower()}/{topic.lower().replace(' ', '-')}-{r_type.value.lower()}",
                            estimated_minutes=minutes,
                        )
                    )
                    created += 1
        db.commit()
    return created


if __name__ == "__main__":
    n_sessions = seed_sessions()
    n_resources = seed_resources()
    print(f"[{SYNTHETIC_NOTICE}] Phase 2/3 seed complete: {n_sessions} sessions, {n_resources} resources")
