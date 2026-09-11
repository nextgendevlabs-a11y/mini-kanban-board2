import type { ChecklistItem, Comment, Priority, WorkspaceSnapshot } from '../domain'

export interface CreateTaskInput {
  boardId: string
  columnId: string
  title: string
  description?: string
  priority?: Priority
  assigneeId?: string
}

export interface UpdateTaskInput {
  title?: string
  description?: string
  assigneeId?: string
  dueDate?: string
  priority?: Priority
  labelIds?: string[]
  blocked?: boolean
}

export interface MoveTaskInput {
  taskId: string
  destinationColumnId: string
  destinationIndex: number
}

export interface DeleteColumnInput {
  columnId: string
  destinationColumnId?: string
}

export interface CreateLabelInput { boardId: string; name: string; color: string }
export interface CreateWorkspaceInput { name: string; memberEmails: string[] }

export interface KanbanService {
  getWorkspace(): Promise<WorkspaceSnapshot>
  resetDemo(): Promise<WorkspaceSnapshot>
  createWorkspace(input: CreateWorkspaceInput): Promise<WorkspaceSnapshot>
  createBoard(name: string): Promise<WorkspaceSnapshot>
  deleteBoard(boardId: string): Promise<WorkspaceSnapshot>
  addColumn(boardId: string, name: string): Promise<WorkspaceSnapshot>
  renameColumn(columnId: string, name: string): Promise<WorkspaceSnapshot>
  reorderColumns(boardId: string, orderedColumnIds: string[]): Promise<WorkspaceSnapshot>
  deleteColumn(input: DeleteColumnInput): Promise<WorkspaceSnapshot>
  createLabel(input: CreateLabelInput): Promise<WorkspaceSnapshot>
  renameLabel(labelId: string, name: string): Promise<WorkspaceSnapshot>
  deleteLabel(labelId: string): Promise<WorkspaceSnapshot>
  createTask(input: CreateTaskInput): Promise<WorkspaceSnapshot>
  updateTask(taskId: string, input: UpdateTaskInput): Promise<WorkspaceSnapshot>
  deleteTask(taskId: string): Promise<WorkspaceSnapshot>
  moveTask(input: MoveTaskInput): Promise<WorkspaceSnapshot>
  archiveTask(taskId: string): Promise<WorkspaceSnapshot>
  restoreTask(taskId: string): Promise<WorkspaceSnapshot>
  addChecklistItem(taskId: string, text: string): Promise<WorkspaceSnapshot>
  updateChecklistItem(taskId: string, itemId: string, input: Partial<Pick<ChecklistItem, 'text' | 'completed'>>): Promise<WorkspaceSnapshot>
  deleteChecklistItem(taskId: string, itemId: string): Promise<WorkspaceSnapshot>
  addComment(taskId: string, body: string): Promise<WorkspaceSnapshot>
  toggleReaction(taskId: string, commentId: string, reaction: string): Promise<WorkspaceSnapshot>
  addAttachment(taskId: string, file: { name: string; size: number; contentType: string }): Promise<WorkspaceSnapshot>
  removeAttachment(taskId: string, attachmentId: string): Promise<WorkspaceSnapshot>
  inviteMember(email: string): Promise<WorkspaceSnapshot>
  acceptInvitation(invitationId: string): Promise<WorkspaceSnapshot>
  markNotificationRead(notificationId: string): Promise<WorkspaceSnapshot>
}

export class ServiceError extends Error {
  constructor(public readonly code: string, message: string) {
    super(message)
    this.name = 'ServiceError'
  }
}
