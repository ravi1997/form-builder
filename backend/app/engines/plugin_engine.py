import ast
import importlib
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional, Union
from bson import ObjectId
from flask import current_app

from app.extensions import mongo, redis_client

logger = logging.getLogger(__name__)


def _now():
    """Get current UTC datetime."""
    import datetime
    return datetime.datetime.utcnow()


def _oid(value):
    """Convert value to ObjectId if valid, otherwise return as-is."""
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    if ObjectId.is_valid(str(value)):
        return ObjectId(str(value))
    return value


class PluginSandbox:
    """Sandboxed environment for plugin execution."""
    
    def __init__(self, plugin_id: str, plugin_version: str, org_id: ObjectId = None):
        self.plugin_id = plugin_id
        self.plugin_version = plugin_version
        self.org_id = org_id
        self.plugin_dir = None
        self.handler_path = None
        self.manifest = None
        self.permissions = []
        
        # Load plugin info
        self._load_plugin_info()
    
    def _load_plugin_info(self):
        """Load plugin information from database."""
        # Get plugin
        plugin = mongo.db.plugins.find_one({
            "plugin_id": self.plugin_id,
            "is_deleted": False
        })
        
        if not plugin:
            raise ValueError(f"Plugin {self.plugin_id} not found")
        
        # Get plugin version
        version = mongo.db.plugin_versions.find_one({
            "plugin_id": plugin["_id"],
            "version": self.plugin_version,
            "status": "active"
        })
        
        if not version:
            raise ValueError(f"Plugin version {self.plugin_version} not found")
        
        self.manifest = version["manifest"]
        self.permissions = self.manifest.get("permissions", [])
        self.plugin_dir = version["files_path"]
        
        # Get handler path
        backend = self.manifest.get("backend", {})
        self.handler_path = backend.get("handler")
        
        if not self.handler_path or not os.path.exists(os.path.join(self.plugin_dir, self.handler_path)):
            raise ValueError(f"Plugin handler not found: {self.handler_path}")
    
    def _create_sandbox_config(self) -> Dict:
        """Create sandbox configuration for plugin."""
        # Get org-specific config if needed
        org_config = {}
        if self.org_id:
            org = mongo.db.organisations.find_one({
                "_id": self.org_id,
                "is_deleted": False
            })
            if org:
                org_config = {
                    "org_id": str(org["_id"]),
                    "org_name": org.get("name", "")
                }
        
        # Create sandbox config
        config = {
            "plugin_id": self.plugin_id,
            "plugin_version": self.plugin_version,
            "permissions": self.permissions,
            "org_config": org_config,
            "database_config": {
                "uri": current_app.config.get("MONGODB_URI"),
                "database_name": current_app.config.get("MONGODB_DB", "formbuilder")
            },
            "redis_config": {
                "url": current_app.config.get("REDIS_URL")
            }
        }
        
        return config
    
    def _create_restricted_environment(self) -> Dict:
        """Create restricted Python environment for plugin."""
        # Safe builtins
        safe_builtins = {
            'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
            'chr', 'complex', 'dict', 'dir', 'divmod', 'enumerate', 'filter',
            'float', 'format', 'frozenset', 'hash', 'hex', 'int', 'iter',
            'len', 'list', 'map', 'max', 'min', 'next', 'oct', 'ord', 'pow',
            'print', 'range', 'repr', 'reversed', 'round', 'set', 'slice',
            'sorted', 'str', 'sum', 'tuple', 'zip', '__import__'
        }
        
        # Add datetime if permission allows
        if 'filesystem_read' in self.permissions:
            safe_builtins.add('datetime')
        
        # Create restricted environment
        restricted_env = {
            '__builtins__': {name: __builtins__[name] for name in safe_builtins if name in __builtins__},
            '__name__': '__plugin__',
            '__file__': os.path.join(self.plugin_dir, self.handler_path),
            '__doc__': None,
            '__package__': None
        }
        
        return restricted_env
    
    def execute_handler(self, method_name: str, *args, **kwargs) -> Any:
        """Execute plugin handler method in sandbox."""
        try:
            # Create sandbox config
            config = self._create_sandbox_config()
            
            # Create temporary file for execution
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                # Write plugin wrapper code
                wrapper_code = self._generate_wrapper_code(method_name, config, args, kwargs)
                f.write(wrapper_code)
                temp_file = f.name
            
            try:
                # Execute in subprocess
                result = subprocess.run(
                    [sys.executable, temp_file],
                    capture_output=True,
                    text=True,
                    timeout=30  # 30 second timeout
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr or result.stdout
                    raise RuntimeError(f"Plugin execution failed: {error_msg}")
                
                # Parse result
                try:
                    output = json.loads(result.stdout)
                except json.JSONDecodeError:
                    raise RuntimeError(f"Plugin returned invalid JSON: {result.stdout}")
                
                if output.get("error"):
                    raise RuntimeError(output["error"])
                
                return output.get("result")
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file)
                except:
                    pass
        
        except subprocess.TimeoutExpired:
            raise RuntimeError("Plugin execution timed out")
        except Exception as e:
            logger.error(f"Error executing plugin {self.plugin_id}.{method_name}: {str(e)}")
            raise
    
    def _generate_wrapper_code(self, method_name: str, config: Dict, args: tuple, kwargs: dict) -> str:
        """Generate wrapper code for plugin execution."""
        import json
        
        wrapper_code = f'''
import json
import sys
import os
import traceback

# Add plugin directory to Python path
plugin_dir = {json.dumps(self.plugin_dir)}
sys.path.insert(0, plugin_dir)

# Load config
config = {json.dumps(config)}

# Create restricted environment
def create_restricted_env():
    import builtins
    
    # Safe builtins
    safe_names = {{
        'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
        'chr', 'complex', 'dict', 'dir', 'divmod', 'enumerate', 'filter',
        'float', 'format', 'frozenset', 'hash', 'hex', 'int', 'iter',
        'len', 'list', 'map', 'max', 'min', 'next', 'oct', 'ord', 'pow',
        'print', 'range', 'repr', 'reversed', 'round', 'set', 'slice',
        'sorted', 'str', 'sum', 'tuple', 'zip', '__import__'
    }}
    
    # Add datetime if permission allows
    permissions = config.get("permissions", [])
    if 'filesystem_read' in permissions:
        safe_names.add('datetime')
    
    restricted_builtins = {{name: getattr(builtins, name) for name in safe_names if hasattr(builtins, name)}}
    
    return {{
        '__builtins__': restricted_builtins,
        '__name__': '__plugin__',
        '__file__': os.path.join(plugin_dir, {json.dumps(self.handler_path)}),
        '__doc__': None,
        '__package__': None
    }}

# Plugin SDK
class PluginSDK:
    def __init__(self, config):
        self.config = config
        self.org_id = config.get("org_config", {}).get("org_id")
        
    def get_database_client(self):
        """Get filtered database client for plugin."""
        from pymongo import MongoClient
        from bson.objectid import ObjectId
        
        if "db_read_own_org" not in self.config.get("permissions", []):
            raise PermissionError("Plugin does not have database read permission")
        
        # Create filtered client
        client = MongoClient(self.config["database_config"]["uri"])
        db = client[self.config["database_config"]["database_name"]]
        
        # Create filtered collection wrapper
        class FilteredCollection:
            def __init__(self, collection, org_id):
                self._collection = collection
                self._org_id = org_id
            
            def find(self, *args, **kwargs):
                # Always filter by org_id
                if "filter" in kwargs:
                    kwargs["filter"]["org_id"] = ObjectId(self._org_id)
                else:
                    kwargs["filter"] = {{"org_id": ObjectId(self._org_id)}}
                return self._collection.find(*args, **kwargs)
            
            def find_one(self, *args, **kwargs):
                # Always filter by org_id
                if "filter" in kwargs:
                    kwargs["filter"]["org_id"] = ObjectId(self._org_id)
                else:
                    kwargs["filter"] = {{"org_id": ObjectId(self._org_id)}}
                return self._collection.find_one(*args, **kwargs)
            
            def __getattr__(self, name):
                return getattr(self._collection, name)
        
        # Wrap collections
        class FilteredDatabase:
            def __init__(self, db, org_id):
                self._db = db
                self._org_id = org_id
            
            def __getattr__(self, name):
                collection = self._db[name]
                return FilteredCollection(collection, self._org_id)
        
        return FilteredDatabase(db, self.org_id)
    
    def make_http_request(self, url, method="GET", headers=None, data=None, timeout=10):
        """Make HTTP request if permission allows."""
        if "internet_access" not in self.config.get("permissions", []):
            raise PermissionError("Plugin does not have internet access permission")
        
        import requests
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers or {},
                json=data,
                timeout=timeout
            )
            return {{
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "content": response.text,
                "json": response.json() if response.headers.get("content-type", "").startswith("application/json") else None
            }}
        except Exception as e:
            raise RuntimeError(f"HTTP request failed: {{str(e)}}")
    
    def read_file(self, path):
        """Read file if permission allows."""
        if "filesystem_read" not in self.config.get("permissions", []):
            raise PermissionError("Plugin does not have filesystem read permission")
        
        # Only allow reading from plugin directory
        full_path = os.path.join(plugin_dir, path)
        if not full_path.startswith(plugin_dir):
            raise PermissionError("Cannot read files outside plugin directory")
        
        try:
            with open(full_path, 'r') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Failed to read file: {{str(e)}}")
    
    def write_file(self, path, content):
        """Write file if permission allows."""
        if "filesystem_write" not in self.config.get("permissions", []):
            raise PermissionError("Plugin does not have filesystem write permission")
        
        # Only allow writing to plugin output directory
        output_dir = os.path.join(plugin_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        full_path = os.path.join(output_dir, path)
        if not full_path.startswith(output_dir):
            raise PermissionError("Cannot write files outside output directory")
        
        try:
            with open(full_path, 'w') as f:
                f.write(content)
        except Exception as e:
            raise RuntimeError(f"Failed to write file: {{str(e)}}")

# Main execution
try:
    # Create SDK instance
    sdk = PluginSDK(config)
    
    # Import and execute plugin handler
    handler_module = __import__({json.dumps(self.handler_path.replace('.py', '').replace('/', '.'))})
    
    # Get handler class
    handler_class = getattr(handler_module, 'PluginHandler')
    
    # Create handler instance
    handler = handler_class(sdk)
    
    # Execute method
    args = {json.dumps(list(args))}
    kwargs = {json.dumps(kwargs)}
    
    result = getattr(handler, {json.dumps(method_name)})(*args, **kwargs)
    
    # Output result
    print(json.dumps({{"result": result}}))
    
except Exception as e:
    error_msg = str(e)
    error_trace = traceback.format_exc()
    print(json.dumps({{"error": error_msg, "trace": error_trace}}))
    sys.exit(1)
'''
        
        return wrapper_code


class PluginEngine:
    """Main plugin engine for loading and executing plugins."""
    
    def __init__(self):
        self.loaded_plugins = {}
        self.plugin_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def load_plugin(self, plugin_id: str, plugin_version: str, org_id: ObjectId = None) -> PluginSandbox:
        """Load a plugin into the engine."""
        cache_key = f"{plugin_id}:{plugin_version}:{org_id}"
        
        # Check cache
        if cache_key in self.plugin_cache:
            cached_time, cached_plugin = self.plugin_cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return cached_plugin
        
        # Create new sandbox
        sandbox = PluginSandbox(plugin_id, plugin_version, org_id)
        
        # Cache it
        self.plugin_cache[cache_key] = (time.time(), sandbox)
        
        return sandbox
    
    def execute_plugin_method(self, plugin_id: str, plugin_version: str, method_name: str,
                            org_id: ObjectId = None, *args, **kwargs) -> Any:
        """Execute a method on a plugin."""
        try:
            # Load plugin
            sandbox = self.load_plugin(plugin_id, plugin_version, org_id)
            
            # Execute method
            result = sandbox.execute_handler(method_name, *args, **kwargs)
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing plugin method {plugin_id}.{method_name}: {str(e)}")
            raise
    
    def get_plugin_components(self, concept_id: str, component_type: str = None) -> List[Dict]:
        """Get all available components for a concept."""
        try:
            query = {
                "concept_id": concept_id,
                "status": "active"
            }
            
            if component_type:
                query["component_type"] = component_type
            
            components = list(mongo.db.component_schemas.find(query))
            
            # Enrich with plugin info
            for component in components:
                plugin = mongo.db.plugins.find_one({
                    "_id": component["plugin_id"],
                    "is_deleted": False
                })
                if plugin:
                    component["plugin_name"] = plugin["name"]
                    component["plugin_version"] = component["plugin_version"]
            
            return components
            
        except Exception as e:
            logger.error(f"Error getting plugin components for {concept_id}: {str(e)}")
            raise
    
    def validate_plugin_dependencies(self, plugin_manifest: Dict) -> bool:
        """Validate plugin dependencies."""
        # Check platform version compatibility
        min_platform_version = plugin_manifest.get("min_platform_version")
        if min_platform_version:
            current_version = current_app.config.get("PLATFORM_VERSION", "1.0.0")
            if self._compare_versions(current_version, min_platform_version) < 0:
                raise ValueError(f"Plugin requires platform version {min_platform_version} or higher")
        
        # Check for conflicting plugins
        plugin_id = plugin_manifest["plugin_id"]
        conflicts = plugin_manifest.get("conflicts", [])
        
        for conflict_plugin_id in conflicts:
            conflict = mongo.db.plugins.find_one({
                "plugin_id": conflict_plugin_id,
                "status": "active",
                "is_deleted": False
            })
            if conflict:
                raise ValueError(f"Plugin conflicts with installed plugin: {conflict_plugin_id}")
        
        return True
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """Compare two semantic version strings."""
        def parse_version(v):
            return [int(part) for part in v.split('.')]
        
        v1_parts = parse_version(version1)
        v2_parts = parse_version(version2)
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1_part = v1_parts[i] if i < len(v1_parts) else 0
            v2_part = v2_parts[i] if i < len(v2_parts) else 0
            
            if v1_part < v2_part:
                return -1
            elif v1_part > v2_part:
                return 1
        
        return 0
    
    def get_plugin_status(self, plugin_id: str) -> Dict:
        """Get plugin status information."""
        try:
            plugin = mongo.db.plugins.find_one({
                "plugin_id": plugin_id,
                "is_deleted": False
            })
            
            if not plugin:
                return {"status": "not_found"}
            
            # Get latest version
            latest_version = mongo.db.plugin_versions.find_one({
                "plugin_id": plugin["_id"],
                "status": "active"
            }, sort=[("released_at", -1)])
            
            # Get active components
            active_components = mongo.db.component_schemas.count_documents({
                "plugin_id": plugin["_id"],
                "status": "active"
            })
            
            return {
                "status": plugin["status"],
                "name": plugin["name"],
                "version": latest_version["version"] if latest_version else None,
                "active_components": active_components,
                "permissions": plugin["permissions"],
                "concept_targets": plugin["concept_targets"]
            }
            
        except Exception as e:
            logger.error(f"Error getting plugin status for {plugin_id}: {str(e)}")
            raise


# Create engine instance
plugin_engine = PluginEngine()