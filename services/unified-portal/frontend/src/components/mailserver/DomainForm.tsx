/**
 * DomainForm Component
 *
 * Form for creating/editing mail domains
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { mailDomainAPI } from '@/lib/api/mailserver'
import type { MailDomain, MailDomainCreate, MailDomainUpdate } from '@/types/mailserver'

interface DomainFormProps {
  domain?: MailDomain | null
  onSuccess?: (domain: MailDomain) => void
  onCancel?: () => void
}

export function DomainForm({ domain, onSuccess, onCancel }: DomainFormProps) {
  const [formData, setFormData] = useState({
    domain_name: '',
    is_active: true,
    max_users: '',
    max_quota: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (domain) {
      setFormData({
        domain_name: domain.domain_name,
        is_active: domain.is_active,
        max_users: domain.max_users !== null ? domain.max_users.toString() : '',
        max_quota: domain.max_quota !== null
          ? Math.round(domain.max_quota / 1024 / 1024).toString()
          : '',
      })
    }
  }, [domain])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const data: MailDomainCreate | MailDomainUpdate = {
        domain_name: formData.domain_name,
        is_active: formData.is_active,
        max_users: formData.max_users ? parseInt(formData.max_users) : null,
        max_quota: formData.max_quota
          ? parseInt(formData.max_quota) * 1024 * 1024
          : null,
      }

      let result: MailDomain
      if (domain) {
        result = await mailDomainAPI.update(domain.id, data)
      } else {
        result = await mailDomainAPI.create(data as MailDomainCreate)
      }

      if (onSuccess) onSuccess(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Operation failed')
      console.error('Domain form submission failed:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>{domain ? 'ドメイン編集' : 'ドメイン新規作成'}</CardTitle>
        <CardDescription>
          メールドメインの{domain ? '情報を編集' : '新規作成'}します
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
              ドメイン名 <span className="text-destructive">*</span>
            </label>
            <input
              type="text"
              value={formData.domain_name}
              onChange={(e) =>
                setFormData({ ...formData, domain_name: e.target.value })
              }
              placeholder="example.com"
              required
              disabled={!!domain}
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            />
            {domain && (
              <p className="text-xs text-muted-foreground mt-1">
                ドメイン名は編集できません
              </p>
            )}
          </div>

          <div>
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
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              最大ユーザー数（オプション）
            </label>
            <input
              type="number"
              value={formData.max_users}
              onChange={(e) =>
                setFormData({ ...formData, max_users: e.target.value })
              }
              placeholder="無制限"
              min="1"
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              最大容量（MB、オプション）
            </label>
            <input
              type="number"
              value={formData.max_quota}
              onChange={(e) =>
                setFormData({ ...formData, max_quota: e.target.value })
              }
              placeholder="無制限"
              min="1"
              className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="flex gap-2 pt-4">
            <Button type="submit" disabled={loading}>
              {loading ? '処理中...' : domain ? '更新' : '作成'}
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
