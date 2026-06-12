"""
Security Middleware for Flask Application

This middleware provides:
- JWT token validation
- Request authentication
- Permission checking
- Rate limiting
- Security logging
- Input validation
- CORS handling
"""

import functools
import logging
import time
from typing import Any, Dict, Optional, Callable, Union
from flask import request, jsonify, current_app, g
from werkzeug.exceptions import HTTPException

from app.services.auth_service import decode_request_bearer_token
from app.services.permission_service import permission_service
from app.utils.security import log_security_event

logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """Security middleware for Flask application."""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize middleware with Flask app."""
        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_request(self._teardown_request)
        
        # Register error handlers
        app.errorhandler(401)(self._unauthorized_handler)
        app.errorhandler(403)(self._forbidden_handler)
        app.errorhandler(429)(self._rate_limit_handler)
    
    def _before_request(self):
        """Process request before it reaches the route."""
        # Store request start time
        g.request_start_time = time.time()
        
        # Get client info
        g.client_ip = self._get_client_ip()
        g.user_agent = request.headers.get('User-Agent', '')
        g.device_info = {
            'platform': request.headers.get('X-Device-Platform'),
            'device_id': request.headers.get('X-Device-Id'),
        }
        
        # Check for public routes (no auth required)
        if self._is_public_route():
            return
        
        # Validate JWT token
        try:
            user_doc, decoded_token = self._validate_jwt()
            g.current_user = user_doc
            g.current_token = decoded_token
        except ValueError as e:
            log_security_event(
                event_type="auth_failed",
                details=str(e),
                ip_address=g.client_ip,
                user_agent=g.user_agent
            )
            return self._create_error_response(401, "UNAUTHORIZED", str(e))
        
        # Check rate limiting
        if self._is_rate_limited():
            log_security_event(
                event_type="rate_limit_exceeded",
                details="Rate limit exceeded",
                ip_address=g.client_ip,
                user_agent=g.user_agent,
                user_id=str(user_doc.get('_id')) if user_doc else None
            )
            return self._create_error_response(429, "RATE_LIMIT_EXCEEDED", "Too many requests")
        
        # Validate input data
        if request.method in ['POST', 'PUT', 'PATCH'] and request.is_json:
            try:
                self._validate_input_data(request.get_json())
            except ValueError as e:
                log_security_event(
                    event_type="invalid_input",
                    details=str(e),
                    ip_address=g.client_ip,
                    user_agent=g.user_agent,
                    user_id=str(user_doc.get('_id')) if user_doc else None
                )
                return self._create_error_response(400, "INVALID_INPUT", str(e))
    
    def _after_request(self, response):
        """Process response after the route."""
        # Calculate request duration
        if hasattr(g, 'request_start_time'):
            duration = time.time() - g.request_start_time
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Log successful requests
        if response.status_code < 400:
            self._log_request_success(response)
        
        return response
    
    def _teardown_request(self, exception):
        """Clean up after request."""
        if exception:
            self._log_request_error(exception)
    
    def _get_client_ip(self) -> str:
        """Get client IP address from request."""
        # Check for forwarded IP first (behind proxy)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fall back to remote address
        return request.remote_addr or ''
    
    def _is_public_route(self) -> bool:
        """Check if current route is public (no auth required)."""
        public_routes = [
            '/api/auth/register',
            '/api/auth/login',
            '/api/auth/verify-email',
            '/api/auth/forgot-password',
            '/api/auth/reset-password',
            '/api/auth/accept-invite/',
            '/health',
            '/ping'
        ]
        
        path = request.path
        
        # Check for public forms
        if path.startswith('/api/forms/') and path.endswith('/public'):
            return True
        
        # Check for exact public routes
        return any(path.startswith(route) for route in public_routes)
    
    def _validate_jwt(self):
        """Validate JWT token from request."""
        auth_header = request.headers.get('Authorization', '')
        if not auth_header:
            raise ValueError("Authorization header required")
        
        if not auth_header.startswith('Bearer '):
            raise ValueError("Bearer token required")
        
        return decode_request_bearer_token(auth_header)
    
    def _is_rate_limited(self) -> bool:
        """Check if request is rate limited."""
        # Simple in-memory rate limiting
        # In production, use Redis or similar
        if not hasattr(current_app, 'rate_limits'):
            current_app.rate_limits = {}
        
        client_ip = g.client_ip
        user_id = getattr(g, 'current_user', {}).get('_id')
        
        # Different limits for authenticated vs unauthenticated
        if user_id:
            key = f"user:{user_id}"
            limit = current_app.config.get('RATE_LIMIT_AUTHENTICATED', 60)  # 60 req/min
        else:
            key = f"ip:{client_ip}"
            limit = current_app.config.get('RATE_LIMIT_UNAUTHENTICATED', 20)  # 20 req/min
        
        now = time.time()
        window_start = int(now // 60) * 60  # Current minute
        
        if key not in current_app.rate_limits:
            current_app.rate_limits[key] = []
        
        # Clean old requests
        current_app.rate_limits[key] = [
            req_time for req_time in current_app.rate_limits[key]
            if req_time > window_start
        ]
        
        # Check limit
        if len(current_app.rate_limits[key]) >= limit:
            return True
        
        # Add current request
        current_app.rate_limits[key].append(now)
        return False
    
    def _validate_input_data(self, data: Dict[str, Any]):
        """Validate input data for security issues."""
        if not isinstance(data, dict):
            return
        
        # Check for potential NoSQL injection
        def _check_value(value):
            if isinstance(value, dict):
                for k, v in value.items():
                    if k.startswith('$'):
                        raise ValueError(f"Invalid key: {k}")
                    _check_value(v)
            elif isinstance(value, list):
                for item in value:
                    _check_value(item)
        
        _check_value(data)
        
        # Check for excessively large payloads
        content_length = request.content_length or 0
        max_content_length = current_app.config.get('MAX_CONTENT_LENGTH', 10 * 1024 * 1024)  # 10MB
        if content_length > max_content_length:
            raise ValueError("Request payload too large")
    
    def _log_request_success(self, response):
        """Log successful request."""
        log_security_event(
            event_type="request_success",
            details={
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "response_time": response.headers.get('X-Response-Time')
            },
            ip_address=g.client_ip,
            user_agent=g.user_agent,
            user_id=str(g.current_user.get('_id')) if hasattr(g, 'current_user') else None
        )
    
    def _log_request_error(self, error):
        """Log request error."""
        log_security_event(
            event_type="request_error",
            details={
                "method": request.method,
                "path": request.path,
                "error": str(error)
            },
            ip_address=g.client_ip,
            user_agent=g.user_agent,
            user_id=str(g.current_user.get('_id')) if hasattr(g, 'current_user') else None
        )
    
    def _create_error_response(self, status_code: int, code: str, message: str):
        """Create standardized error response."""
        return jsonify({
            "status": "error",
            "code": code,
            "message": message
        }), status_code
    
    def _unauthorized_handler(self, error):
        """Handle 401 Unauthorized errors."""
        return self._create_error_response(401, "UNAUTHORIZED", "Authentication required")
    
    def _forbidden_handler(self, error):
        """Handle 403 Forbidden errors."""
        return self._create_error_response(403, "FORBIDDEN", "Access denied")
    
    def _rate_limit_handler(self, error):
        """Handle 429 Too Many Requests errors."""
        return self._create_error_response(429, "RATE_LIMIT_EXCEEDED", "Too many requests")


# Decorators for route protection

def require_auth(f: Callable) -> Callable:
    """Decorator to require authentication."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'current_user') or not g.current_user:
            return jsonify({
                "status": "error",
                "code": "UNAUTHORIZED",
                "message": "Authentication required"
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def require_permission(action: str, resource_type: str = None):
    """Decorator to require specific permission."""
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user') or not g.current_user:
                return jsonify({
                    "status": "error",
                    "code": "UNAUTHORIZED",
                    "message": "Authentication required"
                }), 401
            
            # Build resource context
            resource = {"type": resource_type} if resource_type else {}
            
            # Add resource IDs from kwargs
            if 'org_id' in kwargs:
                resource['org_id'] = kwargs['org_id']
            if 'project_id' in kwargs:
                resource['project_id'] = kwargs['project_id']
            if 'form_id' in kwargs:
                resource['form_id'] = kwargs['form_id']
            
            # Check permission
            result = permission_service.check_permission(
                g.current_user, g.current_token, action, resource
            )
            
            if not result.allowed:
                return jsonify({
                    "status": "error",
                    "code": "FORBIDDEN",
                    "message": result.reason or "Permission denied"
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_role(*roles: str):
    """Decorator to require specific role."""
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(g, 'current_user') or not g.current_user:
                return jsonify({
                    "status": "error",
                    "code": "UNAUTHORIZED",
                    "message": "Authentication required"
                }), 401
            
            user_role = g.current_user.get('system_role')
            if user_role not in roles:
                return jsonify({
                    "status": "error",
                    "code": "FORBIDDEN",
                    "message": f"Required role: one of {roles}"
                }), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_super_admin(f: Callable) -> Callable:
    """Decorator to require super admin role."""
    return require_role('super_admin')(f)


def require_org_admin(f: Callable) -> Callable:
    """Decorator to require org admin role."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'current_user') or not g.current_user:
            return jsonify({
                "status": "error",
                "code": "UNAUTHORIZED",
                "message": "Authentication required"
            }), 401
        
        # Check if user is super admin
        if g.current_user.get('system_role') == 'super_admin':
            return f(*args, **kwargs)
        
        # Check if user is org admin for the requested org
        org_id = kwargs.get('org_id') or request.view_args.get('org_id')
        if not org_id:
            return jsonify({
                "status": "error",
                "code": "BAD_REQUEST",
                "message": "Organization ID required"
            }), 400
        
        from app.services.auth_service import resolve_org_role
        org_role = resolve_org_role(g.current_token, org_id)
        if org_role != 'org_admin':
            return jsonify({
                "status": "error",
                "code": "FORBIDDEN",
                "message": "Organization admin required"
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


# Global middleware instance
security_middleware = SecurityMiddleware()