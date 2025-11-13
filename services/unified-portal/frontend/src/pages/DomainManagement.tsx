import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Globe, Plus, RefreshCw, Trash2, Mail, Lock, CheckCircle, XCircle } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'

// Mock data
const mockDomains = [
  {
    domain: 'kuma8088.com',
    type: 'primary',
    mailEnabled: true,
    wordpressEnabled: true,
    sslStatus: 'active',
    dnsStatus: 'valid',
    mailUsers: 5,
    wordpressSites: 4,
  },
  {
    domain: 'webmakeprofit.org',
    type: 'primary',
    mailEnabled: true,
    wordpressEnabled: true,
    sslStatus: 'active',
    dnsStatus: 'valid',
    mailUsers: 3,
    wordpressSites: 1,
  },
  {
    domain: 'uminomoto-shoyu.com',
    type: 'addon',
    mailEnabled: false,
    wordpressEnabled: true,
    sslStatus: 'active',
    dnsStatus: 'valid',
    mailUsers: 0,
    wordpressSites: 1,
  },
]

const mockDnsRecords = [
  { type: 'A', name: '@', value: '172.67.148.123', ttl: 'Auto' },
  { type: 'A', name: 'www', value: '172.67.148.123', ttl: 'Auto' },
  { type: 'MX', name: '@', value: 'route1.mx.cloudflare.net', priority: 85, ttl: 'Auto' },
  { type: 'MX', name: '@', value: 'route2.mx.cloudflare.net', priority: 12, ttl: 'Auto' },
  { type: 'TXT', name: '@', value: 'v=spf1 include:sendgrid.net ~all', ttl: 'Auto' },
  { type: 'CNAME', name: 'blog', value: 'kuma8088.com', ttl: 'Auto' },
]

export default function DomainManagement() {
  const [showAddModal, setShowAddModal] = useState(false)
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'dns' | 'mail' | 'wordpress'>('overview')

  const { data: domains } = useQuery({
    queryKey: ['domains'],
    queryFn: async () => mockDomains,
  })

  const { data: dnsRecords } = useQuery({
    queryKey: ['dns-records', selectedDomain],
    queryFn: async () => {
      if (!selectedDomain) return []
      return mockDnsRecords
    },
    enabled: !!selectedDomain,
  })

  const handleAction = (action: string, domain?: string) => {
    console.log('Action:', action, domain)
    // TODO: Implement API call
  }

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
          ドメイン管理
        </h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          ドメイン・DNS・メール・WordPressの統合管理
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-4 justify-end">
        <Button onClick={() => setShowAddModal(true)}>
          <Plus className="h-4 w-4 mr-2" />
          ドメイン追加
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
            <CardTitle className="text-sm font-medium">総ドメイン数</CardTitle>
            <Globe className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{domains?.length || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">メール有効</CardTitle>
            <Mail className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {domains?.filter((d) => d.mailEnabled).length || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">WP有効</CardTitle>
            <Globe className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {domains?.filter((d) => d.wordpressEnabled).length || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">SSL有効</CardTitle>
            <Lock className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {domains?.filter((d) => d.sslStatus === 'active').length || 0}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Domains list */}
      <Card>
        <CardHeader>
          <CardTitle>ドメイン一覧</CardTitle>
          <CardDescription>
            管理中のドメインとその設定状況
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {domains?.map((domain) => (
              <div
                key={domain.domain}
                className={`flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer ${
                  selectedDomain === domain.domain ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-300' : ''
                }`}
                onClick={() => setSelectedDomain(domain.domain)}
              >
                <div className="flex items-center gap-4">
                  <Globe className="h-8 w-8 text-primary" />
                  <div>
                    <h3 className="font-semibold">{domain.domain}</h3>
                    <div className="flex gap-4 text-sm text-muted-foreground mt-1">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        domain.type === 'primary'
                          ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400'
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400'
                      }`}>
                        {domain.type}
                      </span>
                      {domain.mailEnabled && (
                        <span className="flex items-center gap-1">
                          <Mail className="h-4 w-4" />
                          {domain.mailUsers} ユーザー
                        </span>
                      )}
                      {domain.wordpressEnabled && (
                        <span className="flex items-center gap-1">
                          <Globe className="h-4 w-4" />
                          {domain.wordpressSites} サイト
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="flex gap-2">
                    {domain.sslStatus === 'active' ? (
                      <div className="flex items-center gap-1 text-green-600">
                        <Lock className="h-4 w-4" />
                        <span className="text-sm">SSL</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 text-red-600">
                        <XCircle className="h-4 w-4" />
                        <span className="text-sm">SSL</span>
                      </div>
                    )}

                    {domain.dnsStatus === 'valid' ? (
                      <div className="flex items-center gap-1 text-green-600">
                        <CheckCircle className="h-4 w-4" />
                        <span className="text-sm">DNS</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-1 text-red-600">
                        <XCircle className="h-4 w-4" />
                        <span className="text-sm">DNS</span>
                      </div>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleAction('edit', domain.domain)
                      }}
                    >
                      編集
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleAction('delete', domain.domain)
                      }}
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

      {/* Domain details (if selected) */}
      {selectedDomain && (
        <>
          {/* Tabs */}
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="flex space-x-8">
              {[
                { id: 'overview', label: '概要' },
                { id: 'dns', label: 'DNS設定' },
                { id: 'mail', label: 'メール設定' },
                { id: 'wordpress', label: 'WordPress設定' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`py-4 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-primary text-primary'
                      : 'border-transparent text-gray-600 hover:text-gray-900 dark:text-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab content */}
          {activeTab === 'dns' && (
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>DNS レコード: {selectedDomain}</CardTitle>
                  <CardDescription>
                    DNSレコードの確認と編集
                  </CardDescription>
                </div>
                <Button size="sm" onClick={() => handleAction('add-dns-record')}>
                  <Plus className="h-4 w-4 mr-2" />
                  レコード追加
                </Button>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left p-4 font-medium">タイプ</th>
                        <th className="text-left p-4 font-medium">名前</th>
                        <th className="text-left p-4 font-medium">値</th>
                        <th className="text-left p-4 font-medium">優先度</th>
                        <th className="text-left p-4 font-medium">TTL</th>
                        <th className="text-right p-4 font-medium">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dnsRecords?.map((record, index) => (
                        <tr key={index} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                          <td className="p-4">
                            <span className="px-2 py-1 rounded bg-gray-100 dark:bg-gray-800 text-xs font-medium">
                              {record.type}
                            </span>
                          </td>
                          <td className="p-4 font-mono text-sm">{record.name}</td>
                          <td className="p-4 font-mono text-sm">{record.value}</td>
                          <td className="p-4">{record.priority || '-'}</td>
                          <td className="p-4">{record.ttl}</td>
                          <td className="p-4 text-right">
                            <div className="flex gap-2 justify-end">
                              <Button size="sm" variant="outline">
                                編集
                              </Button>
                              <Button size="sm" variant="outline">
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'mail' && (
            <Card>
              <CardHeader>
                <CardTitle>メール設定: {selectedDomain}</CardTitle>
                <CardDescription>
                  メールアカウントとSMTP設定
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="p-4 border rounded-lg">
                    <h4 className="font-medium mb-2">SMTP設定</h4>
                    <div className="grid gap-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">送信サーバー</span>
                        <span className="font-mono">dell-workstation.tail67811d.ts.net</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">ポート</span>
                        <span className="font-mono">25</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">認証</span>
                        <span>不要（内部ネットワーク）</span>
                      </div>
                    </div>
                  </div>

                  <div className="p-4 border rounded-lg">
                    <h4 className="font-medium mb-2">受信設定</h4>
                    <div className="grid gap-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">MXレコード</span>
                        <span>Cloudflare Email Routing</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">転送先</span>
                        <span>Email Worker → mailserver-api</span>
                      </div>
                    </div>
                  </div>

                  <Button onClick={() => handleAction('manage-mail-users', selectedDomain)}>
                    メールユーザー管理
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {activeTab === 'wordpress' && (
            <Card>
              <CardHeader>
                <CardTitle>WordPress設定: {selectedDomain}</CardTitle>
                <CardDescription>
                  このドメインで稼働中のWordPressサイト
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground mb-4">
                  このドメインには {domains?.find((d) => d.domain === selectedDomain)?.wordpressSites} 個のWordPressサイトがあります
                </p>
                <Button onClick={() => handleAction('view-wp-sites', selectedDomain)}>
                  WordPressサイト一覧を表示
                </Button>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Add domain modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-2xl">
            <CardHeader>
              <CardTitle>ドメイン追加</CardTitle>
              <CardDescription>
                新しいドメインを追加します
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">ドメイン名</label>
                <input
                  type="text"
                  placeholder="example.com"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">タイプ</label>
                <select className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
                  <option value="primary">Primary Domain</option>
                  <option value="addon">Addon Domain</option>
                  <option value="subdomain">Subdomain</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <input type="checkbox" id="enable-mail" defaultChecked />
                <label htmlFor="enable-mail" className="text-sm">
                  メール機能を有効化
                </label>
              </div>

              <div className="flex items-center gap-2">
                <input type="checkbox" id="enable-wordpress" defaultChecked />
                <label htmlFor="enable-wordpress" className="text-sm">
                  WordPress機能を有効化
                </label>
              </div>

              <div className="flex gap-2 pt-4">
                <Button
                  className="flex-1"
                  onClick={() => {
                    handleAction('add-domain')
                    setShowAddModal(false)
                  }}
                >
                  追加
                </Button>
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setShowAddModal(false)}
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
