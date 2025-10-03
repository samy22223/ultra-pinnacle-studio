import React, { useState, useEffect } from 'react'
import axios from 'axios'

const UserManagement = () => {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedUser, setSelectedUser] = useState(null)
  const [showUserModal, setShowUserModal] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterRole, setFilterRole] = useState('all')

  useEffect(() => {
    fetchUsers()
  }, [])

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.get('http://localhost:8000/admin/users', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setUsers(response.data)
    } catch (err) {
      console.error('Error fetching users:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleUserAction = async (userId, action, data = {}) => {
    try {
      const token = localStorage.getItem('token')
      const response = await axios.post(
        `http://localhost:8000/admin/users/${userId}/${action}`,
        data,
        { headers: { Authorization: `Bearer ${token}` } }
      )

      // Refresh user list
      await fetchUsers()

      // Log admin action
      await axios.post('http://localhost:8000/admin/audit-log', {
        action: `user_${action}`,
        resource: 'user',
        resource_id: userId,
        details: data
      }, { headers: { Authorization: `Bearer ${token}` } })

      alert(`User ${action} successful`)
    } catch (err) {
      console.error(`Error ${action}ing user:`, err)
      alert(`Failed to ${action} user: ${err.message}`)
    }
  }

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.full_name?.toLowerCase().includes(searchTerm.toLowerCase())

    const matchesRole = filterRole === 'all' ||
                       (filterRole === 'admin' && user.is_superuser) ||
                       (filterRole === 'user' && !user.is_superuser)

    return matchesSearch && matchesRole
  })

  const openUserModal = (user) => {
    setSelectedUser(user)
    setShowUserModal(true)
  }

  const closeUserModal = () => {
    setSelectedUser(null)
    setShowUserModal(false)
  }

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Loading users...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="admin-error">
        <h3>Error Loading Users</h3>
        <p>{error}</p>
        <button onClick={fetchUsers} className="admin-btn primary">Retry</button>
      </div>
    )
  }

  return (
    <div className="user-management">
      <div className="admin-section-header">
        <h2>User Management</h2>
        <p>Manage user accounts, permissions, and access</p>
      </div>

      {/* Filters and Search */}
      <div className="user-filters">
        <div className="search-box">
          <input
            type="text"
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="admin-input"
          />
        </div>
        <div className="role-filter">
          <select
            value={filterRole}
            onChange={(e) => setFilterRole(e.target.value)}
            className="admin-select"
          >
            <option value="all">All Roles</option>
            <option value="admin">Administrators</option>
            <option value="user">Regular Users</option>
          </select>
        </div>
      </div>

      {/* User Statistics */}
      <div className="user-stats">
        <div className="stat-card">
          <h4>Total Users</h4>
          <span className="stat-number">{users.length}</span>
        </div>
        <div className="stat-card">
          <h4>Active Users</h4>
          <span className="stat-number">{users.filter(u => u.is_active).length}</span>
        </div>
        <div className="stat-card">
          <h4>Administrators</h4>
          <span className="stat-number">{users.filter(u => u.is_superuser).length}</span>
        </div>
        <div className="stat-card">
          <h4>Banned Users</h4>
          <span className="stat-number">{users.filter(u => !u.is_active).length}</span>
        </div>
      </div>

      {/* Users Table */}
      <div className="users-table-container">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Full Name</th>
              <th>Role</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map(user => (
              <tr key={user.id}>
                <td>{user.username}</td>
                <td>{user.email}</td>
                <td>{user.full_name || '-'}</td>
                <td>
                  <span className={`role-badge ${user.is_superuser ? 'admin' : 'user'}`}>
                    {user.is_superuser ? 'Administrator' : 'User'}
                  </span>
                </td>
                <td>
                  <span className={`status-badge ${user.is_active ? 'active' : 'banned'}`}>
                    {user.is_active ? 'Active' : 'Banned'}
                  </span>
                </td>
                <td>{new Date(user.created_at).toLocaleDateString()}</td>
                <td>
                  <div className="action-buttons">
                    <button
                      onClick={() => openUserModal(user)}
                      className="admin-btn small primary"
                    >
                      Edit
                    </button>
                    {user.is_active ? (
                      <button
                        onClick={() => handleUserAction(user.id, 'ban')}
                        className="admin-btn small warning"
                      >
                        Ban
                      </button>
                    ) : (
                      <button
                        onClick={() => handleUserAction(user.id, 'unban')}
                        className="admin-btn small success"
                      >
                        Unban
                      </button>
                    )}
                    <button
                      onClick={() => {
                        if (window.confirm(`Are you sure you want to delete user ${user.username}?`)) {
                          handleUserAction(user.id, 'delete')
                        }
                      }}
                      className="admin-btn small danger"
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* User Edit Modal */}
      {showUserModal && selectedUser && (
        <UserEditModal
          user={selectedUser}
          onClose={closeUserModal}
          onSave={async (updatedUser) => {
            await handleUserAction(selectedUser.id, 'update', updatedUser)
            closeUserModal()
          }}
        />
      )}
    </div>
  )
}

// User Edit Modal Component
const UserEditModal = ({ user, onClose, onSave }) => {
  const [formData, setFormData] = useState({
    email: user.email || '',
    full_name: user.full_name || '',
    is_superuser: user.is_superuser || false,
    is_active: user.is_active || false
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    onSave(formData)
  }

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }))
  }

  return (
    <div className="admin-modal-overlay" onClick={onClose}>
      <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
        <div className="admin-modal-header">
          <h3>Edit User: {user.username}</h3>
          <button onClick={onClose} className="admin-modal-close">×</button>
        </div>

        <form onSubmit={handleSubmit} className="admin-modal-body">
          <div className="form-group">
            <label htmlFor="email">Email:</label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="admin-input"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="full_name">Full Name:</label>
            <input
              type="text"
              id="full_name"
              name="full_name"
              value={formData.full_name}
              onChange={handleChange}
              className="admin-input"
            />
          </div>

          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                name="is_superuser"
                checked={formData.is_superuser}
                onChange={handleChange}
              />
              Administrator privileges
            </label>
          </div>

          <div className="form-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                name="is_active"
                checked={formData.is_active}
                onChange={handleChange}
              />
              Account active
            </label>
          </div>
        </form>

        <div className="admin-modal-footer">
          <button onClick={onClose} className="admin-btn secondary">Cancel</button>
          <button onClick={handleSubmit} className="admin-btn primary">Save Changes</button>
        </div>
      </div>
    </div>
  )
}

export default UserManagement