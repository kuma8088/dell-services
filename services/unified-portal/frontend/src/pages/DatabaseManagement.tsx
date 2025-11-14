import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Database, Plus, Trash2, RefreshCw, Download, Upload, Search, AlertCircle, Info } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { databaseAPI } from '@/lib/api'
import DatabaseDetailModal from '@/components/DatabaseDetailModal'

export default function DatabaseManagement() {
  const [selectedDb, setSelectedDb] = useState<string | null>(null)
  const [showDetailModal, setShowDetailModal] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const queryClient = useQueryClient()

  // Query: Database status
  const { data: status } = useQuery({
    queryKey: ['database-status'],
    queryFn: databaseAPI.getStatus,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Query: List databases
  const { data: databases, isLoading, error } = useQuery({
    queryKey: ['databases'],
    queryFn: databaseAPI.listDatabases,
    refetchInterval: 30000,
  })

  // Query: Database stats
  const { data: stats } = useQuery({
    queryKey: ['database-stats'],
    queryFn: databaseAPI.getStats,
    refetchInterval: 30000,
  })

  const filteredDatabases = databases?.filter((db) =>
    db.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleAction = (action: string, dbName?: string) => {
    if (action === 'refresh') {
      queryClient.invalidateQueries({ queryKey: ['database-status'] })
      queryClient.invalidateQueries({ queryKey: ['databases'] })
      queryClient.invalidateQueries({ queryKey: ['database-stats'] })
    } else {
      console.log(`${action}:`, dbName || 'all')
      // TODO: Implement other API calls
    }
  }

  const handleDatabaseClick = (dbName: string) => {
    setSelectedDb(dbName)
    setShowDetailModal(true)
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2 text-primary" />
          <p className="text-muted-foreground">データベース一覧を読み込み中...</p>
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
          <p className="text-red-600">データベース一覧の取得に失敗しました</p>
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
        <div className="flex items-center gap-3">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
            データベース管理
          </h2>
          {status && (
            <Badge variant={status.connected ? 'default' : 'destructive'}>
              {status.connected ? '接続中' : '未接続'}
            </Badge>
          )}
        </div>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          MariaDBデータベースの管理を行います（自動更新: 30秒）
          {status && status.connected && (
            <span className="ml-2">
              • {status.version.split('-')[0]} • 稼働時間: {Math.floor(status.uptime / 3600)}時間
            </span>
          )}
        </p>
      </div>

      {/* Database actions */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="データベースを検索..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex h-10 w-full rounded-md border border-input bg-background pl-10 pr-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>
        <Button onClick={() => handleAction('create')}>
          <Plus className="h-4 w-4 mr-2" />
          新規データベース作成
        </Button>
        <Button variant="outline" onClick={() => handleAction('refresh')}>
          <RefreshCw className="h-4 w-4 mr-2" />
          更新
        </Button>
      </div>

      {/* Database statistics */}
      <div className="grid gap-6 sm:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              総データベース数
            </CardTitle>
            <Database className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{databases?.length || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              アクティブなデータベース
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">総容量</CardTitle>
            <Database className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.total_size_mb?.toFixed(2) || 0} MB
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              使用中のストレージ
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">MariaDB バージョン</CardTitle>
            <Database className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.mariadb_version?.split('-')[0] || 'Unknown'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              データベースエンジン
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Databases list */}
      <Card>
        <CardHeader>
          <CardTitle>データベース一覧</CardTitle>
          <CardDescription>
            全{filteredDatabases?.length || 0}個のデータベース
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredDatabases?.map((db) => (
              <div
                key={db.name}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <Database className="h-8 w-8 text-primary" />
                  <div>
                    <h3 className="font-semibold">{db.name}</h3>
                    <p className="text-sm text-muted-foreground mt-1">
                      {db.size_mb.toFixed(2)} MB
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDatabaseClick(db.name)}
                    title="詳細を表示"
                  >
                    <Info className="h-4 w-4 mr-1" />
                    詳細
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleAction('export', db.name)
                    }}
                    title="エクスポート"
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleAction('import', db.name)
                    }}
                    title="インポート"
                  >
                    <Upload className="h-4 w-4" />
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleAction('delete', db.name)
                    }}
                    title="削除"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Database Detail Modal */}
      <DatabaseDetailModal
        isOpen={showDetailModal}
        onClose={() => {
          setShowDetailModal(false)
          setSelectedDb(null)
        }}
        databaseName={selectedDb}
      />
    </div>
  )
}
