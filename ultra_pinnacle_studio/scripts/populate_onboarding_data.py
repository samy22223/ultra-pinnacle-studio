#!/usr/bin/env python3
"""
Script to populate the database with sample onboarding data for testing
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_gateway.database import (
    SessionLocal, OnboardingFlow, OnboardingStep, Tutorial,
    HelpCategory, HelpArticle, Tooltip, UserType
)

def populate_sample_data():
    """Populate database with sample onboarding data"""
    db = SessionLocal()
    try:
        # Get user types
        free_tier = db.query(UserType).filter(UserType.name == "free").first()
        premium_tier = db.query(UserType).filter(UserType.name == "premium").first()
        enterprise_tier = db.query(UserType).filter(UserType.name == "enterprise").first()

        # Create onboarding flows
        print("Creating onboarding flows...")

        # Regular user flow
        regular_flow = OnboardingFlow(
            name="regular_user",
            display_name="Welcome to Ultra Pinnacle Studio",
            description="Get started with the essential features",
            user_type_id=free_tier.id if free_tier else None,
            is_default=True
        )
        db.add(regular_flow)
        db.commit()

        # Premium user flow
        premium_flow = OnboardingFlow(
            name="premium_user",
            display_name="Premium User Onboarding",
            description="Unlock advanced features and capabilities",
            user_type_id=premium_tier.id if premium_tier else None,
            is_default=True
        )
        db.add(premium_flow)
        db.commit()

        # Admin flow
        admin_flow = OnboardingFlow(
            name="admin_user",
            display_name="Administrator Setup",
            description="Configure your administrative features",
            is_default=False
        )
        db.add(admin_flow)
        db.commit()

        # Create onboarding steps for regular user flow
        print("Creating onboarding steps...")

        steps_data = [
            {
                "flow_id": regular_flow.id,
                "step_order": 1,
                "title": "Welcome to Ultra Pinnacle Studio",
                "description": "Let's get you started with the basics",
                "content_type": "modal",
                "content": {
                    "text": "<p>Welcome to Ultra Pinnacle AI Studio! This platform provides powerful AI tools for content creation, code development, and creative projects.</p><p>We'll guide you through the key features to help you get started quickly.</p>",
                    "image": "/static/images/welcome-illustration.png"
                },
                "is_required": True,
                "auto_advance": False,
                "estimated_duration": 30
            },
            {
                "flow_id": regular_flow.id,
                "step_order": 2,
                "title": "AI Chat Interface",
                "description": "Learn how to use the AI chat for conversations",
                "content_type": "highlight",
                "target_element": ".chat-interface",
                "content": {
                    "text": "The AI chat interface is your main way to interact with AI models. You can ask questions, get help with coding, generate content, and much more."
                },
                "is_required": True,
                "auto_advance": False,
                "estimated_duration": 45
            },
            {
                "flow_id": regular_flow.id,
                "step_order": 3,
                "title": "Code Editor",
                "description": "Explore the collaborative code editing features",
                "content_type": "interactive",
                "target_element": ".code-editor",
                "content": {
                    "instructions": [
                        "Open the code editor from the sidebar",
                        "Try typing some code or paste an existing snippet",
                        "Use the AI assistance features to get help",
                        "Save your work to continue later"
                    ]
                },
                "is_required": False,
                "auto_advance": False,
                "estimated_duration": 60
            },
            {
                "flow_id": regular_flow.id,
                "step_order": 4,
                "title": "Help & Support",
                "description": "Know where to find help when you need it",
                "content_type": "modal",
                "content": {
                    "text": "<p>You can always access help through:</p><ul><li>The help center (searchable documentation)</li><li>Interactive tutorials and walkthroughs</li><li>In-app support chat for immediate assistance</li><li>Contextual tooltips that appear as you explore</li></ul>",
                    "video": "/static/videos/help-overview.mp4"
                },
                "is_required": False,
                "auto_advance": True,
                "estimated_duration": 30
            }
        ]

        for step_data in steps_data:
            step = OnboardingStep(**step_data)
            db.add(step)

        db.commit()

        # Create sample tutorials
        print("Creating tutorials...")

        tutorials_data = [
            {
                "title": "Getting Started with AI Chat",
                "description": "Learn the basics of interacting with AI models through our chat interface",
                "category": "getting_started",
                "difficulty_level": "beginner",
                "content_type": "video",
                "video_url": "/static/videos/ai-chat-basics.mp4",
                "thumbnail_url": "/static/images/tutorial-chat-thumb.png",
                "content": {
                    "chapters": [
                        {"title": "Introduction", "start_time": 0, "duration": 30},
                        {"title": "Starting a Conversation", "start_time": 30, "duration": 45},
                        {"title": "Using Different Models", "start_time": 75, "duration": 60},
                        {"title": "Best Practices", "start_time": 135, "duration": 45}
                    ]
                },
                "estimated_duration": 180,
                "tags": ["chat", "ai", "basics", "conversation"],
                "is_active": True
            },
            {
                "title": "Collaborative Code Editing",
                "description": "Master the collaborative code editing features for team development",
                "category": "collaborative_editing",
                "difficulty_level": "intermediate",
                "content_type": "interactive",
                "content": {
                    "steps": [
                        {
                            "title": "Creating a Code Document",
                            "content": "Learn how to create and share code documents with your team",
                            "action": {"type": "create_document", "document_type": "code"}
                        },
                        {
                            "title": "Real-time Collaboration",
                            "content": "See how multiple users can edit the same document simultaneously",
                            "action": {"type": "invite_collaborator"}
                        },
                        {
                            "title": "Version Control",
                            "content": "Understand how changes are tracked and managed",
                            "action": {"type": "show_history"}
                        }
                    ]
                },
                "estimated_duration": 300,
                "tags": ["code", "collaboration", "editing", "team"],
                "is_active": True
            },
            {
                "title": "Admin Panel Overview",
                "description": "Complete guide to managing users, settings, and system configuration",
                "category": "admin_features",
                "difficulty_level": "advanced",
                "content_type": "text",
                "content": """
                <h2>Administrator Features</h2>
                <p>As an administrator, you have access to powerful tools for managing the platform.</p>

                <h3>User Management</h3>
                <p>Manage user accounts, permissions, and access levels through the admin panel.</p>

                <h3>System Settings</h3>
                <p>Configure system-wide settings, rate limits, and feature toggles.</p>

                <h3>Analytics & Monitoring</h3>
                <p>Monitor system performance, user activity, and platform metrics.</p>
                """,
                "estimated_duration": 600,
                "tags": ["admin", "management", "settings", "monitoring"],
                "is_active": True
            }
        ]

        for tutorial_data in tutorials_data:
            tutorial = Tutorial(**tutorial_data)
            db.add(tutorial)

        db.commit()

        # Create help categories
        print("Creating help categories...")

        categories_data = [
            {
                "name": "getting_started",
                "display_name": "Getting Started",
                "description": "Basic setup and initial configuration",
                "icon": "🚀",
                "sort_order": 1,
                "is_active": True
            },
            {
                "name": "ai_features",
                "display_name": "AI Features",
                "description": "Using AI models, chat, and generation tools",
                "icon": "🤖",
                "sort_order": 2,
                "is_active": True
            },
            {
                "name": "collaboration",
                "display_name": "Collaboration",
                "description": "Working with teams and shared documents",
                "icon": "👥",
                "sort_order": 3,
                "is_active": True
            },
            {
                "name": "troubleshooting",
                "display_name": "Troubleshooting",
                "description": "Common issues and how to resolve them",
                "icon": "🔧",
                "sort_order": 4,
                "is_active": True
            }
        ]

        for category_data in categories_data:
            category = HelpCategory(**category_data)
            db.add(category)

        db.commit()

        # Create help articles
        print("Creating help articles...")

        getting_started_cat = db.query(HelpCategory).filter(HelpCategory.name == "getting_started").first()
        ai_features_cat = db.query(HelpCategory).filter(HelpCategory.name == "ai_features").first()
        collaboration_cat = db.query(HelpCategory).filter(HelpCategory.name == "collaboration").first()
        troubleshooting_cat = db.query(HelpCategory).filter(HelpCategory.name == "troubleshooting").first()

        articles_data = [
            {
                "title": "Creating Your First AI Conversation",
                "slug": "creating-first-ai-conversation",
                "content": """
                <h2>Starting Your First AI Conversation</h2>
                <p>Welcome to Ultra Pinnacle AI Studio! Let's create your first AI conversation.</p>

                <h3>Step 1: Access the Chat Interface</h3>
                <p>Click on the "Chat" button in the main navigation or sidebar to open the chat interface.</p>

                <h3>Step 2: Choose an AI Model</h3>
                <p>Select from available AI models like GPT-4, Claude, or local models. Each model has different strengths.</p>

                <h3>Step 3: Start Chatting</h3>
                <p>Type your message in the input field and press Enter. The AI will respond based on the context of your conversation.</p>

                <h3>Tips for Better Conversations</h3>
                <ul>
                <li>Be specific in your questions</li>
                <li>Provide context when asking for help</li>
                <li>Use follow-up questions to refine responses</li>
                <li>Experiment with different AI models for varied perspectives</li>
                </ul>
                """,
                "summary": "Learn how to start your first conversation with AI models in the platform",
                "category_id": getting_started_cat.id,
                "tags": ["chat", "ai", "conversation", "beginner"],
                "difficulty_level": "beginner",
                "is_featured": True,
                "is_active": True
            },
            {
                "title": "Understanding AI Model Capabilities",
                "slug": "understanding-ai-models",
                "content": """
                <h2>AI Model Capabilities</h2>
                <p>Different AI models offer various strengths and use cases. Here's what you need to know.</p>

                <h3>GPT-4</h3>
                <p>Excellent for general conversation, creative writing, and complex reasoning tasks.</p>

                <h3>Claude</h3>
                <p>Strong in analysis, research, and maintaining consistent persona in long conversations.</p>

                <h3>Local Models (Llama)</h3>
                <p>Privacy-focused models that run locally. Good for sensitive data and offline use.</p>

                <h3>Specialized Models</h3>
                <p>Models fine-tuned for specific tasks like code generation, image creation, or music composition.</p>
                """,
                "summary": "Overview of different AI models available and their strengths",
                "category_id": ai_features_cat.id,
                "tags": ["ai", "models", "capabilities"],
                "difficulty_level": "beginner",
                "is_featured": True,
                "is_active": True
            },
            {
                "title": "Collaborative Document Editing",
                "slug": "collaborative-editing",
                "content": """
                <h2>Working Together on Documents</h2>
                <p>Learn how to collaborate effectively on documents with your team.</p>

                <h3>Creating Shared Documents</h3>
                <p>Use the collaborative editor to create documents that multiple users can edit simultaneously.</p>

                <h3>Real-time Collaboration</h3>
                <p>See changes from other users in real-time with color-coded cursors and selection highlights.</p>

                <h3>Version History</h3>
                <p>Access version history to see previous states of the document and revert changes if needed.</p>
                """,
                "summary": "Guide to collaborative document editing features",
                "category_id": collaboration_cat.id,
                "tags": ["collaboration", "editing", "documents", "team"],
                "difficulty_level": "intermediate",
                "is_featured": False,
                "is_active": True
            }
        ]

        for article_data in articles_data:
            article = HelpArticle(**article_data)
            db.add(article)

        db.commit()

        # Create sample tooltips
        print("Creating tooltips...")

        tooltips_data = [
            {
                "identifier": "chat_input_help",
                "title": "AI Chat Input",
                "content": "Type your message here to chat with AI. Press Enter to send, Shift+Enter for new line.",
                "target_element": ".chat-input",
                "trigger_event": "focus",
                "position": "top",
                "show_once": False,
                "priority": 10,
                "is_active": True
            },
            {
                "identifier": "model_selector_help",
                "title": "AI Model Selection",
                "content": "Choose different AI models for varied capabilities. Each model excels at different types of tasks.",
                "target_element": ".model-selector",
                "trigger_event": "hover",
                "position": "bottom",
                "show_once": True,
                "priority": 8,
                "is_active": True
            },
            {
                "identifier": "help_button",
                "title": "Get Help",
                "content": "Access tutorials, documentation, and support chat anytime you need assistance.",
                "target_element": ".help-button",
                "trigger_event": "hover",
                "position": "left",
                "show_once": False,
                "priority": 5,
                "is_active": True
            }
        ]

        for tooltip_data in tooltips_data:
            tooltip = Tooltip(**tooltip_data)
            db.add(tooltip)

        db.commit()

        print("Sample onboarding data populated successfully!")
        print(f"Created {len(steps_data)} onboarding steps")
        print(f"Created {len(tutorials_data)} tutorials")
        print(f"Created {len(categories_data)} help categories")
        print(f"Created {len(articles_data)} help articles")
        print(f"Created {len(tooltips_data)} tooltips")

    except Exception as e:
        print(f"Error populating sample data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    populate_sample_data()