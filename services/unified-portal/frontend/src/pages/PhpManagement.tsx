import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { FileCode, RefreshCw, Download, Settings, AlertCircle } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { phpAPI } from '@/lib/api'

// Mock data for FPM and logs (Backend API not yet implemented)
const mockFpmData = {
  pools: [
    {
      name: 'www',
      processManager: 'dynamic',
      maxChildren: 50,
      startServers: 5,
      minSpareServers: 5,
      maxSpareServers: 35,
    },
  ],
  status: 'running',
  uptime: '5 days 3 hours',
  connections: 12,
}

const mockLogs = [
  {
    timestamp: '2025-11-13 10:30:45',
    level: 'WARNING',
    message: 'PHP Warning: Division by zero in /var/www/html/test.php on line 10',
  },
  {
    timestamp: '2025-11-13 10:25:12',
    level: 'NOTICE',
    message: 'PHP Notice: Undefined variable: foo in /var/www/html/index.php on line 25',
  },
]

// Legacy mock data structure (kept for FPM tab compatibility)
const mockPhpInfo = {
  version: '8.3.0',
  sapi: 'fpm-fcgi',
  configFile: '/usr/local/etc/php/php.ini',
  extensions: [
    { name: 'mysqli', version: '8.3.0', status: 'enabled' },
    { name: 'pdo_mysql', version: '8.3.0', status: 'enabled' },
    { name: 'gd', version: '8.3.0', status: 'enabled' },
    { name: 'imagick', version: '3.7.0', status: 'enabled' },
    { name: 'redis', version: '6.0.2', status: 'enabled' },
    { name: 'opcache', version: '8.3.0', status: 'enabled' },
    { name: 'zip', version: '1.21.1', status: 'enabled' },
    { name: 'mbstring', version: '8.3.0', status: 'enabled' },
    { name: 'curl', version: '8.3.0', status: 'enabled' },
    { name: 'xml', version: '8.3.0', status: 'enabled' },
  ],
  settings: [
    { key: 'memory_limit', value: '256M', default: '128M' },
    { key: 'upload_max_filesize', value: '64M', default: '2M' },
    { key: 'post_max_size', value: '64M', default: '8M' },
    { key: 'max_execution_time', value: '300', default: '30' },
    { key: 'max_input_time', value: '300', default: '60' },
    { key: 'display_errors', value: 'Off', default: 'Off' },
    { key: 'error_reporting', value: 'E_ALL', default: 'E_ALL' },
    { key: 'opcache.enable', value: '1', default: '1' },
    { key: 'opcache.memory_consumption', value: '128', default: '128' },
  ],
  fpm: mockFpmData,
}

export default function PhpManagement() {
  const [activeTab, setActiveTab] = useState<'info' | 'extensions' | 'settings' | 'fpm' | 'logs'>('info')
  const queryClient = useQueryClient()

  // Query: PHP stats (version, modules count, memory limit)
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['php-stats'],
    queryFn: phpAPI.getStats,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Query: PHP modules list
  const { data: modules } = useQuery({
    queryKey: ['php-modules'],
    queryFn: phpAPI.listModules,
    refetchInterval: 60000, // Refresh every 60 seconds
  })

  // Query: PHP configuration
  const { data: config } = useQuery({
    queryKey: ['php-config'],
    queryFn: phpAPI.getConfig,
    refetchInterval: 60000,
  })

  // Mock data for logs (Backend API not yet implemented)
  const { data: logs } = useQuery({
    queryKey: ['php-logs'],
    queryFn: async () => mockLogs,
  })

  // Legacy mock data for compatibility
  const phpInfo = {
    ...mockPhpInfo,
    version: stats?.version || mockPhpInfo.version,
    extensions: modules?.map(m => ({
      name: m.name,
      version: m.version,
      status: 'enabled'
    })) || mockPhpInfo.extensions,
    settings: config ? [
      { key: 'memory_limit', value: config.memory_limit, default: '128M' },
      { key: 'upload_max_filesize', value: config.upload_max_filesize, default: '2M' },
      { key: 'post_max_size', value: config.post_max_size, default: '8M' },
      { key: 'max_execution_time', value: config.max_execution_time, default: '30' },
      { key: 'display_errors', value: config.display_errors, default: 'Off' },
      { key: 'error_reporting', value: config.error_reporting, default: 'E_ALL' },
    ] : mockPhpInfo.settings,
  }

  const handleAction = (action: string) => {
    if (action === 'refresh') {
      queryClient.invalidateQueries({ queryKey: ['php-stats'] })
      queryClient.invalidateQueries({ queryKey: ['php-modules'] })
      queryClient.invalidateQueries({ queryKey: ['php-config'] })
    } else {
      console.log(`${action}`)
      // TODO: Implement other API calls
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2 text-primary" />
          <p className="text-muted-foreground">PHP情報を読み込み中...</p>
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
          <p className="text-red-600">PHP情報の取得に失敗しました</p>
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
          PHP管理
        </h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          PHP設定と拡張モジュールの管理を行います
        </p>
      </div>

      {/* PHP version and actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <FileCode className="h-12 w-12 text-primary" />
          <div>
            <h3 className="text-2xl font-bold">PHP {phpInfo?.version}</h3>
            <p className="text-sm text-muted-foreground">
              {phpInfo?.sapi} | {phpInfo?.fpm.status}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" onClick={() => handleAction('refresh')}>
            <RefreshCw className="h-4 w-4 mr-2" />
            更新
          </Button>
          <Button variant="outline" onClick={() => handleAction('phpinfo')}>
            <Settings className="h-4 w-4 mr-2" />
            phpinfo() 表示
          </Button>
          <Button variant="outline" onClick={() => handleAction('download-config')}>
            <Download className="h-4 w-4 mr-2" />
            設定ダウンロード
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex space-x-8">
          {[
            { id: 'info', label: '基本情報' },
            { id: 'extensions', label: '拡張モジュール' },
            { id: 'settings', label: '設定' },
            { id: 'fpm', label: 'PHP-FPM' },
            { id: 'logs', label: 'ログ' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-primary text-primary'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:border-gray-300 dark:text-gray-300 dark:hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'info' && (
        <div className="grid gap-6 sm:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>システム情報</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">バージョン</span>
                <span className="text-sm font-medium">{phpInfo?.version}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">SAPI</span>
                <span className="text-sm font-medium">{phpInfo?.sapi}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">設定ファイル</span>
                <span className="text-sm font-medium font-mono text-xs">
                  {phpInfo?.configFile}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">拡張モジュール数</span>
                <span className="text-sm font-medium">
                  {phpInfo?.extensions.length}
                </span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>PHP-FPM</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">ステータス</span>
                <span className="text-sm font-medium text-green-600 dark:text-green-400">
                  {phpInfo?.fpm.status}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">稼働時間</span>
                <span className="text-sm font-medium">{phpInfo?.fpm.uptime}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-muted-foreground">アクティブ接続</span>
                <span className="text-sm font-medium">{phpInfo?.fpm.connections}</span>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {activeTab === 'extensions' && (
        <Card>
          <CardHeader>
            <CardTitle>PHP拡張モジュール</CardTitle>
            <CardDescription>
              インストール済みの拡張モジュール一覧
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {phpInfo?.extensions.map((ext) => (
                <div
                  key={ext.name}
                  className="flex items-center justify-between p-4 border rounded-lg"
                >
                  <div>
                    <h4 className="font-medium">{ext.name}</h4>
                    <p className="text-sm text-muted-foreground">v{ext.version}</p>
                  </div>
                  <div
                    className={`px-2 py-1 rounded-full text-xs font-medium ${
                      ext.status === 'enabled'
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                        : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400'
                    }`}
                  >
                    {ext.status}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'settings' && (
        <Card>
          <CardHeader>
            <CardTitle>PHP設定</CardTitle>
            <CardDescription>
              php.ini の主要設定値
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b">
                    <th className="text-left p-4 font-medium">設定項目</th>
                    <th className="text-left p-4 font-medium">現在値</th>
                    <th className="text-left p-4 font-medium">デフォルト値</th>
                    <th className="text-right p-4 font-medium">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {phpInfo?.settings.map((setting) => (
                    <tr key={setting.key} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="p-4 font-mono text-sm">{setting.key}</td>
                      <td className="p-4">
                        <span
                          className={`font-medium ${
                            setting.value !== setting.default
                              ? 'text-orange-600 dark:text-orange-400'
                              : ''
                          }`}
                        >
                          {setting.value}
                        </span>
                      </td>
                      <td className="p-4 text-sm text-muted-foreground">
                        {setting.default}
                      </td>
                      <td className="p-4 text-right">
                        <Button size="sm" variant="outline">
                          編集
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {activeTab === 'fpm' && (
        <Card>
          <CardHeader>
            <CardTitle>PHP-FPM プール設定</CardTitle>
            <CardDescription>
              FPMプロセスマネージャーの設定
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {phpInfo?.fpm.pools.map((pool) => (
              <div key={pool.name} className="space-y-4">
                <h4 className="font-semibold text-lg">Pool: {pool.name}</h4>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="flex justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded">
                    <span className="text-sm text-muted-foreground">
                      Process Manager
                    </span>
                    <span className="text-sm font-medium">{pool.processManager}</span>
                  </div>
                  <div className="flex justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded">
                    <span className="text-sm text-muted-foreground">
                      Max Children
                    </span>
                    <span className="text-sm font-medium">{pool.maxChildren}</span>
                  </div>
                  <div className="flex justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded">
                    <span className="text-sm text-muted-foreground">
                      Start Servers
                    </span>
                    <span className="text-sm font-medium">{pool.startServers}</span>
                  </div>
                  <div className="flex justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded">
                    <span className="text-sm text-muted-foreground">
                      Min Spare Servers
                    </span>
                    <span className="text-sm font-medium">
                      {pool.minSpareServers}
                    </span>
                  </div>
                  <div className="flex justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded">
                    <span className="text-sm text-muted-foreground">
                      Max Spare Servers
                    </span>
                    <span className="text-sm font-medium">
                      {pool.maxSpareServers}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {activeTab === 'logs' && (
        <Card>
          <CardHeader>
            <CardTitle>PHPログ</CardTitle>
            <CardDescription>
              最近のPHPエラーログ
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {logs?.map((log, index) => (
                <div
                  key={index}
                  className="flex items-start gap-4 p-4 border rounded-lg"
                >
                  <AlertCircle
                    className={`h-5 w-5 flex-shrink-0 ${
                      log.level === 'WARNING'
                        ? 'text-yellow-600'
                        : 'text-blue-600'
                    }`}
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          log.level === 'WARNING'
                            ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400'
                            : 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400'
                        }`}
                      >
                        {log.level}
                      </span>
                      <span className="text-sm text-muted-foreground">
                        {log.timestamp}
                      </span>
                    </div>
                    <p className="text-sm font-mono">{log.message}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
