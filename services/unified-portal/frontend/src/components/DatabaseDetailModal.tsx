import { useQuery } from '@tanstack/react-query'
import { X, Database, Table, FileText, Loader2, AlertCircle } from 'lucide-react'
import { databaseAPI } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'

interface DatabaseDetailModalProps {
  isOpen: boolean
  onClose: () => void
  databaseName: string | null
}

export default function DatabaseDetailModal({
  isOpen,
  onClose,
  databaseName,
}: DatabaseDetailModalProps) {
  // Query: Database detail
  const { data: detail, isLoading, error } = useQuery({
    queryKey: ['database-detail', databaseName],
    queryFn: () => databaseAPI.getDatabaseDetail(databaseName!),
    enabled: isOpen && !!databaseName,
  })

  if (!isOpen || !databaseName) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <Database className="h-6 w-6 text-primary" />
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
              {databaseName}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-primary" />
                <p className="text-muted-foreground">データベース詳細を読み込み中...</p>
              </div>
            </div>
          )}

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                データベース詳細の取得に失敗しました: {error instanceof Error ? error.message : '不明なエラー'}
              </AlertDescription>
            </Alert>
          )}

          {detail && (
            <div className="space-y-6">
              {/* Statistics Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Database className="h-4 w-4 text-blue-600" />
                    <span className="text-sm font-medium text-blue-900 dark:text-blue-100">
                      データベースサイズ
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-blue-900 dark:text-blue-100">
                    {detail.size_mb.toFixed(2)} MB
                  </div>
                </div>

                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Table className="h-4 w-4 text-green-600" />
                    <span className="text-sm font-medium text-green-900 dark:text-green-100">
                      テーブル数
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-green-900 dark:text-green-100">
                    {detail.tables_count}
                  </div>
                </div>

                <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <FileText className="h-4 w-4 text-amber-600" />
                    <span className="text-sm font-medium text-amber-900 dark:text-amber-100">
                      総レコード数
                    </span>
                  </div>
                  <div className="text-2xl font-bold text-amber-900 dark:text-amber-100">
                    {detail.rows_count.toLocaleString()}
                  </div>
                </div>
              </div>

              {/* Database Information */}
              <div className="bg-gray-50 dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
                <h4 className="font-semibold mb-3 text-gray-900 dark:text-white">
                  データベース情報
                </h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">データベース名:</span>
                    <span className="font-mono font-medium text-gray-900 dark:text-white">
                      {detail.name}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">テーブル数:</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {detail.tables_count} テーブル
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">総レコード数:</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {detail.rows_count.toLocaleString()} 行
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">使用容量:</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {detail.size_mb.toFixed(2)} MB
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">平均レコードサイズ:</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {detail.rows_count > 0
                        ? ((detail.size_mb * 1024) / detail.rows_count).toFixed(2) + ' KB'
                        : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <Button variant="outline" onClick={onClose}>
                  閉じる
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
