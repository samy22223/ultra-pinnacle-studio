import React, { useState, useEffect, useContext } from 'react'
import axios from 'axios'
import './Auth.css'

// Auth Context for global authentication state
export const AuthContext = React.createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [tokens, setTokens] = useState(null)
  const [loading, setLoading] = useState(true)

  // Initialize auth state from localStorage
  useEffect(() => {
    const initializeAuth = async () => {
      const storedTokens = localStorage.getItem('auth_tokens')
      if (storedTokens) {
        try {
          const parsedTokens = JSON.parse(storedTokens)
          setTokens(parsedTokens)

          // Validate token and get user info
          const userInfo = await fetchUserProfile(parsedTokens.access_token)
          if (userInfo) {
            setUser(userInfo)
          } else {
            // Token invalid, try refresh
            const newTokens = await refreshTokens(parsedTokens.refresh_token)
            if (newTokens) {
              setTokens(newTokens)
              localStorage.setItem('auth_tokens', JSON.stringify(newTokens))
              const userInfo = await fetchUserProfile(newTokens.access_token)
              setUser(userInfo)
            } else {
              logout()
            }
          }
        } catch (error) {
          console.error('Auth initialization error:', error)
          logout()
        }
      }
      setLoading(false)
    }

    initializeAuth()
  }, [])

  const fetchUserProfile = async (accessToken) => {
    try {
      const response = await axios.get('http://localhost:8000/auth/me', {
        headers: { Authorization: `Bearer ${accessToken}` }
      })
      return response.data
    } catch (error) {
      console.error('Failed to fetch user profile:', error)
      return null
    }
  }

  const refreshTokens = async (refreshToken) => {
    try {
      const response = await axios.post('http://localhost:8000/auth/refresh',
        { refresh_token: refreshToken },
        { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
      )
      return response.data
    } catch (error) {
      console.error('Token refresh failed:', error)
      return null
    }
  }

  const login = async (username, password) => {
    try {
      const response = await axios.post('http://localhost:8000/auth/login',
        { username, password },
        { headers: { 'Content-Type': 'application/json' } }
      )

      const { access_token, refresh_token } = response.data
      const tokens = { access_token, refresh_token }

      setTokens(tokens)
      localStorage.setItem('auth_tokens', JSON.stringify(tokens))

      const userInfo = await fetchUserProfile(access_token)
      setUser(userInfo)

      return { success: true }
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || error.message }
    }
  }

  const register = async (username, email, password, fullName) => {
    try {
      const response = await axios.post('http://localhost:8000/auth/register',
        { username, email, password, full_name: fullName },
        { headers: { 'Content-Type': 'application/json' } }
      )

      const { access_token, refresh_token } = response.data
      const tokens = { access_token, refresh_token }

      setTokens(tokens)
      localStorage.setItem('auth_tokens', JSON.stringify(tokens))

      const userInfo = await fetchUserProfile(access_token)
      setUser(userInfo)

      return { success: true }
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || error.message }
    }
  }

  const oauthLogin = (provider) => {
    // Redirect to OAuth provider
    window.location.href = `http://localhost:8000/auth/oauth/${provider}`
  }

  const logout = async () => {
    if (tokens?.refresh_token) {
      try {
        await axios.post('http://localhost:8000/auth/logout',
          { refresh_token: tokens.refresh_token },
          { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
        )
      } catch (error) {
        console.error('Logout error:', error)
      }
    }

    setUser(null)
    setTokens(null)
    localStorage.removeItem('auth_tokens')
  }

  const updateProfile = async (updates) => {
    try {
      const formData = new FormData()
      if (updates.full_name) formData.append('full_name', updates.full_name)
      if (updates.email) formData.append('email', updates.email)

      const response = await axios.put('http://localhost:8000/auth/profile', formData, {
        headers: {
          Authorization: `Bearer ${tokens.access_token}`,
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      })

      // Update local user state
      setUser(prev => ({ ...prev, ...updates }))
      return { success: true }
    } catch (error) {
      return { success: false, error: error.response?.data?.detail || error.message }
    }
  }

  const getAuthHeaders = () => {
    return tokens?.access_token ? { Authorization: `Bearer ${tokens.access_token}` } : {}
  }

  const value = {
    user,
    tokens,
    loading,
    login,
    register,
    oauthLogin,
    logout,
    updateProfile,
    getAuthHeaders,
    isAuthenticated: !!user
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

const Auth = () => {
  const { login, register, oauthLogin, loading } = useAuth()
  const [isLogin, setIsLogin] = useState(true)
  const [formData, setFormData] = useState({
    username: 'demo',
    email: '',
    password: 'demo123',
    fullName: ''
  })
  const [message, setMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    setMessage('')

    try {
      let result
      if (isLogin) {
        result = await login(formData.username, formData.password)
      } else {
        result = await register(formData.username, formData.email, formData.password, formData.fullName)
      }

      if (result.success) {
        setMessage(isLogin ? 'Login successful!' : 'Registration successful!')
      } else {
        setMessage(result.error)
      }
    } catch (error) {
      setMessage('An error occurred. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  if (loading) {
    return <div className="auth-loading">Loading...</div>
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h2>{isLogin ? 'Login' : 'Register'}</h2>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <input
              type="text"
              value={formData.username}
              onChange={(e) => handleInputChange('username', e.target.value)}
              placeholder="Username"
              required
            />
          </div>

          {!isLogin && (
            <>
              <div className="form-group">
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  placeholder="Email"
                  required
                />
              </div>
              <div className="form-group">
                <input
                  type="text"
                  value={formData.fullName}
                  onChange={(e) => handleInputChange('fullName', e.target.value)}
                  placeholder="Full Name"
                />
              </div>
            </>
          )}

          <div className="form-group">
            <input
              type="password"
              value={formData.password}
              onChange={(e) => handleInputChange('password', e.target.value)}
              placeholder="Password"
              required
            />
          </div>

          <button type="submit" disabled={isLoading} className="auth-button">
            {isLoading ? 'Please wait...' : (isLogin ? 'Login' : 'Register')}
          </button>
        </form>

        <div className="auth-divider">
          <span>or</span>
        </div>

        <div className="oauth-buttons">
          <button
            onClick={() => oauthLogin('google')}
            className="oauth-button google"
          >
            Continue with Google
          </button>
          <button
            onClick={() => oauthLogin('github')}
            className="oauth-button github"
          >
            Continue with GitHub
          </button>
        </div>

        <div className="auth-toggle">
          <button
            type="button"
            onClick={() => setIsLogin(!isLogin)}
            className="toggle-button"
          >
            {isLogin ? "Don't have an account? Register" : "Already have an account? Login"}
          </button>
        </div>

        {message && (
          <div className={`auth-message ${message.includes('successful') ? 'success' : 'error'}`}>
            {message}
          </div>
        )}
      </div>
    </div>
  )
}

export default Auth