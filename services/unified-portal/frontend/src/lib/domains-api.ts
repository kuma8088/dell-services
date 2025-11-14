/**
 * Cloudflare DNS API client for Domain Management
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

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
// Types
// ============================================================================

export interface Zone {
  id: string
  name: string
  status: string
  name_servers: string[]
}

export interface DNSRecord {
  id: string
  type: string
  name: string
  content: string
  ttl: number
  proxied: boolean
  priority?: number
}

export interface DNSRecordCreate {
  type: string
  name: string
  content: string
  ttl?: number
  proxied?: boolean
  priority?: number
}

export interface DNSRecordUpdate {
  content?: string
  ttl?: number
  proxied?: boolean
  priority?: number
}

export interface DNSRecordImportError {
  row: number
  record: Record<string, string>
  error: string
}

export interface DNSRecordImportResult {
  success_count: number
  error_count: number
  errors: DNSRecordImportError[]
}

export interface DNSVerificationServerResult {
  server: string
  status: 'success' | 'failed' | 'timeout'
  records: string[]
  error: string | null
}

export interface DNSVerificationResult {
  record_type: string
  name: string
  servers: DNSVerificationServerResult[]
  propagated: boolean
  expected_content: string | null
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * List all Cloudflare zones (domains)
 */
export async function listZones(): Promise<Zone[]> {
  return apiFetch<Zone[]>('/api/v1/domains/zones')
}

/**
 * Get DNS records for a domain
 */
export async function getDNSRecords(
  domain: string,
  recordType?: string
): Promise<DNSRecord[]> {
  const params = recordType ? `?record_type=${recordType}` : ''
  return apiFetch<DNSRecord[]>(`/api/v1/domains/${domain}/dns${params}`)
}

/**
 * Create a DNS record
 */
export async function createDNSRecord(
  domain: string,
  record: DNSRecordCreate
): Promise<DNSRecord> {
  return apiFetch<DNSRecord>(`/api/v1/domains/${domain}/dns`, {
    method: 'POST',
    body: JSON.stringify(record),
  })
}

/**
 * Update a DNS record
 */
export async function updateDNSRecord(
  domain: string,
  recordId: string,
  record: DNSRecordUpdate
): Promise<DNSRecord> {
  return apiFetch<DNSRecord>(`/api/v1/domains/${domain}/dns/${recordId}`, {
    method: 'PUT',
    body: JSON.stringify(record),
  })
}

/**
 * Delete a DNS record
 */
export async function deleteDNSRecord(
  domain: string,
  recordId: string
): Promise<{ success: boolean; message: string }> {
  return apiFetch(`/api/v1/domains/${domain}/dns/${recordId}`, {
    method: 'DELETE',
  })
}

/**
 * Import DNS records from CSV file
 */
export async function importDNSRecords(
  domain: string,
  file: File
): Promise<DNSRecordImportResult> {
  const formData = new FormData()
  formData.append('file', file)

  const url = `${API_BASE_URL}/api/v1/domains/${domain}/dns/import`

  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `API error: ${response.status}`)
  }

  return response.json()
}

/**
 * Verify DNS record propagation
 */
export async function verifyDNSRecord(
  domain: string,
  recordType: string,
  recordName: string,
  expectedContent?: string
): Promise<DNSVerificationResult> {
  const params = new URLSearchParams({
    record_type: recordType,
    record_name: recordName,
  })

  if (expectedContent) {
    params.append('expected_content', expectedContent)
  }

  return apiFetch<DNSVerificationResult>(
    `/api/v1/domains/${domain}/dns/verify?${params.toString()}`,
    { method: 'POST' }
  )
}
