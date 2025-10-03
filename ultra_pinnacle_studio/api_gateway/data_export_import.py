"""
Data Export/Import functionality for Ultra Pinnacle AI Studio
Handles GDPR-compliant data export, multiple formats, and secure data handling
"""
import os
import json
import csv
import uuid
import hashlib
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import zipfile
import tempfile
from io import BytesIO, StringIO

# PDF generation
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# HTML generation
try:
    import jinja2
    JINJA_AVAILABLE = True
except ImportError:
    JINJA_AVAILABLE = False

from .database import (
    get_db, User, Conversation, Message, FileUpload, AuditLog,
    ExportOperation, ImportOperation, ExportSchedule, DataValidationRule
)
from .logging_config import logger
from .config import config

class DataExportService:
    """Service for handling data export operations"""

    def __init__(self):
        self.exports_dir = Path(config["paths"]["exports_dir"])
        self.exports_dir.mkdir(exist_ok=True)
        self.temp_dir = Path(config["paths"]["temp_dir"])
        self.temp_dir.mkdir(exist_ok=True)

    async def create_export_operation(
        self,
        user_id: int,
        export_type: str,
        format: str,
        data_scope: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
        encryption_password: Optional[str] = None,
        requested_by_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """Create a new export operation"""
        db = next(get_db())

        try:
            operation_id = str(uuid.uuid4())

            operation = ExportOperation(
                id=operation_id,
                user_id=user_id,
                export_type=export_type,
                format=format,
                data_scope=data_scope,
                filters=filters or {},
                requested_by_ip=requested_by_ip,
                user_agent=user_agent
            )

            if encryption_password:
                operation.encryption_key = self._hash_password(encryption_password)

            db.add(operation)
            db.commit()

            # Start the export asynchronously
            asyncio.create_task(self._process_export(operation_id))

            logger.info(f"Created export operation {operation_id} for user {user_id}")
            return operation_id

        finally:
            db.close()

    async def _process_export(self, operation_id: str):
        """Process an export operation asynchronously"""
        db = next(get_db())

        try:
            operation = db.query(ExportOperation).filter(ExportOperation.id == operation_id).first()
            if not operation:
                logger.error(f"Export operation {operation_id} not found")
                return

            operation.status = "running"
            operation.started_at = datetime.now(timezone.utc)
            db.commit()

            # Process based on export type
            if operation.export_type == "user_data":
                await self._export_user_data(operation, db)
            elif operation.export_type == "conversations":
                await self._export_conversations(operation, db)
            elif operation.export_type == "bulk_admin":
                await self._export_bulk_admin(operation, db)
            else:
                raise ValueError(f"Unsupported export type: {operation.export_type}")

            operation.status = "completed"
            operation.completed_at = datetime.now(timezone.utc)
            operation.progress = 100.0
            db.commit()

            # Generate download URL
            operation.download_url = f"/api/exports/download/{operation_id}"
            operation.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
            db.commit()

            logger.info(f"Export operation {operation_id} completed successfully")

        except Exception as e:
            logger.error(f"Error processing export {operation_id}: {e}")
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()

    async def _export_user_data(self, operation: ExportOperation, db):
        """Export user data with GDPR compliance"""
        user_id = operation.user_id

        # Collect user data
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("User not found")

        data = {
            "user_profile": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat()
            },
            "conversations": [],
            "messages": [],
            "file_uploads": [],
            "audit_logs": [],
            "export_metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "gdpr_compliant": True,
                "data_retention": "User data exported for portability",
                "export_format": operation.format
            }
        }

        # Get user's conversations
        conversations = db.query(Conversation).filter(
            Conversation.created_by == user_id
        ).all()

        conversation_ids = [conv.id for conv in conversations]

        # Get messages from user's conversations
        messages = db.query(Message).filter(
            Message.conversation_id.in_(conversation_ids)
        ).all()

        # Get user's file uploads
        file_uploads = db.query(FileUpload).filter(
            FileUpload.user_id == user_id
        ).all()

        # Get user's audit logs (GDPR relevant)
        audit_logs = db.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(AuditLog.created_at.desc()).limit(1000).all()

        # Populate data
        data["conversations"] = [{
            "id": conv.id,
            "title": conv.title,
            "model": conv.model,
            "is_public": conv.is_public,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat()
        } for conv in conversations]

        data["messages"] = [{
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "role": msg.role,
            "content": msg.content,
            "model": msg.model,
            "tokens_used": msg.tokens_used,
            "created_at": msg.created_at.isoformat()
        } for msg in messages]

        data["file_uploads"] = [{
            "id": upload.id,
            "filename": upload.filename,
            "original_filename": upload.original_filename,
            "file_size": upload.file_size,
            "content_type": upload.content_type,
            "uploaded_at": upload.uploaded_at.isoformat()
        } for upload in file_uploads]

        data["audit_logs"] = [{
            "id": log.id,
            "action": log.action,
            "resource": log.resource,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat()
        } for log in audit_logs]

        # Generate file based on format
        await self._generate_export_file(operation, data, db)

    async def _export_conversations(self, operation: ExportOperation, db):
        """Export conversations data"""
        data_scope = operation.data_scope
        conversation_ids = data_scope.get("conversation_ids", [])

        if not conversation_ids:
            raise ValueError("No conversation IDs specified")

        conversations = db.query(Conversation).filter(
            Conversation.id.in_(conversation_ids)
        ).all()

        messages = db.query(Message).filter(
            Message.conversation_id.in_(conversation_ids)
        ).order_by(Message.conversation_id, Message.created_at).all()

        data = {
            "conversations": [],
            "messages": [],
            "export_metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "conversation_count": len(conversations),
                "message_count": len(messages),
                "export_format": operation.format
            }
        }

        data["conversations"] = [{
            "id": conv.id,
            "title": conv.title,
            "model": conv.model,
            "is_public": conv.is_public,
            "created_by": conv.created_by,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat()
        } for conv in conversations]

        data["messages"] = [{
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "user_id": msg.user_id,
            "role": msg.role,
            "content": msg.content,
            "model": msg.model,
            "tokens_used": msg.tokens_used,
            "created_at": msg.created_at.isoformat()
        } for msg in messages]

        await self._generate_export_file(operation, data, db)

    async def _export_bulk_admin(self, operation: ExportOperation, db):
        """Export bulk data for administrators"""
        # Only allow superusers
        user = db.query(User).filter(User.id == operation.user_id).first()
        if not user or not user.is_superuser:
            raise ValueError("Admin access required for bulk export")

        data_scope = operation.data_scope
        export_type = data_scope.get("bulk_type", "all_users")

        if export_type == "all_users":
            await self._export_all_users(operation, db)
        elif export_type == "all_conversations":
            await self._export_all_conversations(operation, db)
        elif export_type == "system_audit":
            await self._export_system_audit(operation, db)
        else:
            raise ValueError(f"Unsupported bulk export type: {export_type}")

    async def _export_all_users(self, operation: ExportOperation, db):
        """Export all user data"""
        users = db.query(User).all()

        data = {
            "users": [],
            "export_metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "user_count": len(users),
                "export_type": "bulk_users",
                "gdpr_compliant": True
            }
        }

        for user in users:
            user_data = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
                "conversation_count": len(user.conversations_created),
                "file_upload_count": len(user.file_uploads)
            }
            data["users"].append(user_data)

        await self._generate_export_file(operation, data, db)

    async def _export_all_conversations(self, operation: ExportOperation, db):
        """Export all conversations"""
        conversations = db.query(Conversation).all()
        messages = db.query(Message).order_by(Message.conversation_id, Message.created_at).all()

        data = {
            "conversations": [],
            "messages": [],
            "export_metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "conversation_count": len(conversations),
                "message_count": len(messages),
                "export_type": "bulk_conversations"
            }
        }

        data["conversations"] = [{
            "id": conv.id,
            "title": conv.title,
            "model": conv.model,
            "is_public": conv.is_public,
            "created_by": conv.created_by,
            "created_at": conv.created_at.isoformat(),
            "updated_at": conv.updated_at.isoformat()
        } for conv in conversations]

        data["messages"] = [{
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "user_id": msg.user_id,
            "role": msg.role,
            "content": msg.content,
            "model": msg.model,
            "tokens_used": msg.tokens_used,
            "created_at": msg.created_at.isoformat()
        } for msg in messages]

        await self._generate_export_file(operation, data, db)

    async def _export_system_audit(self, operation: ExportOperation, db):
        """Export system audit logs"""
        audit_logs = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(50000).all()

        data = {
            "audit_logs": [],
            "export_metadata": {
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "audit_log_count": len(audit_logs),
                "export_type": "system_audit"
            }
        }

        data["audit_logs"] = [{
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "resource": log.resource,
            "resource_id": log.resource_id,
            "details": log.details,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at.isoformat()
        } for log in audit_logs]

        await self._generate_export_file(operation, data, db)

    def _calculate_checksum(self, filepath: str) -> str:
        """Calculate SHA256 checksum of file"""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _hash_password(self, password: str) -> str:
        """Hash password for encryption key storage"""
        return hashlib.sha256(password.encode()).hexdigest()

    def _convert_to_csv(self, data: List[Dict[str, Any]]) -> str:
        """Convert list of dictionaries to CSV string"""
        if not data:
            return ""

        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    async def _generate_export_file(self, operation: ExportOperation, data: Dict[str, Any], db):
        """Generate the export file in the requested format"""
        format_type = operation.format.lower()

        if format_type == "json":
            await self._generate_json_export(operation, data)
        elif format_type == "csv":
            await self._generate_csv_export(operation, data)
        elif format_type == "pdf":
            await self._generate_pdf_export(operation, data)
        elif format_type == "html":
            await self._generate_html_export(operation, data)
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

        # Calculate file size and checksum
        if operation.file_path and os.path.exists(operation.file_path):
            operation.file_size = os.path.getsize(operation.file_path)
            operation.checksum = self._calculate_checksum(operation.file_path)

        db.commit()

    async def _generate_json_export(self, operation: ExportOperation, data: Dict[str, Any]):
        """Generate JSON export file"""
        filename = f"export_{operation.id}.json"
        filepath = self.exports_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        operation.file_path = str(filepath)

    async def _generate_csv_export(self, operation: ExportOperation, data: Dict[str, Any]):
        """Generate CSV export file"""
        filename = f"export_{operation.id}.zip"
        filepath = self.exports_dir / filename

        with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Generate CSV files for each data type
            for data_type, items in data.items():
                if isinstance(items, list) and items:
                    csv_content = self._convert_to_csv(items)
                    zip_file.writestr(f"{data_type}.csv", csv_content)

            # Add metadata
            metadata = {
                "export_id": operation.id,
                "export_type": operation.export_type,
                "format": operation.format,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "data_types": list(data.keys())
            }
            zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))

        operation.file_path = str(filepath)

    async def _generate_pdf_export(self, operation: ExportOperation, data: Dict[str, Any]):
        """Generate PDF export file"""
        if not PDF_AVAILABLE:
            raise ValueError("PDF generation not available. Install reportlab.")

        filename = f"export_{operation.id}.pdf"
        filepath = self.exports_dir / filename

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=30,
        )
        story.append(Paragraph(f"Data Export - {operation.export_type.title()}", title_style))
        story.append(Spacer(1, 12))

        # Metadata
        story.append(Paragraph("Export Information:", styles['Heading2']))
        metadata = [
            ["Export ID", operation.id],
            ["Export Type", operation.export_type],
            ["Format", operation.format],
            ["Exported At", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")],
        ]
        metadata_table = Table(metadata, colWidths=[100, 300])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 20))

        # Data summary
        story.append(Paragraph("Data Summary:", styles['Heading2']))
        summary_data = []
        for key, value in data.items():
            if isinstance(value, list):
                summary_data.append([key.title(), f"{len(value)} items"])
            elif isinstance(value, dict):
                summary_data.append([key.title(), f"{len(value)} fields"])

        if summary_data:
            summary_table = Table(summary_data, colWidths=[150, 250])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            story.append(summary_table)

        doc.build(story)
        buffer.seek(0)

        with open(filepath, 'wb') as f:
            f.write(buffer.getvalue())

        operation.file_path = str(filepath)

    async def _generate_html_export(self, operation: ExportOperation, data: Dict[str, Any]):
        """Generate HTML export file"""
        if not JINJA_AVAILABLE:
            raise ValueError("HTML generation not available. Install jinja2.")

        filename = f"export_{operation.id}.html"
        filepath = self.exports_dir / filename

        # Simple HTML template
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Data Export - {{ export_type.title() }}</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
                .section { margin: 20px 0; }
                .data-table { border-collapse: collapse; width: 100%; }
                .data-table th, .data-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                .data-table th { background-color: #f2f2f2; }
                .metadata { background: #e8f4f8; padding: 15px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Data Export - {{ export_type.title() }}</h1>
                <p><strong>Export ID:</strong> {{ operation_id }}</p>
                <p><strong>Exported At:</strong> {{ exported_at }}</p>
                <p><strong>Format:</strong> {{ format }}</p>
            </div>

            {% for section_name, section_data in data.items() %}
                {% if section_data is iterable and section_data is not string %}
                    <div class="section">
                        <h2>{{ section_name.title() }}</h2>
                        {% if section_data %}
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        {% for key in section_data[0].keys() %}
                                            <th>{{ key.title() }}</th>
                                        {% endfor %}
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for item in section_data %}
                                        <tr>
                                            {% for value in item.values() %}
                                                <td>{{ value }}</td>
                                            {% endfor %}
                                        </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        {% else %}
                            <p>No data available</p>
                        {% endif %}
                    </div>
                {% endif %}
            {% endfor %}

            <div class="metadata">
                <h3>Export Metadata</h3>
                <p>This export was generated for data portability purposes.</p>
                <p>GDPR Compliant: Yes</p>
            </div>
        </body>
        </html>
        """

        template = jinja2.Template(html_template)
        html_content = template.render(
            export_type=operation.export_type,
            operation_id=operation.id,
            exported_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            format=operation.format,
            data=data
        )

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        operation.file_path = str(filepath)

    async def create_import_operation(
        self,
        user_id: int,
        import_type: str,
        import_data: bytes,
        validation_rules: Optional[Dict[str, Any]] = None,
        requested_by_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """Create a new import operation"""
        db = next(get_db())

        try:
            operation_id = str(uuid.uuid4())

            operation = ImportOperation(
                id=operation_id,
                user_id=user_id,
                import_type=import_type,
                import_data=import_data,
                validation_rules=validation_rules or {},
                requested_by_ip=requested_by_ip,
                user_agent=user_agent
            )

            db.add(operation)
            db.commit()

            # Start the import asynchronously
            asyncio.create_task(self._process_import(operation_id))

            logger.info(f"Created import operation {operation_id} for user {user_id}")
            return operation_id

        finally:
            db.close()

    async def _process_import(self, operation_id: str):
        """Process an import operation asynchronously"""
        db = next(get_db())

        try:
            operation = db.query(ImportOperation).filter(ImportOperation.id == operation_id).first()
            if not operation:
                logger.error(f"Import operation {operation_id} not found")
                return

            operation.status = "running"
            operation.started_at = datetime.now(timezone.utc)
            db.commit()

            # Process based on import type
            if operation.import_type == "user_data":
                await self._import_user_data(operation, db)
            elif operation.import_type == "conversations":
                await self._import_conversations(operation, db)
            elif operation.import_type == "bulk_admin":
                await self._import_bulk_admin(operation, db)
            else:
                raise ValueError(f"Unsupported import type: {operation.import_type}")

            operation.status = "completed"
            operation.completed_at = datetime.now(timezone.utc)
            db.commit()

            logger.info(f"Import operation {operation_id} completed successfully")

        except Exception as e:
            logger.error(f"Error processing import {operation_id}: {e}")
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.now(timezone.utc)
            db.commit()
        finally:
            db.close()

    async def _import_user_data(self, operation: ImportOperation, db):
        """Import user data with validation"""
        try:
            import_data = json.loads(operation.import_data.decode('utf-8'))
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format in import data")

        # Validate data structure
        if "user_profile" not in import_data:
            raise ValueError("Missing user_profile in import data")

        user_profile = import_data["user_profile"]
        user_id = operation.user_id

        # Validate user ownership
        existing_user = db.query(User).filter(User.id == user_id).first()
        if not existing_user:
            raise ValueError("User not found")

        records_processed = 0
        records_failed = 0
        validation_errors = []

        # Import conversations if present
        if "conversations" in import_data:
            for conv_data in import_data["conversations"]:
                try:
                    # Check if conversation already exists
                    existing_conv = db.query(Conversation).filter(
                        Conversation.id == conv_data["id"]
                    ).first()

                    if existing_conv:
                        # Update existing conversation
                        existing_conv.title = conv_data["title"]
                        existing_conv.updated_at = datetime.now(timezone.utc)
                    else:
                        # Create new conversation
                        conversation = Conversation(
                            id=conv_data["id"],
                            title=conv_data["title"],
                            model=conv_data.get("model", "gpt-4"),
                            created_by=user_id,
                            is_public=conv_data.get("is_public", False)
                        )
                        db.add(conversation)

                        # Add participant relationship
                        participant = ConversationParticipant(
                            conversation_id=conv_data["id"],
                            user_id=user_id,
                            permission_level="owner"
                        )
                        db.add(participant)

                    records_processed += 1

                except Exception as e:
                    records_failed += 1
                    validation_errors.append(f"Conversation {conv_data.get('id', 'unknown')}: {str(e)}")

        # Import messages if present
        if "messages" in import_data:
            for msg_data in import_data["messages"]:
                try:
                    # Check if message already exists
                    existing_msg = db.query(Message).filter(
                        Message.id == msg_data["id"]
                    ).first()

                    if not existing_msg:
                        message = Message(
                            id=msg_data["id"],
                            conversation_id=msg_data["conversation_id"],
                            user_id=msg_data.get("user_id"),
                            role=msg_data["role"],
                            content=msg_data["content"],
                            model=msg_data.get("model"),
                            tokens_used=msg_data.get("tokens_used", 0)
                        )
                        db.add(message)
                        records_processed += 1

                except Exception as e:
                    records_failed += 1
                    validation_errors.append(f"Message {msg_data.get('id', 'unknown')}: {str(e)}")

        # Import file uploads if present
        if "file_uploads" in import_data:
            for file_data in import_data["file_uploads"]:
                try:
                    # Check if file upload already exists
                    existing_file = db.query(FileUpload).filter(
                        FileUpload.id == file_data["id"]
                    ).first()

                    if not existing_file:
                        file_upload = FileUpload(
                            id=file_data["id"],
                            user_id=user_id,
                            filename=file_data["filename"],
                            original_filename=file_data["original_filename"],
                            file_size=file_data["file_size"],
                            content_type=file_data.get("content_type"),
                            uploaded_at=datetime.fromisoformat(file_data["uploaded_at"])
                        )
                        db.add(file_upload)
                        records_processed += 1

                except Exception as e:
                    records_failed += 1
                    validation_errors.append(f"File upload {file_data.get('id', 'unknown')}: {str(e)}")

        operation.records_processed = records_processed
        operation.records_failed = records_failed
        operation.validation_errors = validation_errors

        db.commit()

    async def _import_conversations(self, operation: ImportOperation, db):
        """Import conversations data"""
        try:
            import_data = json.loads(operation.import_data.decode('utf-8'))
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format in import data")

        records_processed = 0
        records_failed = 0
        validation_errors = []

        # Import conversations
        if "conversations" in import_data:
            for conv_data in import_data["conversations"]:
                try:
                    existing_conv = db.query(Conversation).filter(
                        Conversation.id == conv_data["id"]
                    ).first()

                    if not existing_conv:
                        conversation = Conversation(
                            id=conv_data["id"],
                            title=conv_data["title"],
                            model=conv_data.get("model", "gpt-4"),
                            created_by=conv_data.get("created_by", operation.user_id),
                            is_public=conv_data.get("is_public", False)
                        )
                        db.add(conversation)
                        records_processed += 1

                except Exception as e:
                    records_failed += 1
                    validation_errors.append(f"Conversation {conv_data.get('id', 'unknown')}: {str(e)}")

        # Import messages
        if "messages" in import_data:
            for msg_data in import_data["messages"]:
                try:
                    existing_msg = db.query(Message).filter(
                        Message.id == msg_data["id"]
                    ).first()

                    if not existing_msg:
                        message = Message(
                            id=msg_data["id"],
                            conversation_id=msg_data["conversation_id"],
                            user_id=msg_data.get("user_id"),
                            role=msg_data["role"],
                            content=msg_data["content"],
                            model=msg_data.get("model"),
                            tokens_used=msg_data.get("tokens_used", 0)
                        )
                        db.add(message)
                        records_processed += 1

                except Exception as e:
                    records_failed += 1
                    validation_errors.append(f"Message {msg_data.get('id', 'unknown')}: {str(e)}")

        operation.records_processed = records_processed
        operation.records_failed = records_failed
        operation.validation_errors = validation_errors

        db.commit()

    async def _import_bulk_admin(self, operation: ImportOperation, db):
        """Import bulk data for administrators"""
        # Only allow superusers
        user = db.query(User).filter(User.id == operation.user_id).first()
        if not user or not user.is_superuser:
            raise ValueError("Admin access required for bulk import")

        try:
            import_data = json.loads(operation.import_data.decode('utf-8'))
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON format in import data")

        records_processed = 0
        records_failed = 0
        validation_errors = []

        # Import users if present
        if "users" in import_data:
            for user_data in import_data["users"]:
                try:
                    existing_user = db.query(User).filter(
                        User.username == user_data["username"]
                    ).first()

                    if not existing_user:
                        user = User(
                            username=user_data["username"],
                            email=user_data["email"],
                            full_name=user_data.get("full_name"),
                            hashed_password=user_data.get("hashed_password", "placeholder"),
                            is_active=user_data.get("is_active", True),
                            is_superuser=user_data.get("is_superuser", False)
                        )
                        db.add(user)
                        records_processed += 1

                except Exception as e:
                    records_failed += 1
                    validation_errors.append(f"User {user_data.get('username', 'unknown')}: {str(e)}")

        operation.records_processed = records_processed
        operation.records_failed = records_failed
        operation.validation_errors = validation_errors

        db.commit()

# Global export service instance
export_service = DataExportService()
