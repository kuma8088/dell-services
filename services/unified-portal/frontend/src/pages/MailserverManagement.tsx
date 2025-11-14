/**
 * MailserverManagement Page
 *
 * Mailserver user and domain management interface
 */

import { useState } from 'react'
import { Mail, Users, FolderKey, ScrollText } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DomainList } from '@/components/mailserver/DomainList'
import { DomainForm } from '@/components/mailserver/DomainForm'
import { UserList } from '@/components/mailserver/UserList'
import { UserForm } from '@/components/mailserver/UserForm'
import { AuditLogList } from '@/components/mailserver/AuditLogList'
import type { MailDomain, MailUser } from '@/types/mailserver'

type ViewMode = 'domains' | 'users' | 'audit' | 'domain-form' | 'user-form'

export default function MailserverManagement() {
  const [viewMode, setViewMode] = useState<ViewMode>('domains')
  const [selectedDomain, setSelectedDomain] = useState<MailDomain | null>(null)
  const [selectedUser, setSelectedUser] = useState<MailUser | null>(null)
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleDomainCreate = () => {
    setSelectedDomain(null)
    setViewMode('domain-form')
  }

  const handleDomainEdit = (domain: MailDomain) => {
    setSelectedDomain(domain)
    setViewMode('domain-form')
  }

  const handleDomainFormSuccess = () => {
    setViewMode('domains')
    setSelectedDomain(null)
    setRefreshTrigger((prev) => prev + 1)
  }

  const handleUserCreate = (domain?: MailDomain) => {
    setSelectedUser(null)
    setSelectedDomain(domain || null)
    setViewMode('user-form')
  }

  const handleUserEdit = (user: MailUser) => {
    setSelectedUser(user)
    setViewMode('user-form')
  }

  const handleUserFormSuccess = () => {
    setViewMode('users')
    setSelectedUser(null)
    setSelectedDomain(null)
    setRefreshTrigger((prev) => prev + 1)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Mail className="h-8 w-8" />
            Mailserver管理
          </h1>
          <p className="text-muted-foreground mt-2">
            メールドメイン・ユーザー管理と監査ログ
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-2">
            <Button
              variant={viewMode === 'domains' ? 'default' : 'outline'}
              onClick={() => setViewMode('domains')}
              className="flex items-center gap-2"
            >
              <FolderKey className="h-4 w-4" />
              ドメイン管理
            </Button>
            <Button
              variant={viewMode === 'users' ? 'default' : 'outline'}
              onClick={() => setViewMode('users')}
              className="flex items-center gap-2"
            >
              <Users className="h-4 w-4" />
              ユーザー管理
            </Button>
            <Button
              variant={viewMode === 'audit' ? 'default' : 'outline'}
              onClick={() => setViewMode('audit')}
              className="flex items-center gap-2"
            >
              <ScrollText className="h-4 w-4" />
              監査ログ
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Content Area */}
      {viewMode === 'domains' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={handleDomainCreate}>
              ドメイン新規作成
            </Button>
          </div>
          <DomainList
            onEdit={handleDomainEdit}
            onCreateUser={handleUserCreate}
            refreshTrigger={refreshTrigger}
          />
        </div>
      )}

      {viewMode === 'domain-form' && (
        <div className="max-w-2xl">
          <DomainForm
            domain={selectedDomain}
            onSuccess={handleDomainFormSuccess}
            onCancel={() => setViewMode('domains')}
          />
        </div>
      )}

      {viewMode === 'users' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => handleUserCreate()}>
              ユーザー新規作成
            </Button>
          </div>
          <UserList
            onEdit={handleUserEdit}
            refreshTrigger={refreshTrigger}
          />
        </div>
      )}

      {viewMode === 'user-form' && (
        <div className="max-w-2xl">
          <UserForm
            user={selectedUser}
            preselectedDomainId={selectedDomain?.id || null}
            onSuccess={handleUserFormSuccess}
            onCancel={() => setViewMode('users')}
          />
        </div>
      )}

      {viewMode === 'audit' && (
        <AuditLogList refreshTrigger={refreshTrigger} />
      )}
    </div>
  )
}
