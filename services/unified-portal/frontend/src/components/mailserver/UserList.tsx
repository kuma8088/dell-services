/**
 * UserList Component
 *
 * Displays a list of mail users with actions
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { mailUserAPI } from '@/lib/api/mailserver'
import type { MailUser } from '@/types/mailserver'

interface UserListProps {
  domainId?: number | null
  onEdit?: (user: MailUser) => void
  onDelete?: (user: MailUser) => void
  refreshTrigger?: number
}

export function UserList({
  domainId = null,
  onEdit,
  onDelete,
  refreshTrigger = 0,
}: UserListProps) {
  const [users, setUsers] = useState<MailUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadUsers()
  }, [domainId, refreshTrigger])

  const loadUsers = async () => {
    try {
      setLoading(true)
      setError(null)

      const response =
        domainId !== null
          ? await mailUserAPI.listByDomain(domainId, 0, 100)
          : await mailUserAPI.list(0, 100)

      setUsers(response.users)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users')
      console.error('Failed to load users:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (user: MailUser) => {
    if (!confirm(`本当にユーザー「${user.email}」を削除しますか？`)) {
      return
    }

    try {
      await mailUserAPI.delete(user.id)
      await loadUsers()
      if (onDelete) onDelete(user)
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
            <Button onClick={loadUsers} variant="outline" size="sm">
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
        <CardTitle>メールユーザー一覧</CardTitle>
        <CardDescription>
          登録済みメールユーザー: {users.length}件
        </CardDescription>
      </CardHeader>
      <CardContent>
        {users.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">
            ユーザーが登録されていません
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-3">メールアドレス</th>
                  <th className="text-left p-3">ドメイン</th>
                  <th className="text-left p-3">容量</th>
                  <th className="text-left p-3">権限</th>
                  <th className="text-left p-3">ステータス</th>
                  <th className="text-left p-3">作成日</th>
                  <th className="text-right p-3">操作</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-b hover:bg-muted/50">
                    <td className="p-3">
                      <span className="font-medium">{user.email}</span>
                    </td>
                    <td className="p-3 text-sm text-muted-foreground">
                      {user.domain_name}
                    </td>
                    <td className="p-3 text-sm">
                      {Math.round(user.quota / 1024 / 1024)} MB
                    </td>
                    <td className="p-3">
                      <span
                        className={`text-xs px-2 py-1 rounded ${
                          user.is_admin
                            ? 'bg-purple-100 text-purple-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {user.is_admin ? '管理者' : '一般'}
                      </span>
                    </td>
                    <td className="p-3">
                      <span
                        className={`text-xs px-2 py-1 rounded ${
                          user.is_active
                            ? 'bg-green-100 text-green-700'
                            : 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {user.is_active ? '有効' : '無効'}
                      </span>
                    </td>
                    <td className="p-3 text-sm text-muted-foreground">
                      {new Date(user.created_at).toLocaleDateString('ja-JP')}
                    </td>
                    <td className="p-3 text-right">
                      <div className="flex gap-2 justify-end">
                        {onEdit && (
                          <Button
                            onClick={() => onEdit(user)}
                            variant="outline"
                            size="sm"
                          >
                            編集
                          </Button>
                        )}
                        {onDelete && (
                          <Button
                            onClick={() => handleDelete(user)}
                            variant="destructive"
                            size="sm"
                          >
                            削除
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
