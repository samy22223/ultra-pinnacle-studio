import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import './Search.css';

const Search = () => {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    content_types: [],
    date_from: '',
    date_to: ''
  });

  const handleSearch = async () => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      const params = new URLSearchParams({
        query,
        limit: '20'
      });

      const response = await fetch(`/api/search?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setResults(data.results || []);
      }
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  const getContentTypeIcon = (contentType) => {
    const icons = {
      conversation: '💬',
      document: '📄',
      encyclopedia: '📚',
      help: '❓',
      user: '👤'
    };
    return icons[contentType] || '📄';
  };

  return (
    <div className="search-container">
      <h1>{t('search.title', 'Advanced Search')}</h1>

      <div className="search-input-section">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          placeholder={t('search.placeholder', 'Search across all content...')}
          className="search-input"
        />
        <button onClick={handleSearch} disabled={loading}>
          {loading ? '⏳' : '🔍'} {t('search.search', 'Search')}
        </button>
      </div>

      <div className="search-results">
        {loading && <div className="loading">Searching...</div>}

        {results.map((result, index) => (
          <div key={index} className="search-result-item">
            <div className="result-header">
              <span className="result-icon">{getContentTypeIcon(result.content_type)}</span>
              <h3>{result.title}</h3>
              <span className="result-type">{result.content_type}</span>
            </div>
            <div className="result-summary">{result.summary}</div>
            <div className="result-meta">
              {new Date(result.created_at).toLocaleDateString()}
            </div>
          </div>
        ))}

        {!loading && results.length === 0 && query && (
          <div className="no-results">No results found</div>
        )}
      </div>
    </div>
  );
};

export default Search;