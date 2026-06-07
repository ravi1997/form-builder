import os
import datetime
from elasticsearch import Elasticsearch
from flask import current_app

class SearchService:
    def __init__(self):
        self.client = None
        self.index_name = "form_responses"

    def init_app(self, app):
        es_uri = app.config.get("ELASTICSEARCH_URI", "http://localhost:9200")
        try:
            self.client = Elasticsearch(es_uri)
            if not app.config.get("TESTING"):
                if self.client.ping():
                    app.logger.info("Elasticsearch connection verified successfully.")
                    self.create_index_if_not_exists()
                else:
                    app.logger.warning("Elasticsearch server did not respond to ping.")
        except Exception as e:
            app.logger.error(f"Failed to connect to Elasticsearch: {e}")
            self.client = None

    def create_index_if_not_exists(self):
        if not self.client:
            return False
        try:
            if not self.client.indices.exists(index=self.index_name):
                mapping = {
                    "mappings": {
                        "properties": {
                            "response_id": { "type": "keyword" },
                            "form_id": { "type": "keyword" },
                            "org_id": { "type": "keyword" },
                            "submitted_at": { "type": "date" },
                            "values": { "type": "object", "dynamic": True }
                        }
                    }
                }
                self.client.indices.create(index=self.index_name, body=mapping)
                return True
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Failed to create Elasticsearch index: {e}")
            return False

    def index_form_response(self, response_id, form_id, org_id, values, submitted_at=None):
        """
        Indexes form response values in Elasticsearch.
        """
        if not self.client:
            return False
        
        if not submitted_at:
            submitted_at = datetime.datetime.utcnow().isoformat()
            
        doc = {
            "response_id": str(response_id),
            "form_id": str(form_id),
            "org_id": str(org_id),
            "submitted_at": submitted_at,
            "values": values
        }
        
        try:
            self.client.index(index=self.index_name, id=str(response_id), document=doc, refresh=True)
            return True
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Failed to index form response {response_id}: {e}")
            return False

    def delete_form_response(self, response_id):
        if not self.client:
            return False
        try:
            self.client.delete(index=self.index_name, id=str(response_id), refresh=True)
            return True
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Failed to delete indexed response {response_id}: {e}")
            return False

    def search_form_responses(self, form_id, query_text=None, filters=None, page=1, page_size=10):
        """
        Searches form responses in Elasticsearch.
        - query_text: searches matching text fields within 'values'
        - filters: key-value dictionary representing field-level exact match or match filters.
        """
        if not self.client:
            return {"total": 0, "hits": []}

        # Base query to filter by form_id
        must_queries = [
            {"term": {"form_id": str(form_id)}}
        ]

        if query_text:
            must_queries.append({
                "query_string": {
                    "query": query_text,
                    "default_field": "values.*"
                }
            })

        if filters:
            for field, val in filters.items():
                field_name = field if field.startswith("values.") or field in ["org_id", "submitted_at"] else f"values.{field}"
                if isinstance(val, list):
                    must_queries.append({"terms": {field_name: val}})
                else:
                    must_queries.append({"match": {field_name: val}})

        body = {
            "query": {
                "bool": {
                    "must": must_queries
                }
            },
            "from": (page - 1) * page_size,
            "size": page_size,
            "sort": [{"submitted_at": {"order": "desc"}}]
        }

        try:
            res = self.client.search(index=self.index_name, body=body)
            hits = res.get("hits", {})
            total = hits.get("total", {}).get("value", 0) if isinstance(hits.get("total"), dict) else hits.get("total", 0)
            
            records = []
            for hit in hits.get("hits", []):
                records.append(hit.get("_source"))
            return {"total": total, "hits": records}
        except Exception as e:
            if current_app:
                current_app.logger.error(f"Failed to search form responses: {e}")
            return {"total": 0, "hits": []}

search_service = SearchService()
