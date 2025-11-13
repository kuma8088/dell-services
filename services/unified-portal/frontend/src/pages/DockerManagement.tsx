import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Container, Play, Square, RotateCw, FileText, AlertCircle } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { dockerAPI } from '@/lib/api'

export default function DockerManagement() {
  const [selectedContainer, setSelectedContainer] = useState<string | null>(null)
  const [logsDialogOpen, setLogsDialogOpen] = useState(false)
  const queryClient = useQueryClient()

  // Query: List containers
  const { data: containers = [], isLoading, error } = useQuery({
    queryKey: ['docker-containers'],
    queryFn: () => dockerAPI.listContainers(),
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  // Query: Container logs
  const { data: logs } = useQuery({
    queryKey: ['docker-logs', selectedContainer],
    queryFn: () => dockerAPI.getContainerLogs(selectedContainer!, 200),
    enabled: !!selectedContainer && logsDialogOpen,
  })

  // Mutation: Start container
  const startMutation = useMutation({
    mutationFn: dockerAPI.startContainer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['docker-containers'] })
    },
  })

  // Mutation: Stop container
  const stopMutation = useMutation({
    mutationFn: dockerAPI.stopContainer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['docker-containers'] })
    },
  })

  // Mutation: Restart container
  const restartMutation = useMutation({
    mutationFn: dockerAPI.restartContainer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['docker-containers'] })
    },
  })

  const handleAction = (containerId: string, action: 'start' | 'stop' | 'restart') => {
    switch (action) {
      case 'start':
        startMutation.mutate(containerId)
        break
      case 'stop':
        stopMutation.mutate(containerId)
        break
      case 'restart':
        restartMutation.mutate(containerId)
        break
    }
  }

  const handleViewLogs = (containerId: string) => {
    setSelectedContainer(containerId)
    setLogsDialogOpen(true)
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <RotateCw className="h-8 w-8 animate-spin mx-auto mb-2 text-primary" />
          <p className="text-muted-foreground">コンテナ一覧を読み込み中...</p>
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
          <p className="text-red-600">コンテナ一覧の取得に失敗しました</p>
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
          Docker管理
        </h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          Dockerコンテナの管理を行います（自動更新: 10秒）
        </p>
      </div>

      {/* Containers list */}
      <Card>
        <CardHeader>
          <CardTitle>コンテナ一覧</CardTitle>
          <CardDescription>
            全{containers?.length || 0}個のコンテナ
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {containers?.map((container) => (
              <div
                key={container.id}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <Container className="h-8 w-8 text-primary" />
                  <div>
                    <h3 className="font-semibold">{container.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {container.image}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div
                      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        container.status === 'running'
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                          : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400'
                      }`}
                    >
                      {container.status}
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleAction(container.id, 'start')}
                      disabled={
                        container.status === 'running' ||
                        startMutation.isPending
                      }
                      title="コンテナを起動"
                    >
                      <Play className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleAction(container.id, 'stop')}
                      disabled={
                        container.status !== 'running' ||
                        stopMutation.isPending
                      }
                      title="コンテナを停止"
                    >
                      <Square className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleAction(container.id, 'restart')}
                      disabled={restartMutation.isPending}
                      title="コンテナを再起動"
                    >
                      <RotateCw
                        className={`h-4 w-4 ${
                          restartMutation.isPending ? 'animate-spin' : ''
                        }`}
                      />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleViewLogs(container.id)}
                      title="ログを表示"
                    >
                      <FileText className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Logs Dialog */}
      <Dialog open={logsDialogOpen} onOpenChange={setLogsDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>コンテナログ</DialogTitle>
            <DialogDescription>
              {selectedContainer &&
                containers?.find(c => c.id === selectedContainer)?.name}
              {logs && ` - ${logs.lines}行`}
            </DialogDescription>
          </DialogHeader>
          <div className="overflow-auto max-h-[60vh]">
            <pre className="bg-black text-green-400 p-4 rounded text-xs font-mono">
              {logs?.logs || 'ログを読み込み中...'}
            </pre>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
