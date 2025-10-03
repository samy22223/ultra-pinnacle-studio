import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import './HelpCenter.css';

const HelpCenter = ({ isOpen, onClose }) => {
  const { t } = useTranslation('common');
  const [categories, setCategories] = useState([]);
  const [articles, setArticles] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedArticle, setSelectedArticle] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadCategories();
    }
  }, [isOpen]);

  useEffect(() => {
    if (selectedCategory) {
      loadArticles(selectedCategory.id);
    }
  }, [selectedCategory]);

  const loadCategories = async () => {
    try {
      const response = await fetch('/api/help/categories', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setCategories(data);
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

  const loadArticles = async (categoryId = null, search = '') => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (categoryId) params.append('category_id', categoryId);
      if (search) params.append('search', search);

      const response = await fetch(`/api/help/articles?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setArticles(data);
    } catch (error) {
      console.error('Error loading articles:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = (query) => {
    setSearchQuery(query);
    setSelectedCategory(null);
    loadArticles(null, query);
  };

  const handleArticleClick = async (article) => {
    try {
      const response = await fetch(`/api/help/articles/${article.id}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const fullArticle = await response.json();
      setSelectedArticle(fullArticle);
    } catch (error) {
      console.error('Error loading article:', error);
    }
  };

  const handleVote = async (articleId, helpful) => {
    try {
      await fetch(`/api/help/articles/${articleId}/vote`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ helpful })
      });

      // Update the article in the list
      setArticles(articles.map(article =>
        article.id === articleId
          ? {
              ...article,
              helpful_votes: helpful ? article.helpful_votes + 1 : article.helpful_votes,
              total_votes: article.total_votes + 1
            }
          : article
      ));

      if (selectedArticle && selectedArticle.id === articleId) {
        setSelectedArticle({
          ...selectedArticle,
          helpful_votes: helpful ? selectedArticle.helpful_votes + 1 : selectedArticle.helpful_votes,
          total_votes: selectedArticle.total_votes + 1
        });
      }
    } catch (error) {
      console.error('Error voting on article:', error);
    }
  };

  const getHelpfulnessPercentage = (helpful, total) => {
    if (total === 0) return 0;
    return Math.round((helpful / total) * 100);
  };

  if (!isOpen) return null;

  return (
    <div className="help-center-overlay">
      <div className="help-center">
        <div className="help-header">
          <div className="help-title">
            <h2>{t('help.title', 'Help Center')}</h2>
            <p>{t('help.subtitle', 'Find answers and learn how to use Ultra Pinnacle Studio')}</p>
          </div>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="help-search">
          <input
            type="text"
            placeholder={t('help.searchPlaceholder', 'Search for help...')}
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="search-input"
          />
        </div>

        <div className="help-content">
          {!selectedArticle ? (
            <div className="help-main">
              <div className="categories-sidebar">
                <h3>{t('help.categories', 'Categories')}</h3>
                <div className="category-list">
                  <button
                    className={`category-item ${!selectedCategory ? 'active' : ''}`}
                    onClick={() => {
                      setSelectedCategory(null);
                      loadArticles();
                    }}
                  >
                    {t('help.allArticles', 'All Articles')}
                  </button>
                  {categories.map(category => (
                    <button
                      key={category.id}
                      className={`category-item ${selectedCategory?.id === category.id ? 'active' : ''}`}
                      onClick={() => setSelectedCategory(category)}
                    >
                      <span className="category-icon">{category.icon || '📄'}</span>
                      <span className="category-name">{category.display_name}</span>
                      <span className="category-count">{category.article_count}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="articles-content">
                <div className="articles-header">
                  <h3>
                    {selectedCategory
                      ? selectedCategory.display_name
                      : t('help.allArticles', 'All Articles')
                    }
                  </h3>
                  <span className="articles-count">
                    {articles.length} {t('help.articles', 'articles')}
                  </span>
                </div>

                {isLoading ? (
                  <div className="loading-spinner">
                    <div className="spinner"></div>
                    {t('help.loading', 'Loading...')}
                  </div>
                ) : (
                  <div className="articles-list">
                    {articles.map(article => (
                      <div
                        key={article.id}
                        className="article-item"
                        onClick={() => handleArticleClick(article)}
                      >
                        <div className="article-info">
                          <h4>{article.title}</h4>
                          <p className="article-summary">{article.summary}</p>
                          <div className="article-meta">
                            <span className={`difficulty ${article.difficulty_level}`}>
                              {t(`help.difficulty.${article.difficulty_level}`, article.difficulty_level)}
                            </span>
                            <span className="views">{article.view_count} views</span>
                            {article.helpful_votes > 0 && (
                              <span className="helpfulness">
                                {getHelpfulnessPercentage(article.helpful_votes, article.total_votes)}% helpful
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="article-arrow">→</div>
                      </div>
                    ))}

                    {articles.length === 0 && !isLoading && (
                      <div className="no-articles">
                        <p>{t('help.noArticles', 'No articles found')}</p>
                        {searchQuery && (
                          <p>{t('help.tryDifferentSearch', 'Try a different search term')}</p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="article-view">
              <button
                className="back-button"
                onClick={() => setSelectedArticle(null)}
              >
                ← {t('help.backToArticles', 'Back to Articles')}
              </button>

              <div className="article-content">
                <div className="article-header">
                  <h2>{selectedArticle.title}</h2>
                  <div className="article-meta">
                    <span className={`difficulty ${selectedArticle.difficulty_level}`}>
                      {t(`help.difficulty.${selectedArticle.difficulty_level}`, selectedArticle.difficulty_level)}
                    </span>
                    <span className="category">
                      {selectedArticle.category?.display_name}
                    </span>
                    <span className="views">{selectedArticle.view_count} views</span>
                  </div>
                </div>

                <div className="article-body">
                  <div dangerouslySetInnerHTML={{ __html: selectedArticle.content }} />
                </div>

                <div className="article-feedback">
                  <h4>{t('help.wasThisHelpful', 'Was this article helpful?')}</h4>
                  <div className="feedback-buttons">
                    <button
                      className="feedback-btn helpful"
                      onClick={() => handleVote(selectedArticle.id, true)}
                    >
                      👍 {t('help.yes', 'Yes')}
                    </button>
                    <button
                      className="feedback-btn not-helpful"
                      onClick={() => handleVote(selectedArticle.id, false)}
                    >
                      👎 {t('help.no', 'No')}
                    </button>
                  </div>
                  <div className="helpfulness-stats">
                    {selectedArticle.helpful_votes > 0 && (
                      <span>
                        {getHelpfulnessPercentage(selectedArticle.helpful_votes, selectedArticle.total_votes)}%
                        {t('help.ofReadersFoundHelpful', ' of readers found this helpful')}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default HelpCenter;