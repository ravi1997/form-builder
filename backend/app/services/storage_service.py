"""
Storage Service - Handles file operations, upload management, and quota tracking
"""

import os
import hashlib
import shutil
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import logging
from bson import ObjectId
from pymongo.errors import PyMongoError

from ..models.storage import (
    FileUpload, StorageQuota, FileUploadCreate, FileUploadUpdate,
    StorageQuotaCreate, StorageQuotaUpdate
)
from ..models.common import PyObjectId
from ..utils.security import validate_file_type, validate_file_size, sanitize_filename
from ..utils.validators import validate_object_id
from ..utils.service_utils import (
    ServiceError, ValidationError, NotFoundError, QuotaExceededError,
    handle_database_errors, create_service_response, ServiceLogger,
    validate_required_fields, validate_string_length, sanitize_dict
)
from ..extensions import mongo_db

logger = ServiceLogger("storage_service").logger


class StorageService:
    """Service for managing file storage, uploads, and quotas"""
    
    def __init__(self):
        self.uploads_root = os.getenv('UPLOADS_ROOT', '/var/uploads')
        self.max_file_sizes = {
            'pdf': int(os.getenv('MAX_UPLOAD_SIZE_PDF', 52428800)),  # 50MB
            'video': int(os.getenv('MAX_UPLOAD_SIZE_VIDEO', 314572800)),  # 300MB
            'image': int(os.getenv('MAX_UPLOAD_SIZE_IMAGE', 52428800)),  # 50MB
            'other': int(os.getenv('MAX_UPLOAD_SIZE_OTHER', 104857600))  # 100MB
        }
        self.chunk_size = 5 * 1024 * 1024  # 5MB chunks for resumable uploads
        
        # Ensure uploads directory exists
        Path(self.uploads_root).mkdir(parents=True, exist_ok=True)
        
    @handle_database_errors
    async def get_storage_quota(self, org_id: PyObjectId) -> StorageQuota:
        """Get storage quota for an organization"""
        try:
            if not org_id:
                raise ValidationError("Organization ID is required", "org_id")
            
            org_oid = validate_object_id(org_id, "org_id")
            
            quota_doc = await mongo_db.storage_quotas.find_one({"org_id": org_oid})
            if not quota_doc:
                # Create default quota if not exists
                default_quota = await self._create_default_quota(org_oid)
                return default_quota
            return StorageQuota(**quota_doc)
        except Exception as e:
            logger.error(f"Error fetching storage quota for org {org_id}: {e}")
            raise
    
    @handle_database_errors
    async def _create_default_quota(self, org_id: PyObjectId) -> StorageQuota:
        """Create default storage quota for organization"""
        try:
            default_quota_bytes = int(os.getenv('DEFAULT_STORAGE_QUOTA_BYTES', 1073741824))  # 1GB
            
            quota_data = StorageQuotaCreate(
                org_id=org_id,
                quota_bytes=default_quota_bytes,
                warning_threshold=0.8
            )
            
            result = await mongo_db.storage_quotas.insert_one(quota_data.dict(by_alias=True))
            quota_data.id = result.inserted_id
            
            return StorageQuota(**quota_data.dict(by_alias=True))
        except Exception as e:
            logger.error(f"Error creating default quota for org {org_id}: {e}")
            raise
    
    @handle_database_errors
    async def check_storage_available(self, org_id: PyObjectId, file_size: int) -> bool:
        """Check if organization has enough storage space"""
        try:
            if not org_id:
                raise ValidationError("Organization ID is required", "org_id")
            
            if not isinstance(file_size, int) or file_size <= 0:
                raise ValidationError("File size must be a positive integer", "file_size")
            
            quota = await self.get_storage_quota(org_id)
            if not quota:
                return False
                
            used_total = (
                quota.used_bytes.get('files', 0) +
                quota.used_bytes.get('database', 0) +
                quota.used_bytes.get('audit_logs', 0)
            )
            
            available_space = quota.quota_bytes - used_total
            return available_space >= file_size
        except Exception as e:
            logger.error(f"Error checking storage availability for org {org_id}: {e}")
            return False
    
    async def update_storage_usage(self, org_id: PyObjectId, file_size: int, operation: str = 'add') -> None:
        """Update storage usage for organization"""
        try:
            quota = await self.get_storage_quota(org_id)
            if not quota:
                return
                
            current_files = quota.used_bytes.get('files', 0)
            
            if operation == 'add':
                new_files = current_files + file_size
            elif operation == 'subtract':
                new_files = max(0, current_files - file_size)
            else:
                return
                
            await mongo_db.storage_quotas.update_one(
                {"org_id": org_id},
                {
                    "$set": {
                        "used_bytes.files": new_files,
                        "last_calculated_at": datetime.utcnow()
                    }
                }
            )
            
            # Check quota warnings
            total_used = (
                new_files +
                quota.used_bytes.get('database', 0) +
                quota.used_bytes.get('audit_logs', 0)
            )
            
            usage_percentage = total_used / quota.quota_bytes
            if usage_percentage >= quota.warning_threshold:
                await self._trigger_quota_warning(org_id, usage_percentage)
                
        except PyMongoError as e:
            logger.error(f"Error updating storage usage for org {org_id}: {e}")
            raise
    
    async def _trigger_quota_warning(self, org_id: PyObjectId, usage_percentage: float) -> None:
        """Trigger quota warning notification"""
        try:
            # This would integrate with the notification service
            logger.warning(f"Storage quota warning for org {org_id}: {usage_percentage:.1%} used")
            # TODO: Send notification to org administrators
        except Exception as e:
            logger.error(f"Error triggering quota warning for org {org_id}: {e}")
    
    @handle_database_errors
    async def initiate_file_upload(
        self, 
        org_id: PyObjectId,
        form_id: Optional[PyObjectId],
        response_id: Optional[PyObjectId],
        question_id: Optional[str],
        filename: str,
        file_size: int,
        mime_type: str,
        uploaded_by: PyObjectId
    ) -> FileUpload:
        """Initiate a new file upload"""
        try:
            # Validate required fields
            validate_required_fields({
                'org_id': org_id,
                'filename': filename,
                'file_size': file_size,
                'mime_type': mime_type,
                'uploaded_by': uploaded_by
            }, ['org_id', 'filename', 'file_size', 'mime_type', 'uploaded_by'])
            
            # Validate ObjectIds
            org_oid = validate_object_id(org_id, "org_id")
            uploaded_by_oid = validate_object_id(uploaded_by, "uploaded_by")
            
            if form_id:
                form_oid = validate_object_id(form_id, "form_id")
            
            if response_id:
                response_oid = validate_object_id(response_id, "response_id")
            
            # Validate filename and file size
            validate_string_length(filename, 1, 255, "filename")
            
            if not isinstance(file_size, int) or file_size <= 0:
                raise ValidationError("File size must be a positive integer", "file_size")
            
            # Check storage availability
            if not await self.check_storage_available(org_oid, file_size):
                raise QuotaExceededError("storage", file_size, await self._get_available_storage(org_oid))
            
            # Validate file type and size
            file_type = self._determine_file_type(mime_type)
            max_size = self.max_file_sizes.get(file_type, self.max_file_sizes['other'])
            
            if not validate_file_size(file_size, max_size):
                raise ValidationError(f"File size exceeds maximum allowed size for {file_type}", "file_size")
            
            if not validate_file_type(mime_type):
                raise ValidationError("File type not allowed", "mime_type")
            
            # Sanitize filename
            safe_filename = sanitize_filename(filename)
            
            # Create file upload record
            file_data = FileUploadCreate(
                org_id=org_oid,
                form_id=form_oid if form_id else None,
                response_id=response_oid if response_id else None,
                question_id=question_id,
                original_filename=safe_filename,
                stored_filename=self._generate_stored_filename(safe_filename),
                file_size_bytes=file_size,
                mime_type=mime_type,
                file_type=file_type,
                upload_status='pending',
                uploaded_by=uploaded_by_oid
            )
            
            result = await mongo_db.file_uploads.insert_one(file_data.dict(by_alias=True))
            file_data.id = result.inserted_id
            
            # Create file path
            file_path = self._get_file_path(org_oid, file_data.stored_filename)
            
            # Update file record with path
            await mongo_db.file_uploads.update_one(
                {"_id": result.inserted_id},
                {"$set": {"file_path": file_path}}
            )
            
            return FileUpload(**{**file_data.dict(by_alias=True), "file_path": file_path})
            
        except Exception as e:
            logger.error(f"Error initiating file upload: {e}")
            raise
    
    async def _get_available_storage(self, org_id: PyObjectId) -> int:
        """Get available storage for organization"""
        quota = await self.get_storage_quota(org_id)
        if not quota:
            return 0
            
        used_total = (
            quota.used_bytes.get('files', 0) +
            quota.used_bytes.get('database', 0) +
            quota.used_bytes.get('audit_logs', 0)
        )
        
        return quota.quota_bytes - used_total
    
    def _determine_file_type(self, mime_type: str) -> str:
        """Determine file type category from MIME type"""
        mime_type = mime_type.lower()
        
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type == 'application/pdf':
            return 'pdf'
        else:
            return 'other'
    
    def _generate_stored_filename(self, original_filename: str) -> str:
        """Generate unique stored filename"""
        name, ext = os.path.splitext(original_filename)
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{ext}"
    
    def _get_file_path(self, org_id: PyObjectId, stored_filename: str) -> str:
        """Get file path for storage"""
        org_path = Path(self.uploads_root) / str(org_id)
        org_path.mkdir(parents=True, exist_ok=True)
        return str(org_path / stored_filename)
    
    async def upload_file_chunk(
        self, 
        file_id: PyObjectId, 
        chunk_data: bytes, 
        chunk_offset: int,
        chunk_number: int,
        total_chunks: int
    ) -> FileUpload:
        """Upload a chunk of a file"""
        try:
            # Get file upload record
            file_doc = await mongo_db.file_uploads.find_one({"_id": file_id})
            if not file_doc:
                raise ValueError("File upload not found")
            
            file_upload = FileUpload(**file_doc)
            
            # Check if upload is still pending
            if file_upload.upload_status != 'pending':
                raise ValueError("File upload is not in pending state")
            
            # Create temp directory for chunks if not exists
            temp_dir = Path(self.uploads_root) / "temp" / str(file_id)
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Save chunk
            chunk_path = temp_dir / f"chunk_{chunk_number}"
            with open(chunk_path, 'wb') as f:
                f.write(chunk_data)
            
            # Update upload progress
            await mongo_db.file_uploads.update_one(
                {"_id": file_id},
                {
                    "$set": {
                        "upload_offset": chunk_offset + len(chunk_data),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # If this is the last chunk, assemble the file
            if chunk_number == total_chunks - 1:
                return await self._assemble_file_chunks(file_id, temp_dir, total_chunks)
            
            return file_upload
            
        except PyMongoError as e:
            logger.error(f"Error uploading file chunk: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in file chunk upload: {e}")
            raise
    
    async def _assemble_file_chunks(self, file_id: PyObjectId, temp_dir: Path, total_chunks: int) -> FileUpload:
        """Assemble file chunks into complete file"""
        try:
            # Get file upload record
            file_doc = await mongo_db.file_uploads.find_one({"_id": file_id})
            file_upload = FileUpload(**file_doc)
            
            # Create final file path
            final_path = Path(file_upload.file_path)
            final_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Assemble chunks
            with open(final_path, 'wb') as final_file:
                for i in range(total_chunks):
                    chunk_path = temp_dir / f"chunk_{i}"
                    if not chunk_path.exists():
                        raise ValueError(f"Missing chunk {i}")
                    
                    with open(chunk_path, 'rb') as chunk_file:
                        final_file.write(chunk_file.read())
            
            # Calculate checksum
            checksum_sha256 = self._calculate_file_checksum(final_path)
            
            # Update file record
            await mongo_db.file_uploads.update_one(
                {"_id": file_id},
                {
                    "$set": {
                        "upload_status": "complete",
                        "checksum_sha256": checksum_sha256,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Update storage usage
            await self.update_storage_usage(file_upload.org_id, file_upload.file_size_bytes, 'add')
            
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            # Get updated file record
            updated_doc = await mongo_db.file_uploads.find_one({"_id": file_id})
            return FileUpload(**updated_doc)
            
        except Exception as e:
            logger.error(f"Error assembling file chunks: {e}")
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()
    
    async def get_file_upload(self, file_id: PyObjectId) -> Optional[FileUpload]:
        """Get file upload by ID"""
        try:
            file_doc = await mongo_db.file_uploads.find_one({"_id": file_id})
            if not file_doc:
                return None
            return FileUpload(**file_doc)
        except PyMongoError as e:
            logger.error(f"Error fetching file upload {file_id}: {e}")
            raise
    
    async def get_file_uploads_by_org(self, org_id: PyObjectId, limit: int = 100, offset: int = 0) -> List[FileUpload]:
        """Get file uploads for an organization"""
        try:
            cursor = mongo_db.file_uploads.find(
                {"org_id": org_id, "is_deleted": False}
            ).sort("created_at", -1).skip(offset).limit(limit)
            
            files = []
            async for doc in cursor:
                files.append(FileUpload(**doc))
            
            return files
        except PyMongoError as e:
            logger.error(f"Error fetching file uploads for org {org_id}: {e}")
            raise
    
    async def get_file_uploads_by_response(self, response_id: PyObjectId) -> List[FileUpload]:
        """Get file uploads for a response"""
        try:
            cursor = mongo_db.file_uploads.find(
                {"response_id": response_id, "is_deleted": False}
            ).sort("created_at", 1)
            
            files = []
            async for doc in cursor:
                files.append(FileUpload(**doc))
            
            return files
        except PyMongoError as e:
            logger.error(f"Error fetching file uploads for response {response_id}: {e}")
            raise
    
    async def delete_file_upload(self, file_id: PyObjectId, deleted_by: PyObjectId) -> bool:
        """Delete a file upload"""
        try:
            # Get file upload record
            file_doc = await mongo_db.file_uploads.find_one({"_id": file_id})
            if not file_doc:
                return False
            
            file_upload = FileUpload(**file_doc)
            
            # Delete physical file
            file_path = Path(file_upload.file_path)
            if file_path.exists():
                file_path.unlink()
            
            # Update storage usage
            await self.update_storage_usage(file_upload.org_id, file_upload.file_size_bytes, 'subtract')
            
            # Mark as deleted in database
            await mongo_db.file_uploads.update_one(
                {"_id": file_id},
                {
                    "$set": {
                        "is_deleted": True,
                        "deleted_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return True
            
        except PyMongoError as e:
            logger.error(f"Error deleting file upload {file_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error in file deletion: {e}")
            raise
    
    async def get_file_url(self, file_id: PyObjectId, expires_in: int = 3600) -> Optional[str]:
        """Get secure URL for file download"""
        try:
            file_upload = await self.get_file_upload(file_id)
            if not file_upload or file_upload.upload_status != 'complete':
                return None
            
            # Generate secure download URL
            # This would typically involve creating a signed URL or token
            # For now, return a placeholder
            return f"/api/files/{file_id}/download"
            
        except Exception as e:
            logger.error(f"Error generating file URL: {e}")
            return None
    
    async def cleanup_expired_uploads(self) -> int:
        """Clean up expired pending uploads"""
        try:
            expiry_time = datetime.utcnow() - timedelta(days=1)  # 24 hours
            
            # Find expired pending uploads
            cursor = mongo_db.file_uploads.find({
                "upload_status": "pending",
                "created_at": {"$lt": expiry_time}
            })
            
            cleaned_count = 0
            async for doc in cursor:
                file_upload = FileUpload(**doc)
                
                # Delete physical file if exists
                file_path = Path(file_upload.file_path)
                if file_path.exists():
                    file_path.unlink()
                
                # Clean up temp directory
                temp_dir = Path(self.uploads_root) / "temp" / str(file_upload.id)
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                
                # Mark as deleted
                await mongo_db.file_uploads.update_one(
                    {"_id": file_upload.id},
                    {
                        "$set": {
                            "is_deleted": True,
                            "deleted_at": datetime.utcnow(),
                            "upload_status": "expired"
                        }
                    }
                )
                
                cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} expired uploads")
            return cleaned_count
            
        except PyMongoError as e:
            logger.error(f"Error cleaning up expired uploads: {e}")
            raise


# Global service instance
storage_service = StorageService()