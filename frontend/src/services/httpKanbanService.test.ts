import { beforeEach, describe, expect, it, vi } from 'vitest'
import { HttpKanbanService } from './httpKanbanService'

const snapshot = { version: 1 } as never

describe('HttpKanbanService', () => {
  beforeEach(() => vi.restoreAllMocks())

  it('maps service operations to the backend API', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(snapshot), { status: 200 }))
    const service = new HttpKanbanService('http://localhost:8000/api/v1')

    await service.createTask({ boardId: 'b1', columnId: 'c1', title: 'Ship it' })
    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/api/v1/tasks', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ boardId: 'b1', columnId: 'c1', title: 'Ship it' }),
    })
  })

  it('preserves structured backend errors as ServiceError values', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ code: 'DUPLICATE_LABEL', message: 'That label already exists.' }), { status: 409 }))
    const service = new HttpKanbanService('http://localhost:8000/api/v1')

    await expect(service.createLabel({ boardId: 'b1', name: 'Design', color: '#fff' })).rejects.toMatchObject({
      name: 'ServiceError',
      code: 'DUPLICATE_LABEL',
      message: 'That label already exists.',
    })
  })

  it('reports a recoverable error when the backend cannot be reached', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))
    const service = new HttpKanbanService()

    await expect(service.getWorkspace()).rejects.toMatchObject({
      name: 'ServiceError',
      code: 'NETWORK',
    })
  })
})
