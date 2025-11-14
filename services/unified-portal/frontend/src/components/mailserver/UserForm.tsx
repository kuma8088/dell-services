/**
 * UserForm Component
 *
 * Form for creating/editing mail users
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { mailUserAPI, mailDomainAPI } from '@/lib/api/mailserver'
import type { MailUser, MailUserCreate, MailUserUpdate, MailDomain } from '@/types/mailserver'

interface UserFormProps {
  user?: MailUser | null
  preselectedDomainId?: number | null
  onSuccess?: (user: MailUser) => void
  onCancel?: () => void
}

export function UserForm({
  user,
  preselectedDomainId = null,
  onSuccess,
  onCancel,
}: UserFormProps) {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    domain_id: preselectedDomainId?.toString() || '',
    quota: '1024',
    is_active: true,
    is_admin: false,
  })
  const [domains, setDomains] = useState<MailDomain[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDomains()
  }, [])

  useEffect(() => {
    if (user) {
      setFormData({
        email: user.email,
        password: '',
        domain_id: user.domain_id.toString(),
        quota: Math.round(user.quota / 1024 / 1024).toString(),
        is_active: user.is_active,
        is_admin: user.is_admin,
      })
    } else if (preselectedDomainId !== null) {
      setFormData((prev) => ({
        ...prev,
        domain_id: preselectedDomainId.toString(),
      }))
    }
  }, [user, preselectedDomainId])

  const loadDomains = async () => {
    try {
      const response = await mailDomainAPI.list(0, 100)
      setDomains(response.domains.filter((d) => d.is_active))
    } catch (err) {
      console.error('Failed to load domains:', err)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      let result: MailUser

      if (user) {
        // Update existing user
        const data: MailUserUpdate = {
          quota: parseInt(formData.quota) * 1024 * 1024,
          is_active: formData.is_active,
          is_admin: formData.is_admin,
        }

        if (formData.password) {
          data.password = formData.password
        }

        result = await mailUserAPI.update(user.id, data)
      } else {
        // Create new user
        const data: MailUserCreate = {
          email: formData.email,
          password: formData.password,
          domain_id: parseInt(formData.domain_id),
          quota: parseInt(formData.quota) * 1024 * 1024,
          is_active: formData.is_active,
          is_admin: formData.is_admin,
        }

        result = await mailUserAPI.create(data)
      }

      if (onSuccess) onSuccess(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operation failed')
      console.error('User form submission failed:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{user ? 'ユーザー編集' : 'ユーザー新規作成'}</CardTitle>
        <CardDescription>
          メールユーザーの{user ? '情報を編集' : '新規作成'}します
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-destructive/10 text-destructive px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-2">
              ドメイン <span className="text-destructive">*</span>
            </label>
            <select
              value={formData.domain_id}
              onChange={(e) =>
                setFormData({ ...formData, domain_id: e.target.value })
              }
              required
              disabled={!!user}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">ドメインを選択</option>
              {domains.map((domain) => (
                <option key={domain.id} value={domain.id}>
                  {domain.domain_name}
                </option>
              ))}
            </select>
            {user && (
              <p className="text-xs text-muted-foreground mt-1">
                ドメインは変更できません
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              メールアドレス <span className="text-destructive">*</span>
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={
                  user
                    ? formData.email
                    : formData.email.split('@')[0] || formData.email
                }
                onChange={(e) => {
                  const localPart = e.target.value
                  const domain = domains.find(
                    (d) => d.id === parseInt(formData.domain_id)
                  )
                  setFormData({
                    ...formData,
                    email: domain ? `${localPart}@${domain.domain_name}` : localPart,
                  })
                }}
                placeholder="username"
                required
                disabled={!!user}
                className="flex-1 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              />
              {!user && formData.domain_id && (
                <span className="flex items-center px-3 py-2 bg-muted rounded-md text-sm">
                  @{domains.find((d) => d.id === parseInt(formData.domain_id))?.domain_name}
                </span>
              )}
            </div>
            {user && (
              <p className="text-xs text-muted-foreground mt-1">
                メールアドレスは変更できません
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              パスワード {user && '（変更する場合のみ入力）'}
              {!user && <span className="text-destructive"> *</span>}
            </label>
            <input
              type="password"
              value={formData.password}
              onChange={(e) =>
                setFormData({ ...formData, password: e.target.value })
              }
              placeholder={user ? '変更しない場合は空欄' : '8文字以上'}
              required={!user}
              minLength={8}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              容量（MB） <span className="text-destructive">*</span>
            </label>
            <input
              type="number"
              value={formData.quota}
              onChange={(e) =>
                setFormData({ ...formData, quota: e.target.value })
              }
              placeholder="1024"
              required
              min="1"
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="space-y-2">
            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={formData.is_active}
                onChange={(e) =>
                  setFormData({ ...formData, is_active: e.target.checked })
                }
                className="rounded border-gray-300"
              />
              <span className="text-sm font-medium">有効</span>
            </label>

            <label className="flex items-center space-x-2">
              <input
                type="checkbox"
                checked={formData.is_admin}
                onChange={(e) =>
                  setFormData({ ...formData, is_admin: e.target.checked })
                }
                className="rounded border-gray-300"
              />
              <span className="text-sm font-medium">管理者権限</span>
            </label>
          </div>

          <div className="flex gap-2 pt-4">
            <Button type="submit" disabled={loading}>
              {loading ? '処理中...' : user ? '更新' : '作成'}
            </Button>
            {onCancel && (
              <Button type="button" variant="outline" onClick={onCancel}>
                キャンセル
              </Button>
            )}
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
