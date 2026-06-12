import datetime
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Union
from bson import ObjectId
from flask import current_app

from app.extensions import mongo, redis_client
from app.engines.analysis_engine import validate_and_sort_dag, GraphCycleException
from app.services.audit_service import log_audit_event

logger = logging.getLogger(__name__)


def _now():
    """Get current UTC datetime."""
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


def _serialize_doc(doc):
    """Serialize MongoDB document for JSON response."""
    if not doc:
        return doc
    if isinstance(doc, list):
        return [_serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime.datetime):
                result[key] = value.isoformat()
            elif isinstance(value, (dict, list)):
                result[key] = _serialize_doc(value)
            else:
                result[key] = value
        return result
    return doc


def _validate_analysis_graph(graph: Dict) -> Dict:
    """Validate analysis graph structure."""
    if not isinstance(graph, dict):
        raise ValueError("Analysis graph must be a dictionary")
    
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    
    if not isinstance(nodes, list):
        raise ValueError("Graph nodes must be a list")
    
    if not isinstance(edges, list):
        raise ValueError("Graph edges must be a list")
    
    # Validate nodes
    node_ids = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("Each node must be a dictionary")
        
        if "id" not in node:
            raise ValueError("Each node must have an id")
        
        node_id = node["id"]
        if not isinstance(node_id, str):
            raise ValueError("Node ID must be a string")
        
        if node_id in node_ids:
            raise ValueError(f"Duplicate node ID: {node_id}")
        node_ids.add(node_id)
        
        # Validate node type
        if "type" not in node:
            raise ValueError(f"Node {node_id} must have a type")
        
        # Validate node position
        position = node.get("position", {})
        if not isinstance(position, dict):
            raise ValueError(f"Node {node_id} position must be a dictionary")
        
        # Validate node size
        size = node.get("size", {})
        if not isinstance(size, dict):
            raise ValueError(f"Node {node_id} size must be a dictionary")
    
    # Validate edges
    edge_ids = set()
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("Each edge must be a dictionary")
        
        if "id" not in edge:
            edge["id"] = str(uuid.uuid4())
        
        edge_id = edge["id"]
        if edge_id in edge_ids:
            raise ValueError(f"Duplicate edge ID: {edge_id}")
        edge_ids.add(edge_id)
        
        from_node = edge.get("from_node")
        to_node = edge.get("to_node")
        
        if not from_node or not to_node:
            raise ValueError("Edge must have from_node and to_node")
        
        if from_node not in node_ids:
            raise ValueError(f"Edge from_node {from_node} does not exist")
        
        if to_node not in node_ids:
            raise ValueError(f"Edge to_node {to_node} does not exist")
    
    # Validate DAG (no cycles)
    try:
        validate_and_sort_dag(graph)
    except GraphCycleException as e:
        raise ValueError(f"Graph contains cycles: {str(e)}")
    
    return graph


def _check_analysis_permissions(user_id: str, org_id: str, action: str, context: Dict = None) -> bool:
    """Check if user has permission to perform action on analysis."""
    # This would integrate with auth_service.py for ABAC evaluation
    # For now, basic implementation
    if context and context.get("system_role") == "super_admin":
        return True
    
    # Check org membership
    membership = mongo.db.org_memberships.find_one({
        "user_id": _oid(user_id),
        "org_id": _oid(org_id),
        "status": "active",
        "is_deleted": False
    })
    
    if not membership:
        return False
    
    role = membership.get("role")
    if action in ["create", "edit", "delete", "execute"] and role not in ["org_admin", "org_editor", "org_analyst"]:
        return False
    if action == "view" and role not in ["org_admin", "org_editor", "org_analyst", "org_viewer"]:
        return False
    
    return True


class AnalysisService:
    """Service layer for analysis operations including DAG execution."""
    
    def create_analysis(self, data: Dict, author_id: str, context: Dict = None) -> Dict:
        """Create a new analysis."""
        try:
            # Validate required fields
            if not data.get("name"):
                raise ValueError("Analysis name is required")
            
            if not data.get("project_id"):
                raise ValueError("Project ID is required")
            
            # Get project
            project_id = data["project_id"]
            project = mongo.db.projects.find_one({
                "_id": _oid(project_id),
                "is_deleted": False
            })
            
            if not project:
                raise ValueError("Project not found")
            
            # Check permissions
            if not _check_analysis_permissions(author_id, project["org_id"], "create", context):
                raise PermissionError("Insufficient permissions to create analysis")
            
            # Validate graph
            graph = data.get("graph", {})
            graph = _validate_analysis_graph(graph)
            
            # Validate execution modes
            execution_modes = data.get("execution_modes", ["on_demand"])
            valid_modes = ["on_demand", "reactive", "scheduled"]
            for mode in execution_modes:
                if mode not in valid_modes:
                    raise ValueError(f"Invalid execution mode: {mode}")
            
            # Validate schedule if scheduled mode is enabled
            schedule = data.get("schedule")
            if "scheduled" in execution_modes and not schedule:
                raise ValueError("Schedule is required for scheduled execution")
            
            # Create analysis document
            analysis_doc = {
                "org_id": project["org_id"],
                "project_id": _oid(project_id),
                "name": data["name"].strip(),
                "description": data.get("description", "").strip(),
                "linked_form_ids": [_oid(fid) for fid in data.get("linked_form_ids", []) if fid],
                "execution_modes": execution_modes,
                "schedule": schedule,
                "reactive_debounce_ms": data.get("reactive_debounce_ms", 1000),
                "graph": graph,
                "last_run_id": None,
                "status": "idle",
                "created_at": _now(),
                "updated_at": _now(),
                "created_by": _oid(author_id),
                "is_deleted": False,
                "deleted_at": None
            }
            
            # Check for name uniqueness
            existing = mongo.db.analyses.find_one({
                "project_id": _oid(project_id),
                "name": {"$regex": f"^{analysis_doc['name']}$", "$options": "i"},
                "is_deleted": False
            })
            
            if existing:
                raise ValueError("Analysis with this name already exists in the project")
            
            # Insert analysis
            result = mongo.db.analyses.insert_one(analysis_doc)
            analysis_id = result.inserted_id
            
            # Log audit event
            log_audit_event(
                org_id=project["org_id"],
                project_id=project_id,
                entity_type="analysis",
                entity_id=analysis_id,
                action="created",
                actor_id=author_id,
                before={},
                after={"name": analysis_doc["name"], "execution_modes": execution_modes}
            )
            
            return _serialize_doc({
                **analysis_doc,
                "_id": analysis_id
            })
            
        except Exception as e:
            logger.error(f"Error creating analysis: {str(e)}")
            raise
    
    def get_analysis(self, analysis_id: str, user_id: str = None, context: Dict = None) -> Dict:
        """Get analysis by ID."""
        try:
            analysis = mongo.db.analyses.find_one({
                "_id": _oid(analysis_id),
                "is_deleted": False
            })
            
            if not analysis:
                raise ValueError("Analysis not found")
            
            # Check permissions if user_id provided
            if user_id and not _check_analysis_permissions(user_id, analysis["org_id"], "view", context):
                raise PermissionError("Insufficient permissions to view analysis")
            
            # Get last run info
            last_run_id = analysis.get("last_run_id")
            last_run = None
            if last_run_id:
                last_run = mongo.db.analysis_runs.find_one({
                    "_id": _oid(last_run_id)
                })
            
            return _serialize_doc({
                **analysis,
                "last_run": last_run
            })
            
        except Exception as e:
            logger.error(f"Error getting analysis {analysis_id}: {str(e)}")
            raise
    
    def list_analyses(self, project_id: str, user_id: str = None, page: int = 1, 
                     per_page: int = 20, search: str = None, context: Dict = None) -> Dict:
        """List analyses in a project with pagination."""
        try:
            # Get project
            project = mongo.db.projects.find_one({
                "_id": _oid(project_id),
                "is_deleted": False
            })
            
            if not project:
                raise ValueError("Project not found")
            
            # Build query
            query = {
                "project_id": _oid(project_id),
                "is_deleted": False
            }
            
            if search:
                query["name"] = {"$regex": search, "$options": "i"}
            
            # Get total count
            total = mongo.db.analyses.count_documents(query)
            
            # Get analyses with pagination
            analyses = list(mongo.db.analyses.find(query)
                          .sort("created_at", -1)
                          .skip((page - 1) * per_page)
                          .limit(per_page))
            
            # Filter by permissions if user_id provided
            if user_id:
                analyses = [a for a in analyses if _check_analysis_permissions(user_id, a["org_id"], "view", context)]
            
            # Get last run info for each analysis
            for analysis in analyses:
                last_run_id = analysis.get("last_run_id")
                if last_run_id:
                    last_run = mongo.db.analysis_runs.find_one({
                        "_id": _oid(last_run_id)
                    })
                    analysis["last_run"] = last_run
            
            return {
                "analyses": _serialize_doc(analyses),
                "pagination": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "pages": (total + per_page - 1) // per_page
                }
            }
            
        except Exception as e:
            logger.error(f"Error listing analyses: {str(e)}")
            raise
    
    def update_analysis(self, analysis_id: str, data: Dict, user_id: str, context: Dict = None) -> Dict:
        """Update analysis metadata and graph."""
        try:
            # Get analysis
            analysis = mongo.db.analyses.find_one({
                "_id": _oid(analysis_id),
                "is_deleted": False
            })
            
            if not analysis:
                raise ValueError("Analysis not found")
            
            # Check permissions
            if not _check_analysis_permissions(user_id, analysis["org_id"], "edit", context):
                raise PermissionError("Insufficient permissions to edit analysis")
            
            # Build update data
            update_data = {}
            
            if "name" in data:
                name = data["name"].strip()
                if not name:
                    raise ValueError("Analysis name cannot be empty")
                
                # Check uniqueness
                existing = mongo.db.analyses.find_one({
                    "project_id": analysis["project_id"],
                    "name": {"$regex": f"^{name}$", "$options": "i"},
                    "_id": {"$ne": analysis["_id"]},
                    "is_deleted": False
                })
                
                if existing:
                    raise ValueError("Analysis with this name already exists")
                
                update_data["name"] = name
            
            if "description" in data:
                update_data["description"] = data["description"].strip()
            
            if "graph" in data:
                graph = _validate_analysis_graph(data["graph"])
                update_data["graph"] = graph
            
            if "execution_modes" in data:
                execution_modes = data["execution_modes"]
                valid_modes = ["on_demand", "reactive", "scheduled"]
                for mode in execution_modes:
                    if mode not in valid_modes:
                        raise ValueError(f"Invalid execution mode: {mode}")
                update_data["execution_modes"] = execution_modes
            
            if "schedule" in data:
                if "scheduled" in data.get("execution_modes", analysis.get("execution_modes", [])):
                    if not data["schedule"]:
                        raise ValueError("Schedule is required for scheduled execution")
                    update_data["schedule"] = data["schedule"]
            
            if "reactive_debounce_ms" in data:
                debounce = data["reactive_debounce_ms"]
                if not isinstance(debounce, int) or debounce < 0:
                    raise ValueError("Reactive debounce must be a positive integer")
                update_data["reactive_debounce_ms"] = debounce
            
            if update_data:
                update_data["updated_at"] = _now()
                
                # Update analysis
                mongo.db.analyses.update_one(
                    {"_id": analysis["_id"]},
                    {"$set": update_data}
                )
                
                # Log audit event
                log_audit_event(
                    org_id=analysis["org_id"],
                    project_id=analysis["project_id"],
                    entity_type="analysis",
                    entity_id=analysis["_id"],
                    action="updated",
                    actor_id=user_id,
                    before={"name": analysis["name"]},
                    after=update_data
                )
            
            return self.get_analysis(analysis_id, user_id, context)
            
        except Exception as e:
            logger.error(f"Error updating analysis {analysis_id}: {str(e)}")
            raise
    
    def delete_analysis(self, analysis_id: str, user_id: str, context: Dict = None) -> bool:
        """Soft delete an analysis."""
        try:
            # Get analysis
            analysis = mongo.db.analyses.find_one({
                "_id": _oid(analysis_id),
                "is_deleted": False
            })
            
            if not analysis:
                raise ValueError("Analysis not found")
            
            # Check permissions
            if not _check_analysis_permissions(user_id, analysis["org_id"], "delete", context):
                raise PermissionError("Insufficient permissions to delete analysis")
            
            # Soft delete
            mongo.db.analyses.update_one(
                {"_id": analysis["_id"]},
                {
                    "$set": {
                        "is_deleted": True,
                        "deleted_at": _now(),
                        "updated_at": _now()
                    }
                }
            )
            
            # Log audit event
            log_audit_event(
                org_id=analysis["org_id"],
                project_id=analysis["project_id"],
                entity_type="analysis",
                entity_id=analysis["_id"],
                action="deleted",
                actor_id=user_id,
                before={"name": analysis["name"]},
                after={}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting analysis {analysis_id}: {str(e)}")
            raise
    
    def execute_analysis(self, analysis_id: str, user_id: str, trigger: str = "on_demand", 
                        context: Dict = None) -> Dict:
        """Execute an analysis and return run ID."""
        try:
            # Get analysis
            analysis = mongo.db.analyses.find_one({
                "_id": _oid(analysis_id),
                "is_deleted": False
            })
            
            if not analysis:
                raise ValueError("Analysis not found")
            
            # Check permissions
            if not _check_analysis_permissions(user_id, analysis["org_id"], "execute", context):
                raise PermissionError("Insufficient permissions to execute analysis")
            
            # Check if trigger mode is allowed
            execution_modes = analysis.get("execution_modes", [])
            if trigger not in execution_modes and trigger != "manual":
                raise ValueError(f"Trigger mode '{trigger}' is not allowed for this analysis")
            
            # Create analysis run
            run_doc = {
                "analysis_id": analysis["_id"],
                "org_id": analysis["org_id"],
                "trigger": trigger,
                "triggered_by": _oid(user_id),
                "status": "queued",
                "started_at": None,
                "completed_at": None,
                "celery_task_id": None,
                "node_statuses": {},
                "error_summary": None,
                "result_ids": {},
                "created_at": _now()
            }
            
            result = mongo.db.analysis_runs.insert_one(run_doc)
            run_id = result.inserted_id
            
            # Update analysis status
            mongo.db.analyses.update_one(
                {"_id": analysis["_id"]},
                {
                    "$set": {
                        "status": "running",
                        "last_run_id": run_id,
                        "updated_at": _now()
                    }
                }
            )
            
            # Log audit event
            log_audit_event(
                org_id=analysis["org_id"],
                project_id=analysis["project_id"],
                entity_type="analysis",
                entity_id=analysis["_id"],
                action="executed",
                actor_id=user_id,
                before={},
                after={"trigger": trigger, "run_id": str(run_id)}
            )
            
            # Here you would typically queue a Celery task
            # For now, we'll return the run ID
            return _serialize_doc({
                "run_id": str(run_id),
                "status": "queued",
                "analysis_id": str(analysis["_id"])
            })
            
        except Exception as e:
            logger.error(f"Error executing analysis {analysis_id}: {str(e)}")
            raise
    
    def get_analysis_run(self, run_id: str, user_id: str = None, context: Dict = None) -> Dict:
        """Get analysis run details."""
        try:
            run = mongo.db.analysis_runs.find_one({
                "_id": _oid(run_id)
            })
            
            if not run:
                raise ValueError("Analysis run not found")
            
            # Get analysis to check permissions
            analysis = mongo.db.analyses.find_one({
                "_id": run["analysis_id"],
                "is_deleted": False
            })
            
            if not analysis:
                raise ValueError("Associated analysis not found")
            
            # Check permissions if user_id provided
            if user_id and not _check_analysis_permissions(user_id, analysis["org_id"], "view", context):
                raise PermissionError("Insufficient permissions to view analysis run")
            
            # Get results for this run
            results = list(mongo.db.analysis_results.find({
                "run_id": run["_id"]
            }))
            
            return _serialize_doc({
                **run,
                "results": results
            })
            
        except Exception as e:
            logger.error(f"Error getting analysis run {run_id}: {str(e)}")
            raise
    
    def list_analysis_runs(self, analysis_id: str, user_id: str = None, page: int = 1,
                          per_page: int = 20, context: Dict = None) -> Dict:
        """List runs for an analysis."""
        try:
            # Get analysis
            analysis = mongo.db.analyses.find_one({
                "_id": _oid(analysis_id),
                "is_deleted": False
            })
            
            if not analysis:
                raise ValueError("Analysis not found")
            
            # Check permissions if user_id provided
            if user_id and not _check_analysis_permissions(user_id, analysis["org_id"], "view", context):
                raise PermissionError("Insufficient permissions to view analysis runs")
            
            # Get total count
            total = mongo.db.analysis_runs.count_documents({
                "analysis_id": analysis["_id"]
            })
            
            # Get runs with pagination
            runs = list(mongo.db.analysis_runs.find({
                "analysis_id": analysis["_id"]
            }).sort("created_at", -1)
              .skip((page - 1) * per_page)
              .limit(per_page))
            
            return {
                "runs": _serialize_doc(runs),
                "pagination": {
                    "total": total,
                    "page": page,
                    "per_page": per_page,
                    "pages": (total + per_page - 1) // per_page
                }
            }
            
        except Exception as e:
            logger.error(f"Error listing analysis runs for {analysis_id}: {str(e)}")
            raise
    
    def get_analysis_results(self, analysis_id: str, node_id: str, user_id: str = None,
                           context: Dict = None) -> Dict:
        """Get latest results for a specific node in an analysis."""
        try:
            # Get analysis
            analysis = mongo.db.analyses.find_one({
                "_id": _oid(analysis_id),
                "is_deleted": False
            })
            
            if not analysis:
                raise ValueError("Analysis not found")
            
            # Check permissions if user_id provided
            if user_id and not _check_analysis_permissions(user_id, analysis["org_id"], "view", context):
                raise PermissionError("Insufficient permissions to view analysis results")
            
            # Get latest run
            latest_run = mongo.db.analysis_runs.find_one({
                "analysis_id": analysis["_id"],
                "status": "completed"
            }, sort=[("created_at", -1)])
            
            if not latest_run:
                raise ValueError("No completed runs found for this analysis")
            
            # Get result for the specific node
            result = mongo.db.analysis_results.find_one({
                "run_id": latest_run["_id"],
                "node_id": node_id
            })
            
            if not result:
                raise ValueError(f"No results found for node {node_id}")
            
            return _serialize_doc(result)
            
        except Exception as e:
            logger.error(f"Error getting analysis results for {analysis_id}/{node_id}: {str(e)}")
            raise


# Create service instance
analysis_service = AnalysisService()