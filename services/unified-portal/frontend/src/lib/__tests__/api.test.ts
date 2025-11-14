import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  databaseAPI,
  phpAPI,
  managedSitesAPI,
  adminUserAPI,
  dockerAPI,
  wordpressAPI
} from '../api'

// Mock global fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('API Functions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.resetAllMocks()
  })

  // Helper to mock successful fetch response
  const mockSuccessResponse = (data: any) => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => data,
    })
  }

  describe('databaseAPI', () => {
    it('fetches database status', async () => {
      const mockStatus = {
        connected: true,
        version: '10.11.6-MariaDB',
        uptime: 86400,
      }

      mockSuccessResponse(mockStatus)

      const result = await databaseAPI.getStatus()

      expect(mockFetch).toHaveBeenCalled()
      expect(result).toEqual(mockStatus)
    })

    it('lists all databases', async () => {
      const mockDatabases = [
        { name: 'test_db1', size_mb: 100.5 },
        { name: 'test_db2', size_mb: 250.75 },
      ]

      mockSuccessResponse(mockDatabases)

      const result = await databaseAPI.listDatabases()

      expect(mockFetch).toHaveBeenCalled()
      expect(result).toEqual(mockDatabases)
    })

    it('gets database detail', async () => {
      const mockDetail = {
        name: 'test_db',
        size_mb: 100.5,
        tables_count: 15,
        rows_count: 50000,
      }

      mockSuccessResponse(mockDetail)

      const result = await databaseAPI.getDatabaseDetail('test_db')

      expect(mockFetch).toHaveBeenCalled()
      expect(result).toEqual(mockDetail)
    })

    it('gets database stats', async () => {
      const mockStats = {
        total_databases: 16,
        total_size_mb: 1024.5,
        mariadb_version: '10.11.6-MariaDB',
      }

      mockSuccessResponse(mockStats)

      const result = await databaseAPI.getStats()

      expect(mockFetch).toHaveBeenCalled()
      expect(result).toEqual(mockStats)
    })
  })

  describe('phpAPI', () => {
    it('gets PHP version', async () => {
      const mockVersion = {
        version: '8.3.0',
        major: 8,
        minor: 3,
        patch: 0,
      }

      mockSuccessResponse(mockVersion)

      const result = await phpAPI.getVersion()

      expect(mockFetch).toHaveBeenCalled()
      expect(result).toEqual(mockVersion)
    })

    it('lists PHP modules', async () => {
      const mockModules = [
        { name: 'mysqli', version: '8.3.0' },
        { name: 'redis', version: '6.0.2' },
      ]

      mockSuccessResponse(mockModules)

      const result = await phpAPI.listModules()

      expect(mockFetch).toHaveBeenCalled()
      expect(result).toEqual(mockModules)
    })

    it('gets PHP config', async () => {
      const mockConfig = {
        memory_limit: '256M',
        max_execution_time: '300',
        upload_max_filesize: '64M',
        post_max_size: '64M',
        display_errors: 'Off',
        error_reporting: 'E_ALL',
      }

      mockSuccessResponse(mockConfig)

      const result = await phpAPI.getConfig()

      expect(mockFetch).toHaveBeenCalled()
      expect(result).toEqual(mockConfig)
    })

    it('gets PHP stats', async () => {
      const mockStats = {
        version: '8.3.0',
        modules_count: 50,
        memory_limit: '256M',
      }

      mockSuccessResponse(mockStats)

      const result = await phpAPI.getStats()

      expect(mockFetch).toHaveBeenCalled()
      expect(result).toEqual(mockStats)
    })
  })

  describe('managedSitesAPI', () => {
    it('lists managed sites', async () => {
      const mockSites = [
        {
          id: 1,
          site_name: 'test-site',
          domain: 'test.example.com',
          database_name: 'test_db',
          php_version: '8.3',
          enabled: true,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-02T00:00:00Z',
        },
      ]

      mockSuccessResponse(mockSites)

      const result = await managedSitesAPI.listSites()

      expect(mockFetch).toHaveBeenCalled()
      expect(result).toEqual(mockSites)
    })

    it('creates a new managed site', async () => {
      const newSite = {
        site_name: 'new-site',
        domain: 'new.example.com',
        database_name: 'new_db',
        php_version: '8.3',
      }

      const mockResponse = {
        id: 1,
        ...newSite,
        enabled: true,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
      }

      mockSuccessResponse(mockResponse)

      const result = await managedSitesAPI.createSite(newSite)

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/wordpress/managed-sites',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newSite),
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('deletes a managed site', async () => {
      const mockResponse = { success: true, message: 'Site deleted' }

      mockSuccessResponse(mockResponse)

      const result = await managedSitesAPI.deleteSite(1, false)

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/wordpress/managed-sites/1',
        expect.objectContaining({
          method: 'DELETE',
        })
      )
      expect(result).toEqual(mockResponse)
    })
  })

  describe('adminUserAPI', () => {
    it('lists admin users', async () => {
      const mockUsers = [
        {
          id: 1,
          username: 'admin',
          email: 'admin@example.com',
          is_active: true,
          is_superuser: true,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-02T00:00:00Z',
          last_login: '2025-01-03T00:00:00Z',
        },
      ]

      mockSuccessResponse(mockUsers)

      const result = await adminUserAPI.listUsers()

      expect(mockFetch).toHaveBeenCalled()
      expect(result).toEqual(mockUsers)
    })

    it('creates a new admin user', async () => {
      const newUser = {
        username: 'newadmin',
        email: 'newadmin@example.com',
        password: 'Password123',
        is_superuser: false,
      }

      const mockResponse = {
        id: 2,
        username: newUser.username,
        email: newUser.email,
        is_active: true,
        is_superuser: newUser.is_superuser,
        created_at: '2025-01-01T00:00:00Z',
        updated_at: '2025-01-01T00:00:00Z',
        last_login: null,
      }

      mockSuccessResponse(mockResponse)

      const result = await adminUserAPI.createUser(newUser)

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/users',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify(newUser),
        })
      )
      expect(result).toEqual(mockResponse)
    })

    it('deletes an admin user', async () => {
      const mockResponse = { success: true, message: 'User deleted' }

      mockSuccessResponse(mockResponse)

      const result = await adminUserAPI.deleteUser(1)

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/auth/users/1',
        expect.objectContaining({
          method: 'DELETE',
        })
      )
      expect(result).toEqual(mockResponse)
    })
  })

  describe('dockerAPI', () => {
    it('lists all containers', async () => {
      const mockContainers = [
        {
          id: 'abc123',
          name: 'blog-wordpress',
          image: 'wordpress:latest',
          status: 'running',
          created: '2025-01-01T00:00:00Z',
        },
      ]

      mockSuccessResponse(mockContainers)

      const result = await dockerAPI.listContainers()

      expect(mockFetch).toHaveBeenCalled()
      expect(result).toEqual(mockContainers)
    })
  })

  describe('wordpressAPI', () => {
    it('lists WordPress sites', async () => {
      const mockSites = [
        {
          name: 'demo1',
          url: 'https://demo1.example.com',
          status: 'active',
        },
      ]

      mockSuccessResponse(mockSites)

      const result = await wordpressAPI.listSites()

      expect(mockFetch).toHaveBeenCalled()
      expect(result).toEqual(mockSites)
    })
  })
})
