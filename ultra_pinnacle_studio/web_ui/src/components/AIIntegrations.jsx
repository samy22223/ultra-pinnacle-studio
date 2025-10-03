import React, { useState, useEffect, useCallback } from 'react'
import './AIIntegrations.css'

const AIIntegrations = ({ token }) => {
  const [activeTab, setActiveTab] = useState('image-gen')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  // Image Generation State
  const [imagePrompt, setImagePrompt] = useState('')
  const [imageModel, setImageModel] = useState('stable-diffusion')
  const [imageWidth, setImageWidth] = useState(512)
  const [imageHeight, setImageHeight] = useState(512)
  const [negativePrompt, setNegativePrompt] = useState('')
  const [currentTaskId, setCurrentTaskId] = useState(null)
  const [taskStatus, setTaskStatus] = useState(null)

  // Code Completion State
  const [code, setCode] = useState('')
  const [language, setLanguage] = useState('python')
  const [cursorPosition, setCursorPosition] = useState(0)

  // Prompt Engineering State
  const [basePrompt, setBasePrompt] = useState('')
  const [taskType, setTaskType] = useState('creative')
  const [style, setStyle] = useState('balanced')
  const [length, setLength] = useState('medium')

  // Multi-modal State
  const [textPrompt, setTextPrompt] = useState('')
  const [imageFile, setImageFile] = useState(null)
  const [multimodalTask, setMultimodalTask] = useState('analyze')

  // Code Refactoring State
  const [refactorCode, setRefactorCode] = useState('')
  const [refactorLanguage, setRefactorLanguage] = useState('python')
  const [refactoringType, setRefactoringType] = useState('optimize')

  // Conversion State
  const [inputType, setInputType] = useState('text')
  const [outputType, setOutputType] = useState('image')
  const [conversionContent, setConversionContent] = useState('')

  // Code Explanation State
  const [explainCode, setExplainCode] = useState('')
  const [explainLanguage, setExplainLanguage] = useState('python')
  const [explanationLevel, setExplanationLevel] = useState('intermediate')
  const [includeExamples, setIncludeExamples] = useState(true)

  // Debug State
  const [debugCode, setDebugCode] = useState('')
  const [debugLanguage, setDebugLanguage] = useState('python')
  const [errorMessage, setErrorMessage] = useState('')
  const [stackTrace, setStackTrace] = useState('')
  const [retryCount, setRetryCount] = useState(0)
  const [lastRequestTime, setLastRequestTime] = useState(0)

  // Debounce utility
  const debounce = (func, wait) => {
    let timeout
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout)
        func(...args)
      }
      clearTimeout(timeout)
      timeout = setTimeout(later, wait)
    }
  }

  // Rate limiting check
  const checkRateLimit = useCallback(() => {
    const now = Date.now()
    const timeSinceLastRequest = now - lastRequestTime
    if (timeSinceLastRequest < 1000) { // 1 second minimum between requests
      throw new Error('Please wait before making another request')
    }
    setLastRequestTime(now)
  }, [lastRequestTime])

  // Poll for task status
  useEffect(() => {
    let interval
    if (currentTaskId) {
      interval = setInterval(async () => {
        try {
          const response = await fetch(`http://localhost:8000/tasks/${currentTaskId}`, {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          })
          if (response.ok) {
            const status = await response.json()
            setTaskStatus(status)
            if (status.status === 'completed' || status.status === 'failed') {
              setCurrentTaskId(null)
              clearInterval(interval)
            }
          }
        } catch (err) {
          console.error('Error checking task status:', err)
        }
      }, 2000) // Check every 2 seconds
    }
    return () => clearInterval(interval)
  }, [currentTaskId, token])

  const makeAPIRequest = async (endpoint, data, maxRetries = 3) => {
    setLoading(true)
    setError(null)
    setResult(null)

    // Check rate limiting
    try {
      checkRateLimit()
    } catch (err) {
      setError(err.message)
      setLoading(false)
      return
    }

    let lastError
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 second timeout

        const response = await fetch(`http://localhost:8000${endpoint}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(data),
          signal: controller.signal
        })

        clearTimeout(timeoutId)

        if (!response.ok) {
          if (response.status === 429) {
            // Rate limited, wait and retry
            await new Promise(resolve => setTimeout(resolve, 2000 * (attempt + 1)))
            continue
          }
          throw new Error(`HTTP ${response.status}: ${response.statusText}`)
        }

        const result = await response.json()
        setResult(result)
        setRetryCount(0) // Reset retry count on success
        return result

      } catch (err) {
        lastError = err
        if (err.name === 'AbortError') {
          lastError = new Error('Request timed out')
        }

        if (attempt < maxRetries - 1) {
          // Wait before retrying (exponential backoff)
          await new Promise(resolve => setTimeout(resolve, 1000 * (attempt + 1)))
          setRetryCount(attempt + 1)
        }
      }
    }

    // All retries failed
    setError(`Request failed after ${maxRetries} attempts: ${lastError.message}`)
    setRetryCount(maxRetries)
    setLoading(false)
  }

  const handleImageGeneration = async () => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const response = await fetch('http://localhost:8000/ai/generate-image', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          prompt: imagePrompt,
          model: imageModel,
          width: imageWidth,
          height: imageHeight,
          negative_prompt: negativePrompt
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      setCurrentTaskId(result.task_id)
      setResult(result)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCodeCompletion = () => {
    makeAPIRequest('/ai/complete-code', {
      code: code,
      language: language,
      cursor_position: cursorPosition
    })
  }

  const handlePromptEngineering = () => {
    makeAPIRequest('/ai/engineer-prompt', {
      base_prompt: basePrompt,
      task_type: taskType,
      style: style,
      length: length
    })
  }

  const handleMultimodal = () => {
    const formData = new FormData()
    formData.append('text_prompt', textPrompt)
    formData.append('task', multimodalTask)
    if (imageFile) {
      formData.append('image', imageFile)
    }

    fetch('http://localhost:8000/ai/multimodal', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    })
    .then(response => response.json())
    .then(data => setResult(data))
    .catch(err => setError(err.message))
    .finally(() => setLoading(false))
  }

  const handleCodeRefactoring = () => {
    makeAPIRequest('/ai/refactor-code', {
      code: refactorCode,
      language: refactorLanguage,
      refactoring_type: refactoringType
    })
  }

  const handleConversion = () => {
    makeAPIRequest('/ai/convert', {
      input_type: inputType,
      output_type: outputType,
      content: conversionContent
    })
  }

  const handleCodeExplanation = () => {
    makeAPIRequest('/ai/explain-code', {
      code: explainCode,
      language: explainLanguage,
      explanation_level: explanationLevel,
      include_examples: includeExamples
    })
  }

  const handleDebug = () => {
    makeAPIRequest('/ai/debug', {
      code: debugCode,
      language: debugLanguage,
      error_message: errorMessage,
      stack_trace: stackTrace
    })
  }

  const tabs = [
    { id: 'image-gen', label: 'Image Generation', icon: '🎨' },
    { id: 'code-completion', label: 'Code Completion', icon: '💻' },
    { id: 'prompt-eng', label: 'Prompt Engineering', icon: '✨' },
    { id: 'multimodal', label: 'Multi-modal', icon: '🔄' },
    { id: 'refactor', label: 'Code Refactoring', icon: '🔧' },
    { id: 'convert', label: 'Convert', icon: '🔄' },
    { id: 'explain', label: 'Explain Code', icon: '📚' },
    { id: 'debug', label: 'Debug', icon: '🐛' }
  ]

  return (
    <div className="ai-integrations">
      <h1>Advanced AI Features</h1>

      <div className="tabs">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`tab ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span className="tab-icon">{tab.icon}</span>
            <span className="tab-label">{tab.label}</span>
          </button>
        ))}
      </div>

      <div className="tab-content">
        {activeTab === 'image-gen' && (
          <div className="feature-section">
            <h2>AI Image Generation</h2>
            <div className="form-group">
              <label>Prompt:</label>
              <textarea
                value={imagePrompt}
                onChange={(e) => setImagePrompt(e.target.value)}
                placeholder="Describe the image you want to generate..."
                rows={3}
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Model:</label>
                <select value={imageModel} onChange={(e) => setImageModel(e.target.value)}>
                  <option value="stable-diffusion">Stable Diffusion</option>
                </select>
              </div>
              <div className="form-group">
                <label>Width:</label>
                <input
                  type="number"
                  value={imageWidth}
                  onChange={(e) => setImageWidth(parseInt(e.target.value))}
                  min={64}
                  max={2048}
                />
              </div>
              <div className="form-group">
                <label>Height:</label>
                <input
                  type="number"
                  value={imageHeight}
                  onChange={(e) => setImageHeight(parseInt(e.target.value))}
                  min={64}
                  max={2048}
                />
              </div>
            </div>
            <div className="form-group">
              <label>Negative Prompt (optional):</label>
              <input
                type="text"
                value={negativePrompt}
                onChange={(e) => setNegativePrompt(e.target.value)}
                placeholder="What to avoid in the image..."
              />
            </div>
            <button onClick={handleImageGeneration} disabled={loading || !imagePrompt}>
              {loading ? 'Generating...' : 'Generate Image'}
            </button>

            {taskStatus && activeTab === 'image-gen' && (
              <div className="task-status">
                <h3>Generation Status: {taskStatus.status}</h3>
                {taskStatus.status === 'running' && (
                  <div className="progress-indicator">
                    <div className="spinner small"></div>
                    <p>Generating image... This may take 30-120 seconds.</p>
                  </div>
                )}
                {taskStatus.status === 'completed' && taskStatus.result && (
                  <div className="success">
                    <p>✅ Image generated successfully!</p>
                    <p>Image saved at: {taskStatus.result.image_url}</p>
                  </div>
                )}
                {taskStatus.status === 'failed' && (
                  <div className="error">
                    <p>❌ Generation failed: {taskStatus.error}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'code-completion' && (
          <div className="feature-section">
            <h2>Intelligent Code Completion</h2>
            <div className="form-group">
              <label>Code:</label>
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="Enter your code here..."
                rows={10}
                onSelect={(e) => setCursorPosition(e.target.selectionStart)}
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Language:</label>
                <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="java">Java</option>
                  <option value="cpp">C++</option>
                  <option value="go">Go</option>
                </select>
              </div>
              <div className="form-group">
                <label>Cursor Position: {cursorPosition}</label>
              </div>
            </div>
            <button onClick={handleCodeCompletion} disabled={loading || !code}>
              {loading ? 'Completing...' : 'Get Completion'}
            </button>
          </div>
        )}

        {activeTab === 'prompt-eng' && (
          <div className="feature-section">
            <h2>Advanced Prompt Engineering</h2>
            <div className="form-group">
              <label>Base Prompt:</label>
              <textarea
                value={basePrompt}
                onChange={(e) => setBasePrompt(e.target.value)}
                placeholder="Enter your basic prompt..."
                rows={3}
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Task Type:</label>
                <select value={taskType} onChange={(e) => setTaskType(e.target.value)}>
                  <option value="creative">Creative</option>
                  <option value="technical">Technical</option>
                  <option value="business">Business</option>
                  <option value="educational">Educational</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div className="form-group">
                <label>Style:</label>
                <select value={style} onChange={(e) => setStyle(e.target.value)}>
                  <option value="creative">Creative</option>
                  <option value="formal">Formal</option>
                  <option value="casual">Casual</option>
                  <option value="technical">Technical</option>
                  <option value="balanced">Balanced</option>
                </select>
              </div>
              <div className="form-group">
                <label>Length:</label>
                <select value={length} onChange={(e) => setLength(e.target.value)}>
                  <option value="short">Short</option>
                  <option value="medium">Medium</option>
                  <option value="long">Long</option>
                  <option value="detailed">Detailed</option>
                </select>
              </div>
            </div>
            <button onClick={handlePromptEngineering} disabled={loading || !basePrompt}>
              {loading ? 'Engineering...' : 'Engineer Prompt'}
            </button>
          </div>
        )}

        {activeTab === 'multimodal' && (
          <div className="feature-section">
            <h2>Multi-modal AI Interactions</h2>
            <div className="form-group">
              <label>Text Prompt:</label>
              <textarea
                value={textPrompt}
                onChange={(e) => setTextPrompt(e.target.value)}
                placeholder="Describe what you want to do..."
                rows={3}
              />
            </div>
            <div className="form-group">
              <label>Image (optional):</label>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setImageFile(e.target.files[0])}
              />
            </div>
            <div className="form-group">
              <label>Task:</label>
              <select value={multimodalTask} onChange={(e) => setMultimodalTask(e.target.value)}>
                <option value="analyze">Analyze</option>
                <option value="generate">Generate</option>
                <option value="convert">Convert</option>
                <option value="describe">Describe</option>
                <option value="combine">Combine</option>
              </select>
            </div>
            <button onClick={handleMultimodal} disabled={loading || (!textPrompt && !imageFile)}>
              {loading ? 'Processing...' : 'Process Multi-modal'}
            </button>
          </div>
        )}

        {activeTab === 'refactor' && (
          <div className="feature-section">
            <h2>AI-Powered Code Refactoring</h2>
            <div className="form-group">
              <label>Code to Refactor:</label>
              <textarea
                value={refactorCode}
                onChange={(e) => setRefactorCode(e.target.value)}
                placeholder="Paste your code here..."
                rows={10}
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Language:</label>
                <select value={refactorLanguage} onChange={(e) => setRefactorLanguage(e.target.value)}>
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="java">Java</option>
                  <option value="cpp">C++</option>
                </select>
              </div>
              <div className="form-group">
                <label>Refactoring Type:</label>
                <select value={refactoringType} onChange={(e) => setRefactoringType(e.target.value)}>
                  <option value="optimize">Optimize</option>
                  <option value="simplify">Simplify</option>
                  <option value="modernize">Modernize</option>
                  <option value="security">Security</option>
                  <option value="performance">Performance</option>
                </select>
              </div>
            </div>
            <button onClick={handleCodeRefactoring} disabled={loading || !refactorCode}>
              {loading ? 'Refactoring...' : 'Refactor Code'}
            </button>
          </div>
        )}

        {activeTab === 'convert' && (
          <div className="feature-section">
            <h2>Content Conversion</h2>
            <div className="form-row">
              <div className="form-group">
                <label>Input Type:</label>
                <select value={inputType} onChange={(e) => setInputType(e.target.value)}>
                  <option value="text">Text</option>
                  <option value="image">Image</option>
                </select>
              </div>
              <div className="form-group">
                <label>Output Type:</label>
                <select value={outputType} onChange={(e) => setOutputType(e.target.value)}>
                  <option value="text">Text</option>
                  <option value="image">Image</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Content:</label>
              <textarea
                value={conversionContent}
                onChange={(e) => setConversionContent(e.target.value)}
                placeholder={inputType === 'text' ? "Enter text to convert..." : "Describe the image..."}
                rows={5}
              />
            </div>
            <button onClick={handleConversion} disabled={loading || !conversionContent}>
              {loading ? 'Converting...' : 'Convert Content'}
            </button>
          </div>
        )}

        {activeTab === 'explain' && (
          <div className="feature-section">
            <h2>Code Explanation & Documentation</h2>
            <div className="form-group">
              <label>Code to Explain:</label>
              <textarea
                value={explainCode}
                onChange={(e) => setExplainCode(e.target.value)}
                placeholder="Paste your code here..."
                rows={10}
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Language:</label>
                <select value={explainLanguage} onChange={(e) => setExplainLanguage(e.target.value)}>
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="java">Java</option>
                  <option value="cpp">C++</option>
                </select>
              </div>
              <div className="form-group">
                <label>Explanation Level:</label>
                <select value={explanationLevel} onChange={(e) => setExplanationLevel(e.target.value)}>
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={includeExamples}
                    onChange={(e) => setIncludeExamples(e.target.checked)}
                  />
                  Include Examples
                </label>
              </div>
            </div>
            <button onClick={handleCodeExplanation} disabled={loading || !explainCode}>
              {loading ? 'Explaining...' : 'Explain Code'}
            </button>
          </div>
        )}

        {activeTab === 'debug' && (
          <div className="feature-section">
            <h2>AI-Assisted Debugging</h2>
            <div className="form-group">
              <label>Code with Issue:</label>
              <textarea
                value={debugCode}
                onChange={(e) => setDebugCode(e.target.value)}
                placeholder="Paste your problematic code here..."
                rows={10}
              />
            </div>
            <div className="form-row">
              <div className="form-group">
                <label>Language:</label>
                <select value={debugLanguage} onChange={(e) => setDebugLanguage(e.target.value)}>
                  <option value="python">Python</option>
                  <option value="javascript">JavaScript</option>
                  <option value="java">Java</option>
                  <option value="cpp">C++</option>
                </select>
              </div>
            </div>
            <div className="form-group">
              <label>Error Message (optional):</label>
              <textarea
                value={errorMessage}
                onChange={(e) => setErrorMessage(e.target.value)}
                placeholder="Paste the error message..."
                rows={3}
              />
            </div>
            <div className="form-group">
              <label>Stack Trace (optional):</label>
              <textarea
                value={stackTrace}
                onChange={(e) => setStackTrace(e.target.value)}
                placeholder="Paste the stack trace..."
                rows={5}
              />
            </div>
            <button onClick={handleDebug} disabled={loading || !debugCode}>
              {loading ? 'Analyzing...' : 'Debug Code'}
            </button>
          </div>
        )}
      </div>

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Processing your request...</p>
        </div>
      )}

      {error && (
        <div className="error">
          <h3>Error</h3>
          <p>{error}</p>
          {retryCount > 0 && (
            <p className="retry-info">Attempted {retryCount} retries</p>
          )}
          <button
            onClick={() => setError(null)}
            className="dismiss-error"
          >
            Dismiss
          </button>
        </div>
      )}

      {result && (
        <div className="result">
          <h3>Result</h3>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}

export default AIIntegrations