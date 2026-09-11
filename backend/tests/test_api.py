from fastapi.testclient import TestClient

from backend.main import app, database


client = TestClient(app)
BASE = "/api/v1"


def setup_function() -> None:
    database.reset()


def snapshot(response):
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "version",
        "team",
        "users",
        "boards",
        "columns",
        "labels",
        "tasks",
        "invitations",
        "notifications",
    }
    assert body["version"] == 1
    return body


def test_workspace_endpoints_return_snapshots() -> None:
    initial = snapshot(client.get(f"{BASE}/workspace"))
    assert initial["team"]["name"] == "Flowdeck Studio"
    assert len(initial["team"]["boardIds"]) == 3

    created = snapshot(
        client.post(
            f"{BASE}/workspaces",
            json={"name": "Research", "memberEmails": ["new@example.com"]},
        )
    )
    assert created["team"]["name"] == "Research"
    assert len(created["team"]["boardIds"]) == 1
    assert len(created["columns"]) == 3
    assert "new@example.com" in [user["email"] for user in created["users"].values()]

    reset = snapshot(client.post(f"{BASE}/workspace/reset"))
    assert reset["team"]["name"] == "Flowdeck Studio"


def test_board_column_and_label_endpoints() -> None:
    created = snapshot(client.post(f"{BASE}/boards", json={"name": "Roadmap"}))
    board_id = created["team"]["boardIds"][-1]
    assert len(created["boards"][board_id]["columnIds"]) == 3

    created = snapshot(
        client.post(f"{BASE}/boards/{board_id}/columns", json={"name": "Review"})
    )
    column_id = created["boards"][board_id]["columnIds"][-1]
    created = snapshot(
        client.patch(f"{BASE}/columns/{column_id}", json={"name": "Needs review"})
    )
    assert created["columns"][column_id]["name"] == "Needs review"

    ordered = list(reversed(created["boards"][board_id]["columnIds"]))
    created = snapshot(
        client.put(
            f"{BASE}/boards/{board_id}/columns/order",
            json={"orderedColumnIds": ordered},
        )
    )
    assert created["boards"][board_id]["columnIds"] == ordered

    created = snapshot(
        client.post(
            f"{BASE}/boards/{board_id}/labels",
            json={"boardId": board_id, "name": "Bug", "color": "#ff0000"},
        )
    )
    label_id = created["boards"][board_id]["labelIds"][-1]
    created = snapshot(client.patch(f"{BASE}/labels/{label_id}", json={"name": "Defect"}))
    assert created["labels"][label_id]["name"] == "Defect"
    created = snapshot(client.delete(f"{BASE}/labels/{label_id}"))
    assert label_id not in created["labels"]

    deleted = snapshot(client.delete(f"{BASE}/columns/{column_id}"))
    assert column_id not in deleted["columns"]
    deleted = snapshot(client.delete(f"{BASE}/boards/{board_id}"))
    assert board_id not in deleted["boards"]


def test_column_delete_requires_destination_for_active_tasks() -> None:
    response = client.request("DELETE", f"{BASE}/columns/c1")
    assert response.status_code == 400
    assert response.json()["code"] == "DESTINATION_REQUIRED"

    result = snapshot(
        client.request(
            "DELETE",
            f"{BASE}/columns/c1",
            json={"destinationColumnId": "c2"},
        )
    )
    assert "c1" not in result["columns"]
    assert result["tasks"]["t1"]["columnId"] == "c2"


def test_task_endpoints_cover_create_update_move_archive_restore_delete() -> None:
    created = snapshot(
        client.post(
            f"{BASE}/tasks",
            json={
                "boardId": "b1",
                "columnId": "c1",
                "title": "Ship API",
                "description": "Implement the service",
                "priority": "High",
                "assigneeId": "u2",
            },
        )
    )
    task_id = next(task_id for task_id, task in created["tasks"].items() if task["title"] == "Ship API")

    updated = snapshot(
        client.patch(
            f"{BASE}/tasks/{task_id}",
            json={
                "title": "Ship API v1",
                "dueDate": "2026-10-01",
                "priority": "Urgent",
                "labelIds": ["l1"],
                "blocked": True,
            },
        )
    )
    assert updated["tasks"][task_id]["title"] == "Ship API v1"
    assert updated["tasks"][task_id]["dueDate"] == "2026-10-01"
    assert updated["tasks"][task_id]["activity"][-1]["action"] == "marked this task blocked"

    moved = snapshot(
        client.post(
            f"{BASE}/tasks/{task_id}/move",
            json={"destinationColumnId": "c2", "destinationIndex": 0},
        )
    )
    assert moved["tasks"][task_id]["columnId"] == "c2"

    archived = snapshot(client.post(f"{BASE}/tasks/{task_id}/archive"))
    assert archived["tasks"][task_id]["archived"] is True
    restored = snapshot(client.post(f"{BASE}/tasks/{task_id}/restore"))
    assert restored["tasks"][task_id]["archived"] is False
    assert restored["tasks"][task_id]["columnId"] == "c2"

    deleted = snapshot(client.delete(f"{BASE}/tasks/{task_id}"))
    assert task_id not in deleted["tasks"]


def test_task_detail_endpoints() -> None:
    checklist = snapshot(
        client.post(
            f"{BASE}/tasks/t1/checklist",
            json={"text": "Publish release notes"},
        )
    )
    item_id = checklist["tasks"]["t1"]["checklist"][-1]["id"]
    checklist = snapshot(
        client.patch(
            f"{BASE}/tasks/t1/checklist/{item_id}",
            json={"completed": True, "text": "Publish final release notes"},
        )
    )
    assert checklist["tasks"]["t1"]["checklist"][-1]["completed"] is True
    checklist = snapshot(client.delete(f"{BASE}/tasks/t1/checklist/{item_id}"))
    assert item_id not in {item["id"] for item in checklist["tasks"]["t1"]["checklist"]}

    commented = snapshot(
        client.post(
            f"{BASE}/tasks/t1/comments",
            json={"body": "Please review this, @Noah"},
        )
    )
    comment = commented["tasks"]["t1"]["comments"][-1]
    assert comment["mentionedUserIds"] == ["u2"]
    notification_id = next(iter(commented["notifications"]))
    assert commented["notifications"][notification_id]["read"] is False

    reacted = snapshot(
        client.patch(
            f"{BASE}/tasks/t1/comments/{comment['id']}/reaction",
            json={"reaction": "👍"},
        )
    )
    assert reacted["tasks"]["t1"]["comments"][-1]["reactions"]["👍"] == ["u1"]
    toggled = snapshot(
        client.patch(
            f"{BASE}/tasks/t1/comments/{comment['id']}/reaction",
            json={"reaction": "👍"},
        )
    )
    assert toggled["tasks"]["t1"]["comments"][-1]["reactions"]["👍"] == []

    attached = snapshot(
        client.post(
            f"{BASE}/tasks/t1/attachments",
            json={"name": "notes.txt", "size": 42, "contentType": "text/plain"},
        )
    )
    attachment_id = attached["tasks"]["t1"]["attachments"][-1]["id"]
    removed = snapshot(client.delete(f"{BASE}/tasks/t1/attachments/{attachment_id}"))
    assert removed["tasks"]["t1"]["attachments"] == []


def test_membership_and_notification_endpoints() -> None:
    invited = snapshot(
        client.post(f"{BASE}/members/invitations", json={"email": "teammate@example.com"})
    )
    invitation_id = next(iter(invited["invitations"]))
    accepted = snapshot(client.post(f"{BASE}/invitations/{invitation_id}/accept"))
    assert accepted["invitations"][invitation_id]["accepted"] is True

    commented = snapshot(
        client.post(f"{BASE}/tasks/t1/comments", json={"body": "Hello @Noah"})
    )
    notification_id = next(iter(commented["notifications"]))
    read = snapshot(client.patch(f"{BASE}/notifications/{notification_id}/read"))
    assert read["notifications"][notification_id]["read"] is True


def test_validation_and_not_found_errors_match_service_error_shape() -> None:
    invalid = client.post(f"{BASE}/tasks", json={"boardId": "b1", "columnId": "c1", "title": " "})
    assert invalid.status_code == 400
    assert invalid.json()["code"] == "VALIDATION"

    duplicate = client.post(
        f"{BASE}/boards/b1/labels",
        json={"boardId": "b1", "name": "Design", "color": "#fff"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "DUPLICATE_LABEL"

    missing = client.delete(f"{BASE}/tasks/missing")
    assert missing.status_code == 404
    assert missing.json()["code"] == "NOT_FOUND"


def test_generated_openapi_contains_all_contract_operation_ids() -> None:
    operation_ids = {
        operation["operationId"]
        for path in app.openapi()["paths"].values()
        for operation in path.values()
        if isinstance(operation, dict) and "operationId" in operation
    }
    expected = {
        "getWorkspace",
        "resetDemo",
        "createWorkspace",
        "createBoard",
        "deleteBoard",
        "addColumn",
        "renameColumn",
        "reorderColumns",
        "deleteColumn",
        "createLabel",
        "renameLabel",
        "deleteLabel",
        "createTask",
        "updateTask",
        "deleteTask",
        "moveTask",
        "archiveTask",
        "restoreTask",
        "addChecklistItem",
        "updateChecklistItem",
        "deleteChecklistItem",
        "addComment",
        "toggleReaction",
        "addAttachment",
        "removeAttachment",
        "inviteMember",
        "acceptInvitation",
        "markNotificationRead",
    }
    assert operation_ids == expected
