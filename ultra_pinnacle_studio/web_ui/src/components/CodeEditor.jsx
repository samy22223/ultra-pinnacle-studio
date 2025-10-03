import React, { useState, useEffect, useRef } from 'react'
import axios from 'axios'

const CodeEditor = ({ token }) => {
  const [code, setCode] = useState(`// Welcome to Ultra Pinnacle Code Editor
// AI-powered development environment

function helloWorld() {
  console.log("Hello, Ultra Pinnacle!");
}

helloWorld();`)
  const [language, setLanguage] = useState('javascript')
  const [output, setOutput] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [aiSuggestions, setAiSuggestions] = useState([])
  const [cursorPosition, setCursorPosition] = useState(0)
  const [files, setFiles] = useState([])
  const [currentFile, setCurrentFile] = useState('main.js')
  const [projects, setProjects] = useState([])
  const [currentProject, setCurrentProject] = useState('Untitled Project')
  const textareaRef = useRef(null)

  const languages = [
    'javascript', 'python', 'java', 'cpp', 'csharp', 'php', 'ruby', 'go', 'rust', 'typescript'
  ]

  useEffect(() => {
    if (token) {
      loadProjects()
      loadFiles()
    }
  }, [token])

  const loadProjects = async () => {
    try {
      const response = await axios.get('http://localhost:8000/code/projects', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setProjects(response.data)
    } catch (error) {
      console.error('Error loading projects:', error)
    }
  }

  const loadFiles = async () => {
    try {
      const response = await axios.get('http://localhost:8000/code/files', {
        headers: { Authorization: `Bearer ${token}` }
      })
      setFiles(response.data)
    } catch (error) {
      console.error('Error loading files:', error)
    }
  }

  const runCode = async () => {
    setIsRunning(true)
    try {
      const response = await axios.post('http://localhost:8000/code/execute', {
        code,
        language
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setOutput(response.data.output)
    } catch (error) {
      setOutput('Error: ' + error.message)
    } finally {
      setIsRunning(false)
    }
  }

  const getAISuggestions = async () => {
    try {
      const response = await axios.post('http://localhost:8000/code/suggest', {
        code,
        cursor: cursorPosition,
        language
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setAiSuggestions(response.data.suggestions)
    } catch (error) {
      console.error('Error getting AI suggestions:', error)
    }
  }

  const analyzeCode = async () => {
    try {
      const response = await axios.post('http://localhost:8000/code/analyze', {
        code,
        language
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      setOutput('Analysis:\n' + response.data.analysis)
    } catch (error) {
      setOutput('Error: ' + error.message)
    }
  }

  const saveProject = async () => {
    try {
      await axios.post('http://localhost:8000/code/save', {
        name: currentProject,
        files: [{ name: currentFile, content: code, language }]
      }, {
        headers: { Authorization: `Bearer ${token}` }
      })
      alert('Project saved successfully!')
      loadProjects()
    } catch (error) {
      alert('Error saving project: ' + error.message)
    }
  }

  const handleCursorChange = (e) => {
    setCursorPosition(e.target.selectionStart)
  }

  const insertSuggestion = (suggestion) => {
    const before = code.substring(0, cursorPosition)
    const after = code.substring(cursorPosition)
    setCode(before + suggestion + after)
    setAiSuggestions([])
  }

  return (
    <div style={{ display: 'flex', height: '100vh', gap: '1rem' }}>
      {/* File Explorer */}
      <div style={{ width: '200px', borderRight: '1px solid #ccc', padding: '1rem' }}>
        <h3>Files</h3>
        <div style={{ marginBottom: '1rem' }}>
          <input
            type="text"
            value={currentFile}
            onChange={(e) => setCurrentFile(e.target.value)}
            placeholder="File name"
            style={{ width: '100%' }}
          />
        </div>
        <div>
          {files.map(file => (
            <div key={file.name} style={{ padding: '0.5rem', cursor: 'pointer' }}>
              {file.name}
            </div>
          ))}
        </div>
        <h3 style={{ marginTop: '2rem' }}>Projects</h3>
        <div>
          {projects.map(project => (
            <div key={project.id} style={{ padding: '0.5rem', cursor: 'pointer' }}>
              {project.name}
            </div>
          ))}
        </div>
      </div>

      {/* Editor */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '1rem', borderBottom: '1px solid #ccc' }}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <input
              type="text"
              value={currentProject}
              onChange={(e) => setCurrentProject(e.target.value)}
              placeholder="Project name"
            />
            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
              {languages.map(lang => (
                <option key={lang} value={lang}>{lang}</option>
              ))}
            </select>
            <button onClick={runCode} disabled={isRunning}>
              {isRunning ? 'Running...' : 'Run Code'}
            </button>
            <button onClick={analyzeCode}>Analyze</button>
            <button onClick={getAISuggestions}>AI Suggest</button>
            <button onClick={saveProject}>Save Project</button>
          </div>
        </div>

        <div style={{ display: 'flex', flex: 1 }}>
          <div style={{ flex: 1, position: 'relative' }}>
            <textarea
              ref={textareaRef}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onSelect={handleCursorChange}
              onKeyUp={handleCursorChange}
              style={{
                width: '100%',
                height: '100%',
                fontFamily: 'monospace',
                fontSize: '14px',
                padding: '1rem',
                border: 'none',
                outline: 'none',
                resize: 'none'
              }}
              placeholder="Write your code here..."
            />

            {/* AI Suggestions */}
            {aiSuggestions.length > 0 && (
              <div style={{
                position: 'absolute',
                top: '50px',
                left: '20px',
                background: 'white',
                border: '1px solid #ccc',
                borderRadius: '4px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                zIndex: 1000
              }}>
                {aiSuggestions.map((suggestion, index) => (
                  <div
                    key={index}
                    onClick={() => insertSuggestion(suggestion)}
                    style={{
                      padding: '0.5rem',
                      cursor: 'pointer',
                      borderBottom: index < aiSuggestions.length - 1 ? '1px solid #eee' : 'none'
                    }}
                  >
                    {suggestion}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Output Panel */}
          <div style={{ width: '400px', borderLeft: '1px solid #ccc', padding: '1rem' }}>
            <h3>Output</h3>
            <pre style={{
              background: '#f5f5f5',
              padding: '1rem',
              borderRadius: '4px',
              fontSize: '12px',
              height: '80%',
              overflow: 'auto',
              whiteSpace: 'pre-wrap'
            }}>
              {output}
            </pre>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CodeEditor