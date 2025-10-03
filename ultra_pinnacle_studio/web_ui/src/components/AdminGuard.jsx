import React, { useState, useEffect } from 'react'
import axios from 'axios'

const AdminGuard = ({ children, fallback = null }) => {
  const [isAdmin, setIsAdmin] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const checkAdminStatus = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) {
          setIsAdmin(false)
          setLoading(false)
          return
        }

        const response = await axios.get('http://localhost:8000/users/profile', {
          headers: { Authorization: `Bearer ${token}` }
        })

        setIsAdmin(response.data.is_superuser || false)
      } catch (err) {
        console.error('Error checking admin status:', err)
        setError(err.message)
        setIsAdmin(false)
      } finally {
        setLoading(false)
      }
    }

    checkAdminStatus()
  }, [])

  if (loading) {
    return (
      <div className="admin-loading">
        <div className="loading-spinner"></div>
        <p>Verifying admin access...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="admin-error">
        <h3>Access Verification Failed</h3>
        <p>{error}</p>
        {fallback}
      </div>
    )
  }

  if (!isAdmin) {
    return fallback || (
      <div className="admin-access-denied">
        <h3>Admin Access Required</h3>
        <p>You don't have permission to access this area.</p>
        <p>Please contact an administrator if you believe this is an error.</p>
      </div>
    )
  }

  return children
}

export default AdminGuard