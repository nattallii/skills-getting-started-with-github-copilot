from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src.app import activities, app


@pytest.fixture
def client():
    original_activities = deepcopy(activities)
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        activities.clear()
        activities.update(original_activities)


def test_root_redirects_to_frontend(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_activity_details(client):
    response = client.get("/activities")

    assert response.status_code == 200
    assert response.json()["Chess Club"]["participants"] == [
        "michael@mergington.edu",
        "daniel@mergington.edu",
    ]


def test_signup_adds_participant(client):
    response = client.post(
        "/activities/Basketball Team/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Signed up student@example.com for Basketball Team"
    }
    assert "student@example.com" in client.get("/activities").json()["Basketball Team"]["participants"]


def test_signup_rejects_unknown_activity(client):
    response = client.post(
        "/activities/Unknown Activity/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_signup_rejects_duplicate_participant(client):
    endpoint = "/activities/Basketball Team/signup"
    params = {"email": "student@example.com"}

    assert client.post(endpoint, params=params).status_code == 200
    response = client.post(endpoint, params=params)

    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"
    assert client.get("/activities").json()["Basketball Team"]["participants"].count(
        "student@example.com"
    ) == 1


def test_signup_rejects_full_activity_without_mutating_participants(client):
    activity = activities["Basketball Team"]
    activity["participants"] = [
        f"student-{index}@example.com"
        for index in range(activity["max_participants"])
    ]
    participants_before_signup = list(activity["participants"])

    response = client.post(
        "/activities/Basketball Team/signup",
        params={"email": "new-student@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Activity is full"
    assert activity["participants"] == participants_before_signup


def test_unregister_removes_participant(client):
    endpoint = "/activities/Art Club/signup"
    params = {"email": "student@example.com"}
    assert client.post(endpoint, params=params).status_code == 200

    response = client.delete(endpoint, params=params)

    assert response.status_code == 200
    assert response.json() == {
        "message": "Unregistered student@example.com from Art Club"
    }
    assert "student@example.com" not in client.get("/activities").json()["Art Club"]["participants"]


def test_unregister_rejects_unknown_activity(client):
    response = client.delete(
        "/activities/Unknown Activity/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_rejects_nonparticipant(client):
    response = client.delete(
        "/activities/Art Club/signup",
        params={"email": "student@example.com"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"
