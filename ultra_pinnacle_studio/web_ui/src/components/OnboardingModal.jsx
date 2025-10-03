import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import './OnboardingModal.css';

const OnboardingModal = ({ isOpen, onClose, flow, progress, onCompleteStep, onSkipStep, onSkipFlow }) => {
  const { t } = useTranslation('common');
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    if (progress?.current_step_id && flow?.steps) {
      const stepIndex = flow.steps.findIndex(step => step.id === progress.current_step_id);
      if (stepIndex >= 0) {
        setCurrentStepIndex(stepIndex);
      }
    }
  }, [progress, flow]);

  if (!isOpen || !flow || !progress) return null;

  const currentStep = flow.steps[currentStepIndex];
  const progressPercentage = ((currentStepIndex + 1) / flow.steps.length) * 100;

  const handleNext = async () => {
    if (currentStepIndex < flow.steps.length - 1) {
      setIsAnimating(true);
      setTimeout(() => {
        setCurrentStepIndex(currentStepIndex + 1);
        setIsAnimating(false);
      }, 300);
    }
  };

  const handlePrevious = () => {
    if (currentStepIndex > 0) {
      setIsAnimating(true);
      setTimeout(() => {
        setCurrentStepIndex(currentStepIndex - 1);
        setIsAnimating(false);
      }, 300);
    }
  };

  const handleComplete = async () => {
    try {
      await onCompleteStep(currentStep.id);
      if (currentStepIndex < flow.steps.length - 1) {
        handleNext();
      } else {
        // Flow completed
        onClose();
      }
    } catch (error) {
      console.error('Error completing step:', error);
    }
  };

  const handleSkip = async () => {
    if (currentStep.is_required) {
      // Cannot skip required steps
      return;
    }
    try {
      await onSkipStep(currentStep.id);
      if (currentStepIndex < flow.steps.length - 1) {
        handleNext();
      } else {
        onClose();
      }
    } catch (error) {
      console.error('Error skipping step:', error);
    }
  };

  const renderStepContent = () => {
    if (!currentStep) return null;

    switch (currentStep.content_type) {
      case 'modal':
        return (
          <div className="onboarding-step-content">
            <div className="step-header">
              <h2>{currentStep.title}</h2>
              <p>{currentStep.description}</p>
            </div>
            <div className="step-body">
              {currentStep.content?.text && (
                <div className="step-text" dangerouslySetInnerHTML={{ __html: currentStep.content.text }} />
              )}
              {currentStep.content?.image && (
                <div className="step-image">
                  <img src={currentStep.content.image} alt={currentStep.title} />
                </div>
              )}
              {currentStep.content?.video && (
                <div className="step-video">
                  <video controls>
                    <source src={currentStep.content.video} type="video/mp4" />
                  </video>
                </div>
              )}
            </div>
          </div>
        );

      case 'highlight':
        return (
          <div className="onboarding-step-content">
            <div className="step-header">
              <h2>{currentStep.title}</h2>
              <p>{currentStep.description}</p>
            </div>
            <div className="step-highlight-notice">
              <div className="highlight-icon">👆</div>
              <p>Check out the highlighted feature below</p>
            </div>
          </div>
        );

      case 'interactive':
        return (
          <div className="onboarding-step-content">
            <div className="step-header">
              <h2>{currentStep.title}</h2>
              <p>{currentStep.description}</p>
            </div>
            <div className="step-interactive">
              {currentStep.content?.instructions && (
                <div className="interactive-instructions">
                  <h3>What to do:</h3>
                  <ul>
                    {currentStep.content.instructions.map((instruction, index) => (
                      <li key={index}>{instruction}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        );

      default:
        return (
          <div className="onboarding-step-content">
            <div className="step-header">
              <h2>{currentStep.title}</h2>
              <p>{currentStep.description}</p>
            </div>
          </div>
        );
    }
  };

  return (
    <div className="onboarding-modal-overlay">
      <div className="onboarding-modal">
        <div className="modal-header">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
          <div className="progress-text">
            {currentStepIndex + 1} of {flow.steps.length}
          </div>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className={`modal-body ${isAnimating ? 'animating' : ''}`}>
          {renderStepContent()}
        </div>

        <div className="modal-footer">
          <div className="footer-left">
            {!currentStep?.is_required && (
              <button className="skip-button" onClick={handleSkip}>
                {t('onboarding.skip', 'Skip')}
              </button>
            )}
          </div>

          <div className="footer-center">
            <button
              className="nav-button prev"
              onClick={handlePrevious}
              disabled={currentStepIndex === 0}
            >
              ← {t('onboarding.previous', 'Previous')}
            </button>
          </div>

          <div className="footer-right">
            <button className="complete-button" onClick={handleComplete}>
              {currentStepIndex === flow.steps.length - 1
                ? t('onboarding.finish', 'Finish')
                : t('onboarding.next', 'Next')}
              →
            </button>
          </div>
        </div>

        <div className="modal-actions">
          <button className="skip-all-button" onClick={onSkipFlow}>
            {t('onboarding.skipAll', 'Skip all tutorials')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default OnboardingModal;