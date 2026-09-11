import type { ActivityEntry, Board, ChecklistItem, Comment, Column, Label, Task, User, WorkspaceSnapshot } from '../domain'
import type { CreateTaskInput, DeleteColumnInput, KanbanService, MoveTaskInput, UpdateTaskInput } from './contracts'
import { ServiceError } from './contracts'

const STORAGE_KEY = 'modern-mini-kanban:workspace:v1'
const reactionSet = ['👍', '❤️', '🎉', '👀']
const now = () => new Date().toISOString()
const id = (prefix: string) => `${prefix}-${Math.random().toString(36).slice(2, 9)}`

function activity(taskId: string, actorId: string, action: string): ActivityEntry {
  return { id: id('activity'), taskId, actorId, action, createdAt: now() }
}

function seed(): WorkspaceSnapshot {
  const users: Record<string, User> = {
    u1: { id: 'u1', name: 'Maya Chen', email: 'maya@flowdeck.demo', role: 'owner', initials: 'MC', color: '#ff7a59' },
    u2: { id: 'u2', name: 'Noah Williams', email: 'noah@flowdeck.demo', role: 'member', initials: 'NW', color: '#5b8def' },
    u3: { id: 'u3', name: 'Priya Shah', email: 'priya@flowdeck.demo', role: 'member', initials: 'PS', color: '#7b61ff' },
    u4: { id: 'u4', name: 'Leo Martin', email: 'leo@flowdeck.demo', role: 'member', initials: 'LM', color: '#13b981' },
  }
  const boards: Record<string, Board> = {
    b1: { id: 'b1', teamId: 'team-1', name: 'Product launch', columnIds: ['c1', 'c2', 'c3'], labelIds: ['l1', 'l2', 'l3'] },
    b2: { id: 'b2', teamId: 'team-1', name: 'Marketing campaigns', columnIds: ['c4', 'c5', 'c6'], labelIds: ['l4', 'l5'] },
    b3: { id: 'b3', teamId: 'team-1', name: 'Operations', columnIds: ['c7', 'c8', 'c9'], labelIds: [] },
  }
  const columns: Record<string, Column> = {
    c1: { id: 'c1', boardId: 'b1', name: 'To Do', order: 0 }, c2: { id: 'c2', boardId: 'b1', name: 'In Progress', order: 1 }, c3: { id: 'c3', boardId: 'b1', name: 'Done', order: 2 },
    c4: { id: 'c4', boardId: 'b2', name: 'To Do', order: 0 }, c5: { id: 'c5', boardId: 'b2', name: 'In Progress', order: 1 }, c6: { id: 'c6', boardId: 'b2', name: 'Done', order: 2 },
    c7: { id: 'c7', boardId: 'b3', name: 'To Do', order: 0 }, c8: { id: 'c8', boardId: 'b3', name: 'In Progress', order: 1 }, c9: { id: 'c9', boardId: 'b3', name: 'Done', order: 2 },
  }
  const labels: Record<string, Label> = {
    l1: { id: 'l1', boardId: 'b1', name: 'Design', color: '#f3a712' }, l2: { id: 'l2', boardId: 'b1', name: 'Frontend', color: '#5b8def' }, l3: { id: 'l3', boardId: 'b1', name: 'Launch', color: '#13b981' },
    l4: { id: 'l4', boardId: 'b2', name: 'Content', color: '#7b61ff' }, l5: { id: 'l5', boardId: 'b2', name: 'Growth', color: '#ff7a59' },
  }
  const task = (taskId: string, boardId: string, columnId: string, title: string, order: number, extra: Partial<Task> = {}): Task => ({ id: taskId, boardId, columnId, title, description: '', labelIds: [], blocked: false, archived: false, order, checklist: [], comments: [], attachments: [], activity: [activity(taskId, 'u1', 'created this task')], ...extra })
  const tasks: Record<string, Task> = {
    t1: task('t1', 'b1', 'c1', 'Shape the launch narrative', 0, { assigneeId: 'u3', priority: 'High', labelIds: ['l1', 'l3'], description: 'Create a clear story for the first public release.', checklist: [{ id: 'ch1', text: 'Draft the opening promise', completed: true, order: 0 }, { id: 'ch2', text: 'Review with the team', completed: false, order: 1 }] }),
    t2: task('t2', 'b1', 'c1', 'Polish empty states', 1, { assigneeId: 'u2', priority: 'Medium', labelIds: ['l2'] }),
    t3: task('t3', 'b1', 'c2', 'Build the board interactions', 0, { assigneeId: 'u4', priority: 'Urgent', labelIds: ['l2'], blocked: true }),
    t4: task('t4', 'b1', 'c3', 'Choose the visual direction', 0, { assigneeId: 'u1', priority: 'Low', labelIds: ['l1'] }),
    t5: task('t5', 'b2', 'c4', 'Outline campaign themes', 0, { assigneeId: 'u3', priority: 'Medium', labelIds: ['l4'] }),
  }
  return { version: 1, team: { id: 'team-1', name: 'Flowdeck Studio', currentUserId: 'u1', memberIds: Object.keys(users), boardIds: Object.keys(boards) }, users, boards, columns, labels, tasks, invitations: {}, notifications: {} }
}

export class MockKanbanService implements KanbanService {
  private snapshot: WorkspaceSnapshot

  constructor(private readonly storage: Storage | undefined = typeof window === 'undefined' ? undefined : window.localStorage) {
    this.snapshot = this.read() ?? seed()
    this.persist()
  }

  private read() { try { const raw = this.storage?.getItem(STORAGE_KEY); return raw ? JSON.parse(raw) as WorkspaceSnapshot : undefined } catch { return undefined } }
  private persist() { this.storage?.setItem(STORAGE_KEY, JSON.stringify(this.snapshot)) }
  private clone() { return structuredClone(this.snapshot) }
  private finish() { this.persist(); return this.clone() }
  private currentUser() { return this.snapshot.users[this.snapshot.team.currentUserId] }
  private requireOwner() { if (this.currentUser().role !== 'owner') throw new ServiceError('FORBIDDEN', 'Only the team owner can perform this action.') }
  private task(taskId: string) { const task = this.snapshot.tasks[taskId]; if (!task) throw new ServiceError('NOT_FOUND', 'Task not found.'); return task }
  private board(boardId: string) { const board = this.snapshot.boards[boardId]; if (!board) throw new ServiceError('NOT_FOUND', 'Board not found.'); return board }
  private addActivity(task: Task, action: string) { task.activity.push(activity(task.id, this.snapshot.team.currentUserId, action)) }
  private reorderTasks(columnId: string) { Object.values(this.snapshot.tasks).filter(t => t.columnId === columnId && !t.archived).sort((a, b) => a.order - b.order).forEach((t, index) => { t.order = index }) }

  async getWorkspace() { return this.clone() }
  async resetDemo() { this.snapshot = seed(); return this.finish() }
  async createWorkspace(input: { name: string; memberEmails: string[] }) {
    const workspaceName = input.name.trim()
    if (!workspaceName) throw new ServiceError('VALIDATION', 'Workspace name is required.')
    const emails = [...new Set(input.memberEmails.map(email => email.trim().toLowerCase()).filter(Boolean))]
    if (emails.some(email => !email.includes('@'))) throw new ServiceError('VALIDATION', 'Every member must have a valid email address.')
    const owner = this.snapshot.users[this.snapshot.team.currentUserId]
    const users: Record<string, User> = { [owner.id]: { ...owner, role: 'owner' } }
    const colors = ['#5b8def', '#7b61ff', '#13b981', '#f3a712', '#ff7a59']
    emails.forEach((email, index) => {
      const name = email.split('@')[0].replace(/[._-]+/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase())
      const initials = name.split(' ').map(part => part[0]).join('').slice(0, 2).toUpperCase()
      const userId = id('user')
      users[userId] = { id: userId, name, email, role: 'member', initials: initials || 'M', color: colors[index % colors.length] }
    })
    const teamId = id('team')
    const boardId = id('board')
    const columns: Record<string, Column> = {}
    const columnIds = ['To Do', 'In Progress', 'Done'].map((name, order) => { const columnId = id('column'); columns[columnId] = { id: columnId, boardId, name, order }; return columnId })
    this.snapshot = { version: 1, team: { id: teamId, name: workspaceName, currentUserId: owner.id, memberIds: Object.keys(users), boardIds: [boardId] }, users, boards: { [boardId]: { id: boardId, teamId, name: 'Getting started', columnIds, labelIds: [] } }, columns, labels: {}, tasks: {}, invitations: {}, notifications: {} }
    return this.finish()
  }
  async createBoard(name: string) { this.requireOwner(); const trimmed = name.trim(); if (!trimmed) throw new ServiceError('VALIDATION', 'Board name is required.'); const boardId = id('board'); const columnIds = ['To Do', 'In Progress', 'Done'].map((name, order) => { const columnId = id('column'); this.snapshot.columns[columnId] = { id: columnId, boardId, name, order }; return columnId }); this.snapshot.boards[boardId] = { id: boardId, teamId: this.snapshot.team.id, name: trimmed, columnIds, labelIds: [] }; this.snapshot.team.boardIds.push(boardId); return this.finish() }
  async deleteBoard(boardId: string) { this.requireOwner(); this.board(boardId); if (this.snapshot.team.boardIds.length === 1) throw new ServiceError('VALIDATION', 'A team must retain at least one board.'); delete this.snapshot.boards[boardId]; this.snapshot.team.boardIds = this.snapshot.team.boardIds.filter(id => id !== boardId); Object.keys(this.snapshot.columns).filter(id => this.snapshot.columns[id].boardId === boardId).forEach(id => delete this.snapshot.columns[id]); Object.keys(this.snapshot.tasks).filter(id => this.snapshot.tasks[id].boardId === boardId).forEach(id => delete this.snapshot.tasks[id]); return this.finish() }
  async addColumn(boardId: string, name: string) { const board = this.board(boardId); const trimmed = name.trim(); if (!trimmed) throw new ServiceError('VALIDATION', 'Column name is required.'); const columnId = id('column'); this.snapshot.columns[columnId] = { id: columnId, boardId, name: trimmed, order: board.columnIds.length }; board.columnIds.push(columnId); return this.finish() }
  async renameColumn(columnId: string, name: string) { const column = this.snapshot.columns[columnId]; if (!column) throw new ServiceError('NOT_FOUND', 'Column not found.'); const trimmed = name.trim(); if (!trimmed) throw new ServiceError('VALIDATION', 'Column name is required.'); column.name = trimmed; return this.finish() }
  async reorderColumns(boardId: string, orderedColumnIds: string[]) { const board = this.board(boardId); if (orderedColumnIds.length !== board.columnIds.length || orderedColumnIds.some(id => !board.columnIds.includes(id))) throw new ServiceError('VALIDATION', 'Invalid column order.'); board.columnIds = orderedColumnIds; orderedColumnIds.forEach((columnId, order) => { this.snapshot.columns[columnId].order = order }); return this.finish() }
  async deleteColumn(input: DeleteColumnInput) { const column = this.snapshot.columns[input.columnId]; if (!column) throw new ServiceError('NOT_FOUND', 'Column not found.'); const board = this.board(column.boardId); if (board.columnIds.length === 1) throw new ServiceError('VALIDATION', 'A board must retain at least one column.'); const active = Object.values(this.snapshot.tasks).filter(task => task.columnId === column.id && !task.archived); if (active.length && (!input.destinationColumnId || input.destinationColumnId === column.id || !board.columnIds.includes(input.destinationColumnId))) throw new ServiceError('DESTINATION_REQUIRED', 'Choose a destination column for active tasks.'); if (input.destinationColumnId) { active.forEach((task, index) => { task.columnId = input.destinationColumnId!; task.order = index; this.addActivity(task, `moved from ${column.name}`) }) } board.columnIds = board.columnIds.filter(id => id !== column.id); delete this.snapshot.columns[column.id]; return this.finish() }
  async createLabel(input: { boardId: string; name: string; color: string }) { const board = this.board(input.boardId); const name = input.name.trim(); if (!name) throw new ServiceError('VALIDATION', 'Label name is required.'); if (board.labelIds.some(labelId => this.snapshot.labels[labelId].name.toLowerCase() === name.toLowerCase())) throw new ServiceError('DUPLICATE_LABEL', 'That label already exists on this board.'); const labelId = id('label'); this.snapshot.labels[labelId] = { id: labelId, boardId: board.id, name, color: input.color }; board.labelIds.push(labelId); return this.finish() }
  async renameLabel(labelId: string, name: string) { const label = this.snapshot.labels[labelId]; if (!label) throw new ServiceError('NOT_FOUND', 'Label not found.'); const trimmed = name.trim(); if (!trimmed) throw new ServiceError('VALIDATION', 'Label name is required.'); const board = this.board(label.boardId); if (board.labelIds.some(otherId => otherId !== labelId && this.snapshot.labels[otherId].name.toLowerCase() === trimmed.toLowerCase())) throw new ServiceError('DUPLICATE_LABEL', 'That label already exists on this board.'); label.name = trimmed; return this.finish() }
  async deleteLabel(labelId: string) { const label = this.snapshot.labels[labelId]; if (!label) throw new ServiceError('NOT_FOUND', 'Label not found.'); const board = this.board(label.boardId); board.labelIds = board.labelIds.filter(id => id !== labelId); Object.values(this.snapshot.tasks).filter(task => task.boardId === board.id).forEach(task => { task.labelIds = task.labelIds.filter(id => id !== labelId) }); delete this.snapshot.labels[labelId]; return this.finish() }
  async createTask(input: CreateTaskInput) { const board = this.board(input.boardId); if (!board.columnIds.includes(input.columnId)) throw new ServiceError('VALIDATION', 'Column does not belong to this board.'); const title = input.title.trim(); if (!title) throw new ServiceError('VALIDATION', 'Task title is required.'); if (input.assigneeId && !this.snapshot.team.memberIds.includes(input.assigneeId)) throw new ServiceError('VALIDATION', 'Assignee must be a team member.'); const existing = Object.values(this.snapshot.tasks).filter(t => t.columnId === input.columnId && !t.archived); const taskId = id('task'); this.snapshot.tasks[taskId] = { id: taskId, boardId: input.boardId, columnId: input.columnId, title, description: input.description ?? '', assigneeId: input.assigneeId, priority: input.priority, labelIds: [], blocked: false, archived: false, order: existing.length, checklist: [], comments: [], attachments: [], activity: [activity(taskId, this.snapshot.team.currentUserId, 'created this task')] }; return this.finish() }
  async updateTask(taskId: string, input: UpdateTaskInput) { const task = this.task(taskId); if (input.title !== undefined) { if (!input.title.trim()) throw new ServiceError('VALIDATION', 'Task title is required.'); task.title = input.title.trim() } if (input.assigneeId && !this.snapshot.team.memberIds.includes(input.assigneeId)) throw new ServiceError('VALIDATION', 'Assignee must be a team member.'); if (input.labelIds && input.labelIds.some(labelId => !this.snapshot.labels[labelId] || this.snapshot.labels[labelId].boardId !== task.boardId)) throw new ServiceError('VALIDATION', 'Labels must belong to the task board.'); const previousAssignee = task.assigneeId; const previousBlocked = task.blocked; Object.assign(task, input); if (input.assigneeId !== undefined && previousAssignee !== task.assigneeId) this.addActivity(task, 'changed the assignee'); if (input.blocked !== undefined && previousBlocked !== task.blocked) this.addActivity(task, task.blocked ? 'marked this task blocked' : 'cleared the blocked state'); return this.finish() }
  async deleteTask(taskId: string) { const task = this.task(taskId); delete this.snapshot.tasks[task.id]; this.reorderTasks(task.columnId); return this.finish() }
  async moveTask(input: MoveTaskInput) { const task = this.task(input.taskId); const destination = this.snapshot.columns[input.destinationColumnId]; if (!destination || destination.boardId !== task.boardId) throw new ServiceError('VALIDATION', 'Destination column is invalid.'); const oldColumn = this.snapshot.columns[task.columnId]; const oldColumnId = task.columnId; task.columnId = destination.id; const peers = Object.values(this.snapshot.tasks).filter(item => item.id !== task.id && item.columnId === destination.id && !item.archived).sort((a, b) => a.order - b.order); peers.splice(Math.max(0, Math.min(input.destinationIndex, peers.length)), 0, task); peers.forEach((item, index) => { item.order = index }); this.reorderTasks(oldColumnId); this.addActivity(task, `moved from ${oldColumn.name} to ${destination.name}`); return this.finish() }
  async archiveTask(taskId: string) { const task = this.task(taskId); task.archivedFromColumnId = task.columnId; task.archived = true; this.addActivity(task, 'archived this task'); this.reorderTasks(task.columnId); return this.finish() }
  async restoreTask(taskId: string) { const task = this.task(taskId); const board = this.board(task.boardId); const destination = board.columnIds.includes(task.archivedFromColumnId ?? '') ? task.archivedFromColumnId! : board.columnIds[0]; task.columnId = destination; task.archived = false; task.order = Object.values(this.snapshot.tasks).filter(item => item.columnId === destination && !item.archived).length; this.addActivity(task, 'restored this task'); return this.finish() }
  async addChecklistItem(taskId: string, text: string) { const task = this.task(taskId); const value = text.trim(); if (!value) throw new ServiceError('VALIDATION', 'Checklist text is required.'); task.checklist.push({ id: id('check'), text: value, completed: false, order: task.checklist.length }); return this.finish() }
  async updateChecklistItem(taskId: string, itemId: string, input: Partial<Pick<ChecklistItem, 'text' | 'completed'>>) { const item = this.task(taskId).checklist.find(item => item.id === itemId); if (!item) throw new ServiceError('NOT_FOUND', 'Checklist item not found.'); if (input.text !== undefined && !input.text.trim()) throw new ServiceError('VALIDATION', 'Checklist text is required.'); Object.assign(item, input); return this.finish() }
  async deleteChecklistItem(taskId: string, itemId: string) { const task = this.task(taskId); task.checklist = task.checklist.filter(item => item.id !== itemId).map((item, order) => ({ ...item, order })); return this.finish() }
  async addComment(taskId: string, body: string) { const task = this.task(taskId); const trimmed = body.trim(); if (!trimmed) throw new ServiceError('VALIDATION', 'Comment text is required.'); const mentionedUserIds = [...trimmed.matchAll(/@([\w]+)/g)].map(match => Object.values(this.snapshot.users).find(user => user.name.toLowerCase().startsWith(match[1].toLowerCase()))?.id).filter((value): value is string => Boolean(value)); const comment: Comment = { id: id('comment'), taskId, authorId: this.snapshot.team.currentUserId, body: trimmed, mentionedUserIds, reactions: {}, createdAt: now() }; task.comments.push(comment); mentionedUserIds.filter(userId => userId !== this.snapshot.team.currentUserId).forEach(recipientId => { const notificationId = id('notification'); this.snapshot.notifications[notificationId] = { id: notificationId, recipientId, taskId, boardId: task.boardId, authorId: this.snapshot.team.currentUserId, body: trimmed, read: false, createdAt: now() } }); return this.finish() }
  async toggleReaction(taskId: string, commentId: string, reaction: string) { if (!reactionSet.includes(reaction)) throw new ServiceError('VALIDATION', 'Reaction is not supported.'); const comment = this.task(taskId).comments.find(comment => comment.id === commentId); if (!comment) throw new ServiceError('NOT_FOUND', 'Comment not found.'); const users = comment.reactions[reaction] ?? []; comment.reactions[reaction] = users.includes(this.snapshot.team.currentUserId) ? users.filter(userId => userId !== this.snapshot.team.currentUserId) : [...users, this.snapshot.team.currentUserId]; return this.finish() }
  async addAttachment(taskId: string, file: { name: string; size: number; contentType: string }) { const task = this.task(taskId); if (!file.name.trim()) throw new ServiceError('VALIDATION', 'Attachment name is required.'); task.attachments.push({ id: id('attachment'), taskId, ...file, createdAt: now() }); return this.finish() }
  async removeAttachment(taskId: string, attachmentId: string) { const task = this.task(taskId); task.attachments = task.attachments.filter(attachment => attachment.id !== attachmentId); return this.finish() }
  async inviteMember(email: string) { this.requireOwner(); const normalized = email.trim().toLowerCase(); if (!normalized.includes('@')) throw new ServiceError('VALIDATION', 'Enter a valid email address.'); const invitationId = id('invite'); this.snapshot.invitations[invitationId] = { id: invitationId, teamId: this.snapshot.team.id, email: normalized, createdAt: now(), accepted: false }; return this.finish() }
  async acceptInvitation(invitationId: string) { const invitation = this.snapshot.invitations[invitationId]; if (!invitation) throw new ServiceError('NOT_FOUND', 'Invitation not found.'); invitation.accepted = true; return this.finish() }
  async markNotificationRead(notificationId: string) { const notification = this.snapshot.notifications[notificationId]; if (!notification) throw new ServiceError('NOT_FOUND', 'Notification not found.'); notification.read = true; return this.finish() }
}

export const MOCK_STORAGE_KEY = STORAGE_KEY
export const createMockKanbanService = (storage?: Storage) => new MockKanbanService(storage)
