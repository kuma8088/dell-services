import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Plus,
  RefreshCw,
  Trash2,
  Settings,
  Globe,
  Upload,
  Download,
  RotateCcw,
  AlertCircle,
} from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { wordpressAPI } from '@/lib/api'

export default function WordPressManagement() {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showRestoreModal, setShowRestoreModal] = useState(false)
  const [selectedSite, setSelectedSite] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const queryClient = useQueryClient()

  // Query: List sites
  const { data: sites, isLoading, error } = useQuery({
    queryKey: ['wordpress-sites'],
    queryFn: wordpressAPI.listSites,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Query: WordPress stats
  const { data: stats } = useQuery({
    queryKey: ['wordpress-stats'],
    queryFn: wordpressAPI.getStats,
    refetchInterval: 30000,
  })

  const filteredSites = sites?.filter((site) =>
    site.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    site.url.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Mock backups data for restore modal (Backend not implemented)
  const backups = [
    { id: '1', timestamp: '2025-11-13 03:00', type: 'daily', size: '95.2 GB' },
    { id: '2', timestamp: '2025-11-12 03:00', type: 'daily', size: '94.8 GB' },
    { id: '3', timestamp: '2025-11-10 02:00', type: 'weekly', size: '95.0 GB' },
  ]

  const handleAction = (action: string, site?: string) => {
    if (action === 'refresh') {
      queryClient.invalidateQueries({ queryKey: ['wordpress-sites'] })
      queryClient.invalidateQueries({ queryKey: ['wordpress-stats'] })
    } else {
      console.log('Action:', action, site)
      // TODO: Implement other API calls
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2 text-primary" />
          <p className="text-muted-foreground">サイト一覧を読み込み中...</p>
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
          <p className="text-red-600">サイト一覧の取得に失敗しました</p>
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
          WordPress管理
        </h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          WordPressサイトの作成・管理・リストアを行います（自動更新: 30秒）
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <input
            type="text"
            placeholder="サイトを検索..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          新規サイト作成
        </Button>
        <Button variant="outline" onClick={() => handleAction('refresh')}>
          <RefreshCw className="h-4 w-4 mr-2" />
          更新
        </Button>
      </div>

      {/* Statistics */}
      <div className="grid gap-6 sm:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">総サイト数</CardTitle>
            <Globe className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_sites || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              オンライン: {stats?.sites_online || 0}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">総プラグイン数</CardTitle>
            <Download className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_plugins || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              全サイト合計
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Redisキャッシュ</CardTitle>
            <Upload className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.redis_enabled_sites || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              有効サイト数
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              サイトステータス
            </CardTitle>
            <Globe className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.sites_online === stats?.total_sites ? '正常' : '要確認'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              全サイト状態
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Sites list */}
      <Card>
        <CardHeader>
          <CardTitle>サイト一覧</CardTitle>
          <CardDescription>
            全{filteredSites?.length || 0}サイト
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredSites?.map((site) => (
              <div
                key={site.name}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <Globe className="h-8 w-8 text-primary" />
                  <div>
                    <h3 className="font-semibold">{site.name}</h3>
                    <div className="flex gap-4 text-sm text-muted-foreground mt-1">
                      <a
                        href={site.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:text-primary hover:underline"
                      >
                        {site.url}
                      </a>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div
                    className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      site.status === 'online'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                        : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400'
                    }`}
                  >
                    {site.status}
                  </div>

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => window.open(site.url + '/wp-admin', '_blank')}
                      title="管理画面を開く"
                    >
                      <Settings className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleAction('backup', site.name)}
                      title="バックアップ"
                    >
                      <Upload className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setSelectedSite(site.name)
                        setShowRestoreModal(true)
                      }}
                      title="リストア"
                    >
                      <RotateCcw className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleAction('delete', site.name)}
                      title="削除"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Create modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-2xl">
            <CardHeader>
              <CardTitle>新規WordPressサイト作成</CardTitle>
              <CardDescription>
                サイト情報を入力してください
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">サイト名</label>
                <input
                  type="text"
                  placeholder="例: my-new-site"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">ドメイン/URL</label>
                <input
                  type="text"
                  placeholder="例: blog.kuma8088.com/my-site"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">管理者メールアドレス</label>
                <input
                  type="email"
                  placeholder="admin@example.com"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">サイトタイトル</label>
                <input
                  type="text"
                  placeholder="例: My Awesome Blog"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
              </div>

              <div className="flex items-center gap-2">
                <input type="checkbox" id="install-wordfence" defaultChecked />
                <label htmlFor="install-wordfence" className="text-sm">
                  Wordfence Security を自動インストール（推奨）
                </label>
              </div>

              <div className="flex items-center gap-2">
                <input type="checkbox" id="install-redis" defaultChecked />
                <label htmlFor="install-redis" className="text-sm">
                  Redis Object Cache を自動設定（推奨）
                </label>
              </div>

              <div className="flex items-center gap-2">
                <input type="checkbox" id="install-smtp" defaultChecked />
                <label htmlFor="install-smtp" className="text-sm">
                  WP Mail SMTP を自動設定（推奨）
                </label>
              </div>

              <div className="flex gap-2 pt-4">
                <Button
                  className="flex-1"
                  onClick={() => {
                    handleAction('create')
                    setShowCreateModal(false)
                  }}
                >
                  作成
                </Button>
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowCreateModal(false)}
                >
                  キャンセル
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Restore modal */}
      {showRestoreModal && selectedSite && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-2xl">
            <CardHeader>
              <CardTitle>サイトリストア: {selectedSite}</CardTitle>
              <CardDescription>
                復元するバックアップを選択してください
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {backups?.map((backup) => (
                  <div
                    key={backup.id}
                    className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
                  >
                    <div>
                      <h4 className="font-medium">{backup.timestamp}</h4>
                      <p className="text-sm text-muted-foreground">
                        {backup.type} バックアップ | {backup.size}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => {
                        handleAction('restore', `${selectedSite}:${backup.id}`)
                        setShowRestoreModal(false)
                      }}
                    >
                      このバックアップから復元
                    </Button>
                  </div>
                ))}
              </div>

              <div className="border-t pt-4">
                <p className="text-sm text-muted-foreground mb-4">
                  または、外部バックアップファイルをアップロード
                </p>
                <div className="flex gap-2">
                  <input
                    type="file"
                    accept=".zip,.tar.gz"
                    className="flex-1 text-sm"
                  />
                  <Button onClick={() => handleAction('upload-restore')}>
                    アップロード
                  </Button>
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => {
                    setShowRestoreModal(false)
                    setSelectedSite(null)
                  }}
                >
                  キャンセル
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
