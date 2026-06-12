import pytest
from unittest.mock import MagicMock
from bson import ObjectId
import datetime

from app.engines.analysis_engine import (
    validate_and_sort_dag,
    GraphCycleException,
    evaluate_filter,
    evaluate_aggregation,
    evaluate_projection,
    evaluate_formula
)
from app.workers.analysis_tasks import run_analysis_graph_task
from app.services.search_service import search_service

# --- 1. Test Engine DAG functions & Helpers ---

def test_validate_and_sort_dag_valid():
    graph = {
        "A": {"dependencies": []},
        "B": {"dependencies": ["A"]},
        "C": {"dependencies": ["A"]},
        "D": {"dependencies": ["B", "C"]}
    }
    order = validate_and_sort_dag(graph)
    assert order.index("A") < order.index("B")
    assert order.index("A") < order.index("C")
    assert order.index("B") < order.index("D")
    assert order.index("C") < order.index("D")

def test_validate_and_sort_dag_invalid_cycle():
    graph = {
        "A": ["B"],
        "B": ["C"],
        "C": ["A"]
    }
    with pytest.raises(GraphCycleException) as excinfo:
        validate_and_sort_dag(graph)
    assert "cycle" in str(excinfo.value).lower()

def test_evaluate_filter():
    data = [
        {"name": "Alice", "age": 25, "city": "NY"},
        {"name": "Bob", "age": 35, "city": "LA"},
        {"name": "Charlie", "age": 45, "city": "NY"}
    ]
    res = evaluate_filter(data, "age > 30 and city == 'NY'")
    assert len(res) == 1
    assert res[0]["name"] == "Charlie"

def test_evaluate_aggregation():
    data = [
        {"dept": "Sales", "salary": 50000},
        {"dept": "Sales", "salary": 60000},
        {"dept": "Eng", "salary": 80000},
        {"dept": "Eng", "salary": 120000}
    ]
    res = evaluate_aggregation(data, ["dept"], {"salary": "mean"})
    # Result lists dicts with dept and salary (mean)
    assert len(res) == 2
    # Find Eng mean
    eng_res = [r for r in res if r["dept"] == "Eng"][0]
    assert eng_res["salary"] == 100000.0

def test_evaluate_projection():
    data = [
        {"name": "Alice", "age": 25, "city": "NY"},
        {"name": "Bob", "age": 35, "city": "LA"}
    ]
    res = evaluate_projection(data, ["name", "city"])
    assert len(res) == 2
    assert "age" not in res[0]
    assert res[0]["name"] == "Alice"
    assert res[0]["city"] == "NY"

def test_evaluate_formula():
    data = [
        {"item": "apple", "quantity": 10, "unit_price": 0.5},
        {"item": "banana", "quantity": 5, "unit_price": 0.8}
    ]
    res = evaluate_formula(data, "total", "quantity * unit_price")
    assert len(res) == 2
    assert res[0]["total"] == 5.0
    assert res[1]["total"] == 4.0

# --- 2. Test Celery Tasks Execution ---

def test_run_analysis_graph_task_success(db):
    org_id = ObjectId()
    form_id = ObjectId()
    # Create Form
    db.forms.insert_one({"_id": form_id, "org_id": org_id, "name": "Income Form", "is_deleted": False})
    
    # Seed response data
    db.form_responses.insert_many([
        {"form_id": form_id, "org_id": org_id, "values": {"age": 25, "gender": "F", "income": 50000}},
        {"form_id": form_id, "org_id": org_id, "values": {"age": 35, "gender": "M", "income": 80000}},
        {"form_id": form_id, "org_id": org_id, "values": {"age": 45, "gender": "F", "income": 90000}}
    ])
    
    # Create Analysis
    analysis_id = ObjectId()
    analysis_doc = {
        "_id": analysis_id,
        "org_id": org_id,
        "project_id": ObjectId(),
        "name": "Income Analysis for Females",
        "graph": {
            "nodes": [
                {
                    "id": "node_src",
                    "type": "form_source",
                    "properties": {"form_id": str(form_id)}
                },
                {
                    "id": "node_filter",
                    "type": "pandas_filter",
                    "properties": {"query": "gender == 'F'"}
                },
                {
                    "id": "node_agg",
                    "type": "scalar_aggregator",
                    "properties": {"column": "income", "function": "mean"}
                }
            ],
            "edges": [
                {
                    "from_node": "node_src",
                    "from_port": "out",
                    "to_node": "node_filter",
                    "to_port": "in"
                },
                {
                    "from_node": "node_filter",
                    "from_port": "out",
                    "to_node": "node_agg",
                    "to_port": "in"
                }
            ]
        }
    }
    db.analyses.insert_one(analysis_doc)
    
    # Create Run
    run_id = ObjectId()
    run_doc = {
        "_id": run_id,
        "analysis_id": analysis_id,
        "status": "pending",
        "created_at": datetime.datetime.utcnow().isoformat(),
        "updated_at": datetime.datetime.utcnow().isoformat()
    }
    db.analysis_runs.insert_one(run_doc)
    
    # Execute Task
    res = run_analysis_graph_task(str(run_id))
    assert res["status"] == "completed"
    
    # Check execution status of run
    updated_run = db.analysis_runs.find_one({"_id": run_id})
    assert updated_run["status"] == "completed"
    assert updated_run["error"] is None
    
    # Check results are cached
    src_res = db.analysis_results.find_one({"analysis_run_id": run_id, "node_id": "node_src"})
    assert src_res["status"] == "success"
    assert len(src_res["data"]["out"]) == 3
    
    filter_res = db.analysis_results.find_one({"analysis_run_id": run_id, "node_id": "node_filter"})
    assert filter_res["status"] == "success"
    assert len(filter_res["data"]["out"]) == 2
    
    agg_res = db.analysis_results.find_one({"analysis_run_id": run_id, "node_id": "node_agg"})
    assert agg_res["status"] == "success"
    # Average of female incomes (50000 + 90000) / 2 = 70000
    assert agg_res["data"]["out"] == 70000.0

def test_run_analysis_graph_task_block_propagation(db):
    analysis_id = ObjectId()
    analysis_doc = {
        "_id": analysis_id,
        "graph": {
            "nodes": [
                {
                    "id": "node_src",
                    "type": "form_source",
                    "properties": {"form_id": "invalid-id-that-causes-failure"}
                },
                {
                    "id": "node_filter",
                    "type": "pandas_filter",
                    "properties": {"query": "age > 30"}
                },
                {
                    "id": "node_independent",
                    "type": "table_generator",
                    "properties": {"page_size": 5, "columns": []}
                }
            ],
            "edges": [
                {
                    "from_node": "node_src",
                    "from_port": "out",
                    "to_node": "node_filter",
                    "to_port": "in"
                }
            ]
        }
    }
    db.analyses.insert_one(analysis_doc)
    
    run_id = ObjectId()
    db.analysis_runs.insert_one({
        "_id": run_id,
        "analysis_id": analysis_id,
        "status": "pending"
    })
    
    res = run_analysis_graph_task(str(run_id))
    assert res["status"] == "failed"
    
    # node_src should have failed with error
    src_res = db.analysis_results.find_one({"analysis_run_id": run_id, "node_id": "node_src"})
    assert src_res["status"] == "error"
    assert "error" in src_res
    
    # node_filter depending on node_src should be blocked
    filter_res = db.analysis_results.find_one({"analysis_run_id": run_id, "node_id": "node_filter"})
    assert filter_res["status"] == "blocked"
    assert "blocked" in filter_res["error"].lower()
    
    # node_independent should have succeeded since it has no dependencies (empty inputs array)
    ind_res = db.analysis_results.find_one({"analysis_run_id": run_id, "node_id": "node_independent"})
    assert ind_res["status"] == "success"

# --- 3. Test Search Service ---

def test_search_service_indexing_and_searching():
    # Mock Elasticsearch client
    mock_es = MagicMock()
    search_service.client = mock_es
    
    # Test indexing
    response_id = ObjectId()
    form_id = ObjectId()
    org_id = ObjectId()
    values = {"full_name": "John Doe", "score": 95}
    
    search_service.index_form_response(response_id, form_id, org_id, values)
    assert mock_es.index.called
    kwargs = mock_es.index.call_args[1]
    assert kwargs["index"] == "form_responses"
    assert kwargs["id"] == str(response_id)
    assert kwargs["document"]["form_id"] == str(form_id)
    assert kwargs["document"]["values"]["full_name"] == "John Doe"
    
    # Test searching
    mock_es.search.return_value = {
        "hits": {
            "total": {"value": 1},
            "hits": [
                {
                    "_source": {
                        "response_id": str(response_id),
                        "form_id": str(form_id),
                        "values": values
                    }
                }
            ]
        }
    }
    
    search_res = search_service.search_form_responses(
        form_id=form_id,
        query_text="John",
        filters={"score": 95}
    )
    
    assert mock_es.search.called
    search_kwargs = mock_es.search.call_args[1]
    assert search_kwargs["index"] == "form_responses"
    body = search_kwargs["body"]
    
    # Verify search query layout
    must_list = body["query"]["bool"]["must"]
    assert {"term": {"form_id": str(form_id)}} in must_list
    assert any("query_string" in item for item in must_list)
    assert any("match" in item and "values.score" in item["match"] for item in must_list)
    
    # Verify results
    assert search_res["total"] == 1
    assert len(search_res["hits"]) == 1
    assert search_res["hits"][0]["values"]["full_name"] == "John Doe"
