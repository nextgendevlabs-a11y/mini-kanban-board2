export type Role = 'owner' | 'member'
export type Priority = 'Low' | 'Medium' | 'High' | 'Urgent'

export interface User {
  id: string
  name: string
  email: string
  role: Role
  initials: string
  color: string
}

export interface Label {
  id: string
  boardId: string
  name: string
  color: string
}

export interface ChecklistItem {
  id: string
  text: string
  completed: boolean
  order: number
}

export interface Comment {
  id: string
  taskId: string
  authorId: string
  body: string
  mentionedUserIds: string[]
  reactions: Record<string, string[]>
  createdAt: string
}

export interface Attachment {
  id: string
  taskId: string
  name: string
  size: number
  contentType: string
  createdAt: string
}

export interface ActivityEntry {
  id: string
  taskId: string
  actorId: string
  action: string
  createdAt: string
}

export interface Task {
  id: string
  boardId: string
  columnId: string
  title: string
  description: string
  assigneeId?: string
  dueDate?: string
  priority?: Priority
  labelIds: string[]
  blocked: boolean
  archived: boolean
  archivedFromColumnId?: string
  order: number
  checklist: ChecklistItem[]
  comments: Comment[]
  attachments: Attachment[]
  activity: ActivityEntry[]
}

export interface Column {
  id: string
  boardId: string
  name: string
  order: number
}

export interface Board {
  id: string
  teamId: string
  name: string
  columnIds: string[]
  labelIds: string[]
}

export interface Invitation {
  id: string
  teamId: string
  email: string
  createdAt: string
  accepted: boolean
}

export interface Notification {
  id: string
  recipientId: string
  taskId: string
  boardId: string
  authorId: string
  body: string
  read: boolean
  createdAt: string
}

export interface WorkspaceSnapshot {
  version: 1
  team: { id: string; name: string; currentUserId: string; memberIds: string[]; boardIds: string[] }
  users: Record<string, User>
  boards: Record<string, Board>
  columns: Record<string, Column>
  labels: Record<string, Label>
  tasks: Record<string, Task>
  invitations: Record<string, Invitation>
  notifications: Record<string, Notification>
}
