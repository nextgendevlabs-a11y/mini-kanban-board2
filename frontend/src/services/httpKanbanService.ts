import type { ChecklistItem, WorkspaceSnapshot } from '../domain'
import type {
  CreateLabelInput,
  CreateTaskInput,
  CreateWorkspaceInput,
  DeleteColumnInput,
  KanbanService,
  MoveTaskInput,
  UpdateTaskInput,
} from './contracts'
import { ServiceError } from './contracts'

export const DEFAULT_API_BASE_URL = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')

type RequestOptions = {
  method?: string
  body?: unknown
}

export class HttpKanbanService implements KanbanService {
  constructor(private readonly baseUrl = DEFAULT_API_BASE_URL) {}

  private async request(path: string, { method = 'GET', body }: RequestOptions = {}): Promise<WorkspaceSnapshot> {
    let response: Response

    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers: body === undefined ? { Accept: 'application/json' } : { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
      })
    } catch {
      throw new ServiceError('NETWORK', 'Unable to connect to the Flowdeck backend. Please try again.')
    }

    let payload: unknown
    try {
      payload = await response.json()
    } catch {
      payload = undefined
    }

    if (!response.ok) {
      const error = payload && typeof payload === 'object' ? payload as { code?: string; message?: string } : undefined
      throw new ServiceError(error?.code ?? `HTTP_${response.status}`, error?.message ?? 'The backend rejected this request.')
    }

    return payload as WorkspaceSnapshot
  }

  getWorkspace() {
    return this.request('/workspace')
  }

  resetDemo() {
    return this.request('/workspace/reset', { method: 'POST' })
  }

  createWorkspace(input: CreateWorkspaceInput) {
    return this.request('/workspaces', { method: 'POST', body: input })
  }

  createBoard(name: string) {
    return this.request('/boards', { method: 'POST', body: { name } })
  }

  deleteBoard(boardId: string) {
    return this.request(`/boards/${encodeURIComponent(boardId)}`, { method: 'DELETE' })
  }

  addColumn(boardId: string, name: string) {
    return this.request(`/boards/${encodeURIComponent(boardId)}/columns`, { method: 'POST', body: { name } })
  }

  renameColumn(columnId: string, name: string) {
    return this.request(`/columns/${encodeURIComponent(columnId)}`, { method: 'PATCH', body: { name } })
  }

  reorderColumns(boardId: string, orderedColumnIds: string[]) {
    return this.request(`/boards/${encodeURIComponent(boardId)}/columns/order`, { method: 'PUT', body: { orderedColumnIds } })
  }

  deleteColumn(input: DeleteColumnInput) {
    return this.request(`/columns/${encodeURIComponent(input.columnId)}`, {
      method: 'DELETE',
      body: input.destinationColumnId ? { destinationColumnId: input.destinationColumnId } : undefined,
    })
  }

  createLabel(input: CreateLabelInput) {
    return this.request(`/boards/${encodeURIComponent(input.boardId)}/labels`, { method: 'POST', body: input })
  }

  renameLabel(labelId: string, name: string) {
    return this.request(`/labels/${encodeURIComponent(labelId)}`, { method: 'PATCH', body: { name } })
  }

  deleteLabel(labelId: string) {
    return this.request(`/labels/${encodeURIComponent(labelId)}`, { method: 'DELETE' })
  }

  createTask(input: CreateTaskInput) {
    return this.request('/tasks', { method: 'POST', body: input })
  }

  updateTask(taskId: string, input: UpdateTaskInput) {
    return this.request(`/tasks/${encodeURIComponent(taskId)}`, { method: 'PATCH', body: input })
  }

  deleteTask(taskId: string) {
    return this.request(`/tasks/${encodeURIComponent(taskId)}`, { method: 'DELETE' })
  }

  moveTask(input: MoveTaskInput) {
    return this.request(`/tasks/${encodeURIComponent(input.taskId)}/move`, {
      method: 'POST',
      body: { destinationColumnId: input.destinationColumnId, destinationIndex: input.destinationIndex },
    })
  }

  archiveTask(taskId: string) {
    return this.request(`/tasks/${encodeURIComponent(taskId)}/archive`, { method: 'POST' })
  }

  restoreTask(taskId: string) {
    return this.request(`/tasks/${encodeURIComponent(taskId)}/restore`, { method: 'POST' })
  }

  addChecklistItem(taskId: string, text: string) {
    return this.request(`/tasks/${encodeURIComponent(taskId)}/checklist`, { method: 'POST', body: { text } })
  }

  updateChecklistItem(taskId: string, itemId: string, input: Partial<Pick<ChecklistItem, 'text' | 'completed'>>) {
    return this.request(`/tasks/${encodeURIComponent(taskId)}/checklist/${encodeURIComponent(itemId)}`, { method: 'PATCH', body: input })
  }

  deleteChecklistItem(taskId: string, itemId: string) {
    return this.request(`/tasks/${encodeURIComponent(taskId)}/checklist/${encodeURIComponent(itemId)}`, { method: 'DELETE' })
  }

  addComment(taskId: string, body: string) {
    return this.request(`/tasks/${encodeURIComponent(taskId)}/comments`, { method: 'POST', body: { body } })
  }

  toggleReaction(taskId: string, commentId: string, reaction: string) {
    return this.request(`/tasks/${encodeURIComponent(taskId)}/comments/${encodeURIComponent(commentId)}/reaction`, { method: 'PATCH', body: { reaction } })
  }

  addAttachment(taskId: string, file: { name: string; size: number; contentType: string }) {
    return this.request(`/tasks/${encodeURIComponent(taskId)}/attachments`, { method: 'POST', body: file })
  }

  removeAttachment(taskId: string, attachmentId: string) {
    return this.request(`/tasks/${encodeURIComponent(taskId)}/attachments/${encodeURIComponent(attachmentId)}`, { method: 'DELETE' })
  }

  inviteMember(email: string) {
    return this.request('/members/invitations', { method: 'POST', body: { email } })
  }

  acceptInvitation(invitationId: string) {
    return this.request(`/invitations/${encodeURIComponent(invitationId)}/accept`, { method: 'POST' })
  }

  markNotificationRead(notificationId: string) {
    return this.request(`/notifications/${encodeURIComponent(notificationId)}/read`, { method: 'PATCH' })
  }
}

export const createHttpKanbanService = (baseUrl = DEFAULT_API_BASE_URL) => new HttpKanbanService(baseUrl)
