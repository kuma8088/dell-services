import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Globe, Plus, RefreshCw, Trash2, Mail, Lock, CheckCircle, AlertCircle, ExternalLink, Edit, Download, Upload, Search } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  listZones,
  getDNSRecords,
  createDNSRecord,
  updateDNSRecord,
  deleteDNSRecord,
  importDNSRecords,
  verifyDNSRecord,
  type Zone,
  type DNSRecord,
  type DNSRecordCreate,
  type DNSRecordUpdate,
  type DNSRecordImportResult,
  type DNSVerificationResult,
} from '@/lib/domains-api'

// Extended domain interface with metadata
interface DomainMetadata extends Zone {
  mailEnabled: boolean
  wordpressEnabled: boolean
  sslStatus: 'active' | 'pending' | 'error'
  mailUsers: number
  wordpressSites: number
}

export default function DomainManagement() {
  const [showDNSModal, setShowDNSModal] = useState(false)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editingRecord, setEditingRecord] = useState<DNSRecord | null>(null)
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'dns' | 'mail' | 'wordpress'>('overview')
  const [dnsFormData, setDnsFormData] = useState<Partial<DNSRecordCreate>>({
    type: 'A',
    ttl: 1,
    proxied: false,
  })
  const [editFormData, setEditFormData] = useState<DNSRecordUpdate>({})
  const [selectedRecords, setSelectedRecords] = useState<Set<string>>(new Set())
  const [showImportModal, setShowImportModal] = useState(false)
  const [importResult, setImportResult] = useState<DNSRecordImportResult | null>(null)
  const [showVerifyModal, setShowVerifyModal] = useState(false)
  const [verifyingRecord, setVerifyingRecord] = useState<DNSRecord | null>(null)
  const [verifyResult, setVerifyResult] = useState<DNSVerificationResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const queryClient = useQueryClient()

  // Fetch Cloudflare zones
  const { data: zones, isLoading: zonesLoading, error: zonesError } = useQuery({
    queryKey: ['cloudflare-zones'],
    queryFn: listZones,
  })

  // Fetch DNS records for selected domain
  const { data: dnsRecords, isLoading: dnsLoading } = useQuery({
    queryKey: ['dns-records', selectedDomain],
    queryFn: () => getDNSRecords(selectedDomain!),
    enabled: !!selectedDomain && activeTab === 'dns',
  })

  // Clear selection when domain changes
  React.useEffect(() => {
    setSelectedRecords(new Set())
  }, [selectedDomain])

  // Create DNS record mutation
  const createRecordMutation = useMutation({
    mutationFn: ({ domain, record }: { domain: string; record: DNSRecordCreate }) =>
      createDNSRecord(domain, record),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dns-records', selectedDomain] })
      setShowDNSModal(false)
      setDnsFormData({ type: 'A', ttl: 1, proxied: false })
      setError(null)
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to create DNS record')
    },
  })

  // Update DNS record mutation
  const updateRecordMutation = useMutation({
    mutationFn: ({ domain, recordId, record }: { domain: string; recordId: string; record: DNSRecordUpdate }) =>
      updateDNSRecord(domain, recordId, record),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dns-records', selectedDomain] })
      setShowEditModal(false)
      setEditingRecord(null)
      setEditFormData({})
      setError(null)
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to update DNS record')
    },
  })

  // Delete DNS record mutation
  const deleteRecordMutation = useMutation({
    mutationFn: ({ domain, recordId }: { domain: string; recordId: string }) =>
      deleteDNSRecord(domain, recordId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dns-records', selectedDomain] })
    },
    onError: (err: any) => {
      setError(err.response?.data?.detail || 'Failed to delete DNS record')
    },
  })

  // Import DNS records mutation
  const importRecordsMutation = useMutation({
    mutationFn: ({ domain, file }: { domain: string; file: File }) =>
      importDNSRecords(domain, file),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['dns-records', selectedDomain] })
      setImportResult(result)
      setError(null)
    },
    onError: (err: any) => {
      setError(err.message || 'Failed to import DNS records')
    },
  })

  // Verify DNS record mutation
  const verifyRecordMutation = useMutation({
    mutationFn: ({ domain, recordType, recordName, expectedContent }: {
      domain: string
      recordType: string
      recordName: string
      expectedContent?: string
    }) => verifyDNSRecord(domain, recordType, recordName, expectedContent),
    onSuccess: (result) => {
      setVerifyResult(result)
      setError(null)
    },
    onError: (err: any) => {
      setError(err.message || 'Failed to verify DNS record')
    },
  })

  // Convert zones to domains with metadata (mock data for now)
  const domains: DomainMetadata[] = zones?.map((zone) => ({
    ...zone,
    mailEnabled: true, // TODO: Fetch from backend
    wordpressEnabled: true, // TODO: Fetch from backend
    sslStatus: zone.status === 'active' ? 'active' : 'pending',
    mailUsers: 0, // TODO: Fetch from mailserver API
    wordpressSites: 0, // TODO: Fetch from WordPress API
  })) || []

  const handleCreateDNSRecord = () => {
    if (!selectedDomain || !dnsFormData.type || !dnsFormData.name || !dnsFormData.content) {
      setError('Please fill in all required fields')
      return
    }

    createRecordMutation.mutate({
      domain: selectedDomain,
      record: dnsFormData as DNSRecordCreate,
    })
  }

  const handleEditDNSRecord = (record: DNSRecord) => {
    setEditingRecord(record)
    setEditFormData({
      content: record.content,
      ttl: record.ttl,
      proxied: record.proxied,
      priority: record.priority,
    })
    setShowEditModal(true)
    setError(null)
  }

  const handleUpdateDNSRecord = () => {
    if (!selectedDomain || !editingRecord) return

    updateRecordMutation.mutate({
      domain: selectedDomain,
      recordId: editingRecord.id,
      record: editFormData,
    })
  }

  const handleDeleteDNSRecord = (recordId: string) => {
    if (!selectedDomain) return
    if (!confirm('Are you sure you want to delete this DNS record?')) return

    deleteRecordMutation.mutate({ domain: selectedDomain, recordId })
  }

  const handleToggleRecord = (recordId: string) => {
    setSelectedRecords((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(recordId)) {
        newSet.delete(recordId)
      } else {
        newSet.add(recordId)
      }
      return newSet
    })
  }

  const handleToggleAllRecords = () => {
    if (!dnsRecords) return

    if (selectedRecords.size === dnsRecords.length) {
      setSelectedRecords(new Set())
    } else {
      setSelectedRecords(new Set(dnsRecords.map((r) => r.id)))
    }
  }

  const handleBulkDelete = async () => {
    if (!selectedDomain || selectedRecords.size === 0) return

    if (!confirm(`本当に ${selectedRecords.size} 件のDNSレコードを削除しますか？`)) return

    const recordIds = Array.from(selectedRecords)
    let successCount = 0
    let errorCount = 0

    for (const recordId of recordIds) {
      try {
        await deleteDNSRecord(selectedDomain, recordId)
        successCount++
      } catch (err) {
        errorCount++
        console.error(`Failed to delete record ${recordId}:`, err)
      }
    }

    queryClient.invalidateQueries({ queryKey: ['dns-records', selectedDomain] })
    setSelectedRecords(new Set())

    if (errorCount > 0) {
      setError(`${successCount}件削除成功、${errorCount}件失敗しました`)
    }
  }

  const handleExportCSV = () => {
    if (!dnsRecords || dnsRecords.length === 0) return

    // CSV header
    const headers = ['Type', 'Name', 'Content', 'TTL', 'Proxied', 'Priority']

    // Convert records to CSV rows
    const rows = dnsRecords.map((record) => [
      record.type,
      record.name,
      record.content,
      record.ttl.toString(),
      record.proxied ? 'Yes' : 'No',
      record.priority?.toString() || '',
    ])

    // Combine headers and rows
    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
    ].join('\n')

    // Create blob and download
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)

    link.setAttribute('href', url)
    link.setAttribute('download', `dns-records-${selectedDomain}-${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'

    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleImportCSV = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !selectedDomain) return

    importRecordsMutation.mutate({ domain: selectedDomain, file })
    setShowImportModal(true)

    // Reset file input
    event.target.value = ''
  }

  const handleVerifyDNSRecord = (record: DNSRecord) => {
    if (!selectedDomain) return

    setVerifyingRecord(record)
    setShowVerifyModal(true)
    setVerifyResult(null)

    verifyRecordMutation.mutate({
      domain: selectedDomain,
      recordType: record.type,
      recordName: record.name,
      expectedContent: record.content,
    })
  }

  const handleAction = (action: string, domain?: string) => {
    console.log('Action:', action, domain)
    // TODO: Implement other actions
  }

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
          ドメイン管理
        </h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          ドメイン・DNS・メール・WordPressの統合管理（Cloudflare統合）
        </p>
      </div>

      {/* Error banner */}
      {(error || zonesError) && (
        <Card className="border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
              <AlertCircle className="h-5 w-5" />
              <p className="text-sm">
                {error || (zonesError as any)?.response?.data?.detail || 'An error occurred'}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading state */}
      {zonesLoading && (
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">
              Loading Cloudflare zones...
            </p>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      {!zonesLoading && (
        <div className="flex gap-4 justify-end">
          <Button
            variant="outline"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['cloudflare-zones'] })}
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            更新
          </Button>
        </div>
      )}

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
      {!zonesLoading && domains && (
        <Card>
          <CardHeader>
            <CardTitle>ドメイン一覧（Cloudflare）</CardTitle>
            <CardDescription>
              管理中のドメインとその設定状況 - 全{domains.length}ドメイン
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {domains.map((domain) => (
                <div
                  key={domain.id}
                  className={`flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer ${
                    selectedDomain === domain.name ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-300' : ''
                  }`}
                  onClick={() => setSelectedDomain(domain.name)}
                >
                  <div className="flex items-center gap-4">
                    <Globe className="h-8 w-8 text-primary" />
                    <div>
                      <h3 className="font-semibold">{domain.name}</h3>
                      <div className="flex gap-4 text-sm text-muted-foreground mt-1">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          domain.status === 'active'
                            ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                            : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400'
                        }`}>
                          {domain.status}
                        </span>
                        {domain.mailEnabled && (
                          <span className="flex items-center gap-1">
                            <Mail className="h-4 w-4" />
                            Mail有効
                          </span>
                        )}
                        {domain.wordpressEnabled && (
                          <span className="flex items-center gap-1">
                            <Globe className="h-4 w-4" />
                            WP有効
                          </span>
                        )}
                      </div>
                      <div className="flex gap-2 text-xs text-muted-foreground mt-1">
                        <span>NS: {domain.name_servers.slice(0, 2).join(', ')}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="flex gap-2">
                      {domain.sslStatus === 'active' ? (
                        <div className="flex items-center gap-1 text-green-600">
                          <CheckCircle className="h-4 w-4" />
                          <span className="text-sm">Active</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1 text-yellow-600">
                          <AlertCircle className="h-4 w-4" />
                          <span className="text-sm">Pending</span>
                        </div>
                      )}
                    </div>

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation()
                        window.open(`https://dash.cloudflare.com/${domain.id}/dns`, '_blank')
                      }}
                    >
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Cloudflareで管理
                    </Button>

                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation()
                        setActiveTab('dns')
                      }}
                    >
                      DNS管理
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

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
                    Cloudflare DNSレコードの確認と編集
                  </CardDescription>
                </div>
                <div className="flex gap-2">
                  {selectedRecords.size > 0 && (
                    <Button
                      size="sm"
                      variant="destructive"
                      onClick={handleBulkDelete}
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      {selectedRecords.size}件削除
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={handleExportCSV}
                    disabled={!dnsRecords || dnsRecords.length === 0}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    CSV出力
                  </Button>
                  <label>
                    <input
                      type="file"
                      accept=".csv"
                      onChange={handleImportCSV}
                      style={{ display: 'none' }}
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.preventDefault()
                        const input = e.currentTarget.parentElement?.querySelector('input[type="file"]') as HTMLInputElement
                        input?.click()
                      }}
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      CSV取込
                    </Button>
                  </label>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      const zone = domains.find((d) => d.name === selectedDomain)
                      if (zone) {
                        window.open(`https://dash.cloudflare.com/${zone.id}/dns`, '_blank')
                      }
                    }}
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Cloudflareで管理
                  </Button>
                  <Button size="sm" onClick={() => setShowDNSModal(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    レコード追加
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {dnsLoading ? (
                  <p className="text-center text-muted-foreground py-8">
                    Loading DNS records...
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b">
                          <th className="p-4 w-12">
                            <input
                              type="checkbox"
                              checked={dnsRecords && dnsRecords.length > 0 && selectedRecords.size === dnsRecords.length}
                              onChange={handleToggleAllRecords}
                              className="rounded border-gray-300"
                            />
                          </th>
                          <th className="text-left p-4 font-medium">タイプ</th>
                          <th className="text-left p-4 font-medium">名前</th>
                          <th className="text-left p-4 font-medium">値</th>
                          <th className="text-left p-4 font-medium">Proxied</th>
                          <th className="text-left p-4 font-medium">TTL</th>
                          <th className="text-right p-4 font-medium">操作</th>
                        </tr>
                      </thead>
                      <tbody>
                        {dnsRecords?.map((record) => (
                          <tr key={record.id} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                            <td className="p-4">
                              <input
                                type="checkbox"
                                checked={selectedRecords.has(record.id)}
                                onChange={() => handleToggleRecord(record.id)}
                                className="rounded border-gray-300"
                              />
                            </td>
                            <td className="p-4">
                              <span className="px-2 py-1 rounded bg-gray-100 dark:bg-gray-800 text-xs font-medium">
                                {record.type}
                              </span>
                            </td>
                            <td className="p-4 font-mono text-sm">{record.name}</td>
                            <td className="p-4 font-mono text-sm max-w-md truncate">
                              {record.content}
                            </td>
                            <td className="p-4">
                              {record.proxied ? (
                                <span className="text-orange-600">Yes</span>
                              ) : (
                                <span className="text-gray-600">No</span>
                              )}
                            </td>
                            <td className="p-4">{record.ttl === 1 ? 'Auto' : record.ttl}</td>
                            <td className="p-4 text-right">
                              <div className="flex gap-2 justify-end">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleVerifyDNSRecord(record)}
                                  disabled={verifyRecordMutation.isPending}
                                  title="DNS検証"
                                >
                                  <Search className="h-4 w-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleEditDNSRecord(record)}
                                  disabled={updateRecordMutation.isPending}
                                >
                                  <Edit className="h-4 w-4" />
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleDeleteDNSRecord(record.id)}
                                  disabled={deleteRecordMutation.isPending}
                                >
                                  <Trash2 className="h-4 w-4" />
                                </Button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {dnsRecords?.length === 0 && (
                      <p className="text-center text-muted-foreground py-8">
                        No DNS records found
                      </p>
                    )}
                  </div>
                )}
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
                  このドメインには {domains?.find((d) => d.name === selectedDomain)?.wordpressSites} 個のWordPressサイトがあります
                </p>
                <Button onClick={() => handleAction('view-wp-sites', selectedDomain)}>
                  WordPressサイト一覧を表示
                </Button>
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* DNS record creation modal */}
      {showDNSModal && selectedDomain && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-2xl">
            <CardHeader>
              <CardTitle>DNSレコード追加: {selectedDomain}</CardTitle>
              <CardDescription>
                新しいDNSレコードを作成します
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">レコードタイプ *</label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={dnsFormData.type}
                  onChange={(e) => setDnsFormData({ ...dnsFormData, type: e.target.value })}
                >
                  <option value="A">A - IPv4 Address</option>
                  <option value="AAAA">AAAA - IPv6 Address</option>
                  <option value="CNAME">CNAME - Canonical Name</option>
                  <option value="MX">MX - Mail Exchange</option>
                  <option value="TXT">TXT - Text Record</option>
                  <option value="NS">NS - Name Server</option>
                  <option value="SRV">SRV - Service Record</option>
                </select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">名前 *</label>
                <input
                  type="text"
                  placeholder="@ または サブドメイン (例: www)"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={dnsFormData.name || ''}
                  onChange={(e) => setDnsFormData({ ...dnsFormData, name: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">値 *</label>
                <input
                  type="text"
                  placeholder={
                    dnsFormData.type === 'A'
                      ? '例: 192.0.2.1'
                      : dnsFormData.type === 'CNAME'
                      ? '例: example.com'
                      : dnsFormData.type === 'MX'
                      ? '例: mail.example.com'
                      : '値を入力'
                  }
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={dnsFormData.content || ''}
                  onChange={(e) => setDnsFormData({ ...dnsFormData, content: e.target.value })}
                />
              </div>

              {dnsFormData.type === 'MX' && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">優先度</label>
                  <input
                    type="number"
                    placeholder="例: 10"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={dnsFormData.priority || ''}
                    onChange={(e) => setDnsFormData({ ...dnsFormData, priority: parseInt(e.target.value) })}
                  />
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium">TTL</label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={dnsFormData.ttl}
                  onChange={(e) => setDnsFormData({ ...dnsFormData, ttl: parseInt(e.target.value) })}
                >
                  <option value={1}>Auto</option>
                  <option value={60}>1 min</option>
                  <option value={300}>5 min</option>
                  <option value={3600}>1 hour</option>
                  <option value={86400}>1 day</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="proxied"
                  checked={dnsFormData.proxied}
                  onChange={(e) => setDnsFormData({ ...dnsFormData, proxied: e.target.checked })}
                />
                <label htmlFor="proxied" className="text-sm">
                  Cloudflareプロキシを有効化（オレンジクラウド）
                </label>
              </div>

              <div className="flex gap-2 pt-4">
                <Button
                  className="flex-1"
                  onClick={handleCreateDNSRecord}
                  disabled={createRecordMutation.isPending}
                >
                  {createRecordMutation.isPending ? '作成中...' : '作成'}
                </Button>
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => {
                    setShowDNSModal(false)
                    setDnsFormData({ type: 'A', ttl: 1, proxied: false })
                    setError(null)
                  }}
                >
                  キャンセル
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* DNS record edit modal */}
      {showEditModal && editingRecord && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-2xl">
            <CardHeader>
              <CardTitle>DNSレコード編集: {editingRecord.name}</CardTitle>
              <CardDescription>
                DNSレコードの設定を変更します
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">レコードタイプ</label>
                <input
                  type="text"
                  value={editingRecord.type}
                  disabled
                  className="flex h-10 w-full rounded-md border border-input bg-muted px-3 py-2 text-sm cursor-not-allowed"
                />
                <p className="text-xs text-muted-foreground">レコードタイプは変更できません</p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">名前</label>
                <input
                  type="text"
                  value={editingRecord.name}
                  disabled
                  className="flex h-10 w-full rounded-md border border-input bg-muted px-3 py-2 text-sm cursor-not-allowed font-mono"
                />
                <p className="text-xs text-muted-foreground">レコード名は変更できません</p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">値 *</label>
                <input
                  type="text"
                  placeholder={
                    editingRecord.type === 'A'
                      ? '例: 192.0.2.1'
                      : editingRecord.type === 'CNAME'
                      ? '例: example.com'
                      : editingRecord.type === 'MX'
                      ? '例: mail.example.com'
                      : '値を入力'
                  }
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono"
                  value={editFormData.content || ''}
                  onChange={(e) => setEditFormData({ ...editFormData, content: e.target.value })}
                />
              </div>

              {(editingRecord.type === 'MX' || editingRecord.priority !== undefined) && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">優先度</label>
                  <input
                    type="number"
                    placeholder="例: 10"
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    value={editFormData.priority ?? ''}
                    onChange={(e) => setEditFormData({ ...editFormData, priority: parseInt(e.target.value) || undefined })}
                  />
                </div>
              )}

              <div className="space-y-2">
                <label className="text-sm font-medium">TTL</label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={editFormData.ttl ?? editingRecord.ttl}
                  onChange={(e) => setEditFormData({ ...editFormData, ttl: parseInt(e.target.value) })}
                >
                  <option value={1}>Auto</option>
                  <option value={60}>1 min</option>
                  <option value={300}>5 min</option>
                  <option value={3600}>1 hour</option>
                  <option value={86400}>1 day</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="proxied-edit"
                  checked={editFormData.proxied ?? editingRecord.proxied}
                  onChange={(e) => setEditFormData({ ...editFormData, proxied: e.target.checked })}
                />
                <label htmlFor="proxied-edit" className="text-sm">
                  Cloudflareプロキシを有効化（オレンジクラウド）
                </label>
              </div>

              <div className="flex gap-2 pt-4">
                <Button
                  className="flex-1"
                  onClick={handleUpdateDNSRecord}
                  disabled={updateRecordMutation.isPending}
                >
                  {updateRecordMutation.isPending ? '更新中...' : '更新'}
                </Button>
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => {
                    setShowEditModal(false)
                    setEditingRecord(null)
                    setEditFormData({})
                    setError(null)
                  }}
                >
                  キャンセル
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Import Result Modal */}
      {showImportModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => {
            setShowImportModal(false)
            setImportResult(null)
          }}
        >
          <Card
            className="w-full max-w-2xl max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <CardHeader>
              <CardTitle>CSV取込結果</CardTitle>
              <CardDescription>
                DNSレコードの取込結果を表示しています
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {importRecordsMutation.isPending && (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-8 w-8 animate-spin text-primary" />
                  <p className="ml-4 text-muted-foreground">CSVファイルを処理中...</p>
                </div>
              )}

              {importResult && (
                <>
                  <div className="flex items-center gap-4 p-4 bg-muted rounded-lg">
                    <div className="flex-1">
                      <p className="text-sm font-medium">成功: {importResult.success_count}件</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        {importResult.error_count > 0
                          ? `エラー: ${importResult.error_count}件`
                          : '全てのレコードが正常に取り込まれました'}
                      </p>
                    </div>
                    {importResult.error_count === 0 && (
                      <CheckCircle className="h-8 w-8 text-green-600" />
                    )}
                    {importResult.error_count > 0 && (
                      <AlertCircle className="h-8 w-8 text-yellow-600" />
                    )}
                  </div>

                  {importResult.errors.length > 0 && (
                    <div className="space-y-2">
                      <h3 className="text-sm font-medium">エラー詳細</h3>
                      <div className="space-y-2 max-h-[300px] overflow-y-auto">
                        {importResult.errors.map((error, idx) => (
                          <div
                            key={idx}
                            className="p-3 bg-red-50 dark:bg-red-900/20 rounded border border-red-200 dark:border-red-800"
                          >
                            <p className="text-sm font-medium text-red-900 dark:text-red-200">
                              行 {error.row}:
                            </p>
                            <p className="text-xs text-red-700 dark:text-red-300 mt-1">
                              {error.error}
                            </p>
                            <div className="mt-2 text-xs text-muted-foreground">
                              <pre className="bg-black/5 dark:bg-white/5 p-2 rounded overflow-x-auto">
                                {JSON.stringify(error.record, null, 2)}
                              </pre>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              <div className="flex gap-2 pt-4">
                <Button
                  className="flex-1"
                  onClick={() => {
                    setShowImportModal(false)
                    setImportResult(null)
                  }}
                >
                  閉じる
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* DNS Verification Modal */}
      {showVerifyModal && verifyingRecord && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => {
            setShowVerifyModal(false)
            setVerifyingRecord(null)
            setVerifyResult(null)
          }}
        >
          <Card
            className="w-full max-w-3xl max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <CardHeader>
              <CardTitle>DNS伝播検証: {verifyingRecord.name}</CardTitle>
              <CardDescription>
                複数のDNSサーバーからレコードの伝播状況を確認しています
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {verifyRecordMutation.isPending && (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-8 w-8 animate-spin text-primary" />
                  <p className="ml-4 text-muted-foreground">DNS検証中...</p>
                </div>
              )}

              {verifyResult && (
                <>
                  {/* Overall Status */}
                  <div
                    className={`flex items-center gap-4 p-4 rounded-lg ${
                      verifyResult.propagated
                        ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                        : 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800'
                    }`}
                  >
                    <div className="flex-1">
                      <p className="text-sm font-medium">
                        {verifyResult.propagated
                          ? 'DNSレコードは正常に伝播しています'
                          : 'DNSレコードの伝播が完了していません'}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        タイプ: {verifyResult.record_type} | 期待値: {verifyResult.expected_content}
                      </p>
                    </div>
                    {verifyResult.propagated ? (
                      <CheckCircle className="h-8 w-8 text-green-600" />
                    ) : (
                      <AlertCircle className="h-8 w-8 text-yellow-600" />
                    )}
                  </div>

                  {/* Server Results */}
                  <div className="space-y-3">
                    <h3 className="text-sm font-medium">DNSサーバー別結果</h3>
                    {verifyResult.servers.map((server, idx) => (
                      <div
                        key={idx}
                        className={`p-4 rounded-lg border ${
                          server.status === 'success'
                            ? 'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-800'
                            : server.status === 'timeout'
                            ? 'bg-gray-50 dark:bg-gray-900/10 border-gray-200 dark:border-gray-800'
                            : 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium">{server.server}</p>
                            {server.status === 'success' && (
                              <CheckCircle className="h-4 w-4 text-green-600" />
                            )}
                            {server.status === 'failed' && (
                              <AlertCircle className="h-4 w-4 text-red-600" />
                            )}
                            {server.status === 'timeout' && (
                              <AlertCircle className="h-4 w-4 text-gray-600" />
                            )}
                          </div>
                          <span
                            className={`text-xs px-2 py-1 rounded ${
                              server.status === 'success'
                                ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
                                : server.status === 'timeout'
                                ? 'bg-gray-100 dark:bg-gray-900 text-gray-800 dark:text-gray-200'
                                : 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200'
                            }`}
                          >
                            {server.status}
                          </span>
                        </div>

                        {server.records.length > 0 && (
                          <div className="mt-2">
                            <p className="text-xs text-muted-foreground mb-1">検出されたレコード:</p>
                            <div className="space-y-1">
                              {server.records.map((record, ridx) => (
                                <div
                                  key={ridx}
                                  className="text-xs font-mono bg-black/5 dark:bg-white/5 p-2 rounded"
                                >
                                  {record}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {server.error && (
                          <p className="text-xs text-red-600 dark:text-red-400 mt-2">
                            エラー: {server.error}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}

              <div className="flex gap-2 pt-4">
                <Button
                  className="flex-1"
                  onClick={() => {
                    setShowVerifyModal(false)
                    setVerifyingRecord(null)
                    setVerifyResult(null)
                  }}
                >
                  閉じる
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
