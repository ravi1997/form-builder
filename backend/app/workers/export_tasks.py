import os
import datetime
import pandas as pd
from celery import Celery
from bson import ObjectId
from app.extensions import mongo

# Setup Celery
redis_uri = os.environ.get("REDIS_URI", "redis://localhost:6379/0")
celery_app = Celery("export_tasks", broker=redis_uri, backend=redis_uri)

def _utcnow_iso():
    return datetime.datetime.utcnow().isoformat()

def _to_object_id(value):
    if isinstance(value, ObjectId):
        return value
    if ObjectId.is_valid(str(value)):
        return ObjectId(str(value))
    raise ValueError(f"Invalid ObjectId: {value}")

def _safe_result_payload(status, error=None, **extra):
    payload = {"status": status, "error": error}
    payload.update(extra)
    return payload

@celery_app.task(name="app.workers.export_tasks.generate_export_file")
def generate_export_file(export_id):
    """
    Generate export file for analysis results.
    """
    export_oid = _to_object_id(export_id)
    export_doc = mongo.db.analysis_exports.find_one({"_id": export_oid})
    
    if not export_doc:
        return _safe_result_payload("failed", f"Export {export_id} not found")
    
    try:
        # Update status to generating
        mongo.db.analysis_exports.update_one(
            {"_id": export_oid},
            {"$set": {"status": "generating", "updated_at": _utcnow_iso()}}
        )
        
        # Get analysis run
        run_id = export_doc.get("run_id")
        run_oid = _to_object_id(run_id)
        run_doc = mongo.db.analysis_runs.find_one({"_id": run_oid})
        
        if not run_doc:
            raise ValueError(f"Analysis run {run_id} not found")
        
        # Get results for specified nodes
        node_ids = export_doc.get("node_ids", [])
        results = []
        
        for node_id in node_ids:
            result = mongo.db.analysis_results.find_one({
                "run_id": run_oid,
                "node_id": node_id
            })
            
            if result:
                results.append(result)
        
        if not results:
            raise ValueError("No results found for specified nodes")
        
        # Generate export based on format
        format_type = export_doc.get("format")
        filename = export_doc.get("filename", "export")
        
        if format_type == "csv":
            # Combine all results into a single CSV
            all_data = []
            for result in results:
                data = result.get("data", {})
                if isinstance(data, dict) and "rows" in data:
                    all_data.extend(data["rows"])
                elif isinstance(data, list):
                    all_data.extend(data)
            
            if not all_data:
                raise ValueError("No data to export")
            
            df = pd.DataFrame(all_data)
            
            # Generate file path
            uploads_root = os.environ.get("UPLOADS_ROOT", "/tmp/exports")
            os.makedirs(uploads_root, exist_ok=True)
            
            file_path = os.path.join(uploads_root, f"{filename}_{export_oid}.csv")
            df.to_csv(file_path, index=False)
            
            file_size = os.path.getsize(file_path)
            
        elif format_type == "excel":
            # Generate Excel file with multiple sheets
            uploads_root = os.environ.get("UPLOADS_ROOT", "/tmp/exports")
            os.makedirs(uploads_root, exist_ok=True)
            
            file_path = os.path.join(uploads_root, f"{filename}_{export_oid}.xlsx")
            
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                for i, result in enumerate(results):
                    data = result.get("data", {})
                    if isinstance(data, dict) and "rows" in data:
                        df = pd.DataFrame(data["rows"])
                    elif isinstance(data, list):
                        df = pd.DataFrame(data)
                    else:
                        continue
                    
                    sheet_name = f"Node_{result.get('node_id', f'Sheet_{i}')}")[:31]  # Excel sheet name limit
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            file_size = os.path.getsize(file_path)
            
        elif format_type == "pdf":
            # For PDF export, we'll create a simple text-based report for now
            # In a real implementation, you'd use ReportLab or similar
            uploads_root = os.environ.get("UPLOADS_ROOT", "/tmp/exports")
            os.makedirs(uploads_root, exist_ok=True)
            
            file_path = os.path.join(uploads_root, f"{filename}_{export_oid}.txt")
            
            with open(file_path, 'w') as f:
                f.write(f"Analysis Export Report\n")
                f.write(f"Generated: {datetime.datetime.utcnow().isoformat()}\n")
                f.write(f"Format: PDF (Text representation)\n\n")
                
                for result in results:
                    f.write(f"Node: {result.get('node_id', 'Unknown')}\n")
                    f.write(f"Output Type: {result.get('output_type', 'Unknown')}\n")
                    f.write(f"Row Count: {result.get('row_count', 0)}\n\n")
                    
                    data = result.get("data", {})
                    if isinstance(data, dict) and "rows" in data:
                        for row in data["rows"][:10]:  # Limit to first 10 rows for text
                            f.write(f"  {row}\n")
                        if len(data["rows"]) > 10:
                            f.write(f"  ... and {len(data['rows']) - 10} more rows\n")
                    f.write("\n" + "="*50 + "\n\n")
            
            file_size = os.path.getsize(file_path)
            
        else:
            raise ValueError(f"Unsupported export format: {format_type}")
        
        # Update export document
        mongo.db.analysis_exports.update_one(
            {"_id": export_oid},
            {"$set": {
                "status": "ready",
                "file_path": file_path,
                "file_size_bytes": file_size,
                "updated_at": _utcnow_iso()
            }}
        )
        
        return _safe_result_payload(
            "completed",
            None,
            export_id=str(export_oid),
            file_path=file_path,
            file_size_bytes=file_size
        )
        
    except Exception as e:
        error_msg = str(e)
        mongo.db.analysis_exports.update_one(
            {"_id": export_oid},
            {"$set": {
                "status": "failed",
                "updated_at": _utcnow_iso()
            }}
        )
        
        return _safe_result_payload("failed", error_msg, export_id=str(export_oid))

@celery_app.task(name="app.workers.export_tasks.cleanup_expired_exports")
def cleanup_expired_exports():
    """
    Clean up expired export files.
    """
    try:
        # Find expired exports
        expired_exports = mongo.db.analysis_exports.find({
            "expires_at": {"$lt": datetime.datetime.utcnow()},
            "status": "ready"
        })
        
        deleted_count = 0
        for export in expired_exports:
            # Delete file if it exists
            file_path = export.get("file_path")
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except OSError:
                    pass  # File might already be deleted
            
            # Mark export as expired in database
            mongo.db.analysis_exports.update_one(
                {"_id": export["_id"]},
                {"$set": {"status": "expired"}}
            )
        
        return _safe_result_payload("completed", None, deleted_files=deleted_count)
        
    except Exception as e:
        return _safe_result_payload("failed", str(e))