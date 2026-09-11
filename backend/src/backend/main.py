from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Literal
from uuid import uuid4

from fastapi import Body, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field


Priority = Literal["Low", "Medium", "High", "Urgent"]
Role = Literal["owner", "member"]


class ServiceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateWorkspaceInput(InputModel):
    name: str = Field(min_length=1)
    memberEmails: list[str] = []


class NameRequest(InputModel):
    name: str = Field(min_length=1)


class CreateBoardRequest(NameRequest):
    pass


class DeleteColumnRequest(InputModel):
    destinationColumnId: str | None = None


class ReorderColumnsRequest(InputModel):
    orderedColumnIds: list[str]


class CreateLabelInput(InputModel):
    boardId: str
    name: str = Field(min_length=1)
    color: str = Field(min_length=1)


class CreateTaskInput(InputModel):
    boardId: str
    columnId: str
    title: str = Field(min_length=1)
    description: str = ""
    priority: Priority | None = None
    assigneeId: str | None = None


class UpdateTaskInput(InputModel):
    title: str | None = Field(default=None, min_length=1)
    description: str | None = None
    assigneeId: str | None = None
    dueDate: str | None = None
    priority: Priority | None = None
    labelIds: list[str] | None = None
    blocked: bool | None = None


class MoveTaskRequest(InputModel):
    destinationColumnId: str
    destinationIndex: int = Field(ge=0)


class AddChecklistItemRequest(InputModel):
    text: str = Field(min_length=1)


class UpdateChecklistItemRequest(InputModel):
    text: str | None = Field(default=None, min_length=1)
    completed: bool | None = None


class AddCommentRequest(InputModel):
    body: str = Field(min_length=1)


class ToggleReactionRequest(InputModel):
    reaction: Literal["👍", "❤️", "🎉", "👀"]


class AddAttachmentRequest(InputModel):
    name: str = Field(min_length=1)
    size: int = Field(ge=0)
    contentType: str


class InviteMemberRequest(InputModel):
    email: str = Field(min_length=1)


class User(BaseModel):
    id: str
    name: str
    email: str
    role: Role
    initials: str
    color: str


class Label(BaseModel):
    id: str
    boardId: str
    name: str
    color: str


class ChecklistItem(BaseModel):
    id: str
    text: str
    completed: bool
    order: int


class Comment(BaseModel):
    id: str
    taskId: str
    authorId: str
    body: str
    mentionedUserIds: list[str]
    reactions: dict[str, list[str]]
    createdAt: str


class Attachment(BaseModel):
    id: str
    taskId: str
    name: str
    size: int
    contentType: str
    createdAt: str


class ActivityEntry(BaseModel):
    id: str
    taskId: str
    actorId: str
    action: str
    createdAt: str


class Task(BaseModel):
    id: str
    boardId: str
    columnId: str
    title: str
    description: str
    assigneeId: str | None = None
    dueDate: str | None = None
    priority: Priority | None = None
    labelIds: list[str]
    blocked: bool
    archived: bool
    archivedFromColumnId: str | None = None
    order: int
    checklist: list[ChecklistItem]
    comments: list[Comment]
    attachments: list[Attachment]
    activity: list[ActivityEntry]


class Column(BaseModel):
    id: str
    boardId: str
    name: str
    order: int


class Board(BaseModel):
    id: str
    teamId: str
    name: str
    columnIds: list[str]
    labelIds: list[str]


class Invitation(BaseModel):
    id: str
    teamId: str
    email: str
    createdAt: str
    accepted: bool


class Notification(BaseModel):
    id: str
    recipientId: str
    taskId: str
    boardId: str
    authorId: str
    body: str
    read: bool
    createdAt: str


class Team(BaseModel):
    id: str
    name: str
    currentUserId: str
    memberIds: list[str]
    boardIds: list[str]


class WorkspaceSnapshot(BaseModel):
    version: Literal[1]
    team: Team
    users: dict[str, User]
    boards: dict[str, Board]
    columns: dict[str, Column]
    labels: dict[str, Label]
    tasks: dict[str, Task]
    invitations: dict[str, Invitation]
    notifications: dict[str, Notification]


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:7]}"


class MockDatabase:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.snapshot = self._seed()

    def clone(self) -> dict:
        return deepcopy(self.snapshot)

    def finish(self) -> dict:
        return self.clone()

    def _activity(self, task_id: str, actor_id: str, action: str) -> dict:
        return {"id": new_id("activity"), "taskId": task_id, "actorId": actor_id, "action": action, "createdAt": now()}

    def _seed(self) -> dict:
        users = {
            "u1": {"id": "u1", "name": "Maya Chen", "email": "maya@flowdeck.demo", "role": "owner", "initials": "MC", "color": "#ff7a59"},
            "u2": {"id": "u2", "name": "Noah Williams", "email": "noah@flowdeck.demo", "role": "member", "initials": "NW", "color": "#5b8def"},
            "u3": {"id": "u3", "name": "Priya Shah", "email": "priya@flowdeck.demo", "role": "member", "initials": "PS", "color": "#7b61ff"},
            "u4": {"id": "u4", "name": "Leo Martin", "email": "leo@flowdeck.demo", "role": "member", "initials": "LM", "color": "#13b981"},
        }
        boards = {
            "b1": {"id": "b1", "teamId": "team-1", "name": "Product launch", "columnIds": ["c1", "c2", "c3"], "labelIds": ["l1", "l2", "l3"]},
            "b2": {"id": "b2", "teamId": "team-1", "name": "Marketing campaigns", "columnIds": ["c4", "c5", "c6"], "labelIds": ["l4", "l5"]},
            "b3": {"id": "b3", "teamId": "team-1", "name": "Operations", "columnIds": ["c7", "c8", "c9"], "labelIds": []},
        }
        columns = {}
        for board_id, names in {"b1": ["To Do", "In Progress", "Done"], "b2": ["To Do", "In Progress", "Done"], "b3": ["To Do", "In Progress", "Done"]}.items():
            start = {"b1": 1, "b2": 4, "b3": 7}[board_id]
            for index, name in enumerate(names):
                column_id = f"c{start + index}"
                columns[column_id] = {"id": column_id, "boardId": board_id, "name": name, "order": index}
        labels = {
            "l1": {"id": "l1", "boardId": "b1", "name": "Design", "color": "#f3a712"},
            "l2": {"id": "l2", "boardId": "b1", "name": "Frontend", "color": "#5b8def"},
            "l3": {"id": "l3", "boardId": "b1", "name": "Launch", "color": "#13b981"},
            "l4": {"id": "l4", "boardId": "b2", "name": "Content", "color": "#7b61ff"},
            "l5": {"id": "l5", "boardId": "b2", "name": "Growth", "color": "#ff7a59"},
        }

        def task(task_id: str, board_id: str, column_id: str, title: str, order: int, **extra) -> dict:
            value = {"id": task_id, "boardId": board_id, "columnId": column_id, "title": title, "description": "", "labelIds": [], "blocked": False, "archived": False, "order": order, "checklist": [], "comments": [], "attachments": [], "activity": [self._activity(task_id, "u1", "created this task")]}
            value.update(extra)
            return value

        tasks = {
            "t1": task("t1", "b1", "c1", "Shape the launch narrative", 0, assigneeId="u3", priority="High", labelIds=["l1", "l3"], description="Create a clear story for the first public release.", checklist=[{"id": "ch1", "text": "Draft the opening promise", "completed": True, "order": 0}, {"id": "ch2", "text": "Review with the team", "completed": False, "order": 1}]),
            "t2": task("t2", "b1", "c1", "Polish empty states", 1, assigneeId="u2", priority="Medium", labelIds=["l2"]),
            "t3": task("t3", "b1", "c2", "Build the board interactions", 0, assigneeId="u4", priority="Urgent", labelIds=["l2"], blocked=True),
            "t4": task("t4", "b1", "c3", "Choose the visual direction", 0, assigneeId="u1", priority="Low", labelIds=["l1"]),
            "t5": task("t5", "b2", "c4", "Outline campaign themes", 0, assigneeId="u3", priority="Medium", labelIds=["l4"]),
        }
        return {"version": 1, "team": {"id": "team-1", "name": "Flowdeck Studio", "currentUserId": "u1", "memberIds": list(users), "boardIds": list(boards)}, "users": users, "boards": boards, "columns": columns, "labels": labels, "tasks": tasks, "invitations": {}, "notifications": {}}

    def current_user(self) -> dict:
        return self.snapshot["users"][self.snapshot["team"]["currentUserId"]]

    def require_owner(self) -> None:
        if self.current_user()["role"] != "owner":
            raise ServiceError("FORBIDDEN", "Only the team owner can perform this action.")

    def board(self, board_id: str) -> dict:
        board = self.snapshot["boards"].get(board_id)
        if not board:
            raise ServiceError("NOT_FOUND", "Board not found.")
        return board

    def task(self, task_id: str) -> dict:
        task = self.snapshot["tasks"].get(task_id)
        if not task:
            raise ServiceError("NOT_FOUND", "Task not found.")
        return task

    def add_activity(self, task: dict, action: str) -> None:
        task["activity"].append(self._activity(task["id"], self.snapshot["team"]["currentUserId"], action))

    def reorder_tasks(self, column_id: str) -> None:
        tasks = sorted((task for task in self.snapshot["tasks"].values() if task["columnId"] == column_id and not task["archived"]), key=lambda item: item["order"])
        for index, task in enumerate(tasks):
            task["order"] = index

    def create_workspace(self, input: CreateWorkspaceInput) -> dict:
        name = input.name.strip()
        if not name:
            raise ServiceError("VALIDATION", "Workspace name is required.")
        emails = list(dict.fromkeys(email.strip().lower() for email in input.memberEmails if email.strip()))
        if any("@" not in email for email in emails):
            raise ServiceError("VALIDATION", "Every member must have a valid email address.")
        owner = self.current_user()
        users = {owner["id"]: {**owner, "role": "owner"}}
        colors = ["#5b8def", "#7b61ff", "#13b981", "#f3a712", "#ff7a59"]
        for index, email in enumerate(emails):
            display_name = re.sub(r"[._-]+", " ", email.split("@")[0]).title()
            initials = "".join(part[0] for part in display_name.split()).upper()[:2] or "M"
            user_id = new_id("user")
            users[user_id] = {"id": user_id, "name": display_name, "email": email, "role": "member", "initials": initials, "color": colors[index % len(colors)]}
        team_id, board_id = new_id("team"), new_id("board")
        columns = {}
        column_ids = []
        for order, column_name in enumerate(["To Do", "In Progress", "Done"]):
            column_id = new_id("column")
            column_ids.append(column_id)
            columns[column_id] = {"id": column_id, "boardId": board_id, "name": column_name, "order": order}
        self.snapshot = {"version": 1, "team": {"id": team_id, "name": name, "currentUserId": owner["id"], "memberIds": list(users), "boardIds": [board_id]}, "users": users, "boards": {board_id: {"id": board_id, "teamId": team_id, "name": "Getting started", "columnIds": column_ids, "labelIds": []}}, "columns": columns, "labels": {}, "tasks": {}, "invitations": {}, "notifications": {}}
        return self.finish()

    def create_board(self, name: str) -> dict:
        self.require_owner()
        name = name.strip()
        if not name:
            raise ServiceError("VALIDATION", "Board name is required.")
        board_id = new_id("board")
        column_ids = []
        for order, column_name in enumerate(["To Do", "In Progress", "Done"]):
            column_id = new_id("column")
            column_ids.append(column_id)
            self.snapshot["columns"][column_id] = {"id": column_id, "boardId": board_id, "name": column_name, "order": order}
        self.snapshot["boards"][board_id] = {"id": board_id, "teamId": self.snapshot["team"]["id"], "name": name, "columnIds": column_ids, "labelIds": []}
        self.snapshot["team"]["boardIds"].append(board_id)
        return self.finish()

    def delete_board(self, board_id: str) -> dict:
        self.require_owner()
        self.board(board_id)
        if len(self.snapshot["team"]["boardIds"]) == 1:
            raise ServiceError("VALIDATION", "A team must retain at least one board.")
        del self.snapshot["boards"][board_id]
        self.snapshot["team"]["boardIds"].remove(board_id)
        for column_id in [key for key, value in self.snapshot["columns"].items() if value["boardId"] == board_id]:
            del self.snapshot["columns"][column_id]
        for task_id in [key for key, value in self.snapshot["tasks"].items() if value["boardId"] == board_id]:
            del self.snapshot["tasks"][task_id]
        return self.finish()

    def add_column(self, board_id: str, name: str) -> dict:
        board = self.board(board_id)
        name = name.strip()
        if not name:
            raise ServiceError("VALIDATION", "Column name is required.")
        column_id = new_id("column")
        self.snapshot["columns"][column_id] = {"id": column_id, "boardId": board_id, "name": name, "order": len(board["columnIds"])}
        board["columnIds"].append(column_id)
        return self.finish()

    def rename_column(self, column_id: str, name: str) -> dict:
        column = self.snapshot["columns"].get(column_id)
        if not column:
            raise ServiceError("NOT_FOUND", "Column not found.")
        name = name.strip()
        if not name:
            raise ServiceError("VALIDATION", "Column name is required.")
        column["name"] = name
        return self.finish()

    def reorder_columns(self, board_id: str, ordered_column_ids: list[str]) -> dict:
        board = self.board(board_id)
        if len(ordered_column_ids) != len(board["columnIds"]) or any(column_id not in board["columnIds"] for column_id in ordered_column_ids):
            raise ServiceError("VALIDATION", "Invalid column order.")
        board["columnIds"] = ordered_column_ids
        for order, column_id in enumerate(ordered_column_ids):
            self.snapshot["columns"][column_id]["order"] = order
        return self.finish()

    def delete_column(self, column_id: str, destination_column_id: str | None) -> dict:
        column = self.snapshot["columns"].get(column_id)
        if not column:
            raise ServiceError("NOT_FOUND", "Column not found.")
        board = self.board(column["boardId"])
        if len(board["columnIds"]) == 1:
            raise ServiceError("VALIDATION", "A board must retain at least one column.")
        active = [task for task in self.snapshot["tasks"].values() if task["columnId"] == column_id and not task["archived"]]
        if active and (not destination_column_id or destination_column_id == column_id or destination_column_id not in board["columnIds"]):
            raise ServiceError("DESTINATION_REQUIRED", "Choose a destination column for active tasks.")
        if destination_column_id:
            for index, task in enumerate(active):
                task["columnId"] = destination_column_id
                task["order"] = index
                self.add_activity(task, f"moved from {column['name']}")
        board["columnIds"].remove(column_id)
        del self.snapshot["columns"][column_id]
        return self.finish()

    def create_label(self, input: CreateLabelInput) -> dict:
        board = self.board(input.boardId)
        name = input.name.strip()
        if not name:
            raise ServiceError("VALIDATION", "Label name is required.")
        if any(self.snapshot["labels"][label_id]["name"].lower() == name.lower() for label_id in board["labelIds"]):
            raise ServiceError("DUPLICATE_LABEL", "That label already exists on this board.")
        label_id = new_id("label")
        self.snapshot["labels"][label_id] = {"id": label_id, "boardId": board["id"], "name": name, "color": input.color}
        board["labelIds"].append(label_id)
        return self.finish()

    def rename_label(self, label_id: str, name: str) -> dict:
        label = self.snapshot["labels"].get(label_id)
        if not label:
            raise ServiceError("NOT_FOUND", "Label not found.")
        name = name.strip()
        if not name:
            raise ServiceError("VALIDATION", "Label name is required.")
        board = self.board(label["boardId"])
        if any(other != label_id and self.snapshot["labels"][other]["name"].lower() == name.lower() for other in board["labelIds"]):
            raise ServiceError("DUPLICATE_LABEL", "That label already exists on this board.")
        label["name"] = name
        return self.finish()

    def delete_label(self, label_id: str) -> dict:
        label = self.snapshot["labels"].get(label_id)
        if not label:
            raise ServiceError("NOT_FOUND", "Label not found.")
        board = self.board(label["boardId"])
        board["labelIds"].remove(label_id)
        for task in self.snapshot["tasks"].values():
            if task["boardId"] == board["id"]:
                task["labelIds"] = [value for value in task["labelIds"] if value != label_id]
        del self.snapshot["labels"][label_id]
        return self.finish()

    def create_task(self, input: CreateTaskInput) -> dict:
        board = self.board(input.boardId)
        if input.columnId not in board["columnIds"]:
            raise ServiceError("VALIDATION", "Column does not belong to this board.")
        title = input.title.strip()
        if not title:
            raise ServiceError("VALIDATION", "Task title is required.")
        if input.assigneeId and input.assigneeId not in self.snapshot["team"]["memberIds"]:
            raise ServiceError("VALIDATION", "Assignee must be a team member.")
        order = len([task for task in self.snapshot["tasks"].values() if task["columnId"] == input.columnId and not task["archived"]])
        task_id = new_id("task")
        self.snapshot["tasks"][task_id] = {"id": task_id, "boardId": input.boardId, "columnId": input.columnId, "title": title, "description": input.description, "assigneeId": input.assigneeId, "priority": input.priority, "labelIds": [], "blocked": False, "archived": False, "order": order, "checklist": [], "comments": [], "attachments": [], "activity": [self._activity(task_id, self.snapshot["team"]["currentUserId"], "created this task")]}
        return self.finish()

    def update_task(self, task_id: str, input: UpdateTaskInput) -> dict:
        task = self.task(task_id)
        values = input.model_dump(exclude_unset=True)
        if "title" in values:
            title = (values["title"] or "").strip()
            if not title:
                raise ServiceError("VALIDATION", "Task title is required.")
            values["title"] = title
        if values.get("assigneeId") and values["assigneeId"] not in self.snapshot["team"]["memberIds"]:
            raise ServiceError("VALIDATION", "Assignee must be a team member.")
        if values.get("labelIds") and any(label_id not in self.snapshot["labels"] or self.snapshot["labels"][label_id]["boardId"] != task["boardId"] for label_id in values["labelIds"]):
            raise ServiceError("VALIDATION", "Labels must belong to the task board.")
        previous_assignee, previous_blocked = task.get("assigneeId"), task["blocked"]
        task.update(values)
        if "assigneeId" in values and previous_assignee != task.get("assigneeId"):
            self.add_activity(task, "changed the assignee")
        if "blocked" in values and previous_blocked != task["blocked"]:
            self.add_activity(task, "marked this task blocked" if task["blocked"] else "cleared the blocked state")
        return self.finish()

    def delete_task(self, task_id: str) -> dict:
        task = self.task(task_id)
        del self.snapshot["tasks"][task_id]
        self.reorder_tasks(task["columnId"])
        return self.finish()

    def move_task(self, task_id: str, destination_column_id: str, destination_index: int) -> dict:
        task = self.task(task_id)
        destination = self.snapshot["columns"].get(destination_column_id)
        if not destination or destination["boardId"] != task["boardId"]:
            raise ServiceError("VALIDATION", "Destination column is invalid.")
        old_column = self.snapshot["columns"].get(task["columnId"])
        old_column_id = task["columnId"]
        task["columnId"] = destination_column_id
        peers = sorted((item for item in self.snapshot["tasks"].values() if item["id"] != task_id and item["columnId"] == destination_column_id and not item["archived"]), key=lambda item: item["order"])
        peers.insert(min(max(destination_index, 0), len(peers)), task)
        for index, item in enumerate(peers):
            item["order"] = index
        self.reorder_tasks(old_column_id)
        self.add_activity(task, f"moved from {old_column['name']} to {destination['name']}")
        return self.finish()

    def archive_task(self, task_id: str) -> dict:
        task = self.task(task_id)
        task["archivedFromColumnId"] = task["columnId"]
        task["archived"] = True
        self.add_activity(task, "archived this task")
        self.reorder_tasks(task["columnId"])
        return self.finish()

    def restore_task(self, task_id: str) -> dict:
        task = self.task(task_id)
        board = self.board(task["boardId"])
        destination = task.get("archivedFromColumnId") if task.get("archivedFromColumnId") in board["columnIds"] else board["columnIds"][0]
        task["columnId"], task["archived"] = destination, False
        task["order"] = len([item for item in self.snapshot["tasks"].values() if item["columnId"] == destination and not item["archived"]])
        self.add_activity(task, "restored this task")
        return self.finish()

    def add_checklist_item(self, task_id: str, text: str) -> dict:
        task = self.task(task_id)
        text = text.strip()
        if not text:
            raise ServiceError("VALIDATION", "Checklist text is required.")
        task["checklist"].append({"id": new_id("check"), "text": text, "completed": False, "order": len(task["checklist"])})
        return self.finish()

    def update_checklist_item(self, task_id: str, item_id: str, input: UpdateChecklistItemRequest) -> dict:
        items = self.task(task_id)["checklist"]
        item = next((value for value in items if value["id"] == item_id), None)
        if not item:
            raise ServiceError("NOT_FOUND", "Checklist item not found.")
        values = input.model_dump(exclude_unset=True)
        if "text" in values:
            text = (values["text"] or "").strip()
            if not text:
                raise ServiceError("VALIDATION", "Checklist text is required.")
            values["text"] = text
        item.update(values)
        return self.finish()

    def delete_checklist_item(self, task_id: str, item_id: str) -> dict:
        task = self.task(task_id)
        task["checklist"] = [{**item, "order": order} for order, item in enumerate(task["checklist"]) if item["id"] != item_id]
        return self.finish()

    def add_comment(self, task_id: str, body: str) -> dict:
        task = self.task(task_id)
        body = body.strip()
        if not body:
            raise ServiceError("VALIDATION", "Comment text is required.")
        mentioned = []
        for match in re.findall(r"@([\w]+)", body):
            user = next((user for user in self.snapshot["users"].values() if user["name"].lower().startswith(match.lower())), None)
            if user and user["id"] not in mentioned:
                mentioned.append(user["id"])
        comment = {"id": new_id("comment"), "taskId": task_id, "authorId": self.snapshot["team"]["currentUserId"], "body": body, "mentionedUserIds": mentioned, "reactions": {}, "createdAt": now()}
        task["comments"].append(comment)
        for recipient_id in mentioned:
            if recipient_id != self.snapshot["team"]["currentUserId"]:
                notification_id = new_id("notification")
                self.snapshot["notifications"][notification_id] = {"id": notification_id, "recipientId": recipient_id, "taskId": task_id, "boardId": task["boardId"], "authorId": self.snapshot["team"]["currentUserId"], "body": body, "read": False, "createdAt": now()}
        return self.finish()

    def toggle_reaction(self, task_id: str, comment_id: str, reaction: str) -> dict:
        comment = next((value for value in self.task(task_id)["comments"] if value["id"] == comment_id), None)
        if not comment:
            raise ServiceError("NOT_FOUND", "Comment not found.")
        users = comment["reactions"].get(reaction, [])
        current_user_id = self.snapshot["team"]["currentUserId"]
        comment["reactions"][reaction] = [user_id for user_id in users if user_id != current_user_id] if current_user_id in users else [*users, current_user_id]
        return self.finish()

    def add_attachment(self, task_id: str, input: AddAttachmentRequest) -> dict:
        task = self.task(task_id)
        name = input.name.strip()
        if not name:
            raise ServiceError("VALIDATION", "Attachment name is required.")
        task["attachments"].append({"id": new_id("attachment"), "taskId": task_id, "name": name, "size": input.size, "contentType": input.contentType, "createdAt": now()})
        return self.finish()

    def remove_attachment(self, task_id: str, attachment_id: str) -> dict:
        task = self.task(task_id)
        task["attachments"] = [attachment for attachment in task["attachments"] if attachment["id"] != attachment_id]
        return self.finish()

    def invite_member(self, email: str) -> dict:
        self.require_owner()
        email = email.strip().lower()
        if "@" not in email:
            raise ServiceError("VALIDATION", "Enter a valid email address.")
        invitation_id = new_id("invite")
        self.snapshot["invitations"][invitation_id] = {"id": invitation_id, "teamId": self.snapshot["team"]["id"], "email": email, "createdAt": now(), "accepted": False}
        return self.finish()

    def accept_invitation(self, invitation_id: str) -> dict:
        invitation = self.snapshot["invitations"].get(invitation_id)
        if not invitation:
            raise ServiceError("NOT_FOUND", "Invitation not found.")
        invitation["accepted"] = True
        return self.finish()

    def mark_notification_read(self, notification_id: str) -> dict:
        notification = self.snapshot["notifications"].get(notification_id)
        if not notification:
            raise ServiceError("NOT_FOUND", "Notification not found.")
        notification["read"] = True
        return self.finish()


database = MockDatabase()
app = FastAPI(title="Flowdeck Kanban API", version="0.1.0", description="Mock backend for the Flowdeck frontend.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ServiceError)
async def service_error_handler(_: Request, error: ServiceError) -> JSONResponse:
    status = {"FORBIDDEN": 403, "NOT_FOUND": 404, "DUPLICATE_LABEL": 409}.get(error.code, 400)
    return JSONResponse(status_code=status, content={"code": error.code, "message": error.message})


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(_: Request, error: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"code": "VALIDATION", "message": str(error)})


def snapshot_response(data: dict) -> WorkspaceSnapshot:
    return WorkspaceSnapshot.model_validate(data)


@app.get("/api/v1/workspace", operation_id="getWorkspace", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Workspace"])
def get_workspace() -> dict:
    return database.clone()


@app.post("/api/v1/workspace/reset", operation_id="resetDemo", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Workspace"])
def reset_demo() -> dict:
    database.reset()
    return database.finish()


@app.post("/api/v1/workspaces", operation_id="createWorkspace", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Workspace"])
def create_workspace(input: CreateWorkspaceInput) -> dict:
    return database.create_workspace(input)


@app.post("/api/v1/boards", operation_id="createBoard", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Boards"])
def create_board(input: CreateBoardRequest) -> dict:
    return database.create_board(input.name)


@app.delete("/api/v1/boards/{boardId}", operation_id="deleteBoard", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Boards"])
def delete_board(boardId: str) -> dict:
    return database.delete_board(boardId)


@app.post("/api/v1/boards/{boardId}/columns", operation_id="addColumn", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Columns"])
def add_column(boardId: str, input: NameRequest) -> dict:
    return database.add_column(boardId, input.name)


@app.patch("/api/v1/columns/{columnId}", operation_id="renameColumn", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Columns"])
def rename_column(columnId: str, input: NameRequest) -> dict:
    return database.rename_column(columnId, input.name)


@app.delete("/api/v1/columns/{columnId}", operation_id="deleteColumn", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Columns"])
def delete_column(columnId: str, input: DeleteColumnRequest | None = Body(default=None)) -> dict:
    return database.delete_column(columnId, input.destinationColumnId if input else None)


@app.put("/api/v1/boards/{boardId}/columns/order", operation_id="reorderColumns", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Columns"])
def reorder_columns(boardId: str, input: ReorderColumnsRequest) -> dict:
    return database.reorder_columns(boardId, input.orderedColumnIds)


@app.post("/api/v1/boards/{boardId}/labels", operation_id="createLabel", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Labels"])
def create_label(boardId: str, input: CreateLabelInput) -> dict:
    if input.boardId != boardId:
        raise ServiceError("VALIDATION", "boardId must match the path board.")
    return database.create_label(input)


@app.patch("/api/v1/labels/{labelId}", operation_id="renameLabel", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Labels"])
def rename_label(labelId: str, input: NameRequest) -> dict:
    return database.rename_label(labelId, input.name)


@app.delete("/api/v1/labels/{labelId}", operation_id="deleteLabel", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Labels"])
def delete_label(labelId: str) -> dict:
    return database.delete_label(labelId)


@app.post("/api/v1/tasks", operation_id="createTask", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Tasks"])
def create_task(input: CreateTaskInput) -> dict:
    return database.create_task(input)


@app.patch("/api/v1/tasks/{taskId}", operation_id="updateTask", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Tasks"])
def update_task(taskId: str, input: UpdateTaskInput) -> dict:
    return database.update_task(taskId, input)


@app.delete("/api/v1/tasks/{taskId}", operation_id="deleteTask", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Tasks"])
def delete_task(taskId: str) -> dict:
    return database.delete_task(taskId)


@app.post("/api/v1/tasks/{taskId}/move", operation_id="moveTask", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Tasks"])
def move_task(taskId: str, input: MoveTaskRequest) -> dict:
    return database.move_task(taskId, input.destinationColumnId, input.destinationIndex)


@app.post("/api/v1/tasks/{taskId}/archive", operation_id="archiveTask", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Tasks"])
def archive_task(taskId: str) -> dict:
    return database.archive_task(taskId)


@app.post("/api/v1/tasks/{taskId}/restore", operation_id="restoreTask", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Tasks"])
def restore_task(taskId: str) -> dict:
    return database.restore_task(taskId)


@app.post("/api/v1/tasks/{taskId}/checklist", operation_id="addChecklistItem", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Tasks"])
def add_checklist_item(taskId: str, input: AddChecklistItemRequest) -> dict:
    return database.add_checklist_item(taskId, input.text)


@app.patch("/api/v1/tasks/{taskId}/checklist/{itemId}", operation_id="updateChecklistItem", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Tasks"])
def update_checklist_item(taskId: str, itemId: str, input: UpdateChecklistItemRequest) -> dict:
    return database.update_checklist_item(taskId, itemId, input)


@app.delete("/api/v1/tasks/{taskId}/checklist/{itemId}", operation_id="deleteChecklistItem", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Tasks"])
def delete_checklist_item(taskId: str, itemId: str) -> dict:
    return database.delete_checklist_item(taskId, itemId)


@app.post("/api/v1/tasks/{taskId}/comments", operation_id="addComment", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Collaboration"])
def add_comment(taskId: str, input: AddCommentRequest) -> dict:
    return database.add_comment(taskId, input.body)


@app.patch("/api/v1/tasks/{taskId}/comments/{commentId}/reaction", operation_id="toggleReaction", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Collaboration"])
def toggle_reaction(taskId: str, commentId: str, input: ToggleReactionRequest) -> dict:
    return database.toggle_reaction(taskId, commentId, input.reaction)


@app.post("/api/v1/tasks/{taskId}/attachments", operation_id="addAttachment", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Collaboration"])
def add_attachment(taskId: str, input: AddAttachmentRequest) -> dict:
    return database.add_attachment(taskId, input)


@app.delete("/api/v1/tasks/{taskId}/attachments/{attachmentId}", operation_id="removeAttachment", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Collaboration"])
def remove_attachment(taskId: str, attachmentId: str) -> dict:
    return database.remove_attachment(taskId, attachmentId)


@app.post("/api/v1/members/invitations", operation_id="inviteMember", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Collaboration"])
def invite_member(input: InviteMemberRequest) -> dict:
    return database.invite_member(input.email)


@app.post("/api/v1/invitations/{invitationId}/accept", operation_id="acceptInvitation", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Collaboration"])
def accept_invitation(invitationId: str) -> dict:
    return database.accept_invitation(invitationId)


@app.patch("/api/v1/notifications/{notificationId}/read", operation_id="markNotificationRead", response_model=WorkspaceSnapshot, response_model_exclude_none=True, tags=["Notifications"])
def mark_notification_read(notificationId: str) -> dict:
    return database.mark_notification_read(notificationId)
