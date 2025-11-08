import pytest
from fastapi.testclient import TestClient
from numpy.ma.testutils import assert_equal


class TestGetActivityEventsEndpoint:
    def test_events_endpoint_exists(self, client: TestClient):
        response = client.get("/api/activity/events")
        assert response.status_code in [200, 500, 503]

    def test_events_success(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "count" in data
        assert isinstance(data["events"], list)
        assert isinstance(data["count"], int)

    def test_events_no_activity_manager(self, client_no_activity: TestClient):
        response = client_no_activity.get("/api/activity/events")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert_equal(data["detail"], "Activity manager not available")

    def test_events_default_limit(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/events")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0

    @pytest.mark.parametrize(
        "limit",
        [1, 10, 50, 100, 200],
    )
    def test_events_various_limits(self, client_with_activity: TestClient, limit: int):
        response = client_with_activity.get(f"/api/activity/events?limit={limit}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["events"], list)

    def test_events_limit_enforcement(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/events?limit=500")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data

    def test_events_response_structure(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "count" in data
        assert isinstance(data["events"], list)
        assert isinstance(data["count"], int)
        assert data["count"] == len(data["events"])

    @pytest.mark.parametrize(
        "limit",
        [0, -1, -10],
    )
    def test_events_zero_or_negative_limit(
        self, client_with_activity: TestClient, limit: int
    ):
        response = client_with_activity.get(f"/api/activity/events?limit={limit}")
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_events_string_limit(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/events?limit=abc")
        assert response.status_code == 422

    def test_events_float_limit(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/events?limit=10.5")
        assert response.status_code == 422


class TestGetActivityCountEndpoint:
    def test_count_endpoint_exists(self, client: TestClient):
        response = client.get("/api/activity/count")
        assert response.status_code in [200, 500, 503]

    def test_count_success(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/count")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "max_events" in data
        assert isinstance(data["count"], int)
        assert isinstance(data["max_events"], int)

    def test_count_no_activity_manager(self, client_no_activity: TestClient):
        response = client_no_activity.get("/api/activity/count")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert_equal(data["detail"], "Activity manager not available")

    def test_count_response_structure(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/count")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert "max_events" in data
        assert data["count"] >= 0
        assert data["max_events"] == 50

    def test_count_returns_zero_when_empty(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/count")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0

    def test_count_max_events_constant(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/count")
        assert response.status_code == 200
        data = response.json()
        assert data["max_events"] == 50


class TestClearActivityEventsEndpoint:
    def test_clear_endpoint_exists(self, client: TestClient):
        response = client.delete("/api/activity/events")
        assert response.status_code in [200, 500, 503]

    def test_clear_success(self, client_with_activity: TestClient):
        response = client_with_activity.delete("/api/activity/events")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "events_cleared" in data
        assert isinstance(data["events_cleared"], int)

    def test_clear_no_activity_manager(self, client_no_activity: TestClient):
        response = client_no_activity.delete("/api/activity/events")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert_equal(data["detail"], "Activity manager not available")

    def test_clear_response_structure(self, client_with_activity: TestClient):
        response = client_with_activity.delete("/api/activity/events")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "events_cleared" in data
        assert isinstance(data["message"], str)
        assert isinstance(data["events_cleared"], int)
        assert data["events_cleared"] >= 0

    def test_clear_returns_zero_when_empty(self, client_with_activity: TestClient):
        response = client_with_activity.delete("/api/activity/events")
        assert response.status_code == 200
        data = response.json()
        assert data["events_cleared"] == 0

    def test_clear_message_content(self, client_with_activity: TestClient):
        response = client_with_activity.delete("/api/activity/events")
        assert response.status_code == 200
        data = response.json()
        assert "cleared" in data["message"].lower()

    def test_clear_is_delete_method(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/events")
        assert response.status_code == 200

        response = client_with_activity.post("/api/activity/events")
        assert response.status_code == 405

        response = client_with_activity.put("/api/activity/events")
        assert response.status_code == 405

        response = client_with_activity.delete("/api/activity/events")
        assert response.status_code == 200


class TestActivityEndpointsIntegration:
    def test_count_and_events_consistency(self, client_with_activity: TestClient):
        count_response = client_with_activity.get("/api/activity/count")
        events_response = client_with_activity.get("/api/activity/events")

        assert count_response.status_code == 200
        assert events_response.status_code == 200

        count_data = count_response.json()
        events_data = events_response.json()

        assert count_data["count"] == events_data["count"]
        assert count_data["count"] == len(events_data["events"])

    def test_clear_then_count(self, client_with_activity: TestClient):
        clear_response = client_with_activity.delete("/api/activity/events")
        assert clear_response.status_code == 200

        count_response = client_with_activity.get("/api/activity/count")
        assert count_response.status_code == 200
        count_data = count_response.json()
        assert count_data["count"] == 0

    def test_all_endpoints_require_activity_manager(
        self, client_no_activity: TestClient
    ):
        endpoints = [
            ("GET", "/api/activity/events"),
            ("GET", "/api/activity/count"),
            ("DELETE", "/api/activity/events"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = client_no_activity.get(endpoint)
            elif method == "DELETE":
                response = client_no_activity.delete(endpoint)

            assert response.status_code == 503
            data = response.json()
            assert "detail" in data

    def test_error_response_consistency(self, client_no_activity: TestClient):
        endpoints = [
            "/api/activity/events",
            "/api/activity/count",
        ]

        for endpoint in endpoints:
            response = client_no_activity.get(endpoint)
            data = response.json()

            assert "detail" in data
            assert isinstance(data["detail"], str)


class TestActivityEndpointsEdgeCases:
    def test_events_with_very_large_limit(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/events?limit=999999")
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_events_with_multiple_params(self, client_with_activity: TestClient):
        response = client_with_activity.get(
            "/api/activity/events?limit=50&extra_param=value"
        )
        assert response.status_code == 200

    def test_count_with_query_params(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/count?unused=param")
        assert response.status_code == 200

    def test_clear_with_query_params(self, client_with_activity: TestClient):
        response = client_with_activity.delete("/api/activity/events?unused=param")
        assert response.status_code == 200

    def test_endpoints_with_trailing_slash(self, client_with_activity: TestClient):
        response = client_with_activity.get("/api/activity/events/")
        assert response.status_code in [200, 404, 307]

        response = client_with_activity.get("/api/activity/count/")
        assert response.status_code in [200, 404, 307]
