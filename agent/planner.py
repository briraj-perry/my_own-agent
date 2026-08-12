"""Dynamic DAG-based Task & Execution Planner for my_neo-agent.

Decomposes complex coding queries into structured execution plan graphs with steps,
dependencies, target files, and dynamic sub-agent role assignments.
"""

import json
import uuid
import re
from typing import List, Dict, Any, Optional


class PlanStep:
    """Represents an individual step in an execution plan DAG."""

    def __init__(
        self,
        step_id: str,
        title: str,
        description: str,
        target_file: Optional[str] = None,
        action_type: str = "create_file", # create_file, modify_file, analyze, test, execute
        dependencies: Optional[List[str]] = None,
        assigned_role: Optional[str] = None
    ):
        self.step_id = step_id
        self.title = title
        self.description = description
        self.target_file = target_file
        self.action_type = action_type
        self.dependencies = dependencies or []
        self.assigned_role = assigned_role or "Software Engineer"
        self.status = "pending"  # pending, in_progress, completed, failed
        self.result_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "description": self.description,
            "target_file": self.target_file,
            "action_type": self.action_type,
            "dependencies": self.dependencies,
            "assigned_role": self.assigned_role,
            "status": self.status,
            "result_summary": self.result_summary
        }


class ExecutionPlan:
    """Represents a complete multi-step execution plan graph."""

    def __init__(self, plan_id: str, title: str, summary: str, steps: List[PlanStep]):
        self.plan_id = plan_id
        self.title = title
        self.summary = summary
        self.steps = steps
        self.created_at = uuid.uuid4().hex[:8]

    def get_progress_percentage(self) -> int:
        if not self.steps:
            return 100
        completed = sum(1 for s in self.steps if s.status == "completed")
        return int((completed / len(self.steps)) * 100)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "title": self.title,
            "summary": self.summary,
            "progress": self.get_progress_percentage(),
            "steps": [s.to_dict() for s in self.steps]
        }


class ExecutionPlanner:
    """Generates structured multi-step execution DAG plans for user coding requests."""

    @staticmethod
    def create_plan_for_query(query: str, workspace_files: Optional[List[str]] = None) -> ExecutionPlan:
        """Decomposes a user query into a structured execution plan DAG."""
        query_lower = query.lower()
        plan_id = f"plan_{uuid.uuid4().hex[:6]}"
        workspace_files = workspace_files or []

        steps: List[PlanStep] = []

        # 1. Check if user query is an app creation request
        if any(kw in query_lower for kw in ["create app", "build app", "full stack", "web app", "todo app", "calculator", "game"]):
            plan_title = f"Application Development Plan: {query[:40]}"
            summary = "Structured 4-stage build pipeline (Spec & Layout -> UI Engine -> Application Logic -> AST Verification & QA)."

            steps = [
                PlanStep(
                    step_id="step_1",
                    title="🏛️ Specs & Project Architecture",
                    description="Analyze workspace requirements, define modular structure, and setup base configurations.",
                    target_file="README.md",
                    action_type="create_file",
                    assigned_role="Architect"
                ),
                PlanStep(
                    step_id="step_2",
                    title="🎨 UI Structure & Visual Design System",
                    description="Build markup structure, layout components, and dark-mode styling rules.",
                    target_file="index.html" if "web" in query_lower or "html" in query_lower else "ui.py",
                    action_type="create_file",
                    dependencies=["step_1"],
                    assigned_role="Frontend Engineer"
                ),
                PlanStep(
                    step_id="step_3",
                    title="⚙️ Core Logic & Event Handling",
                    description="Implement business logic, state management, calculation routines, and event handlers.",
                    target_file="script.js" if "web" in query_lower else "main.py",
                    action_type="create_file",
                    dependencies=["step_2"],
                    assigned_role="Backend Specialist"
                ),
                PlanStep(
                    step_id="step_4",
                    title="🧪 AST Code Verification & Auto-Fix",
                    description="Scan generated files for syntax tracebacks, validate imports, and auto-fix disk files.",
                    target_file="test_app.py",
                    action_type="test",
                    dependencies=["step_3"],
                    assigned_role="QA Specialist"
                )
            ]

        # 2. Check if user request is a bug fix / refactor request
        elif any(kw in query_lower for kw in ["fix", "bug", "error", "traceback", "refactor", "optimize", "clean"]):
            plan_title = f"Code Diagnostics & Refactoring Plan"
            summary = "2-stage diagnostic pipeline (Scan & Extract Error -> Apply AST-Verified Fix)."

            # Try to identify target file
            target_fn = None
            for wf in workspace_files:
                if wf.lower() in query_lower:
                    target_fn = wf
                    break
            if not target_fn and workspace_files:
                target_fn = workspace_files[0]

            steps = [
                PlanStep(
                    step_id="step_1",
                    title="🔍 Deep Diagnostic & Syntax Scanning",
                    description="Inspect target source code and screen error tracebacks to isolate failing lines.",
                    target_file=target_fn,
                    action_type="analyze",
                    assigned_role="Code Inspector"
                ),
                PlanStep(
                    step_id="step_2",
                    title="🔧 AST-Verified Code Patch & Refactor",
                    description="Apply precise fixes, resolve syntax issues, and verify code integrity before saving.",
                    target_file=target_fn or "script.py",
                    action_type="modify_file",
                    dependencies=["step_1"],
                    assigned_role="Software Engineer"
                )
            ]

        # 3. Standard single task step
        else:
            plan_title = f"Task Plan: {query[:35]}"
            summary = "Targeted execution & disk verification step."

            target_fn = "script.py"
            fn_match = re.search(r'[\'"]?([a-zA-Z0-9_\-\/]+\.(py|js|html|css|json|md))[\'"]?', query, re.IGNORECASE)
            if fn_match:
                target_fn = fn_match.group(1).strip('\'"')

            steps = [
                PlanStep(
                    step_id="step_1",
                    title="⚡ Code Generation & AST Validation",
                    description=f"Generate high-quality solution for query and validate syntax.",
                    target_file=target_fn,
                    action_type="create_file",
                    assigned_role="Neo Coding Agent"
                )
            ]

        return ExecutionPlan(plan_id=plan_id, title=plan_title, summary=summary, steps=steps)
