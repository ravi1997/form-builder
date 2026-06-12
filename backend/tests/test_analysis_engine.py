import pytest
import json
from datetime import datetime
from bson import ObjectId
from app.engines.analysis_engine import (
    validate_graph,
    execute_analysis_graph,
    GraphCycleException,
    NodeExecutionError
)
from app.models.analysis import (
    Node, Edge, Graph, Analysis, AnalysisRun, AnalysisResult
)

class TestAnalysisEngine:
    """Test suite for the analysis DAG engine."""
    
    def test_validate_graph_valid(self):
        """Test validation of a valid graph."""
        graph = {
            "nodes": [
                {
                    "id": "node1",
                    "type": "manual_data_entry",
                    "position": {"x": 0, "y": 0},
                    "properties": {"data": [{"id": 1, "name": "test"}]}
                },
                {
                    "id": "node2", 
                    "type": "filter",
                    "position": {"x": 100, "y": 0},
                    "properties": {"query": "id > 0"}
                }
            ],
            "edges": [
                {
                    "id": "edge1",
                    "from_node": "node1",
                    "from_port": "out",
                    "to_node": "node2",
                    "to_port": "in"
                }
            ]
        }
        
        # Should not raise any exception
        assert validate_graph(graph) is True
    
    def test_validate_graph_cycle(self):
        """Test validation of a graph with cycles."""
        graph = {
            "nodes": [
                {"id": "node1", "type": "manual_data_entry", "position": {"x": 0, "y": 0}},
                {"id": "node2", "type": "filter", "position": {"x": 100, "y": 0}}
            ],
            "edges": [
                {"from_node": "node1", "to_node": "node2"},
                {"from_node": "node2", "to_node": "node1"}  # Creates cycle
            ]
        }
        
        with pytest.raises(ValueError, match="Graph contains cycles"):
            validate_graph(graph)
    
    def test_validate_graph_missing_node_id(self):
        """Test validation of graph with missing node ID."""
        graph = {
            "nodes": [
                {"type": "manual_data_entry", "position": {"x": 0, "y": 0}}  # Missing id
            ],
            "edges": []
        }
        
        with pytest.raises(ValueError, match="Each node must have an id"):
            validate_graph(graph)
    
    def test_execute_manual_data_entry_node(self):
        """Test execution of manual_data_entry node."""
        node = {
            "id": "node1",
            "type": "manual_data_entry",
            "properties": {
                "data": [
                    {"id": 1, "name": "Alice", "age": 25},
                    {"id": 2, "name": "Bob", "age": 30}
                ]
            }
        }
        
        graph = {
            "nodes": [node],
            "edges": []
        }
        
        context = {"org_id": str(ObjectId())}
        result = execute_analysis_graph(graph, context)
        
        assert result["node_statuses"]["node1"] == "success"
        assert "out" in result["node_outputs"]["node1"]
        assert len(result["node_outputs"]["node1"]["out"]) == 2
    
    def test_execute_filter_node(self):
        """Test execution of filter node."""
        graph = {
            "nodes": [
                {
                    "id": "source",
                    "type": "manual_data_entry",
                    "properties": {
                        "data": [
                            {"id": 1, "name": "Alice", "age": 25},
                            {"id": 2, "name": "Bob", "age": 30},
                            {"id": 3, "name": "Charlie", "age": 35}
                        ]
                    }
                },
                {
                    "id": "filter",
                    "type": "filter",
                    "properties": {"query": "age > 28"}
                }
            ],
            "edges": [
                {
                    "from_node": "source",
                    "from_port": "out",
                    "to_node": "filter",
                    "to_port": "in"
                }
            ]
        }
        
        context = {"org_id": str(ObjectId())}
        result = execute_analysis_graph(graph, context)
        
        assert result["node_statuses"]["filter"] == "success"
        filtered_data = result["node_outputs"]["filter"]["out"]
        assert len(filtered_data) == 2  # Bob and Charlie
        assert all(person["age"] > 28 for person in filtered_data)
    
    def test_execute_sort_node(self):
        """Test execution of sort node."""
        graph = {
            "nodes": [
                {
                    "id": "source",
                    "type": "manual_data_entry",
                    "properties": {
                        "data": [
                            {"id": 3, "name": "Charlie", "age": 35},
                            {"id": 1, "name": "Alice", "age": 25},
                            {"id": 2, "name": "Bob", "age": 30}
                        ]
                    }
                },
                {
                    "id": "sort",
                    "type": "sort",
                    "properties": {"columns": ["age"], "ascending": True}
                }
            ],
            "edges": [
                {
                    "from_node": "source",
                    "from_port": "out",
                    "to_node": "sort",
                    "to_port": "in"
                }
            ]
        }
        
        context = {"org_id": str(ObjectId())}
        result = execute_analysis_graph(graph, context)
        
        assert result["node_statuses"]["sort"] == "success"
        sorted_data = result["node_outputs"]["sort"]["out"]
        ages = [person["age"] for person in sorted_data]
        assert ages == [25, 30, 35]  # Sorted ascending
    
    def test_execute_group_by_node(self):
        """Test execution of group_by node."""
        graph = {
            "nodes": [
                {
                    "id": "source",
                    "type": "manual_data_entry",
                    "properties": {
                        "data": [
                            {"department": "Engineering", "salary": 80000},
                            {"department": "Marketing", "salary": 60000},
                            {"department": "Engineering", "salary": 90000},
                            {"department": "Marketing", "salary": 65000}
                        ]
                    }
                },
                {
                    "id": "group_by",
                    "type": "group_by",
                    "properties": {
                        "columns": ["department"],
                        "aggregations": {"salary": "mean"}
                    }
                }
            ],
            "edges": [
                {
                    "from_node": "source",
                    "from_port": "out",
                    "to_node": "group_by",
                    "to_port": "in"
                }
            ]
        }
        
        context = {"org_id": str(ObjectId())}
        result = execute_analysis_graph(graph, context)
        
        assert result["node_statuses"]["group_by"] == "success"
        grouped_data = result["node_outputs"]["group_by"]["out"]
        assert len(grouped_data) == 2  # Engineering and Marketing
        
        # Check average salaries
        engineering = next(item for item in grouped_data if item["department"] == "Engineering")
        marketing = next(item for item in grouped_data if item["department"] == "Marketing")
        
        assert engineering["salary"] == 85000  # (80000 + 90000) / 2
        assert marketing["salary"] == 62500  # (60000 + 65000) / 2
    
    def test_execute_calculate_column_node(self):
        """Test execution of calculate_column node."""
        graph = {
            "nodes": [
                {
                    "id": "source",
                    "type": "manual_data_entry",
                    "properties": {
                        "data": [
                            {"quantity": 2, "unit_price": 10},
                            {"quantity": 3, "unit_price": 15}
                        ]
                    }
                },
                {
                    "id": "calculate",
                    "type": "calculate_column",
                    "properties": {
                        "target_column": "total",
                        "formula": "quantity * unit_price"
                    }
                }
            ],
            "edges": [
                {
                    "from_node": "source",
                    "from_port": "out",
                    "to_node": "calculate",
                    "to_port": "in"
                }
            ]
        }
        
        context = {"org_id": str(ObjectId())}
        result = execute_analysis_graph(graph, context)
        
        assert result["node_statuses"]["calculate"] == "success"
        calculated_data = result["node_outputs"]["calculate"]["out"]
        
        assert calculated_data[0]["total"] == 20  # 2 * 10
        assert calculated_data[1]["total"] == 45  # 3 * 15
    
    def test_execute_kpi_value_node(self):
        """Test execution of kpi_value node."""
        graph = {
            "nodes": [
                {
                    "id": "source",
                    "type": "manual_data_entry",
                    "properties": {
                        "data": [
                            {"sales": 100},
                            {"sales": 150},
                            {"sales": 200}
                        ]
                    }
                },
                {
                    "id": "kpi",
                    "type": "kpi_value",
                    "properties": {
                        "column": "sales",
                        "aggregation": "sum",
                        "label": "Total Sales"
                    }
                }
            ],
            "edges": [
                {
                    "from_node": "source",
                    "from_port": "out",
                    "to_node": "kpi",
                    "to_port": "in"
                }
            ]
        }
        
        context = {"org_id": str(ObjectId())}
        result = execute_analysis_graph(graph, context)
        
        assert result["node_statuses"]["kpi"] == "success"
        kpi_output = result["node_outputs"]["kpi"]["out"]
        
        assert kpi_output["type"] == "kpi"
        assert kpi_output["value"] == 450  # 100 + 150 + 200
        assert kpi_output["label"] == "Total Sales"
    
    def test_execute_bar_chart_data_node(self):
        """Test execution of bar_chart_data node."""
        graph = {
            "nodes": [
                {
                    "id": "source",
                    "type": "manual_data_entry",
                    "properties": {
                        "data": [
                            {"product": "A", "sales": 100},
                            {"product": "B", "sales": 150},
                            {"product": "C", "sales": 200}
                        ]
                    }
                },
                {
                    "id": "chart",
                    "type": "bar_chart_data",
                    "properties": {
                        "label_column": "product",
                        "value_column": "sales"
                    }
                }
            ],
            "edges": [
                {
                    "from_node": "source",
                    "from_port": "out",
                    "to_node": "chart",
                    "to_port": "in"
                }
            ]
        }
        
        context = {"org_id": str(ObjectId())}
        result = execute_analysis_graph(graph, context)
        
        assert result["node_statuses"]["chart"] == "success"
        chart_data = result["node_outputs"]["chart"]["out"]
        
        assert chart_data["type"] == "bar_chart"
        assert chart_data["labels"] == ["A", "B", "C"]
        assert chart_data["datasets"][0]["data"] == [100, 150, 200]
    
    def test_error_isolation(self):
        """Test that errors in one node don't stop others."""
        graph = {
            "nodes": [
                {
                    "id": "source1",
                    "type": "manual_data_entry",
                    "properties": {"data": [{"id": 1, "value": 10}]}
                },
                {
                    "id": "source2",
                    "type": "manual_data_entry",
                    "properties": {"data": [{"id": 2, "value": 20}]}
                },
                {
                    "id": "bad_node",
                    "type": "filter",
                    "properties": {"query": "invalid syntax here"}  # This will fail
                },
                {
                    "id": "good_node",
                    "type": "kpi_value",
                    "properties": {"column": "value", "aggregation": "sum"}
                }
            ],
            "edges": [
                {
                    "from_node": "source1",
                    "from_port": "out",
                    "to_node": "bad_node",
                    "to_port": "in"
                },
                {
                    "from_node": "source2",
                    "from_port": "out",
                    "to_node": "good_node",
                    "to_port": "in"
                }
            ]
        }
        
        context = {"org_id": str(ObjectId())}
        result = execute_analysis_graph(graph, context)
        
        # bad_node should fail
        assert result["node_statuses"]["bad_node"] == "error"
        assert "bad_node" in result["node_errors"]
        
        # good_node should still succeed (error isolation)
        assert result["node_statuses"]["good_node"] == "success"
        assert result["node_outputs"]["good_node"]["out"]["value"] == 20
    
    def test_dependency_blocking(self):
        """Test that nodes are blocked when dependencies fail."""
        graph = {
            "nodes": [
                {
                    "id": "source",
                    "type": "manual_data_entry",
                    "properties": {"data": [{"id": 1, "value": 10}]}
                },
                {
                    "id": "bad_node",
                    "type": "filter",
                    "properties": {"query": "invalid syntax"}  # This will fail
                },
                {
                    "id": "dependent_node",
                    "type": "kpi_value",
                    "properties": {"column": "value", "aggregation": "sum"}
                }
            ],
            "edges": [
                {
                    "from_node": "source",
                    "from_port": "out",
                    "to_node": "bad_node",
                    "to_port": "in"
                },
                {
                    "from_node": "bad_node",
                    "from_port": "out",
                    "to_node": "dependent_node",
                    "to_port": "in"
                }
            ]
        }
        
        context = {"org_id": str(ObjectId())}
        result = execute_analysis_graph(graph, context)
        
        # bad_node should fail
        assert result["node_statuses"]["bad_node"] == "error"
        
        # dependent_node should be blocked
        assert result["node_statuses"]["dependent_node"] == "blocked"
        assert "Dependencies failed" in result["node_errors"]["dependent_node"]
    
    def test_disabled_node(self):
        """Test that disabled nodes are skipped."""
        graph = {
            "nodes": [
                {
                    "id": "source",
                    "type": "manual_data_entry",
                    "properties": {"data": [{"id": 1, "value": 10}]}
                },
                {
                    "id": "disabled_node",
                    "type": "filter",
                    "properties": {"query": "value > 5"},
                    "is_disabled": True
                },
                {
                    "id": "final_node",
                    "type": "kpi_value",
                    "properties": {"column": "value", "aggregation": "sum"}
                }
            ],
            "edges": [
                {
                    "from_node": "source",
                    "from_port": "out",
                    "to_node": "disabled_node",
                    "to_port": "in"
                },
                {
                    "from_node": "disabled_node",
                    "from_port": "out",
                    "to_node": "final_node",
                    "to_port": "in"
                }
            ]
        }
        
        context = {"org_id": str(ObjectId())}
        result = execute_analysis_graph(graph, context)
        
        # disabled_node should be blocked
        assert result["node_statuses"]["disabled_node"] == "blocked"
        
        # final_node should also be blocked due to disabled dependency
        assert result["node_statuses"]["final_node"] == "blocked"
    
    def test_complex_pipeline(self):
        """Test a complex analysis pipeline with multiple node types."""
        graph = {
            "nodes": [
                {
                    "id": "sales_data",
                    "type": "manual_data_entry",
                    "properties": {
                        "data": [
                            {"product": "A", "region": "North", "sales": 100, "quarter": "Q1"},
                            {"product": "B", "region": "South", "sales": 150, "quarter": "Q1"},
                            {"product": "A", "region": "North", "sales": 120, "quarter": "Q2"},
                            {"product": "B", "region": "South", "sales": 180, "quarter": "Q2"},
                            {"product": "A", "region": "North", "sales": 140, "quarter": "Q3"},
                            {"product": "B", "region": "South", "sales": 200, "quarter": "Q3"},
                            {"product": "A", "region": "North", "sales": 160, "quarter": "Q4"},
                            {"product": "B", "region": "South", "sales": 220, "quarter": "Q4"}
                        ]
                    }
                },
                {
                    "id": "filter_high_sales",
                    "type": "filter",
                    "properties": {"query": "sales > 130"}
                },
                {
                    "id": "group_by_region",
                    "type": "group_by",
                    "properties": {
                        "columns": ["region"],
                        "aggregations": {"sales": "sum"}
                    }
                },
                {
                    "id": "region_kpi",
                    "type": "kpi_value",
                    "properties": {
                        "column": "sales",
                        "aggregation": "sum",
                        "label": "Total High Sales"
                    }
                },
                {
                    "id": "sales_chart",
                    "type": "bar_chart_data",
                    "properties": {
                        "label_column": "region",
                        "value_column": "sales"
                    }
                }
            ],
            "edges": [
                {
                    "from_node": "sales_data",
                    "from_port": "out",
                    "to_node": "filter_high_sales",
                    "to_port": "in"
                },
                {
                    "from_node": "filter_high_sales",
                    "from_port": "out",
                    "to_node": "group_by_region",
                    "to_port": "in"
                },
                {
                    "from_node": "group_by_region",
                    "from_port": "out",
                    "to_node": "region_kpi",
                    "to_port": "in"
                },
                {
                    "from_node": "group_by_region",
                    "from_port": "out",
                    "to_node": "sales_chart",
                    "to_port": "in"
                }
            ]
        }
        
        context = {"org_id": str(ObjectId())}
        result = execute_analysis_graph(graph, context)
        
        # All nodes should succeed
        for node_id in ["sales_data", "filter_high_sales", "group_by_region", "region_kpi", "sales_chart"]:
            assert result["node_statuses"][node_id] == "success"
        
        # Check KPI value
        kpi_output = result["node_outputs"]["region_kpi"]["out"]
        assert kpi_output["type"] == "kpi"
        assert kpi_output["value"] > 0  # Should be sum of high sales
        
        # Check chart data
        chart_data = result["node_outputs"]["sales_chart"]["out"]
        assert chart_data["type"] == "bar_chart"
        assert len(chart_data["labels"]) == 2  # North and South regions
        assert len(chart_data["datasets"][0]["data"]) == 2

if __name__ == "__main__":
    pytest.main([__file__])