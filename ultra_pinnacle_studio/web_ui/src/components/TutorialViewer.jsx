import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import './TutorialViewer.css';

const TutorialViewer = ({ tutorial, isOpen, onClose, onProgress, onComplete }) => {
  const { t } = useTranslation('common');
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [rating, setRating] = useState(0);
  const [feedback, setFeedback] = useState('');
  const [showCompletion, setShowCompletion] = useState(false);
  const videoRef = useRef(null);
  const progressInterval = useRef(null);

  useEffect(() => {
    if (isOpen && tutorial) {
      setCurrentTime(0);
      setProgress(tutorial.user_progress?.progress_percentage || 0);
      setRating(tutorial.user_progress?.rating || 0);
      setFeedback(tutorial.user_progress?.feedback || '');
      setShowCompletion(false);

      // Start tutorial if not started
      if (!tutorial.user_progress || tutorial.user_progress.status === 'not_started') {
        handleStartTutorial();
      }
    }
  }, [isOpen, tutorial]);

  useEffect(() => {
    return () => {
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }
    };
  }, []);

  const handleStartTutorial = async () => {
    try {
      await fetch('/api/tutorials/' + tutorial.id + '/start', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });
    } catch (error) {
      console.error('Error starting tutorial:', error);
    }
  };

  const handleVideoLoad = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
      // Seek to saved position if available
      if (tutorial.user_progress?.current_position?.time) {
        videoRef.current.currentTime = tutorial.user_progress.current_position.time;
      }
    }
  };

  const handlePlay = () => {
    setIsPlaying(true);
    startProgressTracking();
  };

  const handlePause = () => {
    setIsPlaying(false);
    stopProgressTracking();
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
      const newProgress = (videoRef.current.currentTime / videoRef.current.duration) * 100;
      setProgress(newProgress);
    }
  };

  const handleSeek = (e) => {
    if (videoRef.current) {
      const rect = e.target.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const percentage = clickX / rect.width;
      const newTime = percentage * duration;

      videoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
      setProgress(percentage * 100);
    }
  };

  const startProgressTracking = () => {
    progressInterval.current = setInterval(async () => {
      if (videoRef.current) {
        const currentProgress = (videoRef.current.currentTime / videoRef.current.duration) * 100;
        try {
          await onProgress(tutorial.id, currentProgress, {
            time: videoRef.current.currentTime,
            duration: videoRef.current.duration
          });
        } catch (error) {
          console.error('Error updating progress:', error);
        }
      }
    }, 5000); // Update every 5 seconds
  };

  const stopProgressTracking = () => {
    if (progressInterval.current) {
      clearInterval(progressInterval.current);
      progressInterval.current = null;
    }
  };

  const handleComplete = async () => {
    try {
      await onComplete(tutorial.id, rating, feedback);
      setShowCompletion(true);
    } catch (error) {
      console.error('Error completing tutorial:', error);
    }
  };

  const formatTime = (time) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  if (!isOpen || !tutorial) return null;

  return (
    <div className="tutorial-viewer-overlay">
      <div className="tutorial-viewer">
        <div className="tutorial-header">
          <div className="tutorial-info">
            <h2>{tutorial.title}</h2>
            <div className="tutorial-meta">
              <span className={`difficulty ${tutorial.difficulty_level}`}>
                {t(`tutorial.difficulty.${tutorial.difficulty_level}`, tutorial.difficulty_level)}
              </span>
              <span className="duration">
                {tutorial.estimated_duration ? Math.ceil(tutorial.estimated_duration / 60) : 0} min
              </span>
              <span className="views">{tutorial.view_count} views</span>
            </div>
          </div>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="tutorial-content">
          {tutorial.content_type === 'video' && tutorial.video_url && (
            <div className="video-container">
              <video
                ref={videoRef}
                src={tutorial.video_url}
                onLoadedMetadata={handleVideoLoad}
                onPlay={handlePlay}
                onPause={handlePause}
                onTimeUpdate={handleTimeUpdate}
                onEnded={() => setProgress(100)}
                controls
                className="tutorial-video"
              />
              <div className="video-controls">
                <div className="progress-bar" onClick={handleSeek}>
                  <div
                    className="progress-fill"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="time-display">
                  {formatTime(currentTime)} / {formatTime(duration)}
                </div>
              </div>
            </div>
          )}

          {tutorial.content_type === 'interactive' && tutorial.content && (
            <div className="interactive-content">
              {tutorial.content.steps && tutorial.content.steps.map((step, index) => (
                <div key={index} className="interactive-step">
                  <h3>{step.title}</h3>
                  <div dangerouslySetInnerHTML={{ __html: step.content }} />
                  {step.action && (
                    <button className="step-action">{step.action.label}</button>
                  )}
                </div>
              ))}
            </div>
          )}

          {tutorial.content_type === 'text' && tutorial.content && (
            <div className="text-content">
              <div dangerouslySetInnerHTML={{ __html: tutorial.content }} />
            </div>
          )}
        </div>

        {!showCompletion && (
          <div className="tutorial-footer">
            <div className="progress-info">
              <div className="progress-text">
                {t('tutorial.progress', 'Progress')}: {Math.round(progress)}%
              </div>
              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {progress >= 95 && (
              <div className="completion-section">
                <h3>{t('tutorial.rateExperience', 'Rate your experience')}</h3>
                <div className="rating-stars">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      className={`star ${rating >= star ? 'active' : ''}`}
                      onClick={() => setRating(star)}
                    >
                      ★
                    </button>
                  ))}
                </div>
                <textarea
                  placeholder={t('tutorial.feedbackPlaceholder', 'Share your feedback (optional)')}
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  className="feedback-input"
                />
                <button
                  className="complete-button"
                  onClick={handleComplete}
                  disabled={rating === 0}
                >
                  {t('tutorial.complete', 'Complete Tutorial')}
                </button>
              </div>
            )}
          </div>
        )}

        {showCompletion && (
          <div className="completion-message">
            <div className="completion-icon">✓</div>
            <h3>{t('tutorial.completed', 'Tutorial Completed!')}</h3>
            <p>{t('tutorial.completedMessage', 'Thank you for completing this tutorial. Your feedback helps us improve.')}</p>
            <button className="close-tutorial" onClick={onClose}>
              {t('tutorial.close', 'Close')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default TutorialViewer;