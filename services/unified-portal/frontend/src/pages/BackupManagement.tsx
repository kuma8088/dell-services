import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Database, Play, Clock, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { backupAPI } from '@/lib/api'

export default function BackupManagement() {
  const queryClient = useQueryClient()

  // Query: Backup stats
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['backup-stats'],
    queryFn: backupAPI.getStats,
    refetchInterval: 60000, // Refresh every 60 seconds
  })

  // Query: Mailserver backups
  const { data: mailserverBackups } = useQuery({
    queryKey: ['mailserver-backups'],
    queryFn: backupAPI.listMailserverBackups,
    refetchInterval: 60000,
  })

  // Query: Blog backups
  const { data: blogBackups } = useQuery({
    queryKey: ['blog-backups'],
    queryFn: backupAPI.listBlogBackups,
    refetchInterval: 60000,
  })

  // Query: Backup schedule
  const { data: schedule } = useQuery({
    queryKey: ['backup-schedule'],
    queryFn: backupAPI.getSchedule,
    refetchInterval: 300000, // Refresh every 5 minutes
  })

  // Merge all backups for history display
  const allBackups = [
    ...(mailserverBackups?.daily || []).map(b => ({ ...b, id: `daily-${b.date}` })),
    ...(mailserverBackups?.weekly || []).map(b => ({ ...b, id: `weekly-${b.date}` })),
    ...(blogBackups?.backups || []).map(b => ({ ...b, id: `blog-${b.date}` }))
  ].sort((a, b) => b.date.localeCompare(a.date))

  const handleBackup = (type: string) => {
    console.log(`Running backup for:`, type)
    // TODO: Implement API call for manual backup execution
  }

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ['backup-stats'] })
    queryClient.invalidateQueries({ queryKey: ['mailserver-backups'] })
    queryClient.invalidateQueries({ queryKey: ['blog-backups'] })
    queryClient.invalidateQueries({ queryKey: ['backup-schedule'] })
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2 text-primary" />
          <p className="text-muted-foreground">バックアップ情報を読み込み中...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="h-8 w-8 mx-auto mb-2 text-red-600" />
          <p className="text-red-600">バックアップ情報の取得に失敗しました</p>
          <p className="text-sm text-muted-foreground mt-1">
            {error instanceof Error ? error.message : '不明なエラー'}
          </p>
        </div>
      </div>
    )
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

      {/* Backup statistics */}
      <div className="grid gap-6 sm:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">総バックアップ数</CardTitle>
            <Database className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_backups || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Mailserver: {stats?.mailserver_backups || 0} | Blog: {stats?.blog_backups || 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">総容量</CardTitle>
            <Database className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_size_gb?.toFixed(2) || 0} GB</div>
            <p className="text-xs text-muted-foreground mt-1">
              バックアップストレージ使用量
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">最終バックアップ</CardTitle>
            <Clock className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.last_backup_time || 'unknown'}</div>
            <p className="text-xs text-muted-foreground mt-1">
              最後の実行日時
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">操作</CardTitle>
            <RefreshCw className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <Button className="w-full" variant="outline" onClick={handleRefresh}>
              <RefreshCw className="h-4 w-4 mr-2" />
              更新
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Backup actions */}
      <div className="grid gap-6 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Mailserverバックアップ</CardTitle>
            <CardDescription>
              スケジュール: {schedule?.mailserver_daily || 'Daily at 03:00 AM'}
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
              自動バックアップは未設定（手動実行のみ）
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

      {/* Backup schedule */}
      <Card>
        <CardHeader>
          <CardTitle>バックアップスケジュール</CardTitle>
          <CardDescription>
            自動バックアップの実行スケジュール
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Mailserver 日次バックアップ:</span>
              <span className="text-sm text-muted-foreground">{schedule?.mailserver_daily || 'Daily at 03:00 AM'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Mailserver 週次バックアップ:</span>
              <span className="text-sm text-muted-foreground">{schedule?.mailserver_weekly || 'Sunday at 02:00 AM'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">S3 レプリケーション:</span>
              <span className="text-sm text-muted-foreground">{schedule?.s3_replication || 'Daily at 04:00 AM'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">マルウェアスキャン:</span>
              <span className="text-sm text-muted-foreground">{schedule?.malware_scan || 'Daily at 05:00 AM'}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Backup history */}
      <Card>
        <CardHeader>
          <CardTitle>バックアップ履歴</CardTitle>
          <CardDescription>
            過去のバックアップ実行履歴（全{allBackups.length}件）
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {allBackups.slice(0, 10).map((backup) => (
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
                      {backup.date}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm font-medium">{backup.size_mb.toFixed(2)} MB</p>
                    <div className="flex items-center gap-1 text-sm text-green-600 dark:text-green-400">
                      <CheckCircle className="h-4 w-4" />
                      成功
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
