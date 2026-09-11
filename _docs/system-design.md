# Modern Mini Kanban Board — System Design

## 1. Goals and boundaries

The first release is a front-end-playable demo. It must feel immediate with seeded
data, preserve changes while moving between the workspace, About, and FAQ, and expose
the same application contract that a real backend can implement later.

Out of scope for this design are authentication, cross-user synchronization, real email
delivery, production file storage, external integrations, and server-side analytics.

## 2. Architecture

```text
React UI
  ├─ page/routing state (workspace | about | faq)
  ├─ view state (selected board, filters, open dialog, focus)
  └─ domain state (workspace snapshot + loading/error state)
          │
          ▼
     KanbanService interface
          │
          ├─ MockKanbanService (test implementation)
          │    ├─ seeded workspace factory
          │    └─ localStorage persistence
          │
          └─ HttpKanbanService (current implementation)
               └─ REST/JSON adapter to the FastAPI backend
```

The UI never reads storage, constructs API URLs, or mutates domain collections directly.
Every backend-shaped operation goes through `frontend/src/services/index.ts` and the
`KanbanService` interface. The HTTP implementation is the application default. The mock
remains available for isolated component and service tests.

## 3. Domain model

- `Team`: current user, owner/member users, boards, and pending invitations.
- `Board`: ordered columns, board-local labels, and task identifiers.
- `Column`: a workflow lane; its position is the task's only workflow status.
- `Task`: title plus description, assignee, due date, priority, labels, blocked state,
  checklist, comments, attachments, archive metadata, and activity.
- `Notification`: valid member mention addressed to the current user.
- `ActivityEntry`: auditable task action with actor and timestamp.

The mock store persists one versioned `WorkspaceSnapshot` under
`modern-mini-kanban:workspace:v1`. Persisted state is a demo convenience, not a
security boundary. Attachment contents are represented by metadata and an object URL
or mock download action; no file is uploaded.

## 4. Service contract

The service owns validation, authorization, ordering, relationship updates, activity,
notifications, and persistence. Its main operations are:

| Area | Operations |
| --- | --- |
| Workspace | `getWorkspace`, `resetDemo` |
| Boards | `createBoard`, `deleteBoard` |
| Columns | `addColumn`, `renameColumn`, `reorderColumns`, `deleteColumn` |
| Labels | `createLabel`, `renameLabel`, `deleteLabel` |
| Tasks | `createTask`, `updateTask`, `deleteTask`, `moveTask`, `archiveTask`, `restoreTask` |
| Task details | `checklist`, `comments`, `reactions`, `attachments` |
| Collaboration | `inviteMember`, `acceptInvitation`, `markNotificationRead` |

All mutating calls return the updated `WorkspaceSnapshot`. This keeps the UI reducer-free
and makes the mock and a future HTTP adapter interchangeable. The UI may update its
local snapshot optimistically, but the service remains the source of truth and returns a
fresh snapshot after each operation.

## 5. State and rendering

The workspace snapshot is kept at the application boundary. Derived board columns,
filtered task IDs, checklist counts, and unread notification counts are computed with
small selectors. Task cards receive only their task and member/label lookups, so a
single task update can avoid rebuilding unaffected card content.

Task movement has two paths:

1. Pointer path: drag a card to a column/position and call `moveTask`.
2. Accessible fallback: task actions → Move → destination column → position.

The fallback is the required keyboard and assistive-technology path. Confirmation is a
UI concern for destructive actions; validation and the actual mutation are service
concerns.

## 6. Error and persistence strategy

- Initial load shows a loading state and a recoverable error with Retry.
- Mutations preserve the last visible snapshot if a service call fails.
- Invalid titles, labels, mentions, permissions, and column deletion destinations are
  rejected with typed `ServiceError` codes.
- The HTTP service maps structured backend errors to `ServiceError` values.
- Resetting the demo replaces the backend workspace with a fresh seed and is explicit.

## 7. Testing strategy

- Unit tests cover seed shape, task ordering, column deletion safeguards, archive
  fallback, mention notifications, label scoping, and persistence.
- Component tests cover initial rendering, creation, filtering, keyboard move fallback,
  navigation, and preservation of changes.
- Browser-level acceptance tests should later exercise the full keyboard-only and narrow
  viewport matrix with Playwright.

## 8. Production evolution

The frontend uses `createHttpKanbanService()` while keeping the React UI and domain
types independent of transport. The adapter retains the same method signatures, maps
server errors to `ServiceError`, and uses server-side authorization as the source of
truth. A later backend can use PostgreSQL with tables for teams, memberships, boards,
columns, tasks, labels, comments, attachments, notifications, and activity entries.
