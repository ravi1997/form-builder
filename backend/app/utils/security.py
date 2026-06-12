"""
Security utility functions for the Form Builder Platform.
"""

import logging
import hashlib
import hmac
import secrets
import time
from typing import Any, Dict, Optional, List
from datetime import datetime
from bson import ObjectId
from flask import current_app, request, g

from app.extensions import mongo

logger = logging.getLogger(__name__)


def log_security_event(event_type: str, details: Any = None, ip_address: str = None, 
                      user_agent: str = None, user_id: str = None, 
                      entity_type: str = None, entity_id: str = None):
    """
    Log security events to the audit_logs collection.
    
    Args:
        event_type: Type of security event
        details: Additional details about the event
        ip_address: IP address of the requester
        user_agent: User agent string
        user_id: User ID if available
        entity_type: Type of entity affected
        entity_id: ID of entity affected
    """
    try:
        # Get current context if not provided
        if ip_address is None and hasattr(g, 'client_ip'):
            ip_address = g.client_ip
        if user_agent is None and hasattr(g, 'user_agent'):
            user_agent = g.user_agent
        if user_id is None and hasattr(g, 'current_user'):
            user_id = str(g.current_user.get('_id'))
        
        # Create audit log entry
        audit_entry = {
            "_id": ObjectId(),
            "org_id": None,  # Will be filled if context available
            "project_id": None,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": event_type,
            "actor_id": ObjectId(user_id) if user_id else None,
            "actor_role": getattr(g, 'current_user', {}).get('system_role') if hasattr(g, 'current_user') else None,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "before": None,
            "after": None,
            "metadata": details if isinstance(details, dict) else {"details": details},
            "timestamp": datetime.utcnow(),
            "archived": False
        }
        
        # Try to determine org_id from context
        if hasattr(g, 'current_token') and g.current_token:
            orgs = g.current_token.get('orgs', [])
            if orgs:
                audit_entry['org_id'] = ObjectId(orgs[0].get('org_id'))
        
        # Insert into database
        mongo.db.audit_logs.insert_one(audit_entry)
        
        # Also log to file for immediate visibility
        logger.info(f"SECURITY_EVENT: {event_type} - User: {user_id} - IP: {ip_address} - Details: {details}")
        
    except Exception as e:
        logger.error(f"Failed to log security event: {e}")


def generate_secure_token(length: int = 32) -> str:
    """
    Generate a cryptographically secure random token.
    
    Args:
        length: Length of the token in bytes
        
    Returns:
        Hex-encoded secure token
    """
    return secrets.token_hex(length)


def hash_sensitive_data(data: str, salt: str = None) -> str:
    """
    Hash sensitive data for logging/storage.
    
    Args:
        data: Data to hash
        salt: Optional salt for hashing
        
    Returns:
        SHA256 hash of the data
    """
    if salt is None:
        salt = current_app.config.get('SECRET_KEY', 'default-salt')
    
    return hashlib.sha256((data + salt).encode('utf-8')).hexdigest()


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify webhook signature using HMAC-SHA256.
    
    Args:
        payload: Raw request payload
        signature: Signature from request header
        secret: Webhook secret
        
    Returns:
        True if signature is valid
    """
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)


def sanitize_input(input_data: Any) -> Any:
    """
    Sanitize input data to prevent injection attacks.
    
    Args:
        input_data: Input data to sanitize
        
    Returns:
        Sanitized data
    """
    if isinstance(input_data, str):
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\\']
        for char in dangerous_chars:
            input_data = input_data.replace(char, '')
        return input_data.strip()
    elif isinstance(input_data, dict):
        return {key: sanitize_input(value) for key, value in input_data.items()}
    elif isinstance(input_data, list):
        return [sanitize_input(item) for item in input_data]
    else:
        return input_data


def validate_email_domain(email: str, allowed_domains: List[str] = None) -> bool:
    """
    Validate email domain against allowed domains.
    
    Args:
        email: Email address to validate
        allowed_domains: List of allowed domains
        
    Returns:
        True if email domain is allowed
    """
    if not email or '@' not in email:
        return False
    
    domain = email.split('@')[1].lower()
    
    if allowed_domains is None:
        return True  # Allow all domains if none specified
    
    return domain in [d.lower() for d in allowed_domains]


def check_password_strength(password: str, user_info: Dict[str, str] = None) -> Dict[str, Any]:
    """
    Check password strength and return strength assessment.
    
    Args:
        password: Password to check
        user_info: User information (email, name) for context checks
        
    Returns:
        Dictionary with strength assessment and feedback
    """
    feedback = []
    score = 0
    
    # Length check
    if len(password) >= 12:
        score += 2
    elif len(password) >= 8:
        score += 1
    else:
        feedback.append("Password should be at least 8 characters long")
    
    # Character variety
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)
    
    if has_upper:
        score += 1
    else:
        feedback.append("Include uppercase letters")
    
    if has_lower:
        score += 1
    else:
        feedback.append("Include lowercase letters")
    
    if has_digit:
        score += 1
    else:
        feedback.append("Include numbers")
    
    if has_special:
        score += 1
    else:
        feedback.append("Include special characters")
    
    # Check for common patterns
    common_patterns = ['password', '123456', 'qwerty', 'admin']
    if any(pattern in password.lower() for pattern in common_patterns):
        score -= 1
        feedback.append("Avoid common password patterns")
    
    # Check for user info in password
    if user_info:
        email = user_info.get('email', '').lower()
        name = user_info.get('name', '').lower()
        
        if email and email.split('@')[0] in password.lower():
            score -= 1
            feedback.append("Password contains email address")
        
        if name and any(part in password.lower() for part in name.split()):
            score -= 1
            feedback.append("Password contains name")
    
    # Determine strength
    if score >= 6:
        strength = "very_strong"
    elif score >= 4:
        strength = "strong"
    elif score >= 2:
        strength = "medium"
    else:
        strength = "weak"
    
    return {
        "strength": strength,
        "score": score,
        "feedback": feedback,
        "is_acceptable": score >= 2  # Minimum acceptable strength
    }


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key with prefix and hash.
    
    Returns:
        Tuple of (raw_key, key_hash)
    """
    raw_key = f"fbk_{secrets.token_hex(24)}"
    key_hash = hashlib.sha256(raw_key.encode('utf-8')).hexdigest()
    return raw_key, key_hash


def validate_api_key_scope(api_key_doc: Dict[str, Any], required_scope: str) -> bool:
    """
    Validate if API key has required scope.
    
    Args:
        api_key_doc: API key document from database
        required_scope: Required scope
        
    Returns:
        True if key has required scope
    """
    if not api_key_doc or api_key_doc.get('status') != 'active':
        return False
    
    scopes = api_key_doc.get('scopes', [])
    return required_scope in scopes


def check_rate_limit(identifier: str, limit: int, window: int = 60) -> bool:
    """
    Check if identifier has exceeded rate limit.
    
    Args:
        identifier: Unique identifier (IP, user_id, etc.)
        limit: Maximum number of requests
        window: Time window in seconds
        
    Returns:
        True if rate limit exceeded
    """
    # This is a simple in-memory implementation
    # In production, use Redis or similar for distributed rate limiting
    if not hasattr(current_app, 'rate_limits'):
        current_app.rate_limits = {}
    
    now = time.time()
    window_start = int(now // window) * window
    
    key = f"rate_limit:{identifier}"
    
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


def detect_suspicious_activity(user_id: str, activity_type: str, metadata: Dict[str, Any] = None) -> bool:
    """
    Detect suspicious user activity patterns.
    
    Args:
        user_id: User ID to check
        activity_type: Type of activity
        metadata: Additional metadata about the activity
        
    Returns:
        True if activity is suspicious
    """
    # This is a basic implementation
    # In production, use more sophisticated anomaly detection
    
    suspicious_indicators = 0
    
    # Check for rapid successive requests
    if activity_type == 'login':
        recent_logins = list(mongo.db.audit_logs.find({
            "actor_id": ObjectId(user_id),
            "action": "login",
            "timestamp": {"$gte": datetime.utcnow().replace(minute=0, second=0, microsecond=0)}
        }))
        
        if len(recent_logins) > 5:  # More than 5 logins in the last minute
            suspicious_indicators += 1
    
    # Check for login from multiple IP addresses
    if activity_type == 'login' and metadata and 'ip_address' in metadata:
        current_ip = metadata['ip_address']
        recent_ips = mongo.db.audit_logs.distinct(
            "ip_address",
            {
                "actor_id": ObjectId(user_id),
                "action": "login",
                "timestamp": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)}
            }
        )
        
        if len(recent_ips) > 3:  # Logins from more than 3 different IPs in 24 hours
            suspicious_indicators += 1
    
    # Check for unusual user agent
    if activity_type == 'login' and metadata and 'user_agent' in metadata:
        user_agent = metadata['user_agent']
        recent_user_agents = mongo.db.audit_logs.distinct(
            "user_agent",
            {
                "actor_id": ObjectId(user_id),
                "action": "login",
                "timestamp": {"$gte": datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)}
            }
        )
        
        if user_agent not in recent_user_agents and len(recent_user_agents) > 0:
            suspicious_indicators += 1
    
    return suspicious_indicators >= 2  # Consider suspicious if 2+ indicators


def encrypt_sensitive_data(data: str, encryption_key: str = None) -> str:
    """
    Encrypt sensitive data (placeholder implementation).
    
    Args:
        data: Data to encrypt
        encryption_key: Encryption key
        
    Returns:
        Encrypted data (placeholder)
    """
    # This is a placeholder implementation
    # In production, use proper encryption like AES-256-GCM
    if encryption_key is None:
        encryption_key = current_app.config.get('ENCRYPTION_KEY', 'default-key')
    
    # For now, just return base64 encoded data
    import base64
    return base64.b64encode(data.encode('utf-8')).decode('utf-8')


def decrypt_sensitive_data(encrypted_data: str, encryption_key: str = None) -> str:
    """
    Decrypt sensitive data (placeholder implementation).
    
    Args:
        encrypted_data: Data to decrypt
        encryption_key: Encryption key
        
    Returns:
        Decrypted data (placeholder)
    """
    # This is a placeholder implementation
    # In production, use proper decryption
    if encryption_key is None:
        encryption_key = current_app.config.get('ENCRYPTION_KEY', 'default-key')
    
    # For now, just decode base64
    import base64
    return base64.b64decode(encrypted_data.encode('utf-8')).decode('utf-8')


def validate_csp_header(csp_header: str) -> bool:
    """
    Validate Content Security Policy header format.
    
    Args:
        csp_header: CSP header string
        
    Returns:
        True if CSP header is valid
    """
    if not csp_header:
        return False
    
    # Basic CSP validation
    required_directives = ['default-src', 'script-src', 'style-src']
    
    for directive in required_directives:
        if f"{directive} " not in csp_header:
            return False
    
    # Check for unsafe-inline or unsafe-eval (should be avoided in production)
    dangerous_keywords = ['unsafe-inline', 'unsafe-eval', 'data:']
    for keyword in dangerous_keywords:
        if keyword in csp_header:
            logger.warning(f"Potentially unsafe CSP directive: {keyword}")
    
    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent directory traversal attacks.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # Remove dangerous characters
    dangerous_chars = ['..', ':', '*', '?', '"', '<', '>', '|']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]
    
    return filename.strip()