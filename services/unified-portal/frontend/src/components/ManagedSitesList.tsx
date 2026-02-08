import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Trash2,
  Settings,
  Globe,
  RotateCcw,
  AlertCircle,
  CheckCircle2,
  Loader2,
  MoreVertical,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { managedSitesAPI, type ManagedWordPressSite, type DNSResolveStatus } from '@/lib/api'
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

// Extract root domain from full domain (e.g., "4line.fx-trader-life.com" -> "fx-trader-life.com")
function getRootDomain(domain: string): string {
  const parts = domain.split('.')
  // Handle common TLDs
  if (parts.length >= 2) {
    // Check for two-part TLDs like .co.jp, .com.au
    const lastTwo = parts.slice(-2).join('.')
    if (['co.jp', 'com.au', 'co.uk', 'com.br'].includes(lastTwo) && parts.length >= 3) {
      return parts.slice(-3).join('.')
    }
    // Standard TLDs
    return parts.slice(-2).join('.')
  }
  return domain
}

const DNS_CHECK_WINDOW_MS = 10 * 60 * 1000 // 10分

function SiteDomainLink({ site }: { site: ManagedWordPressSite }) {
  // Backend returns UTC datetime without 'Z' suffix (e.g., "2026-02-07T01:10:11").
  // Without 'Z', JavaScript parses it as local time, causing a timezone offset
  // (9 hours in JST) that makes isRecent always false.
  const createdAtStr = site.created_at.endsWith('Z') ? site.created_at : site.created_at + 'Z'
  const createdAt = new Date(createdAtStr).getTime()
  const isRecent = Date.now() - createdAt < DNS_CHECK_WINDOW_MS

  const { data: dnsStatus } = useQuery<DNSResolveStatus>({
    queryKey: ['dns-status', site.id],
    queryFn: () => managedSitesAPI.checkDnsStatus(site.id),
    enabled: isRecent,
    refetchInterval: (query) => {
      if (query.state.data?.resolved) return false
      return 5000
    },
  })

  const dnsResolved = !isRecent || dnsStatus?.resolved

  if (!dnsResolved) {
    return (
      <span className="inline-flex items-center gap-1.5 text-sm text-gray-500">
        {site.domain}
        <Badge variant="outline" className="text-xs font-normal text-amber-600 border-amber-300">
          <Loader2 className="h-3 w-3 animate-spin mr-1" />
          DNS反映待ち...
        </Badge>
      </span>
    )
  }

  return (
    <a
      href={`https://${site.domain}`}
      target="_blank"
      rel="noopener noreferrer"
      className="text-sm text-blue-600 hover:underline"
    >
      {site.domain}
    </a>
  )
}

export default function ManagedSitesList({ searchQuery }: ManagedSitesListProps) {
  const queryClient = useQueryClient()
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedSite, setSelectedSite] = useState<ManagedWordPressSite | null>(null)
  const [deleteDatabase, setDeleteDatabase] = useState(false)
  const [successMessage, setSuccessMessage] = useState('')
  const [collapsedDomains, setCollapsedDomains] = useState<Set<string>>(new Set())

  // Query: List managed sites
  const { data: sites, isLoading, error } = useQuery({
    queryKey: ['managed-sites'],
    queryFn: () => managedSitesAPI.listSites(),
    refetchInterval: 30000,
  })

  // Toggle domain collapse state
  const toggleDomain = (domain: string) => {
    setCollapsedDomains(prev => {
      const next = new Set(prev)
      if (next.has(domain)) {
        next.delete(domain)
      } else {
        next.add(domain)
      }
      return next
    })
  }

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

  // Group sites by root domain
  const groupedSites = useMemo(() => {
    if (!filteredSites) return new Map<string, ManagedWordPressSite[]>()

    const groups = new Map<string, ManagedWordPressSite[]>()
    filteredSites.forEach(site => {
      const rootDomain = getRootDomain(site.domain)
      if (!groups.has(rootDomain)) {
        groups.set(rootDomain, [])
      }
      groups.get(rootDomain)!.push(site)
    })

    // Sort groups by domain name
    return new Map([...groups.entries()].sort((a, b) => a[0].localeCompare(b[0])))
  }, [filteredSites])

  const handleDelete = (site: ManagedWordPressSite) => {
    setSelectedSite(site)
    setDeleteDatabase(true)  // デフォルトでデータベースも削除
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
          管理サイト一覧の取得に失敗しました: {error instanceof Error ? error.message : '不明なエラー'}
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

      {/* Sites list grouped by domain */}
      <div className="space-y-6">
        {Array.from(groupedSites.entries()).map(([rootDomain, domainSites]) => (
          <div key={rootDomain} className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            {/* Domain header */}
            <button
              onClick={() => toggleDomain(rootDomain)}
              className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 dark:bg-gray-800 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <div className="flex items-center gap-3">
                {collapsedDomains.has(rootDomain) ? (
                  <ChevronRight className="h-5 w-5 text-gray-500" />
                ) : (
                  <ChevronDown className="h-5 w-5 text-gray-500" />
                )}
                <Globe className="h-5 w-5 text-primary" />
                <span className="font-semibold text-gray-900 dark:text-white">{rootDomain}</span>
                <Badge variant="outline" className="ml-2">
                  {domainSites.length} サイト
                </Badge>
              </div>
            </button>

            {/* Sites in this domain */}
            {!collapsedDomains.has(rootDomain) && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 p-4 bg-white dark:bg-gray-900">
                {domainSites.map((site) => (
                  <div
                    key={site.id}
                    className="bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:shadow-md transition-shadow"
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
                        <SiteDomainLink site={site} />
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
            )}
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
                      データベースも削除する（推奨）
                    </label>
                    <p className="text-xs text-amber-700 mt-1 ml-6">
                      デフォルトでチェックされています。全てのコンテンツが完全に削除されます
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
