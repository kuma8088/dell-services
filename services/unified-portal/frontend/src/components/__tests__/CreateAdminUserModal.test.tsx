import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render } from '@/test/test-utils'
import CreateAdminUserModal from '../CreateAdminUserModal'

describe('CreateAdminUserModal', () => {
  const mockOnClose = vi.fn()
  const mockOnSuccess = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders modal when open', () => {
    render(
      <CreateAdminUserModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    )

    expect(screen.getByText('新規管理ユーザー作成')).toBeInTheDocument()
    expect(screen.getByLabelText('ユーザー名')).toBeInTheDocument()
    expect(screen.getByLabelText('メールアドレス')).toBeInTheDocument()
    expect(screen.getByLabelText('パスワード')).toBeInTheDocument()
    expect(screen.getByLabelText('パスワード確認')).toBeInTheDocument()
  })

  it('does not render when closed', () => {
    render(
      <CreateAdminUserModal
        isOpen={false}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    )

    expect(screen.queryByText('新規管理ユーザー作成')).not.toBeInTheDocument()
  })

  it('validates username format', async () => {
    const user = userEvent.setup()

    render(
      <CreateAdminUserModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    )

    const usernameInput = screen.getByLabelText('ユーザー名')
    await user.type(usernameInput, 'ab')
    await user.tab()

    await waitFor(() => {
      expect(screen.getByText('ユーザー名は3文字以上である必要があります')).toBeInTheDocument()
    })
  })

  it('validates email format', async () => {
    const user = userEvent.setup()

    render(
      <CreateAdminUserModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    )

    const emailInput = screen.getByLabelText('メールアドレス')
    await user.type(emailInput, 'invalid-email')
    await user.tab()

    await waitFor(() => {
      expect(screen.getByText('有効なメールアドレスを入力してください')).toBeInTheDocument()
    })
  })

  it('validates password strength - minimum length', async () => {
    const user = userEvent.setup()

    render(
      <CreateAdminUserModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    )

    const passwordInput = screen.getByLabelText('パスワード')
    await user.type(passwordInput, 'short')
    await user.tab()

    await waitFor(() => {
      expect(screen.getByText('パスワードは8文字以上である必要があります')).toBeInTheDocument()
    })
  })

  it('validates password strength - uppercase requirement', async () => {
    const user = userEvent.setup()

    render(
      <CreateAdminUserModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    )

    const passwordInput = screen.getByLabelText('パスワード')
    await user.type(passwordInput, 'lowercase123')
    await user.tab()

    await waitFor(() => {
      expect(screen.getByText('パスワードに大文字を含めてください')).toBeInTheDocument()
    })
  })

  it('validates password strength - number requirement', async () => {
    const user = userEvent.setup()

    render(
      <CreateAdminUserModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    )

    const passwordInput = screen.getByLabelText('パスワード')
    await user.type(passwordInput, 'Lowercase')
    await user.tab()

    await waitFor(() => {
      expect(screen.getByText('パスワードに数字を含めてください')).toBeInTheDocument()
    })
  })

  it('validates password confirmation match', async () => {
    const user = userEvent.setup()

    render(
      <CreateAdminUserModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    )

    const passwordInput = screen.getByLabelText('パスワード')
    const confirmPasswordInput = screen.getByLabelText('パスワード確認')

    await user.type(passwordInput, 'Password123')
    await user.type(confirmPasswordInput, 'DifferentPassword123')
    await user.tab()

    await waitFor(() => {
      expect(screen.getByText('パスワードが一致しません')).toBeInTheDocument()
    })
  })

  it('closes modal when cancel button clicked', async () => {
    const user = userEvent.setup()

    render(
      <CreateAdminUserModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    )

    const cancelButton = screen.getByRole('button', { name: 'キャンセル' })
    await user.click(cancelButton)

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  it('closes modal when X button clicked', async () => {
    const user = userEvent.setup()

    render(
      <CreateAdminUserModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    )

    const closeButtons = screen.getAllByRole('button')
    const xButton = closeButtons.find(btn => btn.querySelector('svg'))

    if (xButton) {
      await user.click(xButton)
      expect(mockOnClose).toHaveBeenCalled()
    }
  })

  it('enables create button when form is valid', async () => {
    const user = userEvent.setup()

    render(
      <CreateAdminUserModal
        isOpen={true}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    )

    await user.type(screen.getByLabelText('ユーザー名'), 'testuser')
    await user.type(screen.getByLabelText('メールアドレス'), 'test@example.com')
    await user.type(screen.getByLabelText('パスワード'), 'Password123')
    await user.type(screen.getByLabelText('パスワード確認'), 'Password123')

    const createButton = screen.getByRole('button', { name: '作成' })
    expect(createButton).not.toBeDisabled()
  })
})
