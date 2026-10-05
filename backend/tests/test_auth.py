"""Authentication tests (§39): registration, login, invalid password, unauthorized routes."""
from tests.conftest import login


def test_register_new_student(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "New Student", "email": "new@test.edu", "password": "Passw0rd1",
            "roll_number": "S100", "department": "CSE", "branch": "CS",
            "year": 2, "semester": 3, "section": "A",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["role"] == "STUDENT"
    # password is never returned or stored in plain text
    assert "password" not in body["user"]


def test_register_duplicate_email(client, seed_users):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Dup", "email": "student@test.edu", "password": "Passw0rd1",
            "roll_number": "S200", "department": "CSE", "branch": "CS",
            "year": 2, "semester": 3, "section": "A",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_register_weak_password_rejected(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Weak", "email": "weak@test.edu", "password": "abcdefgh",
            "roll_number": "S300", "department": "CSE", "branch": "CS",
            "year": 2, "semester": 3, "section": "A",
        },
    )
    assert response.status_code == 422


def test_login_success_and_me(client, seed_users):
    headers = login(client, "student@test.edu", "Student@123")
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "student@test.edu"


def test_login_invalid_password(client, seed_users):
    response = client.post("/api/v1/auth/login", json={"email": "student@test.edu", "password": "wrong-pass"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_protected_route_without_token(client):
    response = client.get("/api/v1/students/me")
    assert response.status_code == 401


def test_student_cannot_access_admin_routes(client, auth_student):
    response = client.get("/api/v1/dashboards/admin", headers=auth_student)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_faculty_cannot_access_admin_routes(client, auth_faculty):
    response = client.get("/api/v1/dashboards/admin", headers=auth_faculty)
    assert response.status_code == 403


def test_admin_can_access_admin_routes(client, auth_admin):
    response = client.get("/api/v1/dashboards/admin", headers=auth_admin)
    assert response.status_code == 200


def test_passwords_are_hashed_in_db(db_session, seed_users):
    user = seed_users["student_user"]
    assert user.password_hash != "Student@123"
    assert user.password_hash.startswith("$2")  # bcrypt
