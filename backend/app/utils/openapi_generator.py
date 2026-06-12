"""
OpenAPI/Swagger Documentation Generator

This module generates OpenAPI 3.0 documentation for the Form Builder API.
"""

from flask import jsonify, request, current_app
from datetime import datetime
import yaml
import json
from typing import Dict, List, Any


class OpenAPIDocGenerator:
    """OpenAPI documentation generator for Flask app."""
    
    def __init__(self, app=None):
        self.app = app
        self.openapi_spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "Form Builder Platform API",
                "version": "1.0.0",
                "description": "API documentation for the Form Builder Platform",
                "contact": {
                    "name": "API Support",
                    "email": "support@formbuilder.com"
                },
                "license": {
                    "name": "MIT",
                    "url": "https://opensource.org/licenses/MIT"
                }
            },
            "servers": [
                {
                    "url": "http://localhost:5000",
                    "description": "Development server"
                },
                {
                    "url": "https://api.formbuilder.com",
                    "description": "Production server"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {},
                "parameters": {},
                "responses": {}
            },
            "security": [],
            "tags": []
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize with Flask app."""
        self.app = app
        
        # Add OpenAPI endpoint
        @app.route('/api/docs/openapi.json', methods=['GET'])
        def get_openapi_spec():
            return jsonify(self.generate_spec())
        
        @app.route('/api/docs', methods=['GET'])
        def get_docs():
            return """
            <html>
                <head>
                    <title>Form Builder API Documentation</title>
                    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
                    <style>
                        html { box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }
                        *, *:before, *:after { box-sizing: inherit; }
                        body { margin:0; background: #fafafa; }
                    </style>
                </head>
                <body>
                    <div id="swagger-ui"></div>
                    <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"></script>
                    <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-standalone-preset.js"></script>
                    <script>
                        window.onload = function() {
                            const ui = SwaggerUIBundle({
                                url: '/api/docs/openapi.json',
                                dom_id: '#swagger-ui',
                                deepLinking: true,
                                presets: [
                                    SwaggerUIBundle.presets.apis,
                                    SwaggerUIStandalonePreset
                                ],
                                plugins: [
                                    SwaggerUIBundle.plugins.DownloadUrl
                                ],
                                layout: "StandaloneLayout"
                            });
                        };
                    </script>
                </body>
            </html>
            """
    
    def generate_spec(self) -> Dict[str, Any]:
        """Generate the complete OpenAPI specification."""
        self._add_security_schemes()
        self._add_common_schemas()
        self._add_common_parameters()
        self._add_common_responses()
        self._add_tags()
        self._add_paths()
        
        return self.openapi_spec
    
    def _add_security_schemes(self):
        """Add security schemes to the OpenAPI spec."""
        self.openapi_spec["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            },
            "apiKey": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key"
            },
            "oauth2": {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "/oauth/authorize",
                        "tokenUrl": "/oauth/token",
                        "scopes": {
                            "read": "Read access",
                            "write": "Write access",
                            "admin": "Admin access"
                        }
                    }
                }
            }
        }
    
    def _add_common_schemas(self):
        """Add common schemas to the OpenAPI spec."""
        schemas = self.openapi_spec["components"]["schemas"]
        
        # Error response schema
        schemas["ErrorResponse"] = {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["error"],
                    "example": "error"
                },
                "code": {
                    "type": "string",
                    "example": "VALIDATION_ERROR"
                },
                "message": {
                    "type": "string",
                    "example": "Invalid input data"
                },
                "details": {
                    "type": "object",
                    "nullable": true
                },
                "timestamp": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2024-01-01T00:00:00Z"
                }
            },
            "required": ["status", "code", "message", "timestamp"]
        }
        
        # Pagination schema
        schemas["PaginationMeta"] = {
            "type": "object",
            "properties": {
                "page": {
                    "type": "integer",
                    "example": 1
                },
                "per_page": {
                    "type": "integer",
                    "example": 20
                },
                "total": {
                    "type": "integer",
                    "example": 100
                },
                "total_pages": {
                    "type": "integer",
                    "example": 5
                }
            }
        }
        
        # User schema
        schemas["User"] = {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                    "example": "550e8400-e29b-41d4-a716-446655440000"
                },
                "email": {
                    "type": "string",
                    "format": "email",
                    "example": "user@example.com"
                },
                "full_name": {
                    "type": "string",
                    "example": "John Doe"
                },
                "display_name": {
                    "type": "string",
                    "example": "John"
                },
                "status": {
                    "type": "string",
                    "enum": ["pending_approval", "active", "suspended", "deactivated"],
                    "example": "active"
                },
                "email_verified": {
                    "type": "boolean",
                    "example": true
                },
                "created_at": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2024-01-01T00:00:00Z"
                },
                "updated_at": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2024-01-01T00:00:00Z"
                }
            },
            "required": ["id", "email", "full_name", "status", "created_at", "updated_at"]
        }
        
        # Organization schema
        schemas["Organization"] = {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                    "example": "550e8400-e29b-41d4-a716-446655440000"
                },
                "name": {
                    "type": "string",
                    "example": "Acme Corporation"
                },
                "slug": {
                    "type": "string",
                    "example": "acme-corp"
                },
                "description": {
                    "type": "string",
                    "example": "A sample organization"
                },
                "org_type": {
                    "type": "string",
                    "enum": ["organisation", "department", "team", "unit"],
                    "example": "organisation"
                },
                "status": {
                    "type": "string",
                    "enum": ["pending_approval", "active", "suspended"],
                    "example": "active"
                },
                "created_at": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2024-01-01T00:00:00Z"
                },
                "updated_at": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2024-01-01T00:00:00Z"
                }
            },
            "required": ["id", "name", "slug", "org_type", "status", "created_at", "updated_at"]
        }
        
        # Project schema
        schemas["Project"] = {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                    "example": "550e8400-e29b-41d4-a716-446655440000"
                },
                "name": {
                    "type": "string",
                    "example": "Customer Feedback Survey"
                },
                "description": {
                    "type": "string",
                    "example": "Collect customer feedback about our products"
                },
                "slug": {
                    "type": "string",
                    "example": "customer-feedback-survey"
                },
                "owner_org_id": {
                    "type": "string",
                    "format": "uuid",
                    "example": "550e8400-e29b-41d4-a716-446655440000"
                },
                "status": {
                    "type": "string",
                    "enum": ["active", "archived"],
                    "example": "active"
                },
                "created_at": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2024-01-01T00:00:00Z"
                },
                "updated_at": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2024-01-01T00:00:00Z"
                }
            },
            "required": ["id", "name", "slug", "owner_org_id", "status", "created_at", "updated_at"]
        }
        
        # Form schema
        schemas["Form"] = {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "format": "uuid",
                    "example": "550e8400-e29b-41d4-a716-446655440000"
                },
                "name": {
                    "type": "string",
                    "example": "Customer Satisfaction Survey"
                },
                "description": {
                    "type": "string",
                    "example": "Measure customer satisfaction with our services"
                },
                "branches": {
                    "type": "object",
                    "properties": {
                        "main": {
                            "type": "string",
                            "example": "abc123def456"
                        }
                    },
                    "example": {"main": "abc123def456"}
                },
                "production_branch": {
                    "type": "string",
                    "example": "main"
                },
                "created_at": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2024-01-01T00:00:00Z"
                },
                "updated_at": {
                    "type": "string",
                    "format": "date-time",
                    "example": "2024-01-01T00:00:00Z"
                }
            },
            "required": ["id", "name", "branches", "production_branch", "created_at", "updated_at"]
        }
    
    def _add_common_parameters(self):
        """Add common parameters to the OpenAPI spec."""
        self.openapi_spec["components"]["parameters"] = {
            "page": {
                "name": "page",
                "in": "query",
                "description": "Page number for pagination",
                "schema": {
                    "type": "integer",
                    "minimum": 1,
                    "default": 1
                }
            },
            "per_page": {
                "name": "per_page",
                "in": "query",
                "description": "Number of items per page",
                "schema": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20
                }
            },
            "sort": {
                "name": "sort",
                "in": "query",
                "description": "Sort field",
                "schema": {
                    "type": "string"
                }
            },
            "order": {
                "name": "order",
                "in": "query",
                "description": "Sort order",
                "schema": {
                    "type": "string",
                    "enum": ["asc", "desc"],
                    "default": "asc"
                }
            },
            "org_id": {
                "name": "org_id",
                "in": "path",
                "description": "Organization ID",
                "required": True,
                "schema": {
                    "type": "string",
                    "format": "uuid"
                }
            },
            "project_id": {
                "name": "project_id",
                "in": "path",
                "description": "Project ID",
                "required": True,
                "schema": {
                    "type": "string",
                    "format": "uuid"
                }
            },
            "form_id": {
                "name": "form_id",
                "in": "path",
                "description": "Form ID",
                "required": True,
                "schema": {
                    "type": "string",
                    "format": "uuid"
                }
            }
        }
    
    def _add_common_responses(self):
        """Add common responses to the OpenAPI spec."""
        self.openapi_spec["components"]["responses"] = {
            "Unauthorized": {
                "description": "Authentication failed",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/ErrorResponse"
                        }
                    }
                }
            },
            "Forbidden": {
                "description": "Access denied",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/ErrorResponse"
                        }
                    }
                }
            },
            "NotFound": {
                "description": "Resource not found",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/ErrorResponse"
                        }
                    }
                }
            },
            "ValidationError": {
                "description": "Validation error",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/ErrorResponse"
                        }
                    }
                }
            },
            "RateLimitExceeded": {
                "description": "Rate limit exceeded",
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": "#/components/schemas/ErrorResponse"
                        }
                    }
                }
            }
        }
    
    def _add_tags(self):
        """Add tags to the OpenAPI spec."""
        self.openapi_spec["tags"] = [
            {
                "name": "Authentication",
                "description": "Authentication and user management"
            },
            {
                "name": "Organizations",
                "description": "Organization management"
            },
            {
                "name": "Projects",
                "description": "Project management"
            },
            {
                "name": "Forms",
                "description": "Form builder and management"
            },
            {
                "name": "Analysis",
                "description": "Data analysis and processing"
            },
            {
                "name": "Dashboards",
                "description": "Dashboard builder and visualization"
            },
            {
                "name": "Plugins",
                "description": "Plugin management"
            },
            {
                "name": "Uploads",
                "description": "File upload management"
            },
            {
                "name": "Public API",
                "description": "Public REST API endpoints"
            }
        ]
    
    def _add_paths(self):
        """Add API paths to the OpenAPI spec."""
        paths = self.openapi_spec["paths"]
        
        # Health check
        paths["/api/health"] = {
            "get": {
                "tags": ["General"],
                "summary": "Health check",
                "description": "Check if the API is running and healthy",
                "responses": {
                    "200": {
                        "description": "API is healthy",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {
                                            "type": "string",
                                            "example": "healthy"
                                        },
                                        "version": {
                                            "type": "string",
                                            "example": "1.0.0"
                                        },
                                        "services": {
                                            "type": "object",
                                            "properties": {
                                                "mongodb": {
                                                    "type": "string",
                                                    "example": "connected"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        
        # Authentication endpoints
        paths["/api/auth/register"] = {
            "post": {
                "tags": ["Authentication"],
                "summary": "Register a new user",
                "description": "Create a new user account",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "email": {
                                        "type": "string",
                                        "format": "email"
                                    },
                                    "password": {
                                        "type": "string",
                                        "minLength": 8
                                    },
                                    "full_name": {
                                        "type": "string"
                                    },
                                    "display_name": {
                                        "type": "string"
                                    }
                                },
                                "required": ["email", "password", "full_name"]
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "User created successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/User"
                                }
                            }
                        }
                    },
                    "400": {
                        "$ref": "#/components/responses/ValidationError"
                    }
                }
            }
        }
        
        paths["/api/auth/login"] = {
            "post": {
                "tags": ["Authentication"],
                "summary": "User login",
                "description": "Authenticate user and get access token",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "email": {
                                        "type": "string",
                                        "format": "email"
                                    },
                                    "password": {
                                        "type": "string"
                                    }
                                },
                                "required": ["email", "password"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Login successful",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "access_token": {
                                            "type": "string"
                                        },
                                        "refresh_token": {
                                            "type": "string"
                                        },
                                        "user": {
                                            "$ref": "#/components/schemas/User"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "401": {
                        "$ref": "#/components/responses/Unauthorized"
                    }
                }
            }
        }
        
        # Organizations endpoints
        paths["/api/organizations"] = {
            "get": {
                "tags": ["Organizations"],
                "summary": "List organizations",
                "description": "Get a list of organizations",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {"$ref": "#/components/parameters/page"},
                    {"$ref": "#/components/parameters/per_page"},
                    {"$ref": "#/components/parameters/sort"},
                    {"$ref": "#/components/parameters/order"}
                ],
                "responses": {
                    "200": {
                        "description": "List of organizations",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "data": {
                                            "type": "array",
                                            "items": {
                                                "$ref": "#/components/schemas/Organization"
                                            }
                                        },
                                        "meta": {
                                            "$ref": "#/components/schemas/PaginationMeta"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "401": {
                        "$ref": "#/components/responses/Unauthorized"
                    }
                }
            },
            "post": {
                "tags": ["Organizations"],
                "summary": "Create organization",
                "description": "Create a new organization",
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string"
                                    },
                                    "description": {
                                        "type": "string"
                                    },
                                    "org_type": {
                                        "type": "string",
                                        "enum": ["organisation", "department", "team", "unit"],
                                        "default": "organisation"
                                    }
                                },
                                "required": ["name"]
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Organization created",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Organization"
                                }
                            }
                        }
                    },
                    "400": {
                        "$ref": "#/components/responses/ValidationError"
                    }
                }
            }
        }
        
        paths["/api/organizations/{org_id}"] = {
            "get": {
                "tags": ["Organizations"],
                "summary": "Get organization",
                "description": "Get organization details",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {"$ref": "#/components/parameters/org_id"}
                ],
                "responses": {
                    "200": {
                        "description": "Organization details",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Organization"
                                }
                            }
                        }
                    },
                    "404": {
                        "$ref": "#/components/responses/NotFound"
                    }
                }
            },
            "put": {
                "tags": ["Organizations"],
                "summary": "Update organization",
                "description": "Update organization details",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {"$ref": "#/components/parameters/org_id"}
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string"
                                    },
                                    "description": {
                                        "type": "string"
                                    },
                                    "status": {
                                        "type": "string",
                                        "enum": ["active", "suspended"]
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Organization updated",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Organization"
                                }
                            }
                        }
                    },
                    "400": {
                        "$ref": "#/components/responses/ValidationError"
                    },
                    "404": {
                        "$ref": "#/components/responses/NotFound"
                    }
                }
            },
            "delete": {
                "tags": ["Organizations"],
                "summary": "Delete organization",
                "description": "Delete an organization",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {"$ref": "#/components/parameters/org_id"}
                ],
                "responses": {
                    "204": {
                        "description": "Organization deleted"
                    },
                    "404": {
                        "$ref": "#/components/responses/NotFound"
                    }
                }
            }
        }
        
        # Projects endpoints
        paths["/api/organizations/{org_id}/projects"] = {
            "get": {
                "tags": ["Projects"],
                "summary": "List projects",
                "description": "Get projects for an organization",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {"$ref": "#/components/parameters/org_id"},
                    {"$ref": "#/components/parameters/page"},
                    {"$ref": "#/components/parameters/per_page"}
                ],
                "responses": {
                    "200": {
                        "description": "List of projects",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "data": {
                                            "type": "array",
                                            "items": {
                                                "$ref": "#/components/schemas/Project"
                                            }
                                        },
                                        "meta": {
                                            "$ref": "#/components/schemas/PaginationMeta"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "401": {
                        "$ref": "#/components/responses/Unauthorized"
                    },
                    "404": {
                        "$ref": "#/components/responses/NotFound"
                    }
                }
            },
            "post": {
                "tags": ["Projects"],
                "summary": "Create project",
                "description": "Create a new project",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {"$ref": "#/components/parameters/org_id"}
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string"
                                    },
                                    "description": {
                                        "type": "string"
                                    },
                                    "shared_org_ids": {
                                        "type": "array",
                                        "items": {
                                            "type": "string",
                                            "format": "uuid"
                                        }
                                    }
                                },
                                "required": ["name"]
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Project created",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Project"
                                }
                            }
                        }
                    },
                    "400": {
                        "$ref": "#/components/responses/ValidationError"
                    }
                }
            }
        }
        
        # Forms endpoints
        paths["/api/organizations/{org_id}/projects/{project_id}/forms"] = {
            "get": {
                "tags": ["Forms"],
                "summary": "List forms",
                "description": "Get forms for a project",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {"$ref": "#/components/parameters/org_id"},
                    {"$ref": "#/components/parameters/project_id"},
                    {"$ref": "#/components/parameters/page"},
                    {"$ref": "#/components/parameters/per_page"}
                ],
                "responses": {
                    "200": {
                        "description": "List of forms",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "data": {
                                            "type": "array",
                                            "items": {
                                                "$ref": "#/components/schemas/Form"
                                            }
                                        },
                                        "meta": {
                                            "$ref": "#/components/schemas/PaginationMeta"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "401": {
                        "$ref": "#/components/responses/Unauthorized"
                    },
                    "404": {
                        "$ref": "#/components/responses/NotFound"
                    }
                }
            },
            "post": {
                "tags": ["Forms"],
                "summary": "Create form",
                "description": "Create a new form",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {"$ref": "#/components/parameters/org_id"},
                    {"$ref": "#/components/parameters/project_id"}
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {
                                        "type": "string"
                                    },
                                    "description": {
                                        "type": "string"
                                    },
                                    "template_id": {
                                        "type": "string",
                                        "format": "uuid"
                                    }
                                },
                                "required": ["name"]
                            }
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Form created",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Form"
                                }
                            }
                        }
                    },
                    "400": {
                        "$ref": "#/components/responses/ValidationError"
                    }
                }
            }
        }
        
        # Add more paths as needed...
        # This is a simplified version - in a real implementation, 
        # you would add all the endpoints from your route files


# Global instance
openapi_generator = OpenAPIDocGenerator()