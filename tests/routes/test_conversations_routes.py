import pytest
from fastapi.testclient import TestClient


class TestCreateConversationEndpoint:
    def test_create_conversation_endpoint_exists(self, client: TestClient):
        response = client.post("/api/conversations", json={})
        assert response.status_code in [200, 503]

    def test_create_conversation_minimal(self, client: TestClient):
        response = client.post("/api/conversations", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "conversation" in data

    def test_create_conversation_with_title(self, client: TestClient):
        response = client.post("/api/conversations", json={"title": "Test Chat"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_create_conversation_with_model(self, client: TestClient):
        response = client.post(
            "/api/conversations", json={"model": "llama3.2:3b", "title": "Model Test"}
        )
        assert response.status_code == 200

    def test_create_conversation_with_provider(self, client: TestClient):
        response = client.post(
            "/api/conversations",
            json={"provider_id": "my-openai", "title": "Provider Test"},
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "temperature,expected_status",
        [
            (0.0, 200),
            (0.7, 200),
            (2.0, 200),
            (-0.1, 422),
            (2.1, 422),
        ],
    )
    def test_create_conversation_temperature_validation(
        self, client: TestClient, temperature: float, expected_status: int
    ):
        response = client.post(
            "/api/conversations", json={"temperature": temperature}
        )
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "max_tokens,expected_status",
        [
            (1, 200),
            (1000, 200),
            (100000, 200),
            (0, 422),
            (100001, 422),
        ],
    )
    def test_create_conversation_max_tokens_validation(
        self, client: TestClient, max_tokens: int, expected_status: int
    ):
        response = client.post("/api/conversations", json={"max_tokens": max_tokens})
        assert response.status_code == expected_status

    def test_create_conversation_with_context_documents(self, client: TestClient):
        response = client.post(
            "/api/conversations",
            json={"context_documents": ["doc1", "doc2"], "title": "Context Test"},
        )
        assert response.status_code == 200

    def test_create_conversation_with_system_prompt(self, client: TestClient):
        response = client.post(
            "/api/conversations",
            json={"system_prompt": "You are a helpful assistant.", "title": "Prompt Test"},
        )
        assert response.status_code == 200

    def test_create_conversation_no_service(
        self, client_no_conversation_service: TestClient
    ):
        response = client_no_conversation_service.post("/api/conversations", json={})
        assert response.status_code == 503


class TestListConversationsEndpoint:
    def test_list_conversations_endpoint_exists(self, client: TestClient):
        response = client.get("/api/conversations")
        assert response.status_code in [200, 503]

    def test_list_conversations_default(self, client: TestClient):
        response = client.get("/api/conversations")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True

    @pytest.mark.parametrize("limit", [1, 10, 50, 100])
    def test_list_conversations_with_limit(self, client: TestClient, limit: int):
        response = client.get(f"/api/conversations?limit={limit}")
        assert response.status_code == 200

    @pytest.mark.parametrize("offset", [0, 10, 50])
    def test_list_conversations_with_offset(self, client: TestClient, offset: int):
        response = client.get(f"/api/conversations?offset={offset}")
        assert response.status_code == 200

    def test_list_conversations_include_archived(self, client: TestClient):
        response = client.get("/api/conversations?include_archived=true")
        assert response.status_code == 200

    def test_list_conversations_pagination(self, client: TestClient):
        response = client.get("/api/conversations?limit=10&offset=5")
        assert response.status_code == 200

    def test_list_conversations_no_service(
        self, client_no_conversation_service: TestClient
    ):
        response = client_no_conversation_service.get("/api/conversations")
        assert response.status_code == 503


class TestGetConversationEndpoint:
    def test_get_conversation_endpoint_exists(self, client: TestClient):
        response = client.get("/api/conversations/test_conv_id")
        assert response.status_code in [200, 404, 503]

    def test_get_conversation_with_messages(self, client: TestClient):
        response = client.get("/api/conversations/test_conv_id?include_messages=true")
        assert response.status_code in [200, 404, 503]

    def test_get_conversation_without_messages(self, client: TestClient):
        response = client.get("/api/conversations/test_conv_id?include_messages=false")
        assert response.status_code in [200, 404, 503]

    @pytest.mark.parametrize("message_limit", [10, 50, 100])
    def test_get_conversation_message_limit(
        self, client: TestClient, message_limit: int
    ):
        response = client.get(
            f"/api/conversations/test_conv_id?message_limit={message_limit}"
        )
        assert response.status_code in [200, 404, 503]

    @pytest.mark.parametrize(
        "conversation_id",
        [
            "conv123",
            "conversation-with-dashes",
            "conversation_with_underscores",
        ],
    )
    def test_get_conversation_various_id_formats(
        self, client: TestClient, conversation_id: str
    ):
        response = client.get(f"/api/conversations/{conversation_id}")
        assert response.status_code in [200, 404, 503]

    def test_get_conversation_no_service(
        self, client_no_conversation_service: TestClient
    ):
        response = client_no_conversation_service.get("/api/conversations/test_id")
        assert response.status_code == 503


class TestUpdateConversationEndpoint:
    def test_update_conversation_endpoint_exists(self, client: TestClient):
        response = client.patch("/api/conversations/test_conv_id", json={})
        assert response.status_code in [200, 404, 503]

    def test_update_conversation_title(self, client: TestClient):
        response = client.patch(
            "/api/conversations/test_conv_id", json={"title": "Updated Title"}
        )
        assert response.status_code in [200, 404, 503]

    def test_update_conversation_model(self, client: TestClient):
        response = client.patch(
            "/api/conversations/test_conv_id", json={"model": "llama3.2:3b"}
        )
        assert response.status_code in [200, 404, 503]

    def test_update_conversation_provider(self, client: TestClient):
        response = client.patch(
            "/api/conversations/test_conv_id", json={"provider_id": "my-openai"}
        )
        assert response.status_code in [200, 404, 503]

    @pytest.mark.parametrize(
        "temperature,expected_status",
        [
            (0.0, 200),
            (1.0, 200),
            (2.0, 200),
            (-0.1, 422),
            (2.1, 422),
        ],
    )
    def test_update_conversation_temperature_validation(
        self, client: TestClient, temperature: float, expected_status: int
    ):
        response = client.patch(
            "/api/conversations/test_conv_id", json={"temperature": temperature}
        )
        assert response.status_code in [expected_status, 404, 503]

    @pytest.mark.parametrize(
        "max_tokens,expected_status",
        [
            (1, 200),
            (10000, 200),
            (100000, 200),
            (0, 422),
            (100001, 422),
        ],
    )
    def test_update_conversation_max_tokens_validation(
        self, client: TestClient, max_tokens: int, expected_status: int
    ):
        response = client.patch(
            "/api/conversations/test_conv_id", json={"max_tokens": max_tokens}
        )
        assert response.status_code in [expected_status, 404, 503]

    def test_update_conversation_context_documents(self, client: TestClient):
        response = client.patch(
            "/api/conversations/test_conv_id",
            json={"context_documents": ["doc1", "doc2", "doc3"]},
        )
        assert response.status_code in [200, 404, 503]

    def test_update_conversation_system_prompt(self, client: TestClient):
        response = client.patch(
            "/api/conversations/test_conv_id",
            json={"system_prompt": "New system prompt"},
        )
        assert response.status_code in [200, 404, 503]

    def test_update_conversation_multiple_fields(self, client: TestClient):
        response = client.patch(
            "/api/conversations/test_conv_id",
            json={
                "title": "Updated",
                "temperature": 0.8,
                "max_tokens": 3000,
            },
        )
        assert response.status_code in [200, 404, 503]

    def test_update_conversation_no_service(
        self, client_no_conversation_service: TestClient
    ):
        response = client_no_conversation_service.patch(
            "/api/conversations/test_id", json={"title": "Test"}
        )
        assert response.status_code == 503


class TestArchiveConversationEndpoint:
    def test_archive_conversation_endpoint_exists(self, client: TestClient):
        response = client.delete("/api/conversations/test_conv_id")
        assert response.status_code in [200, 404, 503]

    @pytest.mark.parametrize(
        "conversation_id",
        [
            "conv123",
            "conversation-with-dashes",
            "conversation_with_underscores",
        ],
    )
    def test_archive_conversation_various_id_formats(
        self, client: TestClient, conversation_id: str
    ):
        response = client.delete(f"/api/conversations/{conversation_id}")
        assert response.status_code in [200, 404, 503]

    def test_archive_conversation_no_service(
        self, client_no_conversation_service: TestClient
    ):
        response = client_no_conversation_service.delete("/api/conversations/test_id")
        assert response.status_code == 503


class TestSendMessageEndpoint:
    def test_send_message_endpoint_exists(self, client: TestClient):
        response = client.post(
            "/api/conversations/test_conv_id/messages", json={"content": "Hello"}
        )
        assert response.status_code in [200, 404, 500, 503]

    def test_send_message_missing_content(self, client: TestClient):
        response = client.post("/api/conversations/test_conv_id/messages", json={})
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "context_limit,expected_status",
        [
            (1, 200),
            (5, 200),
            (20, 200),
            (0, 422),
            (21, 422),
        ],
    )
    def test_send_message_context_limit_validation(
        self, client: TestClient, context_limit: int, expected_status: int
    ):
        response = client.post(
            "/api/conversations/test_conv_id/messages",
            json={"content": "Test", "context_limit": context_limit},
        )
        assert response.status_code in [expected_status, 404, 500, 503]

    def test_send_message_no_service(
        self, client_no_conversation_service: TestClient
    ):
        response = client_no_conversation_service.post(
            "/api/conversations/test_id/messages", json={"content": "Hello"}
        )
        assert response.status_code == 503


class TestGetMessagesEndpoint:
    def test_get_messages_endpoint_exists(self, client: TestClient):
        response = client.get("/api/conversations/test_conv_id/messages")
        assert response.status_code in [200, 503]

    @pytest.mark.parametrize("limit", [10, 50, 100])
    def test_get_messages_with_limit(self, client: TestClient, limit: int):
        response = client.get(f"/api/conversations/test_conv_id/messages?limit={limit}")
        assert response.status_code in [200, 503]

    @pytest.mark.parametrize("offset", [0, 10, 50])
    def test_get_messages_with_offset(self, client: TestClient, offset: int):
        response = client.get(
            f"/api/conversations/test_conv_id/messages?offset={offset}"
        )
        assert response.status_code in [200, 503]

    def test_get_messages_with_citations(self, client: TestClient):
        response = client.get(
            "/api/conversations/test_conv_id/messages?include_citations=true"
        )
        assert response.status_code in [200, 503]

    def test_get_messages_without_citations(self, client: TestClient):
        response = client.get(
            "/api/conversations/test_conv_id/messages?include_citations=false"
        )
        assert response.status_code in [200, 503]

    def test_get_messages_pagination(self, client: TestClient):
        response = client.get(
            "/api/conversations/test_conv_id/messages?limit=20&offset=10"
        )
        assert response.status_code in [200, 503]

    def test_get_messages_no_service(
        self, client_no_message_service: TestClient
    ):
        response = client_no_message_service.get(
            "/api/conversations/test_id/messages"
        )
        assert response.status_code == 503
