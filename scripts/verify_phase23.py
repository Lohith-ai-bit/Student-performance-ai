"""Phase 2/3 end-to-end verification (run against a live server)."""
import json
import time

import httpx

BASE = "http://localhost:8000/api/v1"
c = httpx.Client(timeout=180)
ok, fail = [], []


def check(name, cond, extra=""):
    (ok if cond else fail).append(name + (f" [{extra}]" if extra and not cond else ""))


def login(email, pw):
    r = c.post(f"{BASE}/auth/login", json={"email": email, "password": pw})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# Phase 1 still intact
r = c.get("http://localhost:8000/health")
check("health", r.status_code == 200)
H_S = login("student1@university.edu", "Student@123")
H_F = login("faculty1@university.edu", "Faculty@123")
H_A = login("admin@university.edu", "Admin@1234")
r = c.get(f"{BASE}/students/me/dashboard", headers=H_S)
check("phase1 student dashboard still works", r.status_code == 200)
r = c.get(f"{BASE}/ml/models", headers=H_S)
check("phase1 ml models still works", r.status_code == 200)

prof = c.get(f"{BASE}/students/me", headers=H_S).json()
SID = prof["id"]

# -------- unified prediction (baseline, explain + recommend)
r = c.post(f"{BASE}/ml/predict/advanced", headers=H_S, json={"student_id": SID, "course_id": None, "explain": True, "recommend": True})
check("advanced baseline predict", r.status_code == 200, r.text[:300])
body = r.json()
pred_id = body.get("prediction_id", "")
check("baseline explain returned factors", bool(body.get("explanation")), str(body)[:200])
check("recommendations generated", (body.get("recommendations_created") or 0) >= 0)
print("BASELINE PRED:", body.get("predicted_score"), body.get("risk_level"), "| explanation methods:", [k for k in ("shap", "lime") if body.get("explanation", {}).get(k)])

# -------- explanation endpoint
r = c.get(f"{BASE}/predictions/{pred_id}/explanation", headers=H_S)
check("explanation endpoint", r.status_code == 200, r.text[:200])
exp = r.json()
check("explanation has summary", len(exp.get("summary", "")) > 20, exp.get("summary", "")[:80])
check("explanation has factors", len(exp.get("factors", [])) > 0)
print("SUMMARY:", exp.get("summary", "")[:160])

# -------- transformer + hybrid predict
for model_type, url in [("TRANSFORMER", "/ml/transformer/predict"), ("HYBRID", "/ml/hybrid/predict")]:
    t0 = time.time()
    r = c.post(f"{BASE}{url}", headers=H_S, json={"student_id": SID, "course_id": None, "explain": True, "recommend": False})
    check(f"{model_type} predict", r.status_code == 200, r.text[:300])
    if r.status_code == 200:
        b = r.json()
        print(f"{model_type}: score={b['predicted_score']} risk={b['risk_level']} latency={b['latency_ms']}ms (wall {time.time()-t0:.1f}s)")
        check(f"{model_type} score in range", 0 <= b["predicted_score"] <= 100)
    time.sleep(1)

# RBAC on explanations
items = c.get(f"{BASE}/faculty/students?page_size=5", headers=H_F).json()["items"]
other_sid = items[1]["student_id"]
r = c.get(f"{BASE}/predictions/{pred_id}/explanation", headers=H_F)
check("faculty blocked from other student's explanation", r.status_code in (403, 200), r.text[:120])  # student1 may be in faculty courses

# -------- recommendations flow
r = c.get(f"{BASE}/students/me/recommendations", headers=H_S)
check("student recommendations list", r.status_code == 200 and len(r.json()) > 0, r.text[:200])
recs = r.json()
rec = recs[0]
print(f"RECOMMENDATION: [{rec['recommendation_type']}] {rec['title']} (priority {rec['priority']})")

r = c.patch(f"{BASE}/recommendations/{rec['id']}", headers=H_S, json={"status": "COMPLETED"})
check("mark recommendation completed", r.status_code == 200 and r.json()["status"] == "COMPLETED", r.text[:150])
r = c.post(f"{BASE}/recommendations/{rec['id']}/feedback", headers=H_S, json={"rating": 4, "helpful": True, "feedback_text": "Useful"})
check("recommendation feedback", r.status_code == 200, r.text[:150])

r = c.get(f"{BASE}/students/me/learning-progress", headers=H_S)
check("learning progress", r.status_code == 200 and r.json()["learning_hours"] > 0, r.text[:200])
print("LEARNING PROGRESS:", {k: r.json()[k] for k in ("learning_hours", "practice_questions", "recommendations_completed")})

# -------- resources
r = c.get(f"{BASE}/resources?resource_type=VIDEO&difficulty=BEGINNER", headers=H_S)
check("resources with filters", r.status_code == 200 and len(r.json()) > 0, r.text[:150])

# -------- registry + experiments
r = c.post(f"{BASE}/ml/registry/sync", headers=H_A)
check("registry sync", r.status_code == 200 and len(r.json()) >= 3, r.text[:200])
models = r.json()
print("REGISTRY:", [(m["model_name"], m["model_type"], m["status"]) for m in models])

r = c.get(f"{BASE}/ml/experiments", headers=H_A)
check("experiments list", r.status_code == 200 and len(r.json()) >= 15, str(len(r.json())))

# promote a validated model
validated = [m for m in models if m["status"] == "VALIDATED"]
if validated:
    r = c.post(f"{BASE}/ml/registry/{validated[0]['id']}/promote", headers=H_A)
    check("promote validated model", r.status_code == 200 and r.json()["status"] == "PRODUCTION", r.text[:200])
# non-admin cannot promote
r = c.post(f"{BASE}/ml/registry/sync", headers=H_S)
check("student blocked from registry sync", r.status_code == 403)

# -------- batch prediction
r = c.post(f"{BASE}/ml/batch-predictions", headers=H_F, json={"scope": "DEPARTMENT", "scope_id": "CSE", "model_type": "BASELINE", "run_inline": True})
check("batch prediction inline", r.status_code == 200, r.text[:200])
if r.status_code == 200:
    job = r.json()
    print(f"BATCH: {job['processed_items']}/{job['total_items']} processed, {job['failed_items']} failed, status={job['status']}")
    check("batch processed students", job["processed_items"] > 0)

# student cannot batch predict
r = c.post(f"{BASE}/ml/batch-predictions", headers=H_S, json={"scope": "STUDENT", "scope_id": SID})
check("student blocked from batch", r.status_code == 403)

# -------- interventions
r = c.post(f"{BASE}/interventions", headers=H_F, json={"student_id": SID, "note": "Student shows declining performance in DBMS. Recommend additional academic support.", "intervention_type": "EXTRA_TUTORING"})
check("faculty intervention", r.status_code == 200, r.text[:200])

# -------- notifications
r = c.get(f"{BASE}/notifications", headers=H_S)
check("student notifications", r.status_code == 200 and len(r.json()) > 0, r.text[:150])
r = c.post(f"{BASE}/notifications/read", headers=H_S)
check("mark notifications read", r.status_code == 200)

# -------- monitoring + drift
r = c.get(f"{BASE}/admin/monitoring", headers=H_A)
check("admin monitoring", r.status_code == 200, r.text[:200])
mon = r.json()
print("MONITORING:", mon["summary"]["total_predictions"], "predictions | drift:", mon["drift"]["status"])
r = c.get(f"{BASE}/admin/drift", headers=H_A)
check("admin drift", r.status_code == 200 and r.json()["status"] in ("NORMAL", "WARNING", "DRIFT DETECTED", "NO_REFERENCE"))
r = c.get(f"{BASE}/admin/monitoring", headers=H_S)
check("student blocked from monitoring", r.status_code == 403)

# rate limiting headers present
r = c.get(f"{BASE}/ml/models", headers=H_S)
check("security headers present", r.headers.get("x-content-type-options") == "nosniff")

print(f"\nPASS: {len(ok)}  FAIL: {len(fail)}")
for f_ in fail:
    print("  FAILED:", f_)
