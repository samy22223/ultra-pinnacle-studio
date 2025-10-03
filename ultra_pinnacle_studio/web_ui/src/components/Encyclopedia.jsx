import React, { useState, useEffect } from 'react'
import axios from 'axios'

const Encyclopedia = () => {
  const [topics, setTopics] = useState([])
  const [selectedTopic, setSelectedTopic] = useState('')
  const [content, setContent] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState('')

  useEffect(() => {
    listTopics()
  }, [])

  const listTopics = async () => {
    try {
      const res = await axios.get('http://localhost:8000/encyclopedia/list')
      setTopics(res.data.topics)
    } catch (error) {
      console.error('Error listing topics:', error)
    }
  }

  const getTopic = async () => {
    if (!selectedTopic) return
    try {
      const res = await axios.get(`http://localhost:8000/encyclopedia/${selectedTopic}`)
      setContent(res.data.content)
    } catch (error) {
      setContent('Error: ' + error.message)
    }
  }

  const search = async () => {
    if (!searchQuery) return
    try {
      const res = await axios.post('http://localhost:8000/encyclopedia/search', { query: searchQuery })
      let html = `<h3>Search Results for "${res.data.query}"</h3>`
      res.data.results.forEach(r => {
        html += `<h4>${r.topic}</h4><ul>`
        r.matches.forEach(match => html += `<li>${match}</li>`)
        html += '</ul>'
      })
      setSearchResults(html)
    } catch (error) {
      setSearchResults('Error: ' + error.message)
    }
  }

  return (
    <div>
      <h2>Encyclopedia</h2>
      <button onClick={listTopics}>List Topics</button>
      <p>{topics.join(', ')}</p>

      <select value={selectedTopic} onChange={(e) => setSelectedTopic(e.target.value)}>
        <option value="">Select Topic</option>
        {topics.map(topic => <option key={topic} value={topic}>{topic}</option>)}
      </select>
      <button onClick={getTopic}>Get Topic</button>
      <div style={{ marginTop: '1rem', whiteSpace: 'pre-wrap' }}>
        {content}
      </div>

      <input
        type="text"
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        placeholder="Search encyclopedia..."
      />
      <button onClick={search}>Search</button>
      <div style={{ marginTop: '1rem' }} dangerouslySetInnerHTML={{ __html: searchResults }} />
    </div>
  )
}

export default Encyclopedia