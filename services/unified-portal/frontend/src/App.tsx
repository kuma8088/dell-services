import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import DockerManagement from './pages/DockerManagement'
import BackupManagement from './pages/BackupManagement'
import DatabaseManagement from './pages/DatabaseManagement'
import PhpManagement from './pages/PhpManagement'
import SecurityManagement from './pages/SecurityManagement'
import WordPressManagement from './pages/WordPressManagement'
import DomainManagement from './pages/DomainManagement'
import Login from './pages/Login'
import Layout from './components/layout/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import { AuthProvider } from './contexts/AuthContext'

function App() {
  return (
    <Router>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="/docker" element={<DockerManagement />} />
            <Route path="/backup" element={<BackupManagement />} />
            <Route path="/database" element={<DatabaseManagement />} />
            <Route path="/php" element={<PhpManagement />} />
            <Route path="/security" element={<SecurityManagement />} />
            <Route path="/wordpress" element={<WordPressManagement />} />
            <Route path="/domains" element={<DomainManagement />} />
          </Route>
        </Routes>
      </AuthProvider>
    </Router>
  )
}

export default App
