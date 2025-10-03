"""
User Feedback and Continuous Improvement System
"""

import json
import time
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import statistics

from .logging_config import logger

class FeedbackCollector:
    """Collect and analyze user feedback"""

    def __init__(self):
        self.feedback_store = deque(maxlen=10000)  # Store last 10k feedback items
        self.feedback_stats = defaultdict(int)
        self.user_feedback = defaultdict(list)  # user_id -> list of feedback
        self.feature_ratings = defaultdict(list)  # feature -> list of ratings
        self.lock = threading.Lock()

    def collect_feedback(self, user_id: str, feedback_type: str, content: Dict[str, Any],
                        rating: Optional[int] = None, metadata: Optional[Dict] = None) -> str:
        """Collect user feedback"""
        feedback_id = f"fb_{int(time.time())}_{hash(f'{user_id}_{feedback_type}') % 10000}"

        feedback_entry = {
            "id": feedback_id,
            "user_id": user_id,
            "type": feedback_type,
            "content": content,
            "rating": rating,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "processed": False
        }

        with self.lock:
            self.feedback_store.append(feedback_entry)
            self.feedback_stats[feedback_type] += 1

            if user_id:
                self.user_feedback[user_id].append(feedback_entry)

            if rating is not None and "feature" in content:
                self.feature_ratings[content["feature"]].append(rating)

        logger.info(f"Collected feedback {feedback_id} from user {user_id}: {feedback_type}")
        return feedback_id

    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics"""
        with self.lock:
            stats = {
                "total_feedback": len(self.feedback_store),
                "feedback_by_type": dict(self.feedback_stats),
                "avg_ratings_by_feature": {}
            }

            # Calculate average ratings
            for feature, ratings in self.feature_ratings.items():
                if ratings:
                    stats["avg_ratings_by_feature"][feature] = {
                        "average": statistics.mean(ratings),
                        "count": len(ratings),
                        "min": min(ratings),
                        "max": max(ratings)
                    }

            return stats

    def get_recent_feedback(self, hours: int = 24, feedback_type: str = None) -> List[Dict]:
        """Get recent feedback entries"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        with self.lock:
            recent = [
                fb for fb in self.feedback_store
                if datetime.fromisoformat(fb["timestamp"]) > cutoff_time
            ]

            if feedback_type:
                recent = [fb for fb in recent if fb["type"] == feedback_type]

            return recent[-100:]  # Return last 100

    def analyze_feedback_trends(self) -> Dict[str, Any]:
        """Analyze feedback trends and patterns"""
        with self.lock:
            # Group feedback by day
            daily_feedback = defaultdict(lambda: defaultdict(int))

            for fb in self.feedback_store:
                date = datetime.fromisoformat(fb["timestamp"]).date().isoformat()
                daily_feedback[date][fb["type"]] += 1

            # Calculate trends
            trends = {
                "daily_counts": dict(daily_feedback),
                "most_common_types": sorted(
                    self.feedback_stats.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5],
                "features_needing_attention": []
            }

            # Identify features with low ratings
            for feature, ratings in self.feature_ratings.items():
                if ratings and statistics.mean(ratings) < 3.0:  # Below 3/5 average
                    trends["features_needing_attention"].append({
                        "feature": feature,
                        "avg_rating": statistics.mean(ratings),
                        "count": len(ratings)
                    })

            return trends

class ImprovementTracker:
    """Track system improvements based on feedback"""

    def __init__(self):
        self.improvements = []
        self.pending_improvements = []
        self.completed_improvements = []
        self.lock = threading.Lock()

    def suggest_improvement(self, source: str, category: str, description: str,
                           priority: str = "medium", related_feedback: List[str] = None) -> str:
        """Suggest a system improvement"""
        improvement_id = f"imp_{int(time.time())}_{hash(description) % 10000}"

        improvement = {
            "id": improvement_id,
            "source": source,  # "user_feedback", "system_monitoring", "performance_analysis"
            "category": category,  # "ui", "performance", "security", "features"
            "description": description,
            "priority": priority,
            "status": "pending",
            "related_feedback": related_feedback or [],
            "created_at": datetime.now().isoformat(),
            "votes": 0,
            "comments": []
        }

        with self.lock:
            self.pending_improvements.append(improvement)
            self.improvements.append(improvement)

        logger.info(f"Suggested improvement {improvement_id}: {description}")
        return improvement_id

    def vote_for_improvement(self, improvement_id: str, user_id: str) -> bool:
        """Vote for an improvement"""
        with self.lock:
            for improvement in self.improvements:
                if improvement["id"] == improvement_id:
                    if user_id not in improvement.get("voters", []):
                        improvement["votes"] += 1
                        improvement.setdefault("voters", []).append(user_id)
                        return True
                    break
        return False

    def complete_improvement(self, improvement_id: str, resolution: str) -> bool:
        """Mark improvement as completed"""
        with self.lock:
            for improvement in self.pending_improvements:
                if improvement["id"] == improvement_id:
                    improvement["status"] = "completed"
                    improvement["completed_at"] = datetime.now().isoformat()
                    improvement["resolution"] = resolution
                    self.completed_improvements.append(improvement)
                    self.pending_improvements.remove(improvement)
                    logger.info(f"Completed improvement {improvement_id}: {resolution}")
                    return True
        return False

    def get_top_improvements(self, limit: int = 10) -> List[Dict]:
        """Get top-voted pending improvements"""
        with self.lock:
            sorted_improvements = sorted(
                self.pending_improvements,
                key=lambda x: (x["votes"], {"high": 3, "medium": 2, "low": 1}[x["priority"]]),
                reverse=True
            )
            return sorted_improvements[:limit]

class BackwardCompatibilityManager:
    """Ensure backward compatibility across versions"""

    def __init__(self):
        self.api_versions = {}
        self.deprecated_features = set()
        self.compatibility_matrix = {}
        self.migration_guides = {}

    def register_api_version(self, version: str, endpoints: Dict[str, Any]):
        """Register API endpoints for a version"""
        self.api_versions[version] = {
            "endpoints": endpoints,
            "release_date": datetime.now().isoformat(),
            "supported": True
        }

    def deprecate_feature(self, feature: str, replacement: str = None,
                         removal_version: str = None, migration_guide: str = None):
        """Mark a feature as deprecated"""
        self.deprecated_features.add(feature)

        deprecation_info = {
            "feature": feature,
            "replacement": replacement,
            "deprecated_at": datetime.now().isoformat(),
            "removal_version": removal_version,
            "migration_guide": migration_guide
        }

        logger.warning(f"Deprecated feature: {feature}")

        if migration_guide:
            self.migration_guides[feature] = migration_guide

    def check_compatibility(self, client_version: str, requested_features: List[str]) -> Dict[str, Any]:
        """Check compatibility of requested features"""
        compatibility_report = {
            "compatible": True,
            "warnings": [],
            "deprecated_features": [],
            "migration_needed": []
        }

        # Check for deprecated features
        for feature in requested_features:
            if feature in self.deprecated_features:
                compatibility_report["deprecated_features"].append(feature)
                compatibility_report["warnings"].append(f"Feature '{feature}' is deprecated")

        # Check version compatibility
        if client_version in self.compatibility_matrix:
            matrix = self.compatibility_matrix[client_version]
            for feature in requested_features:
                if feature in matrix and not matrix[feature]:
                    compatibility_report["compatible"] = False
                    compatibility_report["migration_needed"].append(feature)

        return compatibility_report

    def get_migration_guide(self, feature: str) -> Optional[str]:
        """Get migration guide for a deprecated feature"""
        return self.migration_guides.get(feature)

class AIBasedInsights:
    """AI-powered insights from user feedback and system data"""

    def __init__(self):
        self.feedback_patterns = []
        self.user_segments = {}
        self.predictive_insights = []

    def analyze_feedback_patterns(self, feedback_data: List[Dict]) -> List[str]:
        """Analyze feedback for patterns and insights"""
        insights = []

        # Simple pattern analysis (in real implementation, use ML/AI)
        error_feedback = [f for f in feedback_data if f.get("type") == "error_report"]
        if len(error_feedback) > len(feedback_data) * 0.3:
            insights.append("High error reporting rate detected - investigate system stability")

        low_ratings = [f for f in feedback_data if f.get("rating", 5) < 3]
        if len(low_ratings) > len(feedback_data) * 0.2:
            insights.append("Significant user dissatisfaction detected - review recent changes")

        # Feature-specific insights
        feature_feedback = defaultdict(list)
        for f in feedback_data:
            if "feature" in f.get("content", {}):
                feature_feedback[f["content"]["feature"]].append(f)

        for feature, feedbacks in feature_feedback.items():
            avg_rating = statistics.mean([f.get("rating", 3) for f in feedbacks if f.get("rating")])
            if avg_rating < 2.5:
                insights.append(f"Feature '{feature}' has poor user satisfaction (avg rating: {avg_rating:.1f})")

        return insights

    def generate_recommendations(self, system_metrics: Dict, feedback_stats: Dict) -> List[str]:
        """Generate AI-powered recommendations"""
        recommendations = []

        # Performance-based recommendations
        if system_metrics.get("cpu_percent", 0) > 80:
            recommendations.append("Consider optimizing CPU-intensive operations or scaling resources")

        if system_metrics.get("memory_percent", 0) > 85:
            recommendations.append("Memory usage is high - implement memory optimization strategies")

        # Feedback-based recommendations
        if feedback_stats.get("total_feedback", 0) > 100:
            recommendations.append("High feedback volume detected - consider implementing suggested improvements")

        # User engagement recommendations
        low_usage_features = []
        for feature, stats in feedback_stats.get("avg_ratings_by_feature", {}).items():
            if stats.get("count", 0) < 5:  # Low usage
                low_usage_features.append(feature)

        if low_usage_features:
            recommendations.append(f"Consider promoting or improving underutilized features: {', '.join(low_usage_features[:3])}")

        return recommendations

# Global instances
feedback_collector = FeedbackCollector()
improvement_tracker = ImprovementTracker()
compatibility_manager = BackwardCompatibilityManager()
ai_insights = AIBasedInsights()

logger.info("Feedback and improvement system initialized")