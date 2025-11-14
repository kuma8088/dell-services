import { useState } from 'react'
import { useMutation, useQueryClient } from '@tantml:react-query'
import { X, Loader2, AlertCircle, CheckCircle2, Shield } from 'lucide-react'
import { adminUserAPI, type AdminUserCreate } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface CreateAdminUserModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function CreateAdminUserModal({
  isOpen,
  onClose,
}: CreateAdminUserModalProps) {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<AdminUserCreate>({
    username: '',
    email: '',
    password: '',
    is_superuser: false,
  })
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [success, setSuccess] = useState(false)

  // Mutation: Create user
  const createMutation = useMutation({
    mutationFn: (data: AdminUserCreate) => adminUserAPI.createUser(data),
    onSuccess: () => {
      setSuccess(true)
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      setTimeout(() => {
        handleClose()
      }, 2000)
    },
    onError: (error: Error) => {
      setErrors({ submit: error.message })
    },
  })

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    // Username validation
    if (!formData.username) {
      newErrors.username = 'ユーザー名は必須です'
    } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
      newErrors.username = '英数字、ハイフン、アンダースコアのみ使用可能です'
    } else if (formData.username.length < 3) {
      newErrors.username = 'ユーザー名は3文字以上である必要があります'
    }

    // Email validation
    if (!formData.email) {
      newErrors.email = 'メールアドレスは必須です'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = '有効なメールアドレスを入力してください'
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = 'パスワードは必須です'
    } else if (formData.password.length < 8) {
      newErrors.password = 'パスワードは8文字以上である必要があります'
    } else if (!/[A-Z]/.test(formData.password)) {
      newErrors.password = 'パスワードに大文字を含めてください'
    } else if (!/[a-z]/.test(formData.password)) {
      newErrors.password = 'パスワードに小文字を含めてください'
    } else if (!/[0-9]/.test(formData.password)) {
      newErrors.password = 'パスワードに数字を含めてください'
    }

    // Confirm password validation
    if (!confirmPassword) {
      newErrors.confirmPassword = 'パスワード確認は必須です'
    } else if (formData.password !== confirmPassword) {
      newErrors.confirmPassword = 'パスワードが一致しません'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validateForm()) {
      createMutation.mutate(formData)
    }
  }

  const handleClose = () => {
    setFormData({
      username: '',
      email: '',
      password: '',
      is_superuser: false,
    })
    setConfirmPassword('')
    setErrors({})
    setSuccess(false)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
            新規管理ユーザー作成
          </h3>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            disabled={createMutation.isPending}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* Success message */}
          {success && (
            <Alert className="bg-green-50 border-green-200">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription className="text-green-800">
                ユーザーが正常に作成されました
              </AlertDescription>
            </Alert>
          )}

          {/* Error message */}
          {errors.submit && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{errors.submit}</AlertDescription>
            </Alert>
          )}

          {/* Username */}
          <div className="space-y-2">
            <Label htmlFor="username">
              ユーザー名 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="username"
              value={formData.username}
              onChange={(e) =>
                setFormData({ ...formData, username: e.target.value })
              }
              placeholder="admin_user"
              disabled={createMutation.isPending}
              className={errors.username ? 'border-red-500' : ''}
            />
            {errors.username && (
              <p className="text-sm text-red-600">{errors.username}</p>
            )}
            <p className="text-sm text-gray-500">
              ログイン時に使用するユーザー名（英数字・ハイフン・アンダースコア）
            </p>
          </div>

          {/* Email */}
          <div className="space-y-2">
            <Label htmlFor="email">
              メールアドレス <span className="text-red-500">*</span>
            </Label>
            <Input
              id="email"
              type="email"
              value={formData.email}
              onChange={(e) =>
                setFormData({ ...formData, email: e.target.value })
              }
              placeholder="admin@example.com"
              disabled={createMutation.isPending}
              className={errors.email ? 'border-red-500' : ''}
            />
            {errors.email && (
              <p className="text-sm text-red-600">{errors.email}</p>
            )}
            <p className="text-sm text-gray-500">
              パスワードリセット通知などに使用されます
            </p>
          </div>

          {/* Password */}
          <div className="space-y-2">
            <Label htmlFor="password">
              パスワード <span className="text-red-500">*</span>
            </Label>
            <Input
              id="password"
              type="password"
              value={formData.password}
              onChange={(e) =>
                setFormData({ ...formData, password: e.target.value })
              }
              placeholder="8文字以上（大文字・小文字・数字を含む）"
              disabled={createMutation.isPending}
              className={errors.password ? 'border-red-500' : ''}
            />
            {errors.password && (
              <p className="text-sm text-red-600">{errors.password}</p>
            )}
          </div>

          {/* Confirm Password */}
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">
              パスワード確認 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="パスワードを再入力"
              disabled={createMutation.isPending}
              className={errors.confirmPassword ? 'border-red-500' : ''}
            />
            {errors.confirmPassword && (
              <p className="text-sm text-red-600">{errors.confirmPassword}</p>
            )}
          </div>

          {/* Superuser checkbox */}
          <div className="flex items-start gap-3 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <Checkbox
              id="is_superuser"
              checked={formData.is_superuser}
              onCheckedChange={(checked) =>
                setFormData({ ...formData, is_superuser: checked as boolean })
              }
              disabled={createMutation.isPending}
            />
            <div className="flex-1">
              <label
                htmlFor="is_superuser"
                className="text-sm font-medium text-amber-900 cursor-pointer flex items-center gap-2"
              >
                <Shield className="h-4 w-4" />
                スーパーユーザー権限を付与
              </label>
              <p className="text-xs text-amber-700 mt-1">
                スーパーユーザーは全ての管理機能にアクセスでき、他のユーザーを管理できます
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={handleClose}
              disabled={createMutation.isPending}
            >
              キャンセル
            </Button>
            <Button
              type="submit"
              disabled={createMutation.isPending || success}
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  作成中...
                </>
              ) : success ? (
                '作成完了'
              ) : (
                'ユーザーを作成'
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
