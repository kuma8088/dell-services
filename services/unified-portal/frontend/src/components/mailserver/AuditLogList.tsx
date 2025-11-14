/**
 * AuditLogList Component
 *
 * Displays audit logs for mailserver operations
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { auditLogAPI } from '@/lib/api/mailserver'
import type { AuditLog } from '@/types/mailserver'

interface AuditLogListProps {
  limit?: number
  refreshTrigger?: number
}

export function AuditLogList({ limit = 50, refreshTrigger = 0 }: AuditLogListProps) {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState({
    action_type: '',
    target_type: '',
  })

  useEffect(() => {
    loadLogs()
  }, [refreshTrigger, filter])

  const loadLogs = async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await auditLogAPI.list({
        action_type: filter.action_type || undefined,
        target_type: filter.target_type || undefined,
        limit,
      })

      setLogs(response.logs)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit logs')
      console.error('Failed to load audit logs:', err)
    } finally {
      setLoading(false)
    }
  }

  const getActionBadgeColor = (action: string) => {
    switch (action.toLowerCase()) {
      case 'create':
        return 'bg-green-100 text-green-700'
      case 'update':
        return 'bg-blue-100 text-blue-700'
      case 'delete':
        return 'bg-red-100 text-red-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  const getTargetBadgeColor = (target: string) => {
    switch (target.toLowerCase()) {
      case 'user':
        return 'bg-purple-100 text-purple-700'
      case 'domain':
        return 'bg-indigo-100 text-indigo-700'
      default:
        return 'bg-gray-100 text-gray-700'
    }
  }

  if (loading && logs.length === 0) {
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
            <Button onClick={loadLogs} variant="outline" size="sm">
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
        <CardTitle>監査ログ</CardTitle>
        <CardDescription>
          Mailserver操作履歴: {logs.length}件表示
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Filter Controls */}
        <div className="flex gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium mb-2">操作種別</label>
            <select
              value={filter.action_type}
              onChange={(e) =>
                setFilter({ ...filter, action_type: e.target.value })
              }
              className="px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">すべて</option>
              <option value="create">作成</option>
              <option value="update">更新</option>
              <option value="delete">削除</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">対象種別</label>
            <select
              value={filter.target_type}
              onChange={(e) =>
                setFilter({ ...filter, target_type: e.target.value })
              }
              className="px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">すべて</option>
              <option value="user">ユーザー</option>
              <option value="domain">ドメイン</option>
            </select>
          </div>

          <div className="flex items-end">
            <Button
              onClick={() => setFilter({ action_type: '', target_type: '' })}
              variant="outline"
              size="sm"
            >
              フィルタクリア
            </Button>
          </div>
        </div>

        {/* Logs Table */}
        {logs.length === 0 ? (
          <p className="text-center text-muted-foreground py-8">
            ログが記録されていません
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-3">日時</th>
                  <th className="text-left p-3">操作</th>
                  <th className="text-left p-3">対象</th>
                  <th className="text-left p-3">対象ID</th>
                  <th className="text-left p-3">IPアドレス</th>
                  <th className="text-left p-3">変更内容</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b hover:bg-muted/50">
                    <td className="p-3 text-sm">
                      {new Date(log.created_at).toLocaleString('ja-JP')}
                    </td>
                    <td className="p-3">
                      <span
                        className={`text-xs px-2 py-1 rounded ${getActionBadgeColor(
                          log.action_type
                        )}`}
                      >
                        {log.action_type}
                      </span>
                    </td>
                    <td className="p-3">
                      <span
                        className={`text-xs px-2 py-1 rounded ${getTargetBadgeColor(
                          log.target_type
                        )}`}
                      >
                        {log.target_type}
                      </span>
                    </td>
                    <td className="p-3 text-sm text-muted-foreground">
                      {log.target_id || '-'}
                    </td>
                    <td className="p-3 text-sm text-muted-foreground">
                      {log.ip_address || '-'}
                    </td>
                    <td className="p-3 text-sm">
                      {log.changes ? (
                        <details className="cursor-pointer">
                          <summary className="text-primary hover:underline">
                            詳細
                          </summary>
                          <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-x-auto">
                            {log.changes}
                          </pre>
                        </details>
                      ) : (
                        '-'
                      )}
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
