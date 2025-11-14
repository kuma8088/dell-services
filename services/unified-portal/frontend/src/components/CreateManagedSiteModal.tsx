import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X, Loader2, AlertCircle, CheckCircle2 } from 'lucide-react'
import { managedSitesAPI, type ManagedSiteCreate } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface CreateManagedSiteModalProps {
  isOpen: boolean
  onClose: () => void
}

export default function CreateManagedSiteModal({
  isOpen,
  onClose,
}: CreateManagedSiteModalProps) {
  const queryClient = useQueryClient()
  const [formData, setFormData] = useState<ManagedSiteCreate>({
    site_name: '',
    domain: '',
    database_name: '',
    php_version: '8.2',
  })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [success, setSuccess] = useState(false)

  // Mutation: Create site
  const createMutation = useMutation({
    mutationFn: (data: ManagedSiteCreate) => managedSitesAPI.createSite(data),
    onSuccess: () => {
      setSuccess(true)
      queryClient.invalidateQueries({ queryKey: ['managed-sites'] })
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

    // Site name validation
    if (!formData.site_name) {
      newErrors.site_name = 'サイト名は必須です'
    } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.site_name)) {
      newErrors.site_name = '英数字、ハイフン、アンダースコアのみ使用可能です'
    }

    // Domain validation
    if (!formData.domain) {
      newErrors.domain = 'ドメインは必須です'
    } else if (!/^[a-zA-Z0-9.-]+$/.test(formData.domain)) {
      newErrors.domain = '有効なドメイン名を入力してください'
    }

    // Database name validation (optional)
    if (formData.database_name && !/^[a-zA-Z0-9_]+$/.test(formData.database_name)) {
      newErrors.database_name = '英数字とアンダースコアのみ使用可能です'
    }

    // PHP version validation
    if (!formData.php_version) {
      newErrors.php_version = 'PHPバージョンは必須です'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validateForm()) {
      // Remove empty database_name if not provided
      const submitData = { ...formData }
      if (!submitData.database_name) {
        delete submitData.database_name
      }
      createMutation.mutate(submitData)
    }
  }

  const handleClose = () => {
    setFormData({
      site_name: '',
      domain: '',
      database_name: '',
      php_version: '8.2',
    })
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
            新規WordPressサイト作成
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
                サイトが正常に作成されました
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

          {/* Site name */}
          <div className="space-y-2">
            <Label htmlFor="site_name">
              サイト名 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="site_name"
              value={formData.site_name}
              onChange={(e) =>
                setFormData({ ...formData, site_name: e.target.value })
              }
              placeholder="my-wordpress-site"
              disabled={createMutation.isPending}
              className={errors.site_name ? 'border-red-500' : ''}
            />
            {errors.site_name && (
              <p className="text-sm text-red-600">{errors.site_name}</p>
            )}
            <p className="text-sm text-gray-500">
              英数字、ハイフン、アンダースコアのみ使用可能
            </p>
          </div>

          {/* Domain */}
          <div className="space-y-2">
            <Label htmlFor="domain">
              ドメイン <span className="text-red-500">*</span>
            </Label>
            <Input
              id="domain"
              value={formData.domain}
              onChange={(e) =>
                setFormData({ ...formData, domain: e.target.value })
              }
              placeholder="example.com"
              disabled={createMutation.isPending}
              className={errors.domain ? 'border-red-500' : ''}
            />
            {errors.domain && (
              <p className="text-sm text-red-600">{errors.domain}</p>
            )}
            <p className="text-sm text-gray-500">
              サイトにアクセスするためのドメイン名
            </p>
          </div>

          {/* Database name */}
          <div className="space-y-2">
            <Label htmlFor="database_name">データベース名（オプション）</Label>
            <Input
              id="database_name"
              value={formData.database_name}
              onChange={(e) =>
                setFormData({ ...formData, database_name: e.target.value })
              }
              placeholder="wp_database (空欄の場合は自動生成)"
              disabled={createMutation.isPending}
              className={errors.database_name ? 'border-red-500' : ''}
            />
            {errors.database_name && (
              <p className="text-sm text-red-600">{errors.database_name}</p>
            )}
            <p className="text-sm text-gray-500">
              空欄の場合はサイト名から自動生成されます
            </p>
          </div>

          {/* PHP version */}
          <div className="space-y-2">
            <Label htmlFor="php_version">
              PHPバージョン <span className="text-red-500">*</span>
            </Label>
            <Select
              value={formData.php_version}
              onValueChange={(value) =>
                setFormData({ ...formData, php_version: value })
              }
              disabled={createMutation.isPending}
            >
              <SelectTrigger className={errors.php_version ? 'border-red-500' : ''}>
                <SelectValue placeholder="PHPバージョンを選択" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="8.3">PHP 8.3</SelectItem>
                <SelectItem value="8.2">PHP 8.2 (推奨)</SelectItem>
                <SelectItem value="8.1">PHP 8.1</SelectItem>
                <SelectItem value="8.0">PHP 8.0</SelectItem>
                <SelectItem value="7.4">PHP 7.4</SelectItem>
              </SelectContent>
            </Select>
            {errors.php_version && (
              <p className="text-sm text-red-600">{errors.php_version}</p>
            )}
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
                'サイトを作成'
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
