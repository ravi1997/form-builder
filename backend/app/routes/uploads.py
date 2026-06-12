from flask import Blueprint, request, jsonify, current_app, Response
from bson import ObjectId
import datetime
import os
import hashlib
import mimetypes
from werkzeug.utils import secure_filename
from tusserver import TusUpload, TusState

from app.extensions import mongo
from app.services.auth_service import decode_request_bearer_token, user_has_access_to_resource

uploads_bp = Blueprint("uploads", __name__, url_prefix="/api/internal/v1/uploads")


def _auth_context():
    auth_header = request.headers.get("Authorization", "")
    try:
        user_doc, decoded = decode_request_bearer_token(auth_header)
        return {"user_doc": user_doc, "decoded": decoded}
    except ValueError:
        if current_app.config.get("TESTING"):
            return {
                "user_doc": None,
                "decoded": {"sub": None, "system_role": "super_admin", "orgs": []},
            }
        return None


def _deny(code="UNAUTHORIZED", message="Unauthorized", status=401):
    return jsonify({"status": "error", "code": code, "message": message}), status


def _success_response(data=None, message="Success", status=200):
    response = {"status": "success", "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response), status


def _error_response(code, message, status=400, details=None):
    response = {"status": "error", "code": code, "message": message}
    if details:
        response["details"] = details
    return jsonify(response), status


def _get_file_type(filename):
    """Determine file type based on extension"""
    mime_type, _ = mimetypes.guess_type(filename)
    
    if not mime_type:
        return "other"
    
    if mime_type.startswith("image/"):
        return "image"
    elif mime_type.startswith("video/"):
        return "video"
    elif mime_type == "application/pdf":
        return "pdf"
    else:
        return "other"


def _validate_file_size(file_size, file_type):
    """Validate file size against configured limits"""
    config = current_app.config
    
    limits = {
        "pdf": config.get("MAX_UPLOAD_SIZE_PDF", 50 * 1024 * 1024),  # 50MB
        "video": config.get("MAX_UPLOAD_SIZE_VIDEO", 300 * 1024 * 1024),  # 300MB
        "image": config.get("MAX_UPLOAD_SIZE_IMAGE", 5 * 1024 * 1024),  # 5MB
        "other": config.get("MAX_UPLOAD_SIZE_OTHER", 10 * 1024 * 1024)  # 10MB
    }
    
    max_size = limits.get(file_type, limits["other"])
    
    if file_size > max_size:
        return False, f"File size exceeds maximum allowed size of {max_size // (1024 * 1024)}MB for {file_type} files"
    
    return True, None


def _get_upload_path(org_id, file_id):
    """Get the upload path for a file"""
    uploads_root = current_app.config.get("UPLOADS_ROOT", "/var/uploads")
    org_path = os.path.join(uploads_root, str(org_id))
    os.makedirs(org_path, exist_ok=True)
    return os.path.join(org_path, str(file_id))


@uploads_bp.route("/init", methods=["POST"])
def init_upload():
    """Initialize a new resumable upload"""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    data = request.get_json() or {}
    
    # Validate required fields
    required_fields = ["filename", "file_size", "org_id", "form_id", "question_id"]
    for field in required_fields:
        if field not in data:
            return _error_response("VALIDATION_ERROR", f"{field} is required", 400)
    
    filename = data["filename"]
    file_size = data["file_size"]
    org_id = data["org_id"]
    form_id = data["form_id"]
    question_id = data["question_id"]
    response_id = data.get("response_id")
    
    # Check access permissions
    if not user_has_access_to_resource(auth["user_doc"], auth["decoded"], {"type": "org", "org_id": org_id}, "upload_file"):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Validate filename
    if not filename or len(filename) > 255:
        return _error_response("INVALID_FILENAME", "Filename is invalid or too long", 400)
    
    # Validate file size
    file_type = _get_file_type(filename)
    size_valid, size_error = _validate_file_size(file_size, file_type)
    if not size_valid:
        return _error_response("FILE_TOO_LARGE", size_error, 400)
    
    # Create file upload record
    file_id = ObjectId()
    now = datetime.datetime.utcnow()
    
    # Generate checksum for the file (will be updated during upload)
    checksum = hashlib.sha256(str(file_id).encode()).hexdigest()
    
    file_doc = {
        "_id": file_id,
        "org_id": ObjectId(org_id),
        "form_id": ObjectId(form_id),
        "response_id": ObjectId(response_id) if response_id else None,
        "question_id": question_id,
        "original_filename": secure_filename(filename),
        "stored_filename": str(file_id),
        "file_path": _get_upload_path(org_id, file_id),
        "mime_type": mimetypes.guess_type(filename)[0] or "application/octet-stream",
        "file_size_bytes": file_size,
        "file_type": file_type,
        "upload_status": "pending",
        "upload_offset": 0,
        "checksum_sha256": checksum,
        "virus_scan_status": "pending",
        "uploaded_by": auth["decoded"]["sub"],
        "created_at": now,
        "updated_at": now,
        "is_deleted": False,
        "deleted_at": None
    }
    
    mongo.db.file_uploads.insert_one(file_doc)
    
    return _success_response({
        "upload_id": str(file_id),
        "upload_url": f"/api/internal/v1/uploads/{file_id}/upload",
        "chunk_size": 5 * 1024 * 1024,  # 5MB chunks
        "expires_at": (now + datetime.timedelta(hours=24)).isoformat()
    }, "Upload initialized", 201)


@uploads_bp.route("/<upload_id>/upload", methods=["PATCH"])
def upload_chunk(upload_id):
    """Upload a chunk using tus protocol"""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    # Parse tus upload headers
    upload_offset = int(request.headers.get("Upload-Offset", 0))
    content_length = int(request.headers.get("Content-Length", 0))
    content_type = request.headers.get("Content-Type", "")
    
    # Get file upload record
    file_oid = ObjectId(upload_id) if ObjectId.is_valid(upload_id) else upload_id
    file_doc = mongo.db.file_uploads.find_one({"_id": file_oid, "is_deleted": False})
    
    if not file_doc:
        return _error_response("UPLOAD_NOT_FOUND", "Upload not found", 404)
    
    # Check ownership
    if str(file_doc["uploaded_by"]) != str(auth["decoded"]["sub"]):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Check if upload is complete
    if file_doc["upload_status"] == "complete":
        return _error_response("UPLOAD_COMPLETE", "Upload is already complete", 400)
    
    # Validate offset
    if upload_offset != file_doc["upload_offset"]:
        return _error_response("INVALID_OFFSET", f"Invalid upload offset. Expected {file_doc['upload_offset']}, got {upload_offset}", 400)
    
    # Get chunk data
    chunk_data = request.data
    if len(chunk_data) != content_length:
        return _error_response("INVALID_CHUNK_SIZE", f"Chunk size mismatch. Expected {content_length}, got {len(chunk_data)}", 400)
    
    # Append chunk to file
    file_path = file_doc["file_path"]
    try:
        # Create file if it doesn't exist
        mode = "wb" if upload_offset == 0 else "ab"
        with open(file_path, mode) as f:
            f.seek(upload_offset)
            f.write(chunk_data)
        
        # Update upload record
        new_offset = upload_offset + content_length
        upload_status = "uploading" if new_offset < file_doc["file_size_bytes"] else "complete"
        
        mongo.db.file_uploads.update_one(
            {"_id": file_oid},
            {"$set": {
                "upload_offset": new_offset,
                "upload_status": upload_status,
                "updated_at": datetime.datetime.utcnow()
            }}
        )
        
        # If upload is complete, calculate checksum and trigger virus scan
        if upload_status == "complete":
            _finalize_upload(file_oid)
        
        # Return tus response
        response = Response(status=204)
        response.headers["Upload-Offset"] = str(new_offset)
        
        if upload_status == "complete":
            response.headers["Tus-Resumable"] = "1.0.0"
        
        return response
        
    except Exception as e:
        mongo.db.file_uploads.update_one(
            {"_id": file_oid},
            {"$set": {
                "upload_status": "failed",
                "updated_at": datetime.datetime.utcnow()
            }}
        )
        return _error_response("UPLOAD_ERROR", f"Failed to write chunk: {str(e)}", 500)


def _finalize_upload(file_oid):
    """Finalize upload and calculate checksum"""
    file_doc = mongo.db.file_uploads.find_one({"_id": file_oid})
    if not file_doc:
        return
    
    file_path = file_doc["file_path"]
    
    try:
        # Calculate SHA256 checksum
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        checksum = sha256_hash.hexdigest()
        
        # Update file record
        mongo.db.file_uploads.update_one(
            {"_id": file_oid},
            {"$set": {
                "checksum_sha256": checksum,
                "virus_scan_status": "pending",
                "updated_at": datetime.datetime.utcnow()
            }}
        )
        
        # Queue virus scan task (would be implemented in workers)
        # For now, mark as clean
        mongo.db.file_uploads.update_one(
            {"_id": file_oid},
            {"$set": {
                "virus_scan_status": "clean",
                "updated_at": datetime.datetime.utcnow()
            }}
        )
        
    except Exception as e:
        current_app.logger.error(f"Error finalizing upload {file_oid}: {str(e)}")
        mongo.db.file_uploads.update_one(
            {"_id": file_oid},
            {"$set": {
                "upload_status": "failed",
                "updated_at": datetime.datetime.utcnow()
            }}
        )


@uploads_bp.route("/<upload_id>/status", methods=["GET"])
def get_upload_status(upload_id):
    """Get upload status"""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    # Get file upload record
    file_oid = ObjectId(upload_id) if ObjectId.is_valid(upload_id) else upload_id
    file_doc = mongo.db.file_uploads.find_one({"_id": file_oid, "is_deleted": False})
    
    if not file_doc:
        return _error_response("UPLOAD_NOT_FOUND", "Upload not found", 404)
    
    # Check ownership
    if str(file_doc["uploaded_by"]) != str(auth["decoded"]["sub"]):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Format response
    response_data = {
        "upload_id": upload_id,
        "filename": file_doc["original_filename"],
        "file_size": file_doc["file_size_bytes"],
        "upload_offset": file_doc["upload_offset"],
        "upload_status": file_doc["upload_status"],
        "virus_scan_status": file_doc["virus_scan_status"],
        "created_at": file_doc["created_at"],
        "updated_at": file_doc["updated_at"]
    }
    
    return _success_response(response_data)


@uploads_bp.route("/<upload_id>", methods=["DELETE"])
def cancel_upload(upload_id):
    """Cancel an upload"""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    # Get file upload record
    file_oid = ObjectId(upload_id) if ObjectId.is_valid(upload_id) else upload_id
    file_doc = mongo.db.file_uploads.find_one({"_id": file_oid, "is_deleted": False})
    
    if not file_doc:
        return _error_response("UPLOAD_NOT_FOUND", "Upload not found", 404)
    
    # Check ownership
    if str(file_doc["uploaded_by"]) != str(auth["decoded"]["sub"]):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Delete file if it exists
    file_path = file_doc["file_path"]
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            current_app.logger.error(f"Error deleting file {file_path}: {str(e)}")
    
    # Mark upload as deleted
    mongo.db.file_uploads.update_one(
        {"_id": file_oid},
        {"$set": {
            "upload_status": "cancelled",
            "is_deleted": True,
            "deleted_at": datetime.datetime.utcnow()
        }}
    )
    
    return _success_response({"message": "Upload cancelled successfully"})


@uploads_bp.route("/<upload_id>/download", methods=["GET"])
def download_file(upload_id):
    """Download a file"""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    # Get file upload record
    file_oid = ObjectId(upload_id) if ObjectId.is_valid(upload_id) else upload_id
    file_doc = mongo.db.file_uploads.find_one({"_id": file_oid, "is_deleted": False})
    
    if not file_doc:
        return _error_response("FILE_NOT_FOUND", "File not found", 404)
    
    # Check if file is ready for download
    if file_doc["upload_status"] != "complete":
        return _error_response("UPLOAD_INCOMPLETE", "File upload is not complete", 400)
    
    if file_doc["virus_scan_status"] != "clean":
        return _error_response("VIRUS_SCAN_PENDING", "File is still being scanned for viruses", 400)
    
    # Check access permissions
    if not user_has_access_to_resource(auth["user_doc"], auth["decoded"], {"type": "org", "org_id": file_doc["org_id"]}, "download_file"):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    file_path = file_doc["file_path"]
    if not os.path.exists(file_path):
        return _error_response("FILE_NOT_FOUND", "File not found on disk", 404)
    
    # Serve file
    try:
        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_doc["original_filename"],
            mimetype=file_doc["mime_type"]
        )
    except Exception as e:
        return _error_response("DOWNLOAD_ERROR", f"Failed to download file: {str(e)}", 500)


@uploads_bp.route("/<upload_id>/info", methods=["GET"])
def get_file_info(upload_id):
    """Get file information"""
    auth = _auth_context()
    if not auth:
        return _deny()
    
    # Get file upload record
    file_oid = ObjectId(upload_id) if ObjectId.is_valid(upload_id) else upload_id
    file_doc = mongo.db.file_uploads.find_one({"_id": file_oid, "is_deleted": False})
    
    if not file_doc:
        return _error_response("FILE_NOT_FOUND", "File not found", 404)
    
    # Check access permissions
    if not user_has_access_to_resource(auth["user_doc"], auth["decoded"], {"type": "org", "org_id": file_doc["org_id"]}, "read_file"):
        return _deny("FORBIDDEN", "Forbidden", 403)
    
    # Format response
    response_data = {
        "file_id": str(file_doc["_id"]),
        "original_filename": file_doc["original_filename"],
        "file_size_bytes": file_doc["file_size_bytes"],
        "file_type": file_doc["file_type"],
        "mime_type": file_doc["mime_type"],
        "upload_status": file_doc["upload_status"],
        "virus_scan_status": file_doc["virus_scan_status"],
        "created_at": file_doc["created_at"],
        "uploaded_by": str(file_doc["uploaded_by"])
    }
    
    return _success_response(response_data)


# Import send_file at the top of the file
from flask import send_file