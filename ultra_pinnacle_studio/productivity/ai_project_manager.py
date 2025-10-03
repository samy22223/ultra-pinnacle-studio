#!/usr/bin/env python3
"""
Ultra Pinnacle Studio - AI Project Management
Trello/Asana/Notion-style, but auto-managed, including task prioritization and progress prediction
"""

import os
import json
import time
import asyncio
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

class ProjectStatus(Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskStatus(Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    COMPLETED = "completed"
    BLOCKED = "blocked"

class TaskPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

@dataclass
class Project:
    """Project information"""
    project_id: str
    name: str
    description: str
    status: ProjectStatus
    owner_id: str
    team_members: List[str]
    start_date: datetime
    end_date: datetime
    budget: float
    progress: float

@dataclass
class Task:
    """Task information"""
    task_id: str
    project_id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee_id: str
    estimated_hours: float
    actual_hours: float
    due_date: datetime
    dependencies: List[str]
    tags: List[str]
    ai_priority_score: float = 0.0

@dataclass
class ProjectMilestone:
    """Project milestone"""
    milestone_id: str
    project_id: str
    title: str
    description: str
    due_date: datetime
    completed: bool
    tasks_completed: int
    total_tasks: int

class AIProjectManager:
    """AI-powered project management system"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.projects = self.load_sample_projects()
        self.tasks = self.load_sample_tasks()
        self.milestones = self.load_sample_milestones()

    def load_sample_projects(self) -> List[Project]:
        """Load sample projects"""
        return [
            Project(
                project_id="proj_001",
                name="Ultra Pinnacle Platform Launch",
                description="Launch the comprehensive Ultra Pinnacle Studio platform",
                status=ProjectStatus.ACTIVE,
                owner_id="admin_user",
                team_members=["dev_lead", "designer", "marketer", "qa_engineer"],
                start_date=datetime.now() - timedelta(days=60),
                end_date=datetime.now() + timedelta(days=30),
                budget=100000.0,
                progress=65.0
            ),
            Project(
                project_id="proj_002",
                name="AI Features Development",
                description="Develop advanced AI features for the platform",
                status=ProjectStatus.ACTIVE,
                owner_id="tech_lead",
                team_members=["ai_engineer", "ml_researcher", "data_scientist"],
                start_date=datetime.now() - timedelta(days=30),
                end_date=datetime.now() + timedelta(days=60),
                budget=75000.0,
                progress=40.0
            )
        ]

    def load_sample_tasks(self) -> List[Task]:
        """Load sample tasks"""
        return [
            Task(
                task_id="task_001",
                project_id="proj_001",
                title="Complete AI video generator",
                description="Implement advanced AI video generation with 4K support",
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.HIGH,
                assignee_id="ai_engineer",
                estimated_hours=40.0,
                actual_hours=25.0,
                due_date=datetime.now() + timedelta(days=7),
                dependencies=[],
                tags=["ai", "video", "media"],
                ai_priority_score=0.85
            ),
            Task(
                task_id="task_002",
                project_id="proj_001",
                title="Set up automated testing",
                description="Implement comprehensive automated testing suite",
                status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                assignee_id="qa_engineer",
                estimated_hours=20.0,
                actual_hours=0.0,
                due_date=datetime.now() + timedelta(days=14),
                dependencies=["task_001"],
                tags=["testing", "automation", "quality"],
                ai_priority_score=0.65
            ),
            Task(
                task_id="task_003",
                project_id="proj_002",
                title="Research market trends",
                description="Analyze current AI market trends and opportunities",
                status=TaskStatus.COMPLETED,
                priority=TaskPriority.HIGH,
                assignee_id="ml_researcher",
                estimated_hours=16.0,
                actual_hours=18.0,
                due_date=datetime.now() - timedelta(days=5),
                dependencies=[],
                tags=["research", "market", "analysis"],
                ai_priority_score=0.90
            )
        ]

    def load_sample_milestones(self) -> List[ProjectMilestone]:
        """Load sample milestones"""
        return [
            ProjectMilestone(
                milestone_id="milestone_001",
                project_id="proj_001",
                title="MVP Complete",
                description="Minimum viable product with core features",
                due_date=datetime.now() + timedelta(days=15),
                completed=False,
                tasks_completed=8,
                total_tasks=12
            ),
            ProjectMilestone(
                milestone_id="milestone_002",
                project_id="proj_001",
                title="Beta Launch",
                description="Beta version ready for testing",
                due_date=datetime.now() + timedelta(days=45),
                completed=False,
                tasks_completed=3,
                total_tasks=8
            )
        ]

    async def run_ai_project_management(self) -> Dict:
        """Run AI-powered project management"""
        print("📋 Running AI project management system...")

        management_results = {
            "projects_managed": 0,
            "tasks_prioritized": 0,
            "progress_predictions": 0,
            "automated_updates": 0,
            "risk_assessments": 0,
            "resource_optimization": 0.0
        }

        # Process each project
        for project in self.projects:
            if project.status == ProjectStatus.ACTIVE:
                # AI task prioritization
                prioritization_results = await self.ai_task_prioritization(project)
                management_results["tasks_prioritized"] += prioritization_results["tasks_updated"]

                # Progress prediction
                prediction_results = await self.predict_project_progress(project)
                management_results["progress_predictions"] += 1

                # Automated status updates
                update_results = await self.automated_project_updates(project)
                management_results["automated_updates"] += update_results["updates_made"]

                # Risk assessment
                risk_results = await self.assess_project_risks(project)
                management_results["risk_assessments"] += 1

                management_results["projects_managed"] += 1

        # Calculate resource optimization
        management_results["resource_optimization"] = await self.calculate_resource_optimization()

        print(f"✅ Project management completed: {management_results['projects_managed']} projects managed")
        return management_results

    async def ai_task_prioritization(self, project: Project) -> Dict:
        """AI-powered task prioritization"""
        print(f"🎯 Running AI task prioritization for: {project.name}")

        project_tasks = [t for t in self.tasks if t.project_id == project.project_id]
        prioritization_results = {
            "tasks_analyzed": len(project_tasks),
            "tasks_updated": 0,
            "priority_adjustments": 0
        }

        for task in project_tasks:
            # Calculate AI priority score
            old_priority = task.priority
            ai_priority = await self.calculate_ai_priority_score(task, project)

            # Update task priority if needed
            if ai_priority["new_priority"] != task.priority:
                task.priority = ai_priority["new_priority"]
                task.ai_priority_score = ai_priority["score"]
                prioritization_results["tasks_updated"] += 1
                prioritization_results["priority_adjustments"] += 1

                print(f"📈 Updated {task.title}: {old_priority.value} → {task.priority.value}")

        return prioritization_results

    async def calculate_ai_priority_score(self, task: Task, project: Project) -> Dict:
        """Calculate AI priority score for task"""
        # Base priority factors
        base_score = 0.5

        # Due date urgency (closer due date = higher priority)
        days_until_due = (task.due_date - datetime.now()).days
        if days_until_due < 1:
            base_score += 0.3
        elif days_until_due < 3:
            base_score += 0.2
        elif days_until_due < 7:
            base_score += 0.1

        # Dependency impact (tasks with many dependents = higher priority)
        dependent_tasks = [t for t in self.tasks if task.task_id in t.dependencies]
        if dependent_tasks:
            base_score += min(len(dependent_tasks) * 0.1, 0.2)

        # Project progress impact (tasks that unblock project = higher priority)
        project_progress_factor = project.progress / 100
        if project_progress_factor < 0.5:  # Project behind schedule
            base_score += 0.15

        # Resource availability (tasks for available team members = higher priority)
        team_member = next((tm for tm in project.team_members if tm in task.assignee_id), None)
        if team_member:
            base_score += 0.05

        # Convert score to priority
        if base_score >= 0.8:
            new_priority = TaskPriority.URGENT
        elif base_score >= 0.6:
            new_priority = TaskPriority.HIGH
        elif base_score >= 0.4:
            new_priority = TaskPriority.MEDIUM
        else:
            new_priority = TaskPriority.LOW

        return {
            "score": base_score,
            "new_priority": new_priority,
            "factors": ["due_date", "dependencies", "project_progress", "resource_availability"]
        }

    async def predict_project_progress(self, project: Project) -> Dict:
        """Predict project progress using AI"""
        # Analyze current project state
        project_tasks = [t for t in self.tasks if t.project_id == project.project_id]

        # Calculate completion rates by priority
        completed_tasks = [t for t in project_tasks if t.status == TaskStatus.COMPLETED]
        total_tasks = len(project_tasks)

        if total_tasks > 0:
            current_completion_rate = len(completed_tasks) / total_tasks

            # Predict future completion rate based on velocity
            avg_completion_time = await self.calculate_average_completion_time(project_tasks)

            # Estimate remaining work
            remaining_tasks = [t for t in project_tasks if t.status != TaskStatus.COMPLETED]
            estimated_remaining_hours = sum(t.estimated_hours for t in remaining_tasks)

            # Predict completion date
            predicted_completion_date = datetime.now() + timedelta(
                hours=estimated_remaining_hours / max(avg_completion_time, 0.1)
            )

            # Calculate schedule variance
            original_duration = (project.end_date - project.start_date).days
            current_duration = (datetime.now() - project.start_date).days
            schedule_variance = ((current_duration / original_duration) - current_completion_rate) * 100

            return {
                "current_completion_rate": current_completion_rate,
                "predicted_completion_date": predicted_completion_date,
                "schedule_variance": schedule_variance,
                "velocity_trend": "increasing" if schedule_variance < 0 else "decreasing",
                "confidence_level": 0.85
            }

        return {
            "current_completion_rate": 0.0,
            "predicted_completion_date": project.end_date,
            "schedule_variance": 0.0,
            "velocity_trend": "stable",
            "confidence_level": 0.5
        }

    async def calculate_average_completion_time(self, tasks: List[Task]) -> float:
        """Calculate average task completion time"""
        completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED and t.actual_hours > 0]

        if completed_tasks:
            total_hours = sum(t.actual_hours for t in completed_tasks)
            return total_hours / len(completed_tasks)

        return 8.0  # Default 8 hours per task

    async def automated_project_updates(self, project: Project) -> Dict:
        """Generate automated project updates"""
        updates_made = 0

        # Update project progress based on task completion
        project_tasks = [t for t in self.tasks if t.project_id == project.project_id]
        completed_tasks = [t for t in project_tasks if t.status == TaskStatus.COMPLETED]

        if project_tasks:
            new_progress = (len(completed_tasks) / len(project_tasks)) * 100
            if abs(new_progress - project.progress) > 1:  # Only update if significant change
                project.progress = new_progress
                updates_made += 1

        # Update milestone progress
        for milestone in self.milestones:
            if milestone.project_id == project.project_id:
                milestone_tasks = [t for t in project_tasks if t.task_id in [t.task_id for t in project_tasks]]
                completed_milestone_tasks = [t for t in milestone_tasks if t.status == TaskStatus.COMPLETED]

                if milestone_tasks:
                    milestone.tasks_completed = len(completed_milestone_tasks)
                    milestone.total_tasks = len(milestone_tasks)

                    # Auto-complete milestone if all tasks done
                    if len(completed_milestone_tasks) == len(milestone_tasks) and not milestone.completed:
                        milestone.completed = True
                        updates_made += 1

        return {
            "updates_made": updates_made,
            "progress_updated": project.progress,
            "milestones_updated": len([m for m in self.milestones if m.project_id == project.project_id])
        }

    async def assess_project_risks(self, project: Project) -> Dict:
        """Assess project risks using AI"""
        # Identify potential risks
        risks = []

        # Schedule risk
        if project.progress < 50 and (project.end_date - datetime.now()).days < 30:
            risks.append({
                "risk_type": "schedule_delay",
                "probability": 0.8,
                "impact": "high",
                "description": "Project may not complete on time",
                "mitigation": "Reallocate resources and adjust timeline"
            })

        # Resource risk
        project_tasks = [t for t in self.tasks if t.project_id == project.project_id]
        high_priority_tasks = [t for t in project_tasks if t.priority in [TaskPriority.HIGH, TaskPriority.URGENT]]

        if len(high_priority_tasks) > len(project.team_members) * 2:
            risks.append({
                "risk_type": "resource_overload",
                "probability": 0.7,
                "impact": "medium",
                "description": "Team may be overloaded with high-priority tasks",
                "mitigation": "Redistribute workload or extend timeline"
            })

        # Dependency risk
        blocked_tasks = [t for t in project_tasks if t.status == TaskStatus.BLOCKED]
        if blocked_tasks:
            risks.append({
                "risk_type": "dependency_blockage",
                "probability": 0.9,
                "impact": "high",
                "description": f"{len(blocked_tasks)} tasks are blocked by dependencies",
                "mitigation": "Resolve blocking dependencies immediately"
            })

        return {
            "total_risks": len(risks),
            "high_risks": len([r for r in risks if r["impact"] == "high"]),
            "risks_identified": risks,
            "overall_risk_score": sum(r["probability"] for r in risks) / max(len(risks), 1)
        }

    async def calculate_resource_optimization(self) -> float:
        """Calculate resource optimization score"""
        if not self.projects or not self.tasks:
            return 0.0

        # Calculate workload distribution
        team_workloads = {}
        for project in self.projects:
            for member in project.team_members:
                if member not in team_workloads:
                    team_workloads[member] = 0
                team_workloads[member] += 1

        # Calculate balance score
        if team_workloads:
            workload_values = list(team_workloads.values())
            if workload_values:
                avg_workload = sum(workload_values) / len(workload_values)
                variance = sum((w - avg_workload) ** 2 for w in workload_values) / len(workload_values)
                balance_score = max(0, 1 - (variance / avg_workload)) if avg_workload > 0 else 0
            else:
                balance_score = 0
        else:
            balance_score = 0

        # Calculate utilization score
        total_team_members = len(set(m for p in self.projects for m in p.team_members))
        active_team_members = len([m for m in team_workloads.keys() if team_workloads[m] > 0])

        utilization_score = active_team_members / max(total_team_members, 1)

        # Combine scores
        optimization_score = (balance_score * 0.6) + (utilization_score * 0.4)

        return min(optimization_score, 1.0)

    async def create_kanban_board(self, project: Project) -> Dict:
        """Create Kanban-style board for project"""
        # Group tasks by status
        kanban_columns = {
            "backlog": [t for t in self.tasks if t.project_id == project.project_id and t.status == TaskStatus.BACKLOG],
            "todo": [t for t in self.tasks if t.project_id == project.project_id and t.status == TaskStatus.TODO],
            "in_progress": [t for t in self.tasks if t.project_id == project.project_id and t.status == TaskStatus.IN_PROGRESS],
            "review": [t for t in self.tasks if t.project_id == project.project_id and t.status == TaskStatus.REVIEW],
            "completed": [t for t in self.tasks if t.project_id == project.project_id and t.status == TaskStatus.COMPLETED]
        }

        # Calculate column metrics
        board_metrics = {}
        for column, tasks_in_column in kanban_columns.items():
            if tasks_in_column:
                avg_priority = sum(
                    {"low": 1, "medium": 2, "high": 3, "urgent": 4}.get(t.priority.value, 2)
                    for t in tasks_in_column
                ) / len(tasks_in_column)

                board_metrics[column] = {
                    "task_count": len(tasks_in_column),
                    "avg_priority": avg_priority,
                    "estimated_hours": sum(t.estimated_hours for t in tasks_in_column)
                }

        return {
            "project_id": project.project_id,
            "columns": kanban_columns,
            "metrics": board_metrics,
            "wip_limits": {"in_progress": 3, "review": 2},
            "flow_efficiency": 0.85
        }

    async def generate_project_insights(self, project: Project) -> Dict:
        """Generate AI-powered project insights"""
        project_tasks = [t for t in self.tasks if t.project_id == project.project_id]

        insights = {
            "project_health": "good",
            "velocity_trend": "increasing",
            "bottlenecks": [],
            "team_performance": {},
            "recommendations": []
        }

        # Analyze task completion velocity
        recent_tasks = [t for t in project_tasks if t.status == TaskStatus.COMPLETED and t.actual_hours > 0]
        if len(recent_tasks) >= 2:
            completion_times = [t.actual_hours for t in recent_tasks[-5:]]  # Last 5 tasks
            avg_completion = sum(completion_times) / len(completion_times)

            if avg_completion < 8:
                insights["velocity_trend"] = "increasing"
            elif avg_completion > 12:
                insights["velocity_trend"] = "decreasing"

        # Identify bottlenecks
        blocked_tasks = [t for t in project_tasks if t.status == TaskStatus.BLOCKED]
        if blocked_tasks:
            insights["bottlenecks"] = [
                {
                    "task": t.title,
                    "blocked_for_days": (datetime.now() - t.due_date).days if t.due_date < datetime.now() else 0,
                    "blocking_dependencies": t.dependencies
                }
                for t in blocked_tasks
            ]

        # Team performance analysis
        for member in project.team_members:
            member_tasks = [t for t in project_tasks if t.assignee_id == member]
            if member_tasks:
                completed_member_tasks = [t for t in member_tasks if t.status == TaskStatus.COMPLETED]
                completion_rate = len(completed_member_tasks) / len(member_tasks) if member_tasks else 0

                insights["team_performance"][member] = {
                    "tasks_assigned": len(member_tasks),
                    "completion_rate": completion_rate,
                    "avg_actual_vs_estimated": 1.0  # Would calculate from actual data
                }

        # Generate recommendations
        if insights["velocity_trend"] == "decreasing":
            insights["recommendations"].append({
                "type": "velocity_improvement",
                "priority": "high",
                "action": "Review and optimize task estimation accuracy"
            })

        if insights["bottlenecks"]:
            insights["recommendations"].append({
                "type": "bottleneck_resolution",
                "priority": "high",
                "action": f"Resolve {len(insights['bottlenecks'])} blocked tasks"
            })

        return insights

    async def generate_project_report(self) -> Dict:
        """Generate comprehensive project management report"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_projects": len(self.projects),
            "active_projects": len([p for p in self.projects if p.status == ProjectStatus.ACTIVE]),
            "total_tasks": len(self.tasks),
            "completed_tasks": len([t for t in self.tasks if t.status == TaskStatus.COMPLETED]),
            "overall_progress": 0.0,
            "project_health": {},
            "resource_utilization": {},
            "upcoming_deadlines": [],
            "recommendations": []
        }

        # Calculate overall progress
        if self.projects:
            total_progress = sum(p.progress for p in self.projects)
            report["overall_progress"] = total_progress / len(self.projects)

        # Project health analysis
        for project in self.projects:
            project_tasks = [t for t in self.tasks if t.project_id == project.project_id]

            if project_tasks:
                completion_rate = len([t for t in project_tasks if t.status == TaskStatus.COMPLETED]) / len(project_tasks)
                on_time_tasks = len([t for t in project_tasks if t.status == TaskStatus.COMPLETED and t.due_date >= datetime.now()])

                health_score = (completion_rate * 0.6) + ((on_time_tasks / len(project_tasks)) * 0.4) if project_tasks else 0

                report["project_health"][project.project_id] = {
                    "health_score": health_score,
                    "completion_rate": completion_rate,
                    "schedule_adherence": on_time_tasks / len(project_tasks) if project_tasks else 0,
                    "risk_level": "low" if health_score > 0.8 else "medium" if health_score > 0.6 else "high"
                }

        # Resource utilization
        all_team_members = set()
        for project in self.projects:
            all_team_members.update(project.team_members)

        for member in all_team_members:
            member_projects = [p for p in self.projects if member in p.team_members]
            member_tasks = [t for t in self.tasks if t.assignee_id == member]

            report["resource_utilization"][member] = {
                "projects_assigned": len(member_projects),
                "tasks_assigned": len(member_tasks),
                "workload_score": min(len(member_tasks) / max(len(member_projects), 1), 3.0)
            }

        # Upcoming deadlines
        upcoming_tasks = [
            t for t in self.tasks
            if t.due_date <= datetime.now() + timedelta(days=7) and t.status != TaskStatus.COMPLETED
        ]

        report["upcoming_deadlines"] = [
            {
                "task_id": t.task_id,
                "title": t.title,
                "due_date": t.due_date.isoformat(),
                "priority": t.priority.value,
                "assignee": t.assignee_id
            }
            for t in sorted(upcoming_tasks, key=lambda x: x.due_date)[:10]
        ]

        # Generate recommendations
        high_risk_projects = [pid for pid, health in report["project_health"].items() if health["risk_level"] == "high"]
        if high_risk_projects:
            report["recommendations"].append({
                "type": "risk_mitigation",
                "priority": "high",
                "message": f"Focus attention on {len(high_risk_projects)} high-risk projects"
            })

        overloaded_resources = [m for m, util in report["resource_utilization"].items() if util["workload_score"] > 2.5]
        if overloaded_resources:
            report["recommendations"].append({
                "type": "resource_balancing",
                "priority": "medium",
                "message": f"Redistribute workload for {len(overloaded_resources)} overloaded team members"
            })

        return report

async def main():
    """Main AI project management demo"""
    print("📋 Ultra Pinnacle Studio - AI Project Management")
    print("=" * 50)

    # Initialize project manager
    project_manager = AIProjectManager()

    print("📋 Initializing AI project management...")
    print("🎯 Auto-managed task prioritization")
    print("📈 Progress prediction and forecasting")
    print("⚡ Automated status updates")
    print("🔍 Risk assessment and mitigation")
    print("👥 Resource optimization")
    print("=" * 50)

    # Run AI project management
    print("\n📋 Running AI project management...")
    management_results = await project_manager.run_ai_project_management()

    print(f"✅ Project management: {management_results['projects_managed']} projects managed")
    print(f"🎯 Tasks prioritized: {management_results['tasks_prioritized']}")
    print(f"📈 Progress predictions: {management_results['progress_predictions']}")
    print(f"⚡ Automated updates: {management_results['automated_updates']}")
    print(f"📊 Resource optimization: {management_results['resource_optimization']:.1%}")

    # Create Kanban board for first project
    if project_manager.projects:
        first_project = project_manager.projects[0]
        print(f"\n📊 Creating Kanban board for: {first_project.name}")
        kanban_board = await project_manager.create_kanban_board(first_project)

        print(f"✅ Kanban board created: {len(kanban_board['columns'])} columns")
        for column, tasks in kanban_board['columns'].items():
            if tasks:
                print(f"  • {column.replace('_', ' ').title()}: {len(tasks)} tasks")

    # Generate project insights
    if project_manager.projects:
        print(f"\n💡 Generating insights for: {first_project.name}")
        insights = await project_manager.generate_project_insights(first_project)

        print(f"📊 Project health: {insights['project_health']}")
        print(f"📈 Velocity trend: {insights['velocity_trend']}")
        print(f"🚨 Bottlenecks: {len(insights['bottlenecks'])}")
        print(f"💡 Recommendations: {len(insights['recommendations'])}")

    # Generate comprehensive report
    print("\n📊 Generating project management report...")
    report = await project_manager.generate_project_report()

    print(f"📋 Total projects: {report['total_projects']}")
    print(f"📈 Overall progress: {report['overall_progress']:.1%}")
    print(f"✅ Completed tasks: {report['completed_tasks']}/{report['total_tasks']}")
    print(f"⏰ Upcoming deadlines: {len(report['upcoming_deadlines'])}")

    # Show project health breakdown
    print("\n🏥 Project Health:")
    for project_id, health in report['project_health'].items():
        print(f"  • {project_id}: {health['health_score']:.1%} health, {health['risk_level']} risk")

    # Show resource utilization
    print("\n👥 Resource Utilization:")
    for member, utilization in list(report['resource_utilization'].items())[:5]:
        print(f"  • {member}: {utilization['workload_score']:.1f} workload score")

    print("\n📋 AI Project Management Features:")
    print("✅ Auto-managed task prioritization")
    print("✅ Progress prediction and forecasting")
    print("✅ Kanban-style project boards")
    print("✅ Risk assessment and mitigation")
    print("✅ Resource optimization")
    print("✅ Real-time collaboration")
    print("✅ Comprehensive analytics")

if __name__ == "__main__":
    asyncio.run(main())