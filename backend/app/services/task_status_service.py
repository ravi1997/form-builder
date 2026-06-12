"""
Task Status Service
Service for tracking and monitoring Celery task execution status.
"""

import datetime
from typing import Dict, Any, Optional, List
from bson import ObjectId

from app.extensions import mongo


class TaskStatusService:
    """Service for managing task execution status and monitoring."""
    
    @staticmethod
    def create_task_record(task_name: str, task_id: str, args: List = None, 
                          kwargs: Dict = None, user_id: str = None,
                          org_id: str = None) -> str:
        """
        Create a new task status record.
        
        Args:
            task_name: Name of the Celery task
            task_id: Celery task ID
            args: Task arguments
            kwargs: Task keyword arguments
            user_id: User who initiated the task
            org_id: Organization ID for the task
            
        Returns:
            ID of the created task record
        """
        task_record = {
            "task_name": task_name,
            "celery_task_id": task_id,
            "args": args or [],
            "kwargs": kwargs or {},
            "user_id": ObjectId(user_id) if user_id else None,
            "org_id": ObjectId(org_id) if org_id else None,
            "status": "pending",
            "progress": 0,
            "created_at": datetime.datetime.utcnow(),
            "started_at": None,
            "completed_at": None,
            "error": None,
            "result": None,
            "metadata": {}
        }
        
        result = mongo.db.task_status.insert_one(task_record)
        return str(result.inserted_id)
    
    @staticmethod
    def update_task_status(task_record_id: str, status: str, progress: int = None,
                          error: str = None, result: Dict = None,
                          metadata: Dict = None) -> bool:
        """
        Update task status record.
        
        Args:
            task_record_id: ID of the task record
            status: New status (pending, running, completed, failed)
            progress: Progress percentage (0-100)
            error: Error message if failed
            result: Task result data
            metadata: Additional metadata
            
        Returns:
            True if update was successful
        """
        try:
            task_oid = ObjectId(task_record_id)
            
            update_data = {
                "status": status,
                "updated_at": datetime.datetime.utcnow()
            }
            
            if progress is not None:
                update_data["progress"] = progress
            
            if error is not None:
                update_data["error"] = error
            
            if result is not None:
                update_data["result"] = result
            
            if metadata is not None:
                update_data["metadata"] = metadata
            
            # Set timestamps based on status
            if status == "running":
                update_data["started_at"] = datetime.datetime.utcnow()
            elif status in ["completed", "failed"]:
                update_data["completed_at"] = datetime.datetime.utcnow()
            
            result = mongo.db.task_status.update_one(
                {"_id": task_oid},
                {"$set": update_data}
            )
            
            return result.modified_count > 0
            
        except Exception:
            return False
    
    @staticmethod
    def get_task_status(task_record_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status by record ID.
        
        Args:
            task_record_id: ID of the task record
            
        Returns:
            Task status record or None if not found
        """
        try:
            task_oid = ObjectId(task_record_id)
            return mongo.db.task_status.find_one({"_id": task_oid})
        except Exception:
            return None
    
    @staticmethod
    def get_user_tasks(user_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get tasks for a specific user.
        
        Args:
            user_id: User ID
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of task status records
        """
        try:
            user_oid = ObjectId(user_id)
            cursor = mongo.db.task_status.find(
                {"user_id": user_oid}
            ).sort("created_at", -1).skip(offset).limit(limit)
            
            return list(cursor)
        except Exception:
            return []
    
    @staticmethod
    def get_org_tasks(org_id: str, status: str = None, limit: int = 50, 
                     offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get tasks for a specific organization.
        
        Args:
            org_id: Organization ID
            status: Filter by status (optional)
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of task status records
        """
        try:
            org_oid = ObjectId(org_id)
            query = {"org_id": org_oid}
            
            if status:
                query["status"] = status
            
            cursor = mongo.db.task_status.find(query).sort(
                "created_at", -1
            ).skip(offset).limit(limit)
            
            return list(cursor)
        except Exception:
            return []
    
    @staticmethod
    def get_running_tasks() -> List[Dict[str, Any]]:
        """
        Get all currently running tasks.
        
        Returns:
            List of running task records
        """
        try:
            cursor = mongo.db.task_status.find(
                {"status": "running"}
            ).sort("started_at", 1)
            
            return list(cursor)
        except Exception:
            return []
    
    @staticmethod
    def get_failed_tasks(since_hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get failed tasks within the specified time period.
        
        Args:
            since_hours: Number of hours to look back
            
        Returns:
            List of failed task records
        """
        try:
            since_time = datetime.datetime.utcnow() - datetime.timedelta(hours=since_hours)
            
            cursor = mongo.db.task_status.find({
                "status": "failed",
                "completed_at": {"$gte": since_time}
            }).sort("completed_at", -1)
            
            return list(cursor)
        except Exception:
            return []
    
    @staticmethod
    def get_task_statistics(org_id: str = None) -> Dict[str, Any]:
        """
        Get task execution statistics.
        
        Args:
            org_id: Organization ID (optional)
            
        Returns:
            Dictionary with task statistics
        """
        try:
            match_query = {}
            if org_id:
                match_query["org_id"] = ObjectId(org_id)
            
            pipeline = [
                {"$match": match_query},
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1},
                        "avg_duration": {
                            "$avg": {
                                "$subtract": [
                                    "$completed_at", "$started_at"
                                ]
                            }
                        }
                    }
                }
            ]
            
            results = list(mongo.db.task_status.aggregate(pipeline))
            
            stats = {
                "total": 0,
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "avg_duration_seconds": 0
            }
            
            for result in results:
                status = result["_id"]
                count = result["count"]
                stats["total"] += count
                
                if status in stats:
                    stats[status] = count
                
                if status == "completed" and result["avg_duration"]:
                    # Convert milliseconds to seconds
                    stats["avg_duration_seconds"] = result["avg_duration"] / 1000
            
            return stats
            
        except Exception:
            return {
                "total": 0,
                "pending": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "avg_duration_seconds": 0
            }
    
    @staticmethod
    def cleanup_old_tasks(days: int = 30) -> int:
        """
        Clean up old task records.
        
        Args:
            days: Number of days to keep records
            
        Returns:
            Number of deleted records
        """
        try:
            cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(days=days)
            
            result = mongo.db.task_status.delete_many({
                "created_at": {"$lt": cutoff_time},
                "status": {"$in": ["completed", "failed"]}
            })
            
            return result.deleted_count
            
        except Exception:
            return 0
    
    @staticmethod
    def create_task_decorator(task_name: str):
        """
        Decorator to automatically track task status.
        
        Args:
            task_name: Name of the task
            
        Returns:
            Decorator function
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Extract task record ID from kwargs if provided
                task_record_id = kwargs.pop('task_record_id', None)
                
                if task_record_id:
                    # Update status to running
                    TaskStatusService.update_task_status(
                        task_record_id, 
                        "running",
                        progress=0
                    )
                
                try:
                    # Execute the task
                    result = func(*args, **kwargs)
                    
                    if task_record_id:
                        # Update status to completed
                        TaskStatusService.update_task_status(
                            task_record_id,
                            "completed",
                            progress=100,
                            result=result if isinstance(result, dict) else {"result": result}
                        )
                    
                    return result
                    
                except Exception as e:
                    if task_record_id:
                        # Update status to failed
                        TaskStatusService.update_task_status(
                            task_record_id,
                            "failed",
                            error=str(e)
                        )
                    raise
            
            return wrapper
        return decorator