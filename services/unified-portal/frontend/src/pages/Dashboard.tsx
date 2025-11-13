import { useQuery } from '@tanstack/react-query'
import {
  Server,
  Database,
  Container,
  HardDrive,
  Cpu,
  MemoryStick,
  AlertCircle,
} from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

// Mock data - Replace with actual API calls
const mockStats = {
  services: {
    running: 25,
    total: 28,
  },
  cpu: 45.2,
  memory: 15.8,
  disk: 2.1,
  alerts: 2,
}

export default function Dashboard() {
  // TODO: Replace with actual API call
  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: async () => {
      // const response = await fetch('/api/v1/dashboard/stats')
      // return response.json()
      return mockStats
    },
  })

  const statCards = [
    {
      title: 'サービス稼働状況',
      value: `${stats?.services.running || 0} / ${stats?.services.total || 0}`,
      description: '稼働中のサービス数',
      icon: Server,
      color: 'text-green-600',
    },
    {
      title: 'CPU使用率',
      value: `${stats?.cpu || 0}%`,
      description: '現在のCPU使用率',
      icon: Cpu,
      color: 'text-blue-600',
    },
    {
      title: 'メモリ使用量',
      value: `${stats?.memory || 0} GB`,
      description: '32 GB中',
      icon: MemoryStick,
      color: 'text-purple-600',
    },
    {
      title: 'ディスク使用量',
      value: `${stats?.disk || 0} TB`,
      description: '3.4 TB中',
      icon: HardDrive,
      color: 'text-yellow-600',
    },
  ]

  const serviceCategories = [
    {
      title: 'Blog System',
      description: 'WordPressサイト管理',
      icon: Database,
      stats: [
        { label: '稼働サイト数', value: '16' },
        { label: 'コンテナ数', value: '4' },
      ],
      actions: [
        { label: 'サイト一覧', href: '/blog/sites' },
        { label: 'Docker管理', href: '/docker?filter=blog' },
      ],
    },
    {
      title: 'Mailserver',
      description: 'メールサーバー管理',
      icon: Server,
      stats: [
        { label: 'アクティブユーザー', value: '12' },
        { label: 'コンテナ数', value: '9' },
      ],
      actions: [
        { label: 'ユーザー管理', href: '/mailserver/users' },
        { label: 'Docker管理', href: '/docker?filter=mailserver' },
      ],
    },
    {
      title: 'バックアップ',
      description: 'バックアップ・リストア',
      icon: Database,
      stats: [
        { label: '最終バックアップ', value: '2時間前' },
        { label: '成功率', value: '100%' },
      ],
      actions: [
        { label: 'バックアップ実行', href: '/backup/run' },
        { label: 'バックアップ履歴', href: '/backup/history' },
      ],
    },
    {
      title: 'システム設定',
      description: 'システム全般の設定',
      icon: Container,
      stats: [
        { label: 'アラート数', value: String(stats?.alerts || 0) },
        { label: 'ログ件数', value: '1,234' },
      ],
      actions: [
        { label: 'アラート設定', href: '/settings/alerts' },
        { label: 'ログ表示', href: '/logs' },
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
          システム全体の状況を確認できます
        </p>
      </div>

      {/* Alert banner */}
      {stats?.alerts && stats.alerts > 0 && (
        <div className="rounded-lg bg-yellow-50 dark:bg-yellow-900/20 p-4 border border-yellow-200 dark:border-yellow-800">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                {stats.alerts}件のアラートがあります
              </h3>
              <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                システムの確認が必要です。詳細はアラート設定ページをご確認ください。
              </p>
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
