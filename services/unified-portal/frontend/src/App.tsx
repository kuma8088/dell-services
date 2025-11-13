import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import DockerManagement from './pages/DockerManagement'
import BackupManagement from './pages/BackupManagement'
import Login from './pages/Login'
import Layout from './components/layout/Layout'

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="/docker" element={<DockerManagement />} />
          <Route path="/backup" element={<BackupManagement />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
