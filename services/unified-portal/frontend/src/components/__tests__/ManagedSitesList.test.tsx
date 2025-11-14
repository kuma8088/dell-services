import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/test-utils'
import ManagedSitesList from '../ManagedSitesList'
import * as api from '@/lib/api'

// Mock the API
vi.mock('@/lib/api', () => ({
  managedSitesAPI: {
    listSites: vi.fn(),
    deleteSite: vi.fn(),
    clearCache: vi.fn(),
  },
}))

describe('ManagedSitesList', () => {
  const mockSites = [
    {
      id: 1,
      site_name: 'test-site-1',
      domain: 'test1.example.com',
      database_name: 'test1_db',
      php_version: '8.3',
      enabled: true,
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-01-02T00:00:00Z',
    },
    {
      id: 2,
      site_name: 'test-site-2',
      domain: 'test2.example.com',
      database_name: 'test2_db',
      php_version: '8.2',
      enabled: false,
      created_at: '2025-01-03T00:00:00Z',
      updated_at: '2025-01-04T00:00:00Z',
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state while fetching sites', () => {
    vi.mocked(api.managedSitesAPI.listSites).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    )

    render(<ManagedSitesList searchQuery="" />)

    expect(screen.getByText('管理サイト一覧を読み込み中...')).toBeInTheDocument()
  })

  it('displays list of managed sites', async () => {
    vi.mocked(api.managedSitesAPI.listSites).mockResolvedValue(mockSites)

    render(<ManagedSitesList searchQuery="" />)

    await waitFor(() => {
      expect(screen.getByText('test-site-1')).toBeInTheDocument()
      expect(screen.getByText('test-site-2')).toBeInTheDocument()
      expect(screen.getByText('test1.example.com')).toBeInTheDocument()
      expect(screen.getByText('test2.example.com')).toBeInTheDocument()
    })
  })

  it('shows enabled/disabled badges correctly', async () => {
    vi.mocked(api.managedSitesAPI.listSites).mockResolvedValue(mockSites)

    render(<ManagedSitesList searchQuery="" />)

    await waitFor(() => {
      const badges = screen.getAllByText(/有効|無効/)
      expect(badges).toHaveLength(2)
      expect(screen.getByText('有効')).toBeInTheDocument()
      expect(screen.getByText('無効')).toBeInTheDocument()
    })
  })

  it('filters sites by search query', async () => {
    vi.mocked(api.managedSitesAPI.listSites).mockResolvedValue(mockSites)

    const { rerender } = render(<ManagedSitesList searchQuery="" />)

    await waitFor(() => {
      expect(screen.getByText('test-site-1')).toBeInTheDocument()
      expect(screen.getByText('test-site-2')).toBeInTheDocument()
    })

    // Filter to only show test-site-1
    rerender(<ManagedSitesList searchQuery="test-site-1" />)

    expect(screen.getByText('test-site-1')).toBeInTheDocument()
    expect(screen.queryByText('test-site-2')).not.toBeInTheDocument()
  })

  it('shows empty state when no sites match search', async () => {
    vi.mocked(api.managedSitesAPI.listSites).mockResolvedValue(mockSites)

    render(<ManagedSitesList searchQuery="nonexistent" />)

    await waitFor(() => {
      expect(screen.getByText('管理サイトが見つかりません')).toBeInTheDocument()
    })
  })

  it('shows empty state when no sites exist', async () => {
    vi.mocked(api.managedSitesAPI.listSites).mockResolvedValue([])

    render(<ManagedSitesList searchQuery="" />)

    await waitFor(() => {
      expect(screen.getByText('管理サイトが見つかりません')).toBeInTheDocument()
      expect(screen.getByText('新規サイト作成ボタンから最初のサイトを作成してください。')).toBeInTheDocument()
    })
  })

  it('shows error state when API fails', async () => {
    const errorMessage = 'Failed to fetch sites'
    vi.mocked(api.managedSitesAPI.listSites).mockRejectedValue(
      new Error(errorMessage)
    )

    render(<ManagedSitesList searchQuery="" />)

    await waitFor(() => {
      expect(screen.getByText(/管理サイト一覧の取得に失敗しました/)).toBeInTheDocument()
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
    })
  })

  it('displays PHP version for each site', async () => {
    vi.mocked(api.managedSitesAPI.listSites).mockResolvedValue(mockSites)

    render(<ManagedSitesList searchQuery="" />)

    await waitFor(() => {
      expect(screen.getByText('PHP 8.3')).toBeInTheDocument()
      expect(screen.getByText('PHP 8.2')).toBeInTheDocument()
    })
  })

  it('shows action buttons for each site', async () => {
    vi.mocked(api.managedSitesAPI.listSites).mockResolvedValue(mockSites)

    render(<ManagedSitesList searchQuery="" />)

    await waitFor(() => {
      // Each site should have edit, delete, and cache clear buttons
      const deleteButtons = screen.getAllByTitle('削除')
      expect(deleteButtons).toHaveLength(2)
    })
  })
})
