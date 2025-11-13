import { useQuery } from '@tanstack/react-query'
import { Database, Play, Clock, CheckCircle, AlertCircle } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'

// Mock data - Replace with actual API calls
const mockBackupHistory = [
  {
    id: 1,
    type: 'mailserver',
    status: 'success',
    timestamp: '2025-11-13 03:00:00',
    size: '2.1 GB',
  },
  {
    id: 2,
    type: 'blog',
    status: 'success',
    timestamp: '2025-11-13 03:15:00',
    size: '95.4 GB',
  },
  {
    id: 3,
    type: 'mailserver',
    status: 'success',
    timestamp: '2025-11-12 03:00:00',
    size: '2.0 GB',
  },
]

export default function BackupManagement() {
  const { data: backupHistory } = useQuery({
    queryKey: ['backup-history'],
    queryFn: async () => {
      // const response = await fetch('/api/v1/backup/history')
      // return response.json()
      return mockBackupHistory
    },
  })

  const handleBackup = (type: string) => {
    console.log(`Running backup for:`, type)
    // TODO: Implement API call
  }

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
          バックアップ管理
        </h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          バックアップの実行と履歴を確認できます
        </p>
      </div>

      {/* Backup actions */}
      <div className="grid gap-6 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Mailserverバックアップ</CardTitle>
            <CardDescription>
              最終バックアップ: 2時間前（成功）
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              className="w-full"
              onClick={() => handleBackup('mailserver')}
            >
              <Play className="h-4 w-4 mr-2" />
              今すぐバックアップ実行
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Blog Systemバックアップ</CardTitle>
            <CardDescription>
              最終バックアップ: 2時間前（成功）
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full" onClick={() => handleBackup('blog')}>
              <Play className="h-4 w-4 mr-2" />
              今すぐバックアップ実行
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Backup history */}
      <Card>
        <CardHeader>
          <CardTitle>バックアップ履歴</CardTitle>
          <CardDescription>
            過去のバックアップ実行履歴
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {backupHistory?.map((backup) => (
              <div
                key={backup.id}
                className="flex items-center justify-between p-4 border rounded-lg"
              >
                <div className="flex items-center gap-4">
                  <Database className="h-6 w-6 text-primary" />
                  <div>
                    <h3 className="font-semibold capitalize">{backup.type}</h3>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Clock className="h-4 w-4" />
                      {backup.timestamp}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm font-medium">{backup.size}</p>
                    <div
                      className={`flex items-center gap-1 text-sm ${
                        backup.status === 'success'
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}
                    >
                      {backup.status === 'success' ? (
                        <>
                          <CheckCircle className="h-4 w-4" />
                          成功
                        </>
                      ) : (
                        <>
                          <AlertCircle className="h-4 w-4" />
                          失敗
                        </>
                      )}
                    </div>
                  </div>

                  <Button size="sm" variant="outline">
                    リストア
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
