"""
Tests for the Mergington High School API
"""

import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


class TestActivitiesEndpoint:
    """Tests for /activities endpoint"""

    def test_get_activities_returns_200(self):
        """Test that GET /activities returns 200 status"""
        response = client.get("/activities")
        assert response.status_code == 200

    def test_get_activities_returns_dict(self):
        """Test that GET /activities returns a dictionary of activities"""
        response = client.get("/activities")
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_activity_has_required_fields(self):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_chess_club_exists(self):
        """Test that Chess Club activity exists"""
        response = client.get("/activities")
        activities = response.json()
        assert "Chess Club" in activities


class TestSignupEndpoint:
    """Tests for /activities/{activity_name}/signup endpoint"""

    def test_signup_returns_200(self):
        """Test successful signup returns 200"""
        response = client.post(
            "/activities/Basketball Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        assert "message" in response.json()

    def test_signup_adds_participant(self):
        """Test that signup adds participant to activity"""
        # First, get initial participant count
        response_before = client.get("/activities")
        basketball_before = response_before.json()["Basketball Club"]
        initial_count = len(basketball_before["participants"])
        
        # Sign up new participant
        email = "test_new_participant@mergington.edu"
        client.post(f"/activities/Basketball Club/signup?email={email}")
        
        # Check participant was added
        response_after = client.get("/activities")
        basketball_after = response_after.json()["Basketball Club"]
        assert len(basketball_after["participants"]) == initial_count + 1
        assert email in basketball_after["participants"]

    def test_signup_duplicate_email_returns_400(self):
        """Test that duplicate signup returns 400 error"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"].lower()

    def test_signup_nonexistent_activity_returns_404(self):
        """Test that signup for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_signup_message_format(self):
        """Test that signup returns properly formatted message"""
        response = client.post(
            "/activities/Art Club/signup?email=testsignup@mergington.edu"
        )
        data = response.json()
        assert "Signed up" in data["message"]
        assert "testsignup@mergington.edu" in data["message"]


class TestUnregisterEndpoint:
    """Tests for /activities/{activity_name}/unregister endpoint"""

    def test_unregister_returns_200(self):
        """Test successful unregister returns 200"""
        response = client.post(
            "/activities/Chess Club/unregister?email=michael@mergington.edu"
        )
        assert response.status_code == 200
        assert "message" in response.json()

    def test_unregister_removes_participant(self):
        """Test that unregister removes participant from activity"""
        # First, get initial participant count
        response_before = client.get("/activities")
        soccer_before = response_before.json()["Soccer Team"]
        initial_count = len(soccer_before["participants"])
        email = soccer_before["participants"][0]
        
        # Unregister participant
        client.post(f"/activities/Soccer Team/unregister?email={email}")
        
        # Check participant was removed
        response_after = client.get("/activities")
        soccer_after = response_after.json()["Soccer Team"]
        assert len(soccer_after["participants"]) == initial_count - 1
        assert email not in soccer_after["participants"]

    def test_unregister_not_registered_returns_400(self):
        """Test that unregistering when not registered returns 400"""
        response = client.post(
            "/activities/Drama Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"].lower()

    def test_unregister_nonexistent_activity_returns_404(self):
        """Test that unregister for non-existent activity returns 404"""
        response = client.post(
            "/activities/Nonexistent Activity/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_unregister_message_format(self):
        """Test that unregister returns properly formatted message"""
        response = client.post(
            "/activities/Drama Club/unregister?email=lucas@mergington.edu"
        )
        data = response.json()
        assert "Unregistered" in data["message"]
        assert "lucas@mergington.edu" in data["message"]


class TestRootEndpoint:
    """Tests for root endpoint"""

    def test_root_redirects_to_static(self):
        """Test that root endpoint redirects to /static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert "/static/index.html" in response.headers["location"]


class TestActivityState:
    """Tests for maintaining consistent activity state"""

    def test_signup_affects_availability(self):
        """Test that signup reduces available spots"""
        response_before = client.get("/activities")
        max_participants = response_before.json()["Art Club"]["max_participants"]
        participants_before = len(
            response_before.json()["Art Club"]["participants"]
        )
        
        # Sign up
        client.post("/activities/Art Club/signup?email=spottest@mergington.edu")
        
        # Check updated count
        response_after = client.get("/activities")
        participants_after = len(
            response_after.json()["Art Club"]["participants"]
        )
        assert participants_after == participants_before + 1

    def test_unregister_frees_spot(self):
        """Test that unregister increases available spots"""
        # Get a participant to remove
        response = client.get("/activities")
        drama_participants = response.json()["Drama Club"]["participants"]
        participant_to_remove = drama_participants[-1]
        
        participants_before = len(drama_participants)
        
        # Unregister
        client.post(
            f"/activities/Drama Club/unregister?email={participant_to_remove}"
        )
        
        # Check updated count
        response_after = client.get("/activities")
        participants_after = len(
            response_after.json()["Drama Club"]["participants"]
        )
        assert participants_after == participants_before - 1
