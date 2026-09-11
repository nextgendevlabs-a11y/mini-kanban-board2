import { describe, expect, it, beforeEach } from 'vitest'
import { MOCK_STORAGE_KEY, MockKanbanService } from './mockKanbanService'

class MemoryStorage implements Storage {
  private values = new Map<string, string>()
  get length() { return this.values.size }
  clear() { this.values.clear() }
  getItem(key: string) { return this.values.get(key) ?? null }
  key(index: number) { return [...this.values.keys()][index] ?? null }
  removeItem(key: string) { this.values.delete(key) }
  setItem(key: string, value: string) { this.values.set(key, value) }
}

describe('MockKanbanService', () => {
  let storage: MemoryStorage
  let service: MockKanbanService

  beforeEach(() => { storage = new MemoryStorage(); service = new MockKanbanService(storage) })

  it('seeds a playable workspace and persists mutations', async () => {
    const initial = await service.getWorkspace()
    expect(initial.team.boardIds).toHaveLength(3)
    expect(initial.boards.b1.columnIds.map(id => initial.columns[id].name)).toEqual(['To Do', 'In Progress', 'Done'])

    await service.createTask({ boardId: 'b1', columnId: 'c1', title: 'Persist me' })
    const reloaded = new MockKanbanService(storage)
    expect(Object.values(await reloaded.getWorkspace()).length).toBeGreaterThan(0)
    expect(Object.values((await reloaded.getWorkspace()).tasks).some(task => task.title === 'Persist me')).toBe(true)
    expect(storage.getItem(MOCK_STORAGE_KEY)).toBeTruthy()
  })

  it('moves tasks and preserves order', async () => {
    await service.moveTask({ taskId: 't2', destinationColumnId: 'c2', destinationIndex: 0 })
    const snapshot = await service.getWorkspace()
    expect(snapshot.tasks.t2.columnId).toBe('c2')
    expect(snapshot.tasks.t2.order).toBe(0)
    expect(snapshot.tasks.t3.order).toBe(1)
  })

  it('requires a destination before deleting a non-empty column', async () => {
    await expect(service.deleteColumn({ columnId: 'c1' })).rejects.toMatchObject({ code: 'DESTINATION_REQUIRED' })
    let snapshot = await service.deleteColumn({ columnId: 'c1', destinationColumnId: 'c2' })
    expect(snapshot.columns.c1).toBeUndefined()
    expect(snapshot.tasks.t1.columnId).toBe('c2')
    expect(snapshot.tasks.t2.columnId).toBe('c2')
  })

  it('restores into the first available column when the original was deleted', async () => {
    await service.archiveTask('t1')
    await service.deleteColumn({ columnId: 'c1', destinationColumnId: 'c2' })
    const snapshot = await service.restoreTask('t1')
    expect(snapshot.tasks.t1.archived).toBe(false)
    expect(snapshot.tasks.t1.columnId).toBe('c2')
  })

  it('creates a notification only for a valid mentioned member', async () => {
    await service.addComment('t1', 'Can you review this, @Noah? @Nobody')
    const snapshot = await service.getWorkspace()
    const notifications = Object.values(snapshot.notifications)
    expect(notifications).toHaveLength(1)
    expect(notifications[0].recipientId).toBe('u2')
    expect(notifications[0].read).toBe(false)
  })

  it('keeps labels scoped to their board and rejects duplicates', async () => {
    await expect(service.createLabel({ boardId: 'b1', name: 'Design', color: '#fff' })).rejects.toMatchObject({ code: 'DUPLICATE_LABEL' })
    const snapshot = await service.createLabel({ boardId: 'b2', name: 'Design', color: '#fff' })
    expect(snapshot.boards.b2.labelIds.some(labelId => snapshot.labels[labelId].name === 'Design')).toBe(true)
    expect(snapshot.boards.b1.labelIds).toEqual(['l1', 'l2', 'l3'])
  })
})
