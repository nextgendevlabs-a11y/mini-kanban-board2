import { createMockKanbanService } from './mockKanbanService'

// The UI imports this one boundary. Swap this factory for an HTTP adapter in production.
export const kanbanService = createMockKanbanService()
export { MockKanbanService, MOCK_STORAGE_KEY } from './mockKanbanService'
export { ServiceError } from './contracts'
export type * from './contracts'
