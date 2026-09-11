import { createHttpKanbanService } from './httpKanbanService'

// The UI imports this one boundary so the transport can change without leaking into components.
export const kanbanService = createHttpKanbanService()
export { HttpKanbanService, DEFAULT_API_BASE_URL, createHttpKanbanService } from './httpKanbanService'
export { MockKanbanService, MOCK_STORAGE_KEY } from './mockKanbanService'
export { ServiceError } from './contracts'
export type * from './contracts'
