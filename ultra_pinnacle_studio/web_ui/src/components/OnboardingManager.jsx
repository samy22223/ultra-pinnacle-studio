import React, { useState, useEffect, useContext } from 'react';
import { useTranslation } from 'react-i18next';
import OnboardingModal from './OnboardingModal';
import OnboardingTooltip from './OnboardingTooltip';
import TutorialViewer from './TutorialViewer';
import HelpCenter from './HelpCenter';
import SupportChat from './SupportChat';

const OnboardingContext = React.createContext();

export const useOnboarding = () => {
  const context = useContext(OnboardingContext);
  if (!context) {
    throw new Error('useOnboarding must be used within an OnboardingProvider');
  }
  return context;
};

const OnboardingManager = ({ children }) => {
  const { t } = useTranslation('common');
  const [onboardingState, setOnboardingState] = useState({
    // Modal states
    showOnboardingModal: false,
    showTutorialViewer: false,
    showHelpCenter: false,
    showSupportChat: false,

    // Data states
    flows: [],
    progress: null,
    tutorials: [],
    tooltips: [],
    currentTutorial: null,

    // Loading states
    loading: false
  });

  useEffect(() => {
    loadInitialData();
    checkOnboardingStatus();
  }, []);

  const loadInitialData = async () => {
    try {
      setOnboardingState(prev => ({ ...prev, loading: true }));

      // Load onboarding flows
      const flowsResponse = await fetch('/api/onboarding/flows', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const flows = await flowsResponse.json();

      // Load tutorials
      const tutorialsResponse = await fetch('/api/tutorials', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const tutorials = await tutorialsResponse.json();

      // Load active tooltips
      const tooltipsResponse = await fetch('/api/tooltips', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const tooltips = await tooltipsResponse.json();

      setOnboardingState(prev => ({
        ...prev,
        flows,
        tutorials,
        tooltips,
        loading: false
      }));
    } catch (error) {
      console.error('Error loading onboarding data:', error);
      setOnboardingState(prev => ({ ...prev, loading: false }));
    }
  };

  const checkOnboardingStatus = async () => {
    try {
      const response = await fetch('/api/onboarding/progress', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        const progress = await response.json();
        setOnboardingState(prev => ({ ...prev, progress }));

        // Auto-show onboarding for new users
        if (progress.has_progress && progress.progress.status === 'not_started') {
          setTimeout(() => {
            showOnboardingModal();
          }, 2000); // Show after 2 seconds
        }
      }
    } catch (error) {
      console.error('Error checking onboarding status:', error);
    }
  };

  const showOnboardingModal = () => {
    setOnboardingState(prev => ({ ...prev, showOnboardingModal: true }));
  };

  const hideOnboardingModal = () => {
    setOnboardingState(prev => ({ ...prev, showOnboardingModal: false }));
  };

  const showTutorialViewer = (tutorial) => {
    setOnboardingState(prev => ({
      ...prev,
      showTutorialViewer: true,
      currentTutorial: tutorial
    }));
  };

  const hideTutorialViewer = () => {
    setOnboardingState(prev => ({
      ...prev,
      showTutorialViewer: false,
      currentTutorial: null
    }));
  };

  const showHelpCenter = () => {
    setOnboardingState(prev => ({ ...prev, showHelpCenter: true }));
  };

  const hideHelpCenter = () => {
    setOnboardingState(prev => ({ ...prev, showHelpCenter: false }));
  };

  const showSupportChat = () => {
    setOnboardingState(prev => ({ ...prev, showSupportChat: true }));
  };

  const hideSupportChat = () => {
    setOnboardingState(prev => ({ ...prev, showSupportChat: false }));
  };

  const completeOnboardingStep = async (stepId) => {
    try {
      const response = await fetch(`/api/onboarding/step/${stepId}/complete`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        // Refresh progress
        await checkOnboardingStatus();
        return true;
      }
    } catch (error) {
      console.error('Error completing onboarding step:', error);
    }
    return false;
  };

  const skipOnboardingStep = async (stepId) => {
    try {
      const response = await fetch(`/api/onboarding/step/${stepId}/skip`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        // Refresh progress
        await checkOnboardingStatus();
        return true;
      }
    } catch (error) {
      console.error('Error skipping onboarding step:', error);
    }
    return false;
  };

  const skipOnboarding = async () => {
    try {
      const response = await fetch('/api/onboarding/skip', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        hideOnboardingModal();
        await checkOnboardingStatus();
        return true;
      }
    } catch (error) {
      console.error('Error skipping onboarding:', error);
    }
    return false;
  };

  const updateTutorialProgress = async (tutorialId, progress, position) => {
    try {
      const response = await fetch(`/api/tutorials/${tutorialId}/progress`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          progress_percentage: progress,
          current_position: position
        })
      });

      if (response.ok) {
        // Refresh tutorials data
        await loadInitialData();
        return true;
      }
    } catch (error) {
      console.error('Error updating tutorial progress:', error);
    }
    return false;
  };

  const completeTutorial = async (tutorialId, rating, feedback) => {
    try {
      const response = await fetch(`/api/tutorials/${tutorialId}/complete`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          rating,
          feedback
        })
      });

      if (response.ok) {
        // Refresh tutorials data
        await loadInitialData();
        return true;
      }
    } catch (error) {
      console.error('Error completing tutorial:', error);
    }
    return false;
  };

  const recordTooltipInteraction = async (tooltipId, interactionType, data) => {
    try {
      await fetch(`/api/tooltips/${tooltipId}/interact`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          interaction_type: interactionType,
          interaction_data: data
        })
      });
    } catch (error) {
      console.error('Error recording tooltip interaction:', error);
    }
  };

  const contextValue = {
    // State
    ...onboardingState,

    // Actions
    showOnboardingModal,
    hideOnboardingModal,
    showTutorialViewer,
    hideTutorialViewer,
    showHelpCenter,
    hideHelpCenter,
    showSupportChat,
    hideSupportChat,

    // Onboarding actions
    completeOnboardingStep,
    skipOnboardingStep,
    skipOnboarding,

    // Tutorial actions
    updateTutorialProgress,
    completeTutorial,

    // Tooltip actions
    recordTooltipInteraction,

    // Data refresh
    refreshData: loadInitialData
  };

  return (
    <OnboardingContext.Provider value={contextValue}>
      {children}

      {/* Onboarding Modal */}
      <OnboardingModal
        isOpen={onboardingState.showOnboardingModal}
        onClose={hideOnboardingModal}
        flow={onboardingState.progress?.flow}
        progress={onboardingState.progress?.progress}
        onCompleteStep={completeOnboardingStep}
        onSkipStep={skipOnboardingStep}
        onSkipFlow={skipOnboarding}
      />

      {/* Tutorial Viewer */}
      <TutorialViewer
        tutorial={onboardingState.currentTutorial}
        isOpen={onboardingState.showTutorialViewer}
        onClose={hideTutorialViewer}
        onProgress={updateTutorialProgress}
        onComplete={completeTutorial}
      />

      {/* Help Center */}
      <HelpCenter
        isOpen={onboardingState.showHelpCenter}
        onClose={hideHelpCenter}
      />

      {/* Support Chat */}
      <SupportChat
        isOpen={onboardingState.showSupportChat}
        onClose={hideSupportChat}
      />

      {/* Active Tooltips */}
      {onboardingState.tooltips.map(tooltip => (
        <OnboardingTooltip
          key={tooltip.id}
          tooltip={tooltip}
          targetElement={tooltip.target_element}
          isVisible={true}
          onDismiss={(id) => recordTooltipInteraction(id, 'dismissed')}
          onInteract={recordTooltipInteraction}
          position={tooltip.position}
          trigger={tooltip.trigger_event}
        />
      ))}
    </OnboardingContext.Provider>
  );
};

export default OnboardingManager;