from flask import jsonify, current_app
from werkzeug.exceptions import HTTPException
from bson import ObjectId
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Tuple


class APIError(Exception):
    """Base API error class"""
    def __init__(self, code: str, message: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIError):
    """Validation error"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("VALIDATION_ERROR", message, 400, details)


class AuthenticationError(APIError):
    """Authentication error"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__("UNAUTHORIZED", message, 401)


class AuthorizationError(APIError):
    """Authorization error"""
    def __init__(self, message: str = "Access denied"):
        super().__init__("FORBIDDEN", message, 403)


class NotFoundError(APIError):
    """Resource not found error"""
    def __init__(self, resource_type: str, resource_id: str = None):
        message = f"{resource_type} not found"
        if resource_id:
            message += f": {resource_id}"
        super().__init__("NOT_FOUND", message, 404)


class ConflictError(APIError):
    """Conflict error"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("CONFLICT", message, 409, details)


class RateLimitError(APIError):
    """Rate limit exceeded error"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__("RATE_LIMIT_EXCEEDED", message, 429)


class InternalServerError(APIError):
    """Internal server error"""
    def __init__(self, message: str = "Internal server error"):
        super().__init__("INTERNAL_ERROR", message, 500)


class ServiceUnavailableError(APIError):
    """Service unavailable error"""
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__("SERVICE_UNAVAILABLE", message, 503)


def create_error_response(error: APIError) -> Tuple[Dict[str, Any], int]:
    """Create a standardized error response"""
    response = {
        "status": "error",
        "code": error.code,
        "message": error.message
    }
    
    if error.details:
        response["details"] = error.details
    
    # Add timestamp for debugging
    response["timestamp"] = datetime.utcnow().isoformat()
    
    # Add request ID if available
    if hasattr(current_app, 'request_id'):
        response["request_id"] = current_app.request_id
    
    return response, error.status_code


def handle_validation_error(error: Exception) -> Tuple[Dict[str, Any], int]:
    """Handle validation errors"""
    if isinstance(error, ValueError):
        return create_error_response(ValidationError(str(error)))
    elif isinstance(error, TypeError):
        return create_error_response(ValidationError("Invalid data type"))
    else:
        return create_error_response(ValidationError("Validation failed"))


def handle_database_error(error: Exception) -> Tuple[Dict[str, Any], int]:
    """Handle database errors"""
    current_app.logger.error(f"Database error: {str(error)}")
    return create_error_response(InternalServerError("Database error"))


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """Log error with context"""
    error_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "timestamp": datetime.utcnow().isoformat(),
        "traceback": traceback.format_exc()
    }
    
    if context:
        error_data.update(context)
    
    current_app.logger.error(json.dumps(error_data))


def register_error_handlers(app):
    """Register error handlers for the Flask app"""
    
    @app.errorhandler(APIError)
    def handle_api_error(error):
        response, status_code = create_error_response(error)
        return jsonify(response), status_code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error_flask(error):
        response, status_code = create_error_response(error)
        return jsonify(response), status_code
    
    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            "status": "error",
            "code": "NOT_FOUND",
            "message": "Resource not found",
            "timestamp": datetime.utcnow().isoformat()
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({
            "status": "error",
            "code": "METHOD_NOT_ALLOWED",
            "message": "Method not allowed",
            "timestamp": datetime.utcnow().isoformat()
        }), 405
    
    @app.errorhandler(400)
    def handle_bad_request(error):
        return jsonify({
            "status": "error",
            "code": "BAD_REQUEST",
            "message": "Bad request",
            "timestamp": datetime.utcnow().isoformat()
        }), 400
    
    @app.errorhandler(401)
    def handle_unauthorized(error):
        return jsonify({
            "status": "error",
            "code": "UNAUTHORIZED",
            "message": "Authentication required",
            "timestamp": datetime.utcnow().isoformat()
        }), 401
    
    @app.errorhandler(403)
    def handle_forbidden(error):
        return jsonify({
            "status": "error",
            "code": "FORBIDDEN",
            "message": "Access denied",
            "timestamp": datetime.utcnow().isoformat()
        }), 403
    
    @app.errorhandler(429)
    def handle_rate_limit_exceeded(error):
        return jsonify({
            "status": "error",
            "code": "RATE_LIMIT_EXCEEDED",
            "message": "Rate limit exceeded",
            "timestamp": datetime.utcnow().isoformat()
        }), 429
    
    @app.errorhandler(500)
    def handle_internal_server_error(error):
        current_app.logger.error(f"Internal server error: {str(error)}")
        return jsonify({
            "status": "error",
            "code": "INTERNAL_ERROR",
            "message": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }), 500
    
    @app.errorhandler(503)
    def handle_service_unavailable(error):
        return jsonify({
            "status": "error",
            "code": "SERVICE_UNAVAILABLE",
            "message": "Service temporarily unavailable",
            "timestamp": datetime.utcnow().isoformat()
        }), 503
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        response = {
            "status": "error",
            "code": error.name.upper().replace(" ", "_"),
            "message": error.description,
            "timestamp": datetime.utcnow().isoformat()
        }
        return jsonify(response), error.code
    
    @app.errorhandler(Exception)
    def handle_generic_exception(error):
        # Log the full error for debugging
        log_error(error, {
            "endpoint": request.endpoint if request else "unknown",
            "method": request.method if request else "unknown",
            "path": request.path if request else "unknown"
        })
        
        # Return generic error to client
        return jsonify({
            "status": "error",
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }), 500