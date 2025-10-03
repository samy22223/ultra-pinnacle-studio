import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import './OnboardingTooltip.css';

const OnboardingTooltip = ({
  tooltip,
  targetElement,
  isVisible,
  onDismiss,
  onInteract,
  position = 'top',
  trigger = 'hover'
}) => {
  const { t } = useTranslation('common');
  const [isShown, setIsShown] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });
  const tooltipRef = useRef(null);
  const targetRef = useRef(null);

  useEffect(() => {
    if (isVisible && targetElement) {
      const target = document.querySelector(targetElement);
      if (target) {
        targetRef.current = target;

        if (trigger === 'hover') {
          const showTooltip = () => setIsShown(true);
          const hideTooltip = () => {
            setIsShown(false);
            onInteract && onInteract(tooltip.id, 'viewed');
          };

          target.addEventListener('mouseenter', showTooltip);
          target.addEventListener('mouseleave', hideTooltip);

          return () => {
            target.removeEventListener('mouseenter', showTooltip);
            target.removeEventListener('mouseleave', hideTooltip);
          };
        } else if (trigger === 'click') {
          const toggleTooltip = () => setIsShown(!isShown);
          target.addEventListener('click', toggleTooltip);

          return () => {
            target.removeEventListener('click', toggleTooltip);
          };
        } else if (trigger === 'auto') {
          // Auto-show tooltip
          setIsShown(true);
        }
      }
    }
  }, [isVisible, targetElement, trigger, tooltip, onInteract]);

  useEffect(() => {
    if (isShown && tooltipRef.current && targetRef.current) {
      updatePosition();
    }
  }, [isShown, position]);

  const updatePosition = () => {
    if (!tooltipRef.current || !targetRef.current) return;

    const targetRect = targetRef.current.getBoundingClientRect();
    const tooltipRect = tooltipRef.current.getBoundingClientRect();
    const viewport = {
      width: window.innerWidth,
      height: window.innerHeight
    };

    let top = 0;
    let left = 0;

    // Calculate position based on preferred position
    switch (position) {
      case 'top':
        top = targetRect.top - tooltipRect.height - 8;
        left = targetRect.left + (targetRect.width / 2) - (tooltipRect.width / 2);
        break;
      case 'bottom':
        top = targetRect.bottom + 8;
        left = targetRect.left + (targetRect.width / 2) - (tooltipRect.width / 2);
        break;
      case 'left':
        top = targetRect.top + (targetRect.height / 2) - (tooltipRect.height / 2);
        left = targetRect.left - tooltipRect.width - 8;
        break;
      case 'right':
        top = targetRect.top + (targetRect.height / 2) - (tooltipRect.height / 2);
        left = targetRect.right + 8;
        break;
      default:
        top = targetRect.top - tooltipRect.height - 8;
        left = targetRect.left + (targetRect.width / 2) - (tooltipRect.width / 2);
    }

    // Adjust if tooltip goes outside viewport
    if (left < 10) left = 10;
    if (left + tooltipRect.width > viewport.width - 10) {
      left = viewport.width - tooltipRect.width - 10;
    }
    if (top < 10) top = 10;
    if (top + tooltipRect.height > viewport.height - 10) {
      top = viewport.height - tooltipRect.height - 10;
    }

    setTooltipPosition({ top, left });
  };

  const handleDismiss = () => {
    setIsShown(false);
    onDismiss && onDismiss(tooltip.id);
    onInteract && onInteract(tooltip.id, 'dismissed');
  };

  const handleClick = () => {
    onInteract && onInteract(tooltip.id, 'clicked');
  };

  const handleLinkClick = (e) => {
    onInteract && onInteract(tooltip.id, 'followed_link');
  };

  if (!isVisible || !isShown || !tooltip) return null;

  return (
    <div
      ref={tooltipRef}
      className={`onboarding-tooltip tooltip-${position}`}
      style={{
        top: tooltipPosition.top,
        left: tooltipPosition.left
      }}
    >
      <div className="tooltip-content">
        <div className="tooltip-header">
          <h4>{tooltip.title}</h4>
          <button className="tooltip-close" onClick={handleDismiss}>×</button>
        </div>

        <div className="tooltip-body">
          <div
            className="tooltip-text"
            dangerouslySetInnerHTML={{ __html: tooltip.content }}
          />
        </div>

        <div className="tooltip-actions">
          <button className="tooltip-got-it" onClick={handleDismiss}>
            {t('tooltips.gotIt', 'Got it!')}
          </button>
        </div>
      </div>

      <div className="tooltip-arrow" />
    </div>
  );
};

export default OnboardingTooltip;