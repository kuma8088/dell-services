import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Container, Play, Square, RotateCw, FileText } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'

// Mock data - Replace with actual API calls
const mockContainers = [
  {
    id: 'abc123',
    name: 'blog-wordpress',
    status: 'running',
    image: 'wordpress:latest',
    uptime: '2 days',
  },
  {
    id: 'def456',
    name: 'mailserver-postfix',
    status: 'running',
    image: 'postfix:latest',
    uptime: '5 days',
  },
  {
    id: 'ghi789',
    name: 'unified-portal-backend',
    status: 'running',
    image: 'python:3.11',
    uptime: '1 hour',
  },
]

export default function DockerManagement() {
  const [selectedContainer, setSelectedContainer] = useState<string | null>(null)

  const { data: containers } = useQuery({
    queryKey: ['docker-containers'],
    queryFn: async () => {
      // const response = await fetch('/api/v1/docker/containers')
      // return response.json()
      return mockContainers
    },
  })

  const handleAction = (containerId: string, action: string) => {
    console.log(`${action} container:`, containerId)
    // TODO: Implement API call
  }

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
          Docker管理
        </h2>
        <p className="mt-2 text-sm text-gray-600 dark:text-gray-300">
          Dockerコンテナの管理を行います
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
                    <p className="text-sm text-muted-foreground mt-1">
                      稼働時間: {container.uptime}
                    </p>
                  </div>

                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleAction(container.id, 'start')}
                      disabled={container.status === 'running'}
                    >
                      <Play className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleAction(container.id, 'stop')}
                      disabled={container.status !== 'running'}
                    >
                      <Square className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleAction(container.id, 'restart')}
                    >
                      <RotateCw className="h-4 w-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setSelectedContainer(container.id)}
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
    </div>
  )
}
