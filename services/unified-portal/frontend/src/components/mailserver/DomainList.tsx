/**
 * DomainList Component
 *
 * Displays a list of mail domains with actions
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { mailDomainAPI } from '@/lib/api/mailserver'
import type { MailDomain } from '@/types/mailserver'

interface DomainListProps {
  onEdit?: (domain: MailDomain) => void
  onDelete?: (domain: MailDomain) => void
  onCreateUser?: (domain: MailDomain) => void
  refreshTrigger?: number
}

export function DomainList({
  onEdit,
  onDelete,
  onCreateUser,
  refreshTrigger = 0,
}: DomainListProps) {
  const [domains, setDomains] = useState<MailDomain[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDomains()
  }, [refreshTrigger])

  const loadDomains = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await mailDomainAPI.list(0, 100)
      setDomains(response.domains)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load domains')
      console.error('Failed to load domains:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (domain: MailDomain) => {
    if (!confirm(`本当にドメイン「${domain.domain_name}」を削除しますか？`)) {
      return
    }

    try {
      await mailDomainAPI.delete(domain.id)
      await loadDomains()
      if (onDelete) onDelete(domain)
    } catch (err) {
      alert(`削除に失敗しました: ${err instanceof Error ? err.message : 'Unknown error'}`)
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-center text-muted-foreground">読み込み中...</p>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-center text-destructive">エラー: {error}</p>
          <div className="mt-4 text-center">
            <Button onClick={loadDomains} variant="outline" size="sm">
              再読み込み
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>メールドメイン一覧</CardTitle>
        <CardDescription>
          登録済みメールドメイン: {domains.length}件
        </CardDescription>
      </CardHeader>
      <CardContent>
        {domains.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">
            ドメインが登録されていません
          </p>
        ) : (
          <div className="space-y-4">
            {domains.map((domain) => (
              <div
                key={domain.id}
                className="flex items-center justify-between border rounded-lg p-4"
              >
                <div className="flex-1">
                  <h4 className="font-semibold text-lg">{domain.domain_name}</h4>
                  <div className="flex gap-4 mt-2 text-sm text-muted-foreground">
                    <span>
                      ステータス:{' '}
                      <span
                        className={
                          domain.is_active ? 'text-green-600' : 'text-gray-500'
                        }
                      >
                        {domain.is_active ? '有効' : '無効'}
                      </span>
                    </span>
                    {domain.max_users !== null && (
                      <span>最大ユーザー数: {domain.max_users}</span>
                    )}
                    {domain.max_quota !== null && (
                      <span>
                        最大容量: {Math.round(domain.max_quota / 1024 / 1024)} MB
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    作成日: {new Date(domain.created_at).toLocaleString('ja-JP')}
                  </p>
                </div>
                <div className="flex gap-2">
                  {onCreateUser && (
                    <Button
                      onClick={() => onCreateUser(domain)}
                      variant="outline"
                      size="sm"
                    >
                      ユーザー追加
                    </Button>
                  )}
                  {onEdit && (
                    <Button
                      onClick={() => onEdit(domain)}
                      variant="outline"
                      size="sm"
                    >
                      編集
                    </Button>
                  )}
                  {onDelete && (
                    <Button
                      onClick={() => handleDelete(domain)}
                      variant="destructive"
                      size="sm"
                    >
                      削除
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
