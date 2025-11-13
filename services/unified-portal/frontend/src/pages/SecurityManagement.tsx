import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Shield, AlertTriangle, CheckCircle, XCircle, RefreshCw } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { securityAPI } from '@/lib/api'

// Mock data
const mockSecurityStatus = {
  overall: 'warning',
  score: 72,
  issues: {
    critical: 2,
    high: 1,
    medium: 3,
    low: 2,
  },
  checks: [
    {
      name: 'ブルートフォース攻撃対策',
      status: 'fail',
      severity: 'critical',
      description: 'Wordfenceが未導入です',
      action: 'Wordfence導入',
    },
    {
      name: 'XMLRPC保護',
      status: 'fail',
      severity: 'critical',
      description: 'XMLRPCが有効です（DDoS攻撃の標的）',
      action: 'XMLRPC無効化',
    },
    {
      name: 'セキュリティヘッダー',
      status: 'warning',
      severity: 'high',
      description: '一部のセキュリティヘッダーが未設定です',
      action: 'Nginxヘッダー追加',
    },
    {
      name: 'SSL/TLS暗号化',
      status: 'pass',
      severity: 'critical',
      description: 'Cloudflare経由で暗号化済み',
      action: null,
    },
    {
      name: 'DDoS防御',
      status: 'pass',
      severity: 'high',
      description: 'Cloudflareで保護済み',
      action: null,
    },
    {
      name: 'Rate Limiting',
      status: 'warning',
      severity: 'medium',
      description: 'Cloudflare Freeプランで制限あり',
      action: 'Proプランへのアップグレード',
    },
    {
      name: 'WordPress自動更新',
      status: 'warning',
      severity: 'medium',
      description: '一部サイトで無効化されています',
      action: '自動更新有効化',
    },
  ],
}

const mockPluginStatus = [
  { site: 'kuma8088', wordfence: false, xmlrpc: true, autoUpdate: true },
  { site: 'demo1-kuma8088', wordfence: false, xmlrpc: true, autoUpdate: true },
  { site: 'webmakeprofit', wordfence: false, xmlrpc: true, autoUpdate: false },
]

export default function SecurityManagement() {
  const queryClient = useQueryClient()

  // Query: Security stats (SSL, HTTPS, Cloudflare protection)
  const { data: _stats, isLoading, error } = useQuery({
    queryKey: ['security-stats'],
    queryFn: securityAPI.getStats,
    refetchInterval: 60000, // Refresh every 60 seconds
  })

  // Query: SSL certificates (for future implementation)
  const { data: _certificates } = useQuery({
    queryKey: ['ssl-certificates'],
    queryFn: securityAPI.listSSLCertificates,
    refetchInterval: 300000, // Refresh every 5 minutes
  })

  // Query: Security headers (for future implementation)
  const { data: _headers } = useQuery({
    queryKey: ['security-headers'],
    queryFn: securityAPI.getSecurityHeaders,
    refetchInterval: 300000,
  })

  // Mock data for detailed checks and plugin status (Backend not yet fully implemented)
  const { data: securityStatus } = useQuery({
    queryKey: ['security-status'],
    queryFn: async () => mockSecurityStatus,
  })

  const { data: pluginStatus } = useQuery({
    queryKey: ['plugin-status'],
    queryFn: async () => mockPluginStatus,
  })

  const handleAction = (action: string) => {
    if (action === 'refresh') {
      queryClient.invalidateQueries({ queryKey: ['security-stats'] })
      queryClient.invalidateQueries({ queryKey: ['ssl-certificates'] })
      queryClient.invalidateQueries({ queryKey: ['security-headers'] })
    } else {
      console.log('Security action:', action)
      // TODO: Implement other API calls
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2 text-primary" />
          <p className="text-muted-foreground">セキュリティ情報を読み込み中...</p>
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-red-600" />
          <p className="text-red-600">セキュリティ情報の取得に失敗しました</p>
          <p className="text-sm text-muted-foreground mt-1">
            {error instanceof Error ? error.message : '不明なエラー'}
          </p>
        </div>
      </div>
    )
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pass':
        return 'text-green-600 dark:text-green-400'
      case 'warning':
        return 'text-yellow-600 dark:text-yellow-400'
      case 'fail':
        return 'text-red-600 dark:text-red-400'
      default:
        return 'text-gray-600'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pass':
        return <CheckCircle className="h-5 w-5" />
      case 'warning':
        return <AlertTriangle className="h-5 w-5" />
      case 'fail':
        return <XCircle className="h-5 w-5" />
      default:
        return null
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
          セキュリティ管理
        </h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          WordPressセキュリティ状況の確認と対策
        </p>
      </div>

      {/* Security score */}
      <div className="grid gap-6 sm:grid-cols-5">
        <Card className="sm:col-span-2">
          <CardHeader className="text-center">
            <CardTitle className="text-sm font-medium">
              総合セキュリティスコア
            </CardTitle>
          </CardHeader>
          <CardContent className="text-center">
            <div className={`text-6xl font-bold ${getScoreColor(securityStatus?.score || 0)}`}>
              {securityStatus?.score}
            </div>
            <p className="text-sm text-muted-foreground mt-2">/ 100</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Critical</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {securityStatus?.issues.critical}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">High</CardTitle>
            <AlertTriangle className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">
              {securityStatus?.issues.high}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Medium</CardTitle>
            <AlertTriangle className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {securityStatus?.issues.medium}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Security checks */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>セキュリティチェック</CardTitle>
            <CardDescription>
              システムのセキュリティ状況
            </CardDescription>
          </div>
          <Button variant="outline" onClick={() => handleAction('refresh')}>
            <RefreshCw className="h-4 w-4 mr-2" />
            再チェック
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {securityStatus?.checks.map((check, index) => (
              <div
                key={index}
                className="flex items-start justify-between p-4 border rounded-lg"
              >
                <div className="flex items-start gap-4">
                  <div className={getStatusColor(check.status)}>
                    {getStatusIcon(check.status)}
                  </div>
                  <div>
                    <h4 className="font-medium">{check.name}</h4>
                    <p className="text-sm text-muted-foreground mt-1">
                      {check.description}
                    </p>
                    <div className="flex items-center gap-2 mt-2">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          check.severity === 'critical'
                            ? 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
                            : check.severity === 'high'
                            ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400'
                            : 'bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400'
                        }`}
                      >
                        {check.severity}
                      </span>
                    </div>
                  </div>
                </div>

                {check.action && (
                  <Button
                    size="sm"
                    onClick={() => handleAction(check.action)}
                  >
                    {check.action}
                  </Button>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Plugin status per site */}
      <Card>
        <CardHeader>
          <CardTitle>サイト別セキュリティ状況</CardTitle>
          <CardDescription>
            WordPressサイトごとのセキュリティプラグイン状況
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-4 font-medium">サイト</th>
                  <th className="text-center p-4 font-medium">Wordfence</th>
                  <th className="text-center p-4 font-medium">XMLRPC</th>
                  <th className="text-center p-4 font-medium">自動更新</th>
                  <th className="text-right p-4 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {pluginStatus?.map((site) => (
                  <tr key={site.site} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="p-4 font-medium">{site.site}</td>
                    <td className="p-4 text-center">
                      {site.wordfence ? (
                        <CheckCircle className="h-5 w-5 text-green-600 mx-auto" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-600 mx-auto" />
                      )}
                    </td>
                    <td className="p-4 text-center">
                      {site.xmlrpc ? (
                        <XCircle className="h-5 w-5 text-red-600 mx-auto" />
                      ) : (
                        <CheckCircle className="h-5 w-5 text-green-600 mx-auto" />
                      )}
                    </td>
                    <td className="p-4 text-center">
                      {site.autoUpdate ? (
                        <CheckCircle className="h-5 w-5 text-green-600 mx-auto" />
                      ) : (
                        <AlertTriangle className="h-5 w-5 text-yellow-600 mx-auto" />
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <Button size="sm" variant="outline">
                        修正
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Recommended actions */}
      <Card className="border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-yellow-600" />
            <CardTitle>推奨アクション</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-sm">
            1. Wordfenceを全16サイトに導入（ブルートフォース攻撃対策）
          </p>
          <p className="text-sm">
            2. XMLRPCを無効化（DDoS攻撃対策）
          </p>
          <p className="text-sm">
            3. Nginxセキュリティヘッダーを追加（XSS/クリックジャッキング対策）
          </p>
          <p className="text-sm">
            4. Cloudflare Proプランへのアップグレードを検討（$20/月）
          </p>
          <div className="pt-4">
            <Button onClick={() => handleAction('apply-all')}>
              全ての推奨アクションを適用
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
