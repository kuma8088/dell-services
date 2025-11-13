/**
 * API client for Unified Portal Backend
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Generic API fetch wrapper with error handling
 */
async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
      throw new Error(error.detail || `API error: ${response.status}`)
    }

    return response.json()
  } catch (error) {
    console.error(`API request failed: ${url}`, error)
    throw error
  }
}

// ============================================================================
// Dashboard API Types
// ============================================================================

export interface DashboardOverview {
  total_containers: number
  running_containers: number
  wordpress_sites: number
  total_databases: number
  backup_count: number
}

export interface SystemStats {
  cpu_percent: number
  memory_used_gb: number
  memory_total_gb: number
  memory_percent: number
  disk_used_gb: number
  disk_total_gb: number
  disk_percent: number
  load_average: number[]
  uptime_seconds: number
}

export interface ContainerStats {
  total: number
  running: number
  containers: Array<{
    name: string
    status: string
    health: string
    uptime: string
  }>
}

export interface WordPressStats {
  total_sites: number
  sites: Array<{
    site_id: string
    domain: string
    status: string
  }>
}

export interface RedisStats {
  connected: boolean
  version: string
  used_memory: string
  connected_clients: number
  total_keys: number
}

// ============================================================================
// Dashboard API Functions
// ============================================================================

export const dashboardAPI = {
  /**
   * Get dashboard overview
   */
  getOverview: () =>
    apiFetch<DashboardOverview>('/api/v1/dashboard/overview'),

  /**
   * Get system resource stats
   */
  getSystemStats: () =>
    apiFetch<SystemStats>('/api/v1/dashboard/system'),

  /**
   * Get container stats
   */
  getContainerStats: () =>
    apiFetch<ContainerStats>('/api/v1/dashboard/containers'),

  /**
   * Get WordPress stats
   */
  getWordPressStats: () =>
    apiFetch<WordPressStats>('/api/v1/dashboard/wordpress'),

  /**
   * Get Redis stats
   */
  getRedisStats: () =>
    apiFetch<RedisStats>('/api/v1/dashboard/redis'),
}

// ============================================================================
// Docker API Types
// ============================================================================

export interface ContainerBase {
  id: string
  name: string
  status: string
  image: string
}

export interface ContainerDetail extends ContainerBase {
  created: string
  ports: string[]
  stats: {
    cpu_percent: string
    memory_usage: string
    network_io: string
    block_io: string
  }
}

export interface ContainerLogs {
  logs: string
  lines: number
}

export interface DockerStats {
  containers_running: number
  containers_stopped: number
  containers_total: number
  images_count: number
}

export interface OperationResult {
  success: boolean
  message: string
  container_id?: string
}

// ============================================================================
// Docker API Functions
// ============================================================================

export const dockerAPI = {
  /**
   * List all Docker containers
   */
  listContainers: (status?: 'running' | 'stopped') => {
    const params = status ? `?status=${status}` : ''
    return apiFetch<ContainerBase[]>(`/api/v1/docker/containers${params}`)
  },

  /**
   * Get container details
   */
  getContainerDetail: (containerId: string) =>
    apiFetch<ContainerDetail>(`/api/v1/docker/containers/${containerId}`),

  /**
   * Start a container
   */
  startContainer: (containerId: string) =>
    apiFetch<OperationResult>(`/api/v1/docker/containers/${containerId}/start`, {
      method: 'POST',
    }),

  /**
   * Stop a container
   */
  stopContainer: (containerId: string) =>
    apiFetch<OperationResult>(`/api/v1/docker/containers/${containerId}/stop`, {
      method: 'POST',
    }),

  /**
   * Restart a container
   */
  restartContainer: (containerId: string) =>
    apiFetch<OperationResult>(`/api/v1/docker/containers/${containerId}/restart`, {
      method: 'POST',
    }),

  /**
   * Get container logs
   */
  getContainerLogs: (containerId: string, tail: number = 100) =>
    apiFetch<ContainerLogs>(`/api/v1/docker/containers/${containerId}/logs?tail=${tail}`),

  /**
   * Get Docker stats
   */
  getDockerStats: () =>
    apiFetch<DockerStats>('/api/v1/docker/stats'),
}

// ============================================================================
// WordPress API Types
// ============================================================================

export interface WordPressSiteBase {
  name: string
  url: string
  status: string
}

export interface WordPressSiteDetail extends WordPressSiteBase {
  wp_version: string
  php_version: string
  theme: string
  db_name: string
  redis_enabled: boolean
}

export interface WordPressPlugin {
  name: string
  status: string
  version: string
  update_available?: boolean
}

export interface WordPressStats {
  total_sites: number
  sites_online: number
  total_plugins: number
  redis_enabled_sites: number
}

export interface CacheOperation {
  success: boolean
  message: string
  site_name: string
}

export interface SMTPStatus {
  configured: boolean
  from_email?: string
  from_name?: string
  mailer?: string
}

// ============================================================================
// WordPress API Functions
// ============================================================================

export const wordpressAPI = {
  /**
   * List all WordPress sites
   */
  listSites: () =>
    apiFetch<WordPressSiteBase[]>('/api/v1/wordpress/sites'),

  /**
   * Get site details
   */
  getSiteDetail: (siteName: string) =>
    apiFetch<WordPressSiteDetail>(`/api/v1/wordpress/sites/${siteName}`),

  /**
   * Get site plugins
   */
  getSitePlugins: (siteName: string) =>
    apiFetch<WordPressPlugin[]>(`/api/v1/wordpress/sites/${siteName}/plugins`),

  /**
   * Clear site cache
   */
  clearCache: (siteName: string) =>
    apiFetch<CacheOperation>(`/api/v1/wordpress/sites/${siteName}/cache/clear`, {
      method: 'POST',
    }),

  /**
   * Get SMTP status
   */
  getSMTPStatus: (siteName: string) =>
    apiFetch<SMTPStatus>(`/api/v1/wordpress/sites/${siteName}/smtp-status`),

  /**
   * Get WordPress stats
   */
  getStats: () =>
    apiFetch<WordPressStats>('/api/v1/wordpress/stats'),
}

// ============================================================================
// Database API Types
// ============================================================================

export interface DatabaseInfo {
  name: string
  size_mb: number
}

export interface DatabaseStats {
  total_databases: number
  total_size_mb: number
  mariadb_version: string
}

// ============================================================================
// Database API Functions
// ============================================================================

export const databaseAPI = {
  /**
   * List all databases
   */
  listDatabases: () =>
    apiFetch<DatabaseInfo[]>('/api/v1/database/list'),

  /**
   * Get database statistics
   */
  getStats: () =>
    apiFetch<DatabaseStats>('/api/v1/database/stats'),
}

// ============================================================================
// PHP API Types
// ============================================================================

export interface PHPVersion {
  version: string
  major: number
  minor: number
  patch: number
}

export interface PHPModule {
  name: string
  version: string
}

export interface PHPConfig {
  memory_limit: string
  max_execution_time: string
  upload_max_filesize: string
  post_max_size: string
  display_errors: string
  error_reporting: string
}

export interface PHPStats {
  version: string
  modules_count: number
  memory_limit: string
}

// ============================================================================
// PHP API Functions
// ============================================================================

export const phpAPI = {
  /**
   * Get PHP version information
   */
  getVersion: () =>
    apiFetch<PHPVersion>('/api/v1/php/version'),

  /**
   * List all loaded PHP modules
   */
  listModules: () =>
    apiFetch<PHPModule[]>('/api/v1/php/modules'),

  /**
   * Get PHP configuration settings
   */
  getConfig: () =>
    apiFetch<PHPConfig>('/api/v1/php/config'),

  /**
   * Get PHP system statistics
   */
  getStats: () =>
    apiFetch<PHPStats>('/api/v1/php/stats'),
}

// ============================================================================
// Security API Types
// ============================================================================

export interface SSLCertificate {
  domain: string
  issuer: string
  valid_until: string
  status: string
}

export interface CloudflareZone {
  name: string
  id: string
  ssl_mode: string
  status: string
}

export interface CloudflareSSLStatus {
  zones: CloudflareZone[]
}

export interface SecurityHeaders {
  nginx_config: string
  headers: Record<string, string>
}

export interface SecurityStats {
  ssl_enabled: boolean
  https_enforced: boolean
  cloudflare_protection: boolean
  security_headers_enabled: boolean
  cloudflare_zones_count: number
}

// ============================================================================
// Security API Functions
// ============================================================================

export const securityAPI = {
  /**
   * List SSL certificates for blog domains
   */
  listSSLCertificates: () =>
    apiFetch<SSLCertificate[]>('/api/v1/security/ssl/certificates'),

  /**
   * Get Cloudflare SSL status for all zones
   */
  getCloudflareSSL: () =>
    apiFetch<CloudflareSSLStatus>('/api/v1/security/cloudflare/ssl'),

  /**
   * Get security headers configuration from Nginx
   */
  getSecurityHeaders: () =>
    apiFetch<SecurityHeaders>('/api/v1/security/headers'),

  /**
   * Get security system statistics
   */
  getStats: () =>
    apiFetch<SecurityStats>('/api/v1/security/stats'),
}

// ============================================================================
// Backup API Types
// ============================================================================

export interface BackupInfo {
  date: string
  size_mb: number
  path: string
  type: string  // daily, weekly, blog
}

export interface MailserverBackups {
  daily: BackupInfo[]
  weekly: BackupInfo[]
}

export interface BlogBackups {
  backups: BackupInfo[]
}

export interface BackupStats {
  total_backups: number
  total_size_gb: number
  last_backup_time: string
  mailserver_backups: number
  blog_backups: number
}

export interface BackupSchedule {
  mailserver_daily: string
  mailserver_weekly: string
  s3_replication: string
  malware_scan: string
}

// ============================================================================
// Backup API Functions
// ============================================================================

export const backupAPI = {
  /**
   * List all mailserver backups (daily and weekly)
   */
  listMailserverBackups: () =>
    apiFetch<MailserverBackups>('/api/v1/backup/mailserver/list'),

  /**
   * List all blog backups
   */
  listBlogBackups: () =>
    apiFetch<BlogBackups>('/api/v1/backup/blog/list'),

  /**
   * Get backup system statistics
   */
  getStats: () =>
    apiFetch<BackupStats>('/api/v1/backup/stats'),

  /**
   * Get backup schedule information
   */
  getSchedule: () =>
    apiFetch<BackupSchedule>('/api/v1/backup/schedule'),
}

// ============================================================================
// Export for convenience
// ============================================================================

export { apiFetch, API_BASE_URL }
