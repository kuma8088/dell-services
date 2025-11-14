/**
 * Mailserver API Client
 *
 * API client for Mailserver User Management integration
 */

import { apiFetch } from '../api'
import type {
  MailUser,
  MailUserCreate,
  MailUserUpdate,
  MailUserListResponse,
  MailDomain,
  MailDomainCreate,
  MailDomainUpdate,
  MailDomainListResponse,
  AuditLog,
  AuditLogQuery,
  AuditLogListResponse,
} from '../../types/mailserver'

// ============================================================================
// Mail User API Functions
// ============================================================================

export const mailUserAPI = {
  /**
   * Get all mail users
   */
  list: (skip: number = 0, limit: number = 100) =>
    apiFetch<MailUserListResponse>(
      `/api/mailserver/users?skip=${skip}&limit=${limit}`
    ),

  /**
   * Get a specific mail user by ID
   */
  get: (userId: number) =>
    apiFetch<MailUser>(`/api/mailserver/users/${userId}`),

  /**
   * Create a new mail user
   */
  create: (data: MailUserCreate) =>
    apiFetch<MailUser>('/api/mailserver/users', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /**
   * Update an existing mail user
   */
  update: (userId: number, data: MailUserUpdate) =>
    apiFetch<MailUser>(`/api/mailserver/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  /**
   * Delete a mail user
   */
  delete: (userId: number) =>
    apiFetch<{ message: string }>(`/api/mailserver/users/${userId}`, {
      method: 'DELETE',
    }),

  /**
   * Get users by domain
   */
  listByDomain: (domainId: number, skip: number = 0, limit: number = 100) =>
    apiFetch<MailUserListResponse>(
      `/api/mailserver/domains/${domainId}/users?skip=${skip}&limit=${limit}`
    ),
}

// ============================================================================
// Mail Domain API Functions
// ============================================================================

export const mailDomainAPI = {
  /**
   * Get all mail domains
   */
  list: (skip: number = 0, limit: number = 100) =>
    apiFetch<MailDomainListResponse>(
      `/api/mailserver/domains?skip=${skip}&limit=${limit}`
    ),

  /**
   * Get a specific mail domain by ID
   */
  get: (domainId: number) =>
    apiFetch<MailDomain>(`/api/mailserver/domains/${domainId}`),

  /**
   * Create a new mail domain
   */
  create: (data: MailDomainCreate) =>
    apiFetch<MailDomain>('/api/mailserver/domains', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /**
   * Update an existing mail domain
   */
  update: (domainId: number, data: MailDomainUpdate) =>
    apiFetch<MailDomain>(`/api/mailserver/domains/${domainId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  /**
   * Delete a mail domain
   */
  delete: (domainId: number) =>
    apiFetch<{ message: string }>(`/api/mailserver/domains/${domainId}`, {
      method: 'DELETE',
    }),
}

// ============================================================================
// Audit Log API Functions
// ============================================================================

export const auditLogAPI = {
  /**
   * Get audit logs with optional filtering
   */
  list: (query: AuditLogQuery = {}) => {
    const params = new URLSearchParams()

    if (query.action_type) params.append('action_type', query.action_type)
    if (query.target_type) params.append('target_type', query.target_type)
    if (query.user_id !== undefined) params.append('user_id', query.user_id.toString())
    if (query.skip !== undefined) params.append('skip', query.skip.toString())
    if (query.limit !== undefined) params.append('limit', query.limit.toString())

    const queryString = params.toString()
    const endpoint = `/api/mailserver/audit-logs${queryString ? `?${queryString}` : ''}`

    return apiFetch<AuditLogListResponse>(endpoint)
  },

  /**
   * Get a specific audit log by ID
   */
  get: (logId: number) =>
    apiFetch<AuditLog>(`/api/mailserver/audit-logs/${logId}`),
}

// ============================================================================
// Combined Mailserver API
// ============================================================================

export const mailserverAPI = {
  users: mailUserAPI,
  domains: mailDomainAPI,
  auditLogs: auditLogAPI,
}

export default mailserverAPI
