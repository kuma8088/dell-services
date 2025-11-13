import { useQuery } from '@tanstack/react-query'
import {
  Server,
  Database,
  Container,
  HardDrive,
  Cpu,
  MemoryStick,
  AlertCircle,
  Activity,
} from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { dashboardAPI } from '@/lib/api'

export default function Dashboard() {
  // Fetch dashboard data from Backend API
  const { data: systemStats } = useQuery({
    queryKey: ['dashboard-system'],
    queryFn: dashboardAPI.getSystemStats,
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  const { data: containers } = useQuery({
    queryKey: ['dashboard-containers'],
    queryFn: dashboardAPI.getContainerStats,
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  const { data: wordpress } = useQuery({
    queryKey: ['dashboard-wordpress'],
    queryFn: dashboardAPI.getWordPressStats,
    refetchInterval: 30000,
  })

  const { data: redis } = useQuery({
    queryKey: ['dashboard-redis'],
    queryFn: dashboardAPI.getRedisStats,
    refetchInterval: 10000,
  })

  const { data: backup } = useQuery({
    queryKey: ['dashboard-backup'],
    queryFn: dashboardAPI.getBackupStats,
    refetchInterval: 30000,
  })

  // Format uptime in human-readable format
  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    return `${days}日 ${hours}時間`
  }

  // Alert detection
  const alerts = []
  if (systemStats?.cpu_percent && systemStats.cpu_percent > 80) {
    alerts.push('CPU使用率が高くなっています')
  }
  if (systemStats?.memory_percent && systemStats.memory_percent > 80) {
    alerts.push('メモリ使用率が高くなっています')
  }
  if (systemStats?.disk_percent && systemStats.disk_percent > 90) {
    alerts.push('ディスク使用率が高くなっています')
  }

  // Calculate running containers
  const runningContainers = containers?.filter(c => c.status === 'running').length || 0
  const totalContainers = containers?.length || 0

  const statCards = [
    {
      title: 'サービス稼働状況',
      value: `${runningContainers} / ${totalContainers}`,
      description: '稼働中のコンテナ数',
      icon: Server,
      color: 'text-green-600',
    },
    {
      title: 'CPU使用率',
      value: `${systemStats?.cpu_percent?.toFixed(1) || 0}%`,
      description: `Load Avg: ${systemStats?.load_average?.[0]?.toFixed(2) || 0}`,
      icon: Cpu,
      color: 'text-blue-600',
    },
    {
      title: 'メモリ使用量',
      value: `${systemStats?.memory_used_gb?.toFixed(1) || 0} GB`,
      description: `${systemStats?.memory_total_gb || 32} GB中 (${systemStats?.memory_percent?.toFixed(1) || 0}%)`,
      icon: MemoryStick,
      color: 'text-purple-600',
    },
    {
      title: 'ディスク使用量',
      value: `${systemStats?.disk_used_gb?.toFixed(2) || 0} GB`,
      description: `${systemStats?.disk_total_gb?.toFixed(1) || 3.4} GB中 (${systemStats?.disk_percent?.toFixed(1) || 0}%)`,
      icon: HardDrive,
      color: 'text-yellow-600',
    },
  ]

  // Calculate WordPress sites with Redis connection
  const totalWordPressSites = wordpress?.length || 0
  const wordpressSitesWithRedis = wordpress?.filter(site => site.redis_connected).length || 0
  const isRedisConnected = redis && redis.connected_clients > 0

  const serviceCategories = [
    {
      title: 'Blog System',
      description: 'WordPressサイト管理',
      icon: Database,
      stats: [
        { label: '稼働サイト数', value: String(totalWordPressSites) },
        {
          label: 'Redisキャッシュ',
          value: isRedisConnected
            ? `${wordpressSitesWithRedis}/${totalWordPressSites}サイト接続`
            : '未接続'
        },
      ],
      actions: [
        { label: 'サイト一覧', href: '/wordpress' },
        { label: 'データベース', href: '/database' },
      ],
    },
    {
      title: 'システムリソース',
      description: 'CPU・メモリ・ディスク',
      icon: Activity,
      stats: [
        {
          label: 'システム稼働時間',
          value: systemStats?.uptime_seconds ? formatUptime(systemStats.uptime_seconds) : '不明'
        },
        { label: 'データベース数', value: String(totalWordPressSites) },
      ],
      actions: [
        { label: 'Docker管理', href: '/docker' },
        { label: 'PHP設定', href: '/php' },
      ],
    },
    {
      title: 'バックアップ',
      description: 'バックアップ・リストア',
      icon: Database,
      stats: [
        { label: 'バックアップ総数', value: String(backup?.total_backups || 0) },
        { label: 'スケジュール', value: '日次/週次' },
      ],
      actions: [
        { label: 'バックアップ管理', href: '/backup' },
        { label: 'スケジュール確認', href: '/backup' },
      ],
    },
    {
      title: 'セキュリティ',
      description: 'SSL証明書・セキュリティ設定',
      icon: Container,
      stats: [
        { label: 'SSL証明書', value: '有効' },
        { label: 'Cloudflare保護', value: '有効' },
      ],
      actions: [
        { label: 'セキュリティ設定', href: '/security' },
        { label: 'ドメイン管理', href: '/domains' },
      ],
    },
  ]

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
          ダッシュボード
        </h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          システム全体の状況を確認できます（自動更新: 5-30秒）
        </p>
      </div>

      {/* Alert banner */}
      {alerts.length > 0 && (
        <div className="rounded-lg bg-yellow-50 dark:bg-yellow-900/20 p-4 border border-yellow-200 dark:border-yellow-800">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                {alerts.length}件のアラートがあります
              </h3>
              <ul className="text-sm text-yellow-700 dark:text-yellow-300 mt-1 space-y-1">
                {alerts.map((alert, index) => (
                  <li key={index}>• {alert}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Stats cards */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => (
          <Card key={card.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {card.title}
              </CardTitle>
              <card.icon className={`h-4 w-4 ${card.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{card.value}</div>
              <p className="text-xs text-muted-foreground mt-1">
                {card.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Service categories - Xserver style */}
      <div>
        <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          サービス管理
        </h3>
        <div className="grid gap-6 sm:grid-cols-2">
          {serviceCategories.map((category) => (
            <Card key={category.title} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <category.icon className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-lg">{category.title}</CardTitle>
                    <CardDescription>{category.description}</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Stats */}
                <div className="grid grid-cols-2 gap-4">
                  {category.stats.map((stat) => (
                    <div key={stat.label} className="text-sm">
                      <div className="text-muted-foreground">{stat.label}</div>
                      <div className="font-semibold text-lg">{stat.value}</div>
                    </div>
                  ))}
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-2 border-t">
                  {category.actions.map((action) => (
                    <a
                      key={action.label}
                      href={action.href}
                      className="flex-1 text-center px-3 py-2 text-sm font-medium text-primary hover:bg-primary/10 rounded-md transition-colors"
                    >
                      {action.label}
                    </a>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
