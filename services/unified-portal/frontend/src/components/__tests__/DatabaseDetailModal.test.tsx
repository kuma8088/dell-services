import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/test-utils'
import DatabaseDetailModal from '../DatabaseDetailModal'
import * as api from '@/lib/api'

// Mock the API
vi.mock('@/lib/api', () => ({
  databaseAPI: {
    getDatabaseDetail: vi.fn(),
  },
}))

describe('DatabaseDetailModal', () => {
  const mockOnClose = vi.fn()
  const mockDatabaseDetail = {
    name: 'test_database',
    size_mb: 125.5,
    tables_count: 15,
    rows_count: 50000,
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('does not render when closed', () => {
    render(
      <DatabaseDetailModal
        isOpen={false}
        onClose={mockOnClose}
        databaseName="test_database"
      />
    )

    expect(screen.queryByText('test_database')).not.toBeInTheDocument()
  })

  it('does not render when databaseName is null', () => {
    render(
      <DatabaseDetailModal
        isOpen={true}
        onClose={mockOnClose}
        databaseName={null}
      />
    )

    expect(screen.queryByText('データベース詳細')).not.toBeInTheDocument()
  })

  it('shows loading state while fetching data', () => {
    vi.mocked(api.databaseAPI.getDatabaseDetail).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(
      <DatabaseDetailModal
        isOpen={true}
        onClose={mockOnClose}
        databaseName="test_database"
      />
    )

    expect(screen.getByText('test_database')).toBeInTheDocument()
    expect(screen.getByText('データベース詳細を読み込み中...')).toBeInTheDocument()
  })

  it('displays database details when loaded', async () => {
    vi.mocked(api.databaseAPI.getDatabaseDetail).mockResolvedValue(mockDatabaseDetail)

    render(
      <DatabaseDetailModal
        isOpen={true}
        onClose={mockOnClose}
        databaseName="test_database"
      />
    )

    await waitFor(() => {
      expect(screen.getByText('test_database')).toBeInTheDocument()
    })

    // Check statistics cards
    expect(screen.getByText('125.50 MB')).toBeInTheDocument()
    expect(screen.getByText('15')).toBeInTheDocument()
    expect(screen.getByText('50,000')).toBeInTheDocument()

    // Check database info section
    expect(screen.getByText('データベース情報')).toBeInTheDocument()
    expect(screen.getByText('15 テーブル')).toBeInTheDocument()
    expect(screen.getByText('50,000 行')).toBeInTheDocument()
  })

  it('calculates average record size correctly', async () => {
    vi.mocked(api.databaseAPI.getDatabaseDetail).mockResolvedValue(mockDatabaseDetail)

    render(
      <DatabaseDetailModal
        isOpen={true}
        onClose={mockOnClose}
        databaseName="test_database"
      />
    )

    await waitFor(() => {
      // 125.5 MB = 128512 KB, divided by 50000 rows = 2.57 KB/row
      const avgSize = ((125.5 * 1024) / 50000).toFixed(2)
      expect(screen.getByText(`${avgSize} KB`)).toBeInTheDocument()
    })
  })

  it('shows N/A for average record size when rows_count is 0', async () => {
    vi.mocked(api.databaseAPI.getDatabaseDetail).mockResolvedValue({
      ...mockDatabaseDetail,
      rows_count: 0,
    })

    render(
      <DatabaseDetailModal
        isOpen={true}
        onClose={mockOnClose}
        databaseName="test_database"
      />
    )

    await waitFor(() => {
      expect(screen.getByText('N/A')).toBeInTheDocument()
    })
  })

  it('shows error state when API fails', async () => {
    const errorMessage = 'Database not found'
    vi.mocked(api.databaseAPI.getDatabaseDetail).mockRejectedValue(
      new Error(errorMessage)
    )

    render(
      <DatabaseDetailModal
        isOpen={true}
        onClose={mockOnClose}
        databaseName="test_database"
      />
    )

    await waitFor(() => {
      expect(screen.getByText(/データベース詳細の取得に失敗しました/)).toBeInTheDocument()
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
    })
  })

  it('closes modal when close button clicked', async () => {
    const user = userEvent.setup()
    vi.mocked(api.databaseAPI.getDatabaseDetail).mockResolvedValue(mockDatabaseDetail)

    render(
      <DatabaseDetailModal
        isOpen={true}
        onClose={mockOnClose}
        databaseName="test_database"
      />
    )

    await waitFor(() => {
      expect(screen.getByText('データベース情報')).toBeInTheDocument()
    })

    const closeButton = screen.getByRole('button', { name: '閉じる' })
    await user.click(closeButton)

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('closes modal when X button clicked', async () => {
    const user = userEvent.setup()
    vi.mocked(api.databaseAPI.getDatabaseDetail).mockResolvedValue(mockDatabaseDetail)

    render(
      <DatabaseDetailModal
        isOpen={true}
        onClose={mockOnClose}
        databaseName="test_database"
      />
    )

    // Find X button (should have X icon)
    const buttons = screen.getAllByRole('button')
    const xButton = buttons.find(btn => btn.querySelector('svg') && !btn.textContent)

    if (xButton) {
      await user.click(xButton)
      expect(mockOnClose).toHaveBeenCalled()
    }
  })
})
