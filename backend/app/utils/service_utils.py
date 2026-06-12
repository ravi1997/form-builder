"""
Service Utilities - Common utilities for all services including error handling, validation, and logging
"""

import logging
import traceback
from typing import Any, Dict, Optional, Union, List
from datetime import datetime
from bson import ObjectId
from pymongo.errors import PyMongoError, DuplicateKeyError, ConnectionFailure
from flask import current_app
import json


class ServiceError(Exception):
    """Base exception for service errors"""
    
    def __init__(self, message: str, error_code: str = "SERVICE_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(ServiceError):
    """Raised when validation fails"""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field


class NotFoundError(ServiceError):
    """Raised when a resource is not found"""
    
    def __init__(self, resource_type: str, resource_id: Any, details: Optional[Dict[str, Any]] = None):
        message = f"{resource_type} not found: {resource_id}"
        super().__init__(message, "NOT_FOUND", details)
        self.resource_type = resource_type
        self.resource_id = resource_id


class PermissionError(ServiceError):
    """Raised when permission is denied"""
    
    def __init__(self, action: str, resource_type: str, details: Optional[Dict[str, Any]] = None):
        message = f"Permission denied: {action} on {resource_type}"
        super().__init__(message, "PERMISSION_DENIED", details)
        self.action = action
        self.resource_type = resource_type


class ConflictError(ServiceError):
    """Raised when there's a conflict (e.g., duplicate resource)"""
    
    def __init__(self, message: str, conflict_type: str = "CONFLICT", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, conflict_type, details)


class QuotaExceededError(ServiceError):
    """Raised when quota is exceeded"""
    
    def __init__(self, quota_type: str, current: int, limit: int, details: Optional[Dict[str, Any]] = None):
        message = f"{quota_type} quota exceeded: {current}/{limit}"
        super().__init__(message, "QUOTA_EXCEEDED", details)
        self.quota_type = quota_type
        self.current = current
        self.limit = limit


def validate_object_id(value: Any, field_name: str = "ID") -> ObjectId:
    """Validate and convert value to ObjectId"""
    if value is None:
        raise ValidationError(f"{field_name} is required", field_name)
    
    if isinstance(value, ObjectId):
        return value
    
    if isinstance(value, str):
        if not ObjectId.is_valid(value):
            raise ValidationError(f"Invalid {field_name} format", field_name)
        return ObjectId(value)
    
    raise ValidationError(f"{field_name} must be a string or ObjectId", field_name)


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
    """Validate that all required fields are present"""
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == "":
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(
            f"Missing required fields: {', '.join(missing_fields)}",
            details={"missing_fields": missing_fields}
        )


def validate_string_length(value: str, min_length: int = 0, max_length: int = 255, field_name: str = "field") -> None:
    """Validate string length"""
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string", field_name)
    
    if len(value) < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters long", field_name)
    
    if len(value) > max_length:
        raise ValidationError(f"{field_name} must be at most {max_length} characters long", field_name)


def validate_email(email: str) -> None:
    """Validate email format"""
    import re
    
    if not isinstance(email, str):
        raise ValidationError("Email must be a string", "email")
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError("Invalid email format", "email")


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize string input"""
    if not isinstance(value, str):
        return ""
    
    # Remove leading/trailing whitespace
    value = value.strip()
    
    # Limit length
    if len(value) > max_length:
        value = value[:max_length]
    
    return value


def sanitize_dict(data: Dict[str, Any], sensitive_fields: List[str] = None) -> Dict[str, Any]:
    """Sanitize dictionary by removing sensitive fields"""
    if not isinstance(data, dict):
        return {}
    
    sensitive_fields = sensitive_fields or [
        'password', 'password_hash', 'secret', 'token', 'key', 'credit_card',
        'ssn', 'social_security', 'bank_account', 'routing_number'
    ]
    
    sanitized = {}
    for key, value in data.items():
        if key.lower() in sensitive_fields:
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, sensitive_fields)
        elif isinstance(value, list):
            sanitized[key] = [sanitize_dict(item, sensitive_fields) if isinstance(item, dict) else item for item in value]
        else:
            sanitized[key] = value
    
    return sanitized


def handle_database_errors(func):
    """Decorator to handle common database errors"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DuplicateKeyError as e:
            error_msg = "Resource already exists"
            if hasattr(e, 'details') and 'keyValue' in e.details:
                error_msg = f"Duplicate key error: {e.details['keyValue']}"
            raise ConflictError(error_msg, "DUPLICATE_KEY", {"original_error": str(e)})
        except ConnectionFailure as e:
            raise ServiceError("Database connection failed", "DB_CONNECTION_ERROR", {"original_error": str(e)})
        except PyMongoError as e:
            raise ServiceError("Database operation failed", "DB_ERROR", {"original_error": str(e)})
    return wrapper


def log_service_call(logger: logging.Logger, service_name: str, method_name: str, 
                     args: tuple = None, kwargs: dict = None, result: Any = None, 
                     error: Exception = None, execution_time: float = None):
    """Log service call with details"""
    
    log_data = {
        "service": service_name,
        "method": method_name,
        "timestamp": datetime.utcnow().isoformat(),
        "execution_time_ms": execution_time * 1000 if execution_time else None,
        "success": error is None
    }
    
    if error:
        log_data["error"] = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc()
        }
    
    # Sanitize args and kwargs for logging
    if args:
        log_data["args_count"] = len(args)
    
    if kwargs:
        sanitized_kwargs = sanitize_dict(kwargs)
        log_data["kwargs"] = sanitized_kwargs
    
    if result and not error:
        # For successful calls, log a summary of the result
        if isinstance(result, dict):
            log_data["result_keys"] = list(result.keys())
        elif isinstance(result, list):
            log_data["result_count"] = len(result)
    
    if error:
        logger.error(f"Service call failed: {json.dumps(log_data, default=str)}")
    else:
        logger.info(f"Service call completed: {json.dumps(log_data, default=str)}")


def time_service_call(logger: logging.Logger, service_name: str, method_name: str):
    """Decorator to time service calls and log them"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            error = None
            result = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                execution_time = time.time() - start_time
                log_service_call(
                    logger=logger,
                    service_name=service_name,
                    method_name=method_name,
                    args=args,
                    kwargs=kwargs,
                    result=result,
                    error=error,
                    execution_time=execution_time
                )
        return wrapper
    return decorator


class ServiceLogger:
    """Helper class for service logging"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(f"services.{service_name}")
    
    def log_call(self, method_name: str, **kwargs):
        """Log a service call"""
        log_service_call(
            logger=self.logger,
            service_name=self.service_name,
            method_name=method_name,
            **kwargs
        )
    
    def time_method(self, method_name: str):
        """Decorator to time and log method calls"""
        return time_service_call(self.logger, self.service_name, method_name)
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """Log an error with context"""
        error_data = {
            "service": self.service_name,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        }
        
        self.logger.error(f"Service error: {json.dumps(error_data, default=str)}")
    
    def log_warning(self, message: str, context: Dict[str, Any] = None):
        """Log a warning with context"""
        warning_data = {
            "service": self.service_name,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        }
        
        self.logger.warning(f"Service warning: {json.dumps(warning_data, default=str)}")
    
    def log_info(self, message: str, context: Dict[str, Any] = None):
        """Log info with context"""
        info_data = {
            "service": self.service_name,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        }
        
        self.logger.info(f"Service info: {json.dumps(info_data, default=str)}")


def create_service_response(success: bool, data: Any = None, message: str = None, 
                           error_code: str = None, details: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a standardized service response"""
    response = {
        "success": success,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if success:
        response["data"] = data
        if message:
            response["message"] = message
    else:
        response["error"] = {
            "code": error_code or "UNKNOWN_ERROR",
            "message": message or "An error occurred"
        }
        if details:
            response["error"]["details"] = details
    
    return response


def handle_service_exception(func):
    """Decorator to handle service exceptions and return standardized responses"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ServiceError as e:
            return create_service_response(
                success=False,
                message=e.message,
                error_code=e.error_code,
                details=e.details
            )
        except Exception as e:
            # Log unexpected errors
            logging.getLogger("services").error(
                f"Unexpected error in {func.__name__}: {str(e)}",
                exc_info=True
            )
            return create_service_response(
                success=False,
                message="An unexpected error occurred",
                error_code="INTERNAL_ERROR",
                details={"original_error": str(e)}
            )
    return wrapper


# Common validation patterns
def validate_pagination_params(page: int, per_page: int, max_per_page: int = 100) -> tuple[int, int]:
    """Validate pagination parameters"""
    if not isinstance(page, int) or page < 1:
        page = 1
    
    if not isinstance(per_page, int) or per_page < 1:
        per_page = 20
    
    if per_page > max_per_page:
        per_page = max_per_page
    
    return page, per_page


def validate_sort_params(sort_by: str, valid_fields: List[str], default_sort: str = "created_at") -> str:
    """Validate sort parameters"""
    if not sort_by or sort_by not in valid_fields:
        return default_sort
    
    return sort_by


def validate_filter_params(filters: Dict[str, Any], valid_filters: List[str]) -> Dict[str, Any]:
    """Validate filter parameters"""
    if not isinstance(filters, dict):
        return {}
    
    validated_filters = {}
    for key, value in filters.items():
        if key in valid_filters:
            validated_filters[key] = value
    
    return validated_filters