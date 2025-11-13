import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Database, Plus, Trash2, RefreshCw, Download, Upload, Search } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'

// Mock data - Replace with actual API calls
const mockDatabases = [
  {
    name: 'wp_kuma8088',
    size: '245 MB',
    tables: 87,
    charset: 'utf8mb4',
    collation: 'utf8mb4_unicode_ci',
  },
  {
    name: 'wp_demo1_kuma8088',
    size: '128 MB',
    tables: 45,
    charset: 'utf8mb4',
    collation: 'utf8mb4_unicode_ci',
  },
  {
    name: 'wp_webmakeprofit',
    size: '512 MB',
    tables: 102,
    charset: 'utf8mb4',
    collation: 'utf8mb4_unicode_ci',
  },
  {
    name: 'mailserver_usermgmt',
    size: '12 MB',
    tables: 8,
    charset: 'utf8mb4',
    collation: 'utf8mb4_unicode_ci',
  },
]

const mockUsers = [
  { name: 'root', host: 'localhost', grants: 'ALL PRIVILEGES' },
  { name: 'usermgmt', host: '%', grants: 'SELECT, INSERT, UPDATE, DELETE' },
  { name: 'wordpress', host: '%', grants: 'SELECT, INSERT, UPDATE, DELETE' },
]

export default function DatabaseManagement() {
  const [selectedDb, setSelectedDb] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  const { data: databases } = useQuery({
    queryKey: ['databases'],
    queryFn: async () => {
      // const response = await fetch('/api/v1/database/list')
      // return response.json()
      return mockDatabases
    },
  })

  const { data: users } = useQuery({
    queryKey: ['database-users'],
    queryFn: async () => {
      // const response = await fetch('/api/v1/database/users')
      // return response.json()
      return mockUsers
    },
  })

  const filteredDatabases = databases?.filter((db) =>
    db.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleAction = (action: string, dbName?: string) => {
    console.log(`${action}:`, dbName || 'all')
    // TODO: Implement API call
  }

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
          データベース管理
        </h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          MariaDBデータベースの管理を行います
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
            <div className="text-2xl font-bold">897 MB</div>
            <p className="text-xs text-muted-foreground mt-1">
              使用中のストレージ
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">ユーザー数</CardTitle>
            <Database className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{users?.length || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              登録ユーザー
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
                className={`flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors cursor-pointer ${
                  selectedDb === db.name ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-700' : ''
                }`}
                onClick={() => setSelectedDb(db.name)}
              >
                <div className="flex items-center gap-4">
                  <Database className="h-8 w-8 text-primary" />
                  <div>
                    <h3 className="font-semibold">{db.name}</h3>
                    <div className="flex gap-4 text-sm text-muted-foreground mt-1">
                      <span>{db.tables} テーブル</span>
                      <span>{db.charset}</span>
                      <span>{db.collation}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <p className="text-sm font-medium">{db.size}</p>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleAction('export', db.name)
                      }}
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

      {/* Database users */}
      <Card>
        <CardHeader>
          <CardTitle>データベースユーザー</CardTitle>
          <CardDescription>
            登録されているユーザー一覧
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left p-4 font-medium">ユーザー名</th>
                  <th className="text-left p-4 font-medium">ホスト</th>
                  <th className="text-left p-4 font-medium">権限</th>
                  <th className="text-right p-4 font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {users?.map((user) => (
                  <tr key={`${user.name}@${user.host}`} className="border-b hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="p-4 font-medium">{user.name}</td>
                    <td className="p-4">{user.host}</td>
                    <td className="p-4 text-sm text-muted-foreground">
                      {user.grants}
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex gap-2 justify-end">
                        <Button size="sm" variant="outline">
                          編集
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={user.name === 'root'}
                        >
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

      {/* Query executor (if database selected) */}
      {selectedDb && (
        <Card>
          <CardHeader>
            <CardTitle>SQLクエリ実行</CardTitle>
            <CardDescription>
              {selectedDb} に対してSQLクエリを実行
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <textarea
              placeholder="SELECT * FROM wp_posts LIMIT 10;"
              className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none font-mono"
            />
            <div className="flex gap-2">
              <Button onClick={() => handleAction('execute', selectedDb)}>
                クエリ実行
              </Button>
              <Button
                variant="outline"
                onClick={() => handleAction('explain', selectedDb)}
              >
                EXPLAIN
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
