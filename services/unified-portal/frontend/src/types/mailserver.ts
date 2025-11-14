/**
 * Mailserver Type Definitions
 *
 * TypeScript interfaces for Mailserver API integration
 */

/**
 * Mail User
 */
export interface MailUser {
  id: number;
  email: string;
  domain_id: number;
  domain_name: string;
  quota: number;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * Mail User Creation Request
 */
export interface MailUserCreate {
  email: string;
  password: string;
  domain_id: number;
  quota?: number;
  is_active?: boolean;
  is_admin?: boolean;
}

/**
 * Mail User Update Request
 */
export interface MailUserUpdate {
  email?: string;
  password?: string;
  quota?: number;
  is_active?: boolean;
  is_admin?: boolean;
}

/**
 * Mail Domain
 */
export interface MailDomain {
  id: number;
  domain_name: string;
  is_active: boolean;
  max_users: number | null;
  max_quota: number | null;
  created_at: string;
  updated_at: string;
}

/**
 * Mail Domain Creation Request
 */
export interface MailDomainCreate {
  domain_name: string;
  is_active?: boolean;
  max_users?: number | null;
  max_quota?: number | null;
}

/**
 * Mail Domain Update Request
 */
export interface MailDomainUpdate {
  domain_name?: string;
  is_active?: boolean;
  max_users?: number | null;
  max_quota?: number | null;
}

/**
 * Audit Log
 */
export interface AuditLog {
  id: number;
  action_type: string;
  target_type: string;
  target_id: number | null;
  user_id: number | null;
  changes: string | null;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
}

/**
 * Audit Log Query Parameters
 */
export interface AuditLogQuery {
  action_type?: string;
  target_type?: string;
  user_id?: number;
  skip?: number;
  limit?: number;
}

/**
 * API Response: Mail User List
 */
export interface MailUserListResponse {
  users: MailUser[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * API Response: Mail Domain List
 */
export interface MailDomainListResponse {
  domains: MailDomain[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * API Response: Audit Log List
 */
export interface AuditLogListResponse {
  logs: AuditLog[];
  total: number;
  skip: number;
  limit: number;
}

/**
 * API Error Response
 */
export interface ApiError {
  detail: string;
  status_code?: number;
}
