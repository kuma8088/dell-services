import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tantml:react-query'
import {
  Trash2,
  Settings,
  Globe,
  RotateCcw,
  AlertCircle,
  CheckCircle2,
  Loader2,
  MoreVertical,
} from 'lucide-react'
import { managedSitesAPI, type ManagedWordPressSite } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface ManagedSitesListProps {
  searchQuery: string
}

export default function ManagedSitesList({ searchQuery }: ManagedSitesListProps) {
  const queryClient = useQueryClient()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedSite, setSelectedSite] = useState<ManagedWordPressSite | null>(null)
  const [deleteDatabase, setDeleteDatabase] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')

  // Query: List managed sites
  const { data: sites, isLoading, error } = useQuery({
    queryKey: ['managed-sites'],
    queryFn: () => managedSitesAPI.listSites(),
    refetchInterval: 30000,
  })

  // Mutation: Delete site
  const deleteMutation = useMutation({
    mutationFn: (params: { siteId: number; deleteDatabase: boolean }) =>
      managedSitesAPI.deleteSite(params.siteId, params.deleteDatabase),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['managed-sites'] })
      setSuccessMessage('サイトが正常に削除されました')
      setTimeout(() => setSuccessMessage(''), 5000)
      setDeleteDialogOpen(false)
      setSelectedSite(null)
    },
  })

  // Mutation: Clear cache
  const clearCacheMutation = useMutation({
    mutationFn: (siteId: number) =>
      managedSitesAPI.clearCache(siteId, { cache_type: 'all' }),
    onSuccess: () => {
      setSuccessMessage('キャッシュがクリアされました')
      setTimeout(() => setSuccessMessage(''), 5000)
    },
  })

  const filteredSites = sites?.filter((site) =>
    site.site_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    site.domain.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleDelete = (site: ManagedWordPressSite) => {
    setSelectedSite(site)
    setDeleteDatabase(false)
    setDeleteDialogOpen(true)
  }

  const confirmDelete = () => {
    if (selectedSite) {
      deleteMutation.mutate({
        siteId: selectedSite.id,
        deleteDatabase,
      })
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-primary" />
          <p className="text-muted-foreground">管理サイト一覧を読み込み中...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          管理サイト一覧の取得に失敗しました: {error.message}
        </AlertDescription>
      </Alert>
    )
  }

  // Empty state
  if (!sites || sites.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <Globe className="h-12 w-12 text-gray-400 mb-4" />
        <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
          管理サイトがありません
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          「新規サイト作成」ボタンから最初のサイトを作成してください
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Success message */}
      {successMessage && (
        <Alert className="bg-green-50 border-green-200">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">
            {successMessage}
          </AlertDescription>
        </Alert>
      )}

      {/* Sites list */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredSites?.map((site) => (
          <div
            key={site.id}
            className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="font-medium text-gray-900 dark:text-white">
                    {site.site_name}
                  </h3>
                  <Badge variant={site.enabled ? 'default' : 'secondary'}>
                    {site.enabled ? '有効' : '無効'}
                  </Badge>
                </div>
                <a
                  href={`https://${site.domain}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:underline"
                >
                  {site.domain}
                </a>
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    onClick={() => clearCacheMutation.mutate(site.id)}
                    disabled={clearCacheMutation.isPending}
                  >
                    <RotateCcw className="h-4 w-4 mr-2" />
                    キャッシュクリア
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => handleDelete(site)}
                    className="text-red-600"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    削除
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                <Settings className="h-4 w-4" />
                <span>PHP {site.php_version}</span>
              </div>
              <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                <span className="font-mono text-xs">{site.database_name}</span>
              </div>
              <div className="text-xs text-gray-500">
                作成日: {new Date(site.created_at).toLocaleDateString('ja-JP')}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>サイトを削除しますか？</AlertDialogTitle>
            <AlertDialogDescription>
              <div className="space-y-3">
                <p>
                  <strong>{selectedSite?.site_name}</strong> を削除します。
                  この操作は取り消せません。
                </p>
                <div className="flex items-start gap-2 p-3 bg-amber-50 border border-amber-200 rounded">
                  <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
                  <div className="flex-1">
                    <label className="flex items-center gap-2 text-sm font-medium text-amber-900 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={deleteDatabase}
                        onChange={(e) => setDeleteDatabase(e.target.checked)}
                        className="rounded border-amber-300"
                      />
                      データベースも削除する
                    </label>
                    <p className="text-xs text-amber-700 mt-1 ml-6">
                      データベースを削除すると、全てのコンテンツが完全に失われます
                    </p>
                  </div>
                </div>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>
              キャンセル
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={deleteMutation.isPending}
              className="bg-red-600 hover:bg-red-700"
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  削除中...
                </>
              ) : (
                '削除する'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
