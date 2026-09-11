import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import { MOCK_STORAGE_KEY } from './services'

const mockService = vi.hoisted(() => ({ value: undefined as any }))

vi.mock('./services', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./services')>()
  mockService.value = new actual.MockKanbanService()
  return { ...actual, kanbanService: mockService.value }
})

describe('App', () => {
  beforeEach(async () => { window.localStorage.clear(); await mockService.value.resetDemo(); vi.restoreAllMocks() })

  it('renders seeded boards and navigates without losing mock state', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'Product launch' })).toBeInTheDocument()
    const user = userEvent.setup()
    vi.spyOn(window, 'prompt').mockReturnValue('A new demo task')
    await user.click(screen.getByRole('button', { name: 'Add task to To Do' }))
    await waitFor(() => expect(screen.getByText('A new demo task')).toBeInTheDocument())
    await user.click(screen.getByRole('button', { name: 'About' }))
    expect(screen.getByRole('heading', { name: 'Make space for better work.' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /Back to workspace/ }))
    expect(await screen.findByText('A new demo task')).toBeInTheDocument()
    expect(window.localStorage.getItem(MOCK_STORAGE_KEY)).toBeTruthy()
  })

  it('filters tasks by priority and clears the filter', async () => {
    render(<App />)
    await screen.findByRole('heading', { name: 'Product launch' })
    const user = userEvent.setup()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Filter by priority' }), 'Urgent')
    expect(screen.getByText('Build the board interactions')).toBeInTheDocument()
    expect(screen.queryByText('Shape the launch narrative')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(screen.getByText('Shape the launch narrative')).toBeInTheDocument()
  })

  it('creates a workspace with members through the service boundary', async () => {
    render(<App />)
    await screen.findByRole('heading', { name: 'Product launch' })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Create workspace' }))
    await user.clear(screen.getByRole('textbox', { name: 'Workspace name' }))
    await user.type(screen.getByRole('textbox', { name: 'Workspace name' }), 'Design crew')
    await user.type(screen.getByRole('textbox', { name: 'Member email' }), 'alex@example.com')
    await user.click(screen.getByRole('button', { name: 'Add' }))
    await user.click(screen.getAllByRole('button', { name: 'Create workspace' }).at(-1)!)
    expect(await screen.findByText('Design crew')).toBeInTheDocument()
    expect(screen.getByText('2 members · Personal demo')).toBeInTheDocument()
  })
})
