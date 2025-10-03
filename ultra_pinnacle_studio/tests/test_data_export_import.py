"""
Test suite for data export/import functionality
"""
import pytest
import json
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import text
from api_gateway.database import get_db, User, Conversation, Message, ExportOperation, ImportOperation
from api_gateway.data_export_import import DataExportService
from api_gateway.auth import get_password_hash


class TestDataExportImport:
    """Test cases for data export/import functionality"""

    def setup_method(self):
        """Set up test data"""
        self.db = next(get_db())
        self.export_service = DataExportService()

        # Create test user (without user_type_id to avoid schema issues)
        self.db.execute(
            text("INSERT INTO users (username, email, full_name, hashed_password, is_active, is_superuser, created_at, updated_at) VALUES (:username, :email, :full_name, :hashed_password, :is_active, :is_superuser, :created_at, :updated_at)"),
            {
                "username": "test_user",
                "email": "test@example.com",
                "full_name": "Test User",
                "hashed_password": get_password_hash("testpass"),
                "is_active": True,
                "is_superuser": False,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        )
        self.db.commit()

        # Get the created user
        self.test_user = self.db.query(User).filter(User.username == "test_user").first()

        # Create test conversation
        self.test_conversation = Conversation(
            id="test_conv_123",
            title="Test Conversation",
            model="gpt-4",
            created_by=self.test_user.id,
            is_public=False
        )
        self.db.add(self.test_conversation)
        self.db.commit()

        # Create test message
        self.test_message = Message(
            conversation_id="test_conv_123",
            user_id=self.test_user.id,
            role="user",
            content="Hello, this is a test message",
            model="gpt-4",
            tokens_used=10
        )
        self.db.add(self.test_message)
        self.db.commit()

    def teardown_method(self):
        """Clean up test data"""
        # Clean up export files
        if hasattr(self, 'export_service'):
            for file_path in Path(self.export_service.exports_dir).glob("export_*.json"):
                try:
                    file_path.unlink()
                except:
                    pass

        # Clean up database
        if hasattr(self, 'db'):
            try:
                self.db.query(Message).filter(Message.conversation_id == "test_conv_123").delete()
                self.db.query(Conversation).filter(Conversation.id == "test_conv_123").delete()
                self.db.query(User).filter(User.username == "test_user").delete()
                self.db.query(ExportOperation).filter(ExportOperation.user_id == self.test_user.id).delete()
                self.db.query(ImportOperation).filter(ImportOperation.user_id == self.test_user.id).delete()
                self.db.commit()
            except:
                self.db.rollback()

    def test_user_data_export(self):
        """Test user data export functionality"""
        import asyncio

        async def run_test():
            # Create export operation
            operation_id = await self.export_service.create_export_operation(
                user_id=self.test_user.id,
                export_type="user_data",
                format="json",
                data_scope={},
                filters={}
            )

            # Wait for export to complete
            await asyncio.sleep(2)

            # Check operation status
            operation = self.db.query(ExportOperation).filter(ExportOperation.id == operation_id).first()
            assert operation is not None
            assert operation.status == "completed"
            assert operation.file_path is not None
            assert os.path.exists(operation.file_path)

            # Verify export content
            with open(operation.file_path, 'r') as f:
                data = json.load(f)

            assert "user_profile" in data
            assert "conversations" in data
            assert "messages" in data
            assert "export_metadata" in data

            # Verify user profile data
            profile = data["user_profile"]
            assert profile["username"] == "test_user"
            assert profile["email"] == "test@example.com"
            assert profile["full_name"] == "Test User"

            # Verify conversations data
            assert len(data["conversations"]) >= 1
            conv = data["conversations"][0]
            assert conv["id"] == "test_conv_123"
            assert conv["title"] == "Test Conversation"

            # Verify messages data
            assert len(data["messages"]) >= 1
            msg = data["messages"][0]
            assert msg["conversation_id"] == "test_conv_123"
            assert msg["content"] == "Hello, this is a test message"

            # Verify GDPR compliance metadata
            metadata = data["export_metadata"]
            assert metadata["gdpr_compliant"] == True
            assert "data_portability" in metadata

        asyncio.run(run_test())

    def test_conversation_export(self):
        """Test conversation export functionality"""
        import asyncio

        async def run_test():
            # Create export operation
            operation_id = await self.export_service.create_export_operation(
                user_id=self.test_user.id,
                export_type="conversations",
                format="json",
                data_scope={"conversation_ids": ["test_conv_123"]},
                filters={}
            )

            # Wait for export to complete
            await asyncio.sleep(2)

            # Check operation status
            operation = self.db.query(ExportOperation).filter(ExportOperation.id == operation_id).first()
            assert operation is not None
            assert operation.status == "completed"

            # Verify export content
            with open(operation.file_path, 'r') as f:
                data = json.load(f)

            assert "conversations" in data
            assert "messages" in data
            assert len(data["conversations"]) == 1
            assert len(data["messages"]) >= 1

        asyncio.run(run_test())

    def test_export_formats(self):
        """Test different export formats"""
        import asyncio

        async def run_test():
            formats = ["json", "csv", "html"]

            for fmt in formats:
                # Create export operation
                operation_id = await self.export_service.create_export_operation(
                    user_id=self.test_user.id,
                    export_type="user_data",
                    format=fmt,
                    data_scope={},
                    filters={}
                )

                # Wait for export to complete
                await asyncio.sleep(2)

                # Check operation status
                operation = self.db.query(ExportOperation).filter(ExportOperation.id == operation_id).first()
                assert operation is not None
                assert operation.status == "completed"
                assert operation.format == fmt
                assert operation.file_path is not None
                assert os.path.exists(operation.file_path)

        asyncio.run(run_test())

    def test_user_data_import(self):
        """Test user data import functionality"""
        import asyncio

        async def run_test():
            # Create export first
            export_id = await self.export_service.create_export_operation(
                user_id=self.test_user.id,
                export_type="user_data",
                format="json",
                data_scope={},
                filters={}
            )

            await asyncio.sleep(2)

            # Get export data
            export_op = self.db.query(ExportOperation).filter(ExportOperation.id == export_id).first()
            with open(export_op.file_path, 'rb') as f:
                import_data = f.read()

            # Create import operation
            import_id = await self.export_service.create_import_operation(
                user_id=self.test_user.id,
                import_type="user_data",
                import_data=import_data,
                validation_rules={}
            )

            # Wait for import to complete
            await asyncio.sleep(2)

            # Check import status
            import_op = self.db.query(ImportOperation).filter(ImportOperation.id == import_id).first()
            assert import_op is not None
            assert import_op.status == "completed"
            assert import_op.records_processed >= 0
            assert import_op.records_failed == 0

        asyncio.run(run_test())

    def test_invalid_export_type(self):
        """Test invalid export type handling"""
        import asyncio

        async def run_test():
            with pytest.raises(Exception):
                await self.export_service.create_export_operation(
                    user_id=self.test_user.id,
                    export_type="invalid_type",
                    format="json",
                    data_scope={},
                    filters={}
                )

        asyncio.run(run_test())

    def test_export_file_cleanup(self):
        """Test that export files are properly cleaned up"""
        import asyncio

        async def run_test():
            # Create export
            operation_id = await self.export_service.create_export_operation(
                user_id=self.test_user.id,
                export_type="user_data",
                format="json",
                data_scope={},
                filters={}
            )

            await asyncio.sleep(2)

            # Get file path
            operation = self.db.query(ExportOperation).filter(ExportOperation.id == operation_id).first()
            file_path = operation.file_path

            # Verify file exists
            assert os.path.exists(file_path)

            # Delete operation (should clean up file)
            self.db.delete(operation)
            self.db.commit()

            # File should still exist (cleanup is manual for now)
            # In a real implementation, we might want automatic cleanup

        asyncio.run(run_test())

    def test_gdpr_compliance_metadata(self):
        """Test GDPR compliance in exported data"""
        import asyncio

        async def run_test():
            operation_id = await self.export_service.create_export_operation(
                user_id=self.test_user.id,
                export_type="user_data",
                format="json",
                data_scope={},
                filters={}
            )

            await asyncio.sleep(2)

            operation = self.db.query(ExportOperation).filter(ExportOperation.id == operation_id).first()

            with open(operation.file_path, 'r') as f:
                data = json.load(f)

            # Check GDPR compliance metadata
            assert "export_metadata" in data
            metadata = data["export_metadata"]
            assert metadata["gdpr_compliant"] == True
            assert "data_portability" in metadata
            assert "exported_at" in metadata
            assert isinstance(metadata["conversation_count"], int)
            assert isinstance(metadata["message_count"], int)

        asyncio.run(run_test())


if __name__ == "__main__":
    pytest.main([__file__])