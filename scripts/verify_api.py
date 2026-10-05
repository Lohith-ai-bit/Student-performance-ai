"""Phase 1 end-to-end API verification (run against a live uvicorn server)."""
import json

import httpx

BASE = "http://localhost:8000/api/v1"
c = httpx.Client(timeout=60)
ok, fail = [], []


def check(name, cond, extra=""):
    (ok if cond else fail).append(name + (f" [{extra}]" if extra and not cond else ""))


r = c.get("http://localhost:8000/health")
check("health", r.status_code == 200)

# register a new student
r = c.post(
    f"{BASE}/auth/register",
    json={
        "name": "Test Runner", "email": "testrunner@university.edu", "password": "Testpass1",
        "roll_number": "T999", "department": "CSE", "branch": "Computer Science and Engineering",
        "year": 2, "semester": 3, "section": "A",
    },
)
if r.status_code == 201:
    new_tok = r.json().get("access_token", "")
else:
    # idempotent re-runs: the account already exists, log in instead
    r = c.post(f"{BASE}/auth/login", json={"email": "testrunner@university.edu", "password": "Testpass1"})
    new_tok = r.json().get("access_token", "")
check("register student (or existing account)", r.status_code == 201 or bool(new_tok))

r = c.post(
    f"{BASE}/auth/register",
    json={
        "name": "Test Runner", "email": "testrunner@university.edu", "password": "Testpass1",
        "roll_number": "T998", "department": "CSE", "branch": "X", "year": 2, "semester": 3, "section": "A",
    },
)
check("duplicate email rejected (409)", r.status_code == 409, r.text[:120])

tokens = {}
for role, email, pw in [
    ("admin", "admin@university.edu", "Admin@1234"),
    ("faculty", "faculty1@university.edu", "Faculty@123"),
    ("student", "student1@university.edu", "Student@123"),
]:
    r = c.post(f"{BASE}/auth/login", json={"email": email, "password": pw})
    check(f"login {role}", r.status_code == 200, r.text[:150])
    tokens[role] = r.json()["access_token"]

r = c.post(f"{BASE}/auth/login", json={"email": "student1@university.edu", "password": "wrong"})
check("invalid password 401", r.status_code == 401)
r = c.get(f"{BASE}/students/me/dashboard")
check("no token 401", r.status_code == 401)

H_A = {"Authorization": f"Bearer {tokens['admin']}"}
H_F = {"Authorization": f"Bearer {tokens['faculty']}"}
H_S = {"Authorization": f"Bearer {tokens['student']}"}
H_N = {"Authorization": f"Bearer {new_tok}"}

r = c.get(f"{BASE}/students/me/dashboard", headers=H_S)
check("student dashboard", r.status_code == 200, r.text[:200])
d = r.json()
check("student has performance rows", len(d["performance"]) > 0)
r = c.get(f"{BASE}/students/me/assessments", headers=H_S)
check("student assessments", r.status_code == 200 and len(r.json()) > 0)
r = c.get(f"{BASE}/students/me/attendance", headers=H_S)
check("student attendance", r.status_code == 200)
r = c.get(f"{BASE}/students/me/activities", headers=H_S)
check("student activities", r.status_code == 200)

r = c.get(f"{BASE}/dashboards/admin", headers=H_S)
check("student blocked from admin dashboard", r.status_code == 403)
r = c.get(f"{BASE}/students", headers=H_S)
check("student blocked from admin students", r.status_code == 403)
r = c.get(f"{BASE}/dashboards/admin", headers=H_F)
check("faculty blocked from admin dashboard", r.status_code == 403)
r = c.get(f"{BASE}/dashboards/admin", headers=H_A)
check("admin dashboard", r.status_code == 200, r.text[:200])
check("admin totals plausible", r.json()["totals"]["students"] >= 120, str(r.json()["totals"]))

r = c.get(f"{BASE}/dashboards/faculty", headers=H_F)
check("faculty dashboard", r.status_code == 200, r.text[:200])
r = c.get(f"{BASE}/faculty/students", headers=H_F)
check("faculty student table", r.status_code == 200 and len(r.json()["items"]) > 0)
r = c.get(f"{BASE}/faculty/students?search=student1", headers=H_F)
check("faculty search", r.status_code == 200)

items = c.get(f"{BASE}/faculty/students?page_size=5", headers=H_F).json()["items"]
sid = items[0]["student_id"]
r = c.get(f"{BASE}/faculty/students/{sid}", headers=H_F)
check("faculty student detail", r.status_code == 200, r.text[:200])
r = c.get(f"{BASE}/faculty/students/{sid}/predict", headers=H_F)
check("faculty generate prediction", r.status_code == 200, r.text[:300])
pred = r.json() if r.status_code == 200 else {}
if pred:
    print("PREDICTION:", json.dumps({k: pred[k] for k in ("predicted_score", "risk_probability", "risk_level", "model_name", "model_version")}))

prof = c.get(f"{BASE}/students/me", headers=H_S).json()
r = c.post(f"{BASE}/ml/predict", json={"student_id": prof["id"], "course_id": None}, headers=H_S)
check("student self predict", r.status_code == 200, r.text[:300])
other_sid = items[1]["student_id"] if len(items) > 1 else sid
r = c.post(f"{BASE}/ml/predict", json={"student_id": other_sid, "course_id": None}, headers=H_S)
check("student blocked predicting others", r.status_code == 403, r.text[:150])

r = c.get(f"{BASE}/ml/models", headers=H_S)
check("ml models", r.status_code == 200 and len(r.json()["models"]) == 2)
r = c.get(f"{BASE}/ml/evaluate", headers=H_S)
check("ml evaluate", r.status_code == 200 and len(r.json()["evaluations"]) >= 8)

r = c.get(f"{BASE}/students/me/predictions/history", headers=H_S)
check("student prediction history", r.status_code == 200)
r = c.get(f"{BASE}/students/me/predictions", headers=H_S)
check("student predictions + disclaimer", r.status_code == 200 and "disclaimer" in r.json())

csv_content = (
    "student_id,course,attendance,quiz_score,assignment_score,midterm_score,date\n"
    "S001,CS301,81,72,88,79,2026-09-20\n"
    "S001,CS301,999,72,88,79,2026-09-21\n"
    "S999,CS301,80,70,70,70,2026-09-22\n"
    "S002,XX999,80,70,70,70,2026-09-22\n"
)
files = {"file": ("import.csv", csv_content, "text/csv")}
r = c.post(f"{BASE}/faculty/imports/csv/preview", headers=H_F, files=files)
check("csv preview", r.status_code == 200, r.text[:200])
rep = r.json()["report"]
check("csv preview reports invalid rows", rep["invalid_rows"] == 3, json.dumps(rep)[:300])
r = c.post(f"{BASE}/faculty/imports/csv/confirm", headers=H_F, files=files)
rep = r.json()["report"]
check(
    "csv confirm processes valid rows",
    rep["invalid_rows"] == 3 and (rep["inserted"] + rep["skipped_duplicates"]) == 4,
    json.dumps(rep)[:300],
)

students_list = c.get(f"{BASE}/faculty/students?page_size=1", headers=H_F).json()["items"]
sid2 = students_list[0]["student_id"]
courses = c.get(f"{BASE}/faculty/me/courses", headers=H_F).json()["items"]
faculty_course_ids = {x["id"] for x in courses}
enr = c.get(f"{BASE}/enrollments?student_id={sid2}", headers=H_A).json()
cid = next(e["course_id"] for e in enr if e["course_id"] in faculty_course_ids)
r = c.post(f"{BASE}/faculty/assessments", headers=H_F, json={
    "student_id": sid2, "course_id": cid, "assessment_type": "QUIZ",
    "score": 85, "maximum_score": 100, "assessment_date": "2026-09-25"})
check("faculty add assessment", r.status_code == 201, r.text[:200])
r = c.post(f"{BASE}/faculty/attendance", headers=H_F, json={
    "student_id": sid2, "course_id": cid, "classes_conducted": 20,
    "classes_attended": 15, "date": "2026-09-25"})
check("faculty add attendance (computed %)", r.status_code == 201 and r.json()["attendance_percentage"] == 75.0, r.text[:200])
r = c.post(f"{BASE}/faculty/attendance", headers=H_F, json={
    "student_id": sid2, "course_id": cid, "classes_conducted": 20,
    "classes_attended": 25, "date": "2026-09-26"})
check("attendance attended>conducted rejected", r.status_code == 422)
r = c.post(f"{BASE}/faculty/activities", headers=H_F, json={
    "student_id": sid2, "course_id": cid, "activity_date": "2026-09-25",
    "session_duration": 45, "videos_watched": 4, "videos_completed": 3,
    "quiz_attempts": 2, "assignments_submitted": 1, "late_submissions": 0,
    "practice_questions_attempted": 15, "login_count": 3})
check("faculty add activity", r.status_code == 201, r.text[:200])

r = c.get(f"{BASE}/students/00000000-0000-0000-0000-000000000000", headers=H_A)
check("error envelope shape", r.status_code == 404 and r.json()["error"]["code"] == "STUDENT_NOT_FOUND", r.text[:200])

prof_n = c.get(f"{BASE}/students/me", headers=H_N).json()
r = c.post(f"{BASE}/ml/predict", json={"student_id": prof_n["id"], "course_id": None}, headers=H_N)
check("empty student predict -> 422 friendly", r.status_code == 422 and "data" in r.json()["error"]["message"].lower(), r.text[:200])

print(f"\nPASS: {len(ok)}  FAIL: {len(fail)}")
for f_ in fail:
    print("  FAILED:", f_)
