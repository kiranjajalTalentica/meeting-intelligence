"""
Tests for the LangGraph workflow structure.

These tests verify the graph compiles and runs without errors.
At Phase 1, nodes return empty data — we just confirm the shape.
"""

from app.graph.workflow import build_workflow


class TestWorkflowStructure:
    def test_workflow_compiles(self):
        """The graph should compile without errors."""
        workflow = build_workflow()
        assert workflow is not None

    def test_workflow_runs_with_stub_nodes(self):
        """Running the workflow with stubs should return valid state."""
        workflow = build_workflow()
        result = workflow.invoke(
            {
                "meeting_id": "test-001",
                "transcript": "Alice: Hello. Bob: Hi.",
                "topics": [],
                "summary": "",
                "decisions": [],
                "action_items": [],
                "open_questions": [],
            }
        )
        assert result["meeting_id"] == "test-001"
        assert result["summary"] == ""
        assert result["topics"] == []
        assert result["decisions"] == []
        assert result["action_items"] == []
        assert result["open_questions"] == []
