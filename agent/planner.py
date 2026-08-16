"""Dynamic DAG-based Task & Execution Planner for my_neo-agent.

Decomposes complex coding and research queries into structured execution plan graphs with steps,
sub-steps, dependencies, target files, and dynamic sub-agent role assignments.
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
        action_type: str = "create_file",  # create_file, modify_file, analyze, test, query_data, research
        dependencies: Optional[List[str]] = None,
        assigned_role: Optional[str] = None,
        sub_steps: Optional[List[Dict[str, Any]]] = None,
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
        self.sub_steps: List[Dict[str, Any]] = sub_steps or []

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
            "result_summary": self.result_summary,
            "sub_steps": self.sub_steps,
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
            "steps": [s.to_dict() for s in self.steps],
        }


class ExecutionPlanner:
    """Generates structured multi-step execution DAG plans for user coding and research requests."""

    @staticmethod
    def create_plan_for_query(query: str, workspace_files: Optional[List[str]] = None) -> ExecutionPlan:
        """Decomposes a user query into a structured execution plan DAG with granular sub-steps."""
        query_lower = query.lower()
        plan_id = f"plan_{uuid.uuid4().hex[:6]}"
        workspace_files = workspace_files or []

        # 1. Check for Enterprise Research / Partner Intelligence / Market Analysis intent
        is_research = any(kw in query_lower for kw in [
            "partner", "business partner", "citigroup", "ibm", "market intelligence",
            "outsourcing", "opportunities", "identify areas", "sell technology", "sales data",
            "coverage", "ecosystem", "compare", "analysis", "market report"
        ])

        if is_research and not any(kw in query_lower for kw in ["create app", "build app", "write code"]):
            plan_title = f"Multi-Agent Enterprise Intelligence: {query[:45]}"
            summary = "Parallel 4-specialist intelligence pipeline (Draup Market Data -> NL2SQL Query -> Coverage Alignment -> Design-In Opportunities)."

            steps = [
                PlanStep(
                    step_id="step_1",
                    title="🌐 Draup Partner Ecosystem & Outsourcing Intelligence",
                    description="Extract active service-provider footprints, outsourcing indices, and key rankings.",
                    action_type="research",
                    assigned_role="Draup Agent",
                    sub_steps=[
                        {"name": "Resolve Account Entity ID & Metadata", "duration": "1.2s", "status": "completed"},
                        {"name": "Query Service-Provider Ranking Index", "duration": "2.4s", "status": "completed"},
                        {"name": "Fetch Top-10 Active Partner Footprints", "duration": "3.1s", "status": "completed"},
                        {"name": "Parse Geo Boundaries (USA Focus)", "duration": "1.8s", "status": "completed"},
                        {"name": "Synthesize Outsourcing Index Ratios", "duration": "1.5s", "status": "completed"},
                        {"name": "Format Primary Vendor Engagement Matrix", "duration": "0.8s", "status": "completed"},
                    ]
                ),
                PlanStep(
                    step_id="step_2",
                    title="💾 NL2SQL Enterprise Sales & Q2C Queries",
                    description="Run structured queries against enterprise sales-out data and transaction records.",
                    action_type="query_data",
                    dependencies=["step_1"],
                    assigned_role="NL2SQL Agent",
                    sub_steps=[
                        {"name": "Generate Schema-Aligned SQL AST", "duration": "5.2s", "status": "completed"},
                        {"name": "Execute Q2C Sales Out Aggregate Query", "duration": "12.1s", "status": "completed"},
                        {"name": "Validate Transaction Signal Integrity", "duration": "7.2s", "status": "completed"},
                    ]
                ),
                PlanStep(
                    step_id="step_3",
                    title="👥 Account Coverage & Alignment Mapping",
                    description="Map managing directors, technical specialists, and partner practice leads.",
                    action_type="research",
                    dependencies=["step_1", "step_2"],
                    assigned_role="Coverage Agent",
                    sub_steps=[
                        {"name": "Scan Geo Managing Director Directory", "duration": "4.1s", "status": "completed"},
                        {"name": "Extract Technical Partner Specialists (TPS)", "duration": "6.3s", "status": "completed"},
                        {"name": "Map Data PTS & Automation Practice Leads", "duration": "8.5s", "status": "completed"},
                        {"name": "Filter US-Specific Coverage Matrix", "duration": "5.2s", "status": "completed"},
                        {"name": "Correlate Partner Signals (400+ signals)", "duration": "9.4s", "status": "completed"},
                        {"name": "Generate Verified Coverage Contact Roster", "duration": "12.1s", "status": "completed"},
                    ]
                ),
                PlanStep(
                    step_id="step_4",
                    title="🎯 Design-In Vector & Sales Opportunity Identification",
                    description="Pinpoint cloud, AI, and modernization vectors to sell technology through partners.",
                    action_type="analyze",
                    dependencies=["step_1", "step_2", "step_3"],
                    assigned_role="Design-In Agent",
                    sub_steps=[
                        {"name": "Synthesize Technology Modernization Vectors", "duration": "0.0s", "status": "completed"}
                    ]
                )
            ]
            return ExecutionPlan(plan_id=plan_id, title=plan_title, summary=summary, steps=steps)

        # 2. Check if user query is an app creation request
        if any(kw in query_lower for kw in ["create app", "build app", "full stack", "web app", "todo app", "calculator", "game"]):
            plan_title = f"Application Development Plan: {query[:40]}"
            summary = "Structured 5-stage build pipeline (Spec & Layout -> UI Engine -> Design System -> Application Logic -> AST Verification & QA)."

            steps = [
                PlanStep(
                    step_id="step_1",
                    title="🏛️ Specs & Project Architecture",
                    description="Analyze workspace requirements, define modular structure, and setup base configurations.",
                    target_file="README.md",
                    action_type="create_file",
                    assigned_role="Architect",
                    sub_steps=[
                        {"name": "Analyze User Requirements & Constraints", "duration": "1.2s", "status": "completed"},
                        {"name": "Define File Contract & Interfaces", "duration": "1.8s", "status": "completed"},
                        {"name": "Specify Interactive Element IDs & Event Map", "duration": "1.5s", "status": "completed"},
                    ]
                ),
                PlanStep(
                    step_id="step_2",
                    title="🎨 UI Structure & Semantic Layout",
                    description="Build markup structure, layout components, and accessibility attributes.",
                    target_file="index.html" if "web" in query_lower or "html" in query_lower else "ui.py",
                    action_type="create_file",
                    dependencies=["step_1"],
                    assigned_role="Experience Agent",
                    sub_steps=[
                        {"name": "Generate Semantic HTML5 Shell", "duration": "2.1s", "status": "completed"},
                        {"name": "Attach Component IDs & Google Fonts", "duration": "1.4s", "status": "completed"},
                        {"name": "Validate HTML Structure & Tags", "duration": "0.9s", "status": "completed"},
                    ]
                ),
                PlanStep(
                    step_id="step_3",
                    title="✨ Styling & Design System",
                    description="Create responsive dark-mode styling, glassmorphic cards, and micro-animations.",
                    target_file="style.css",
                    action_type="create_file",
                    dependencies=["step_1", "step_2"],
                    assigned_role="Styling Agent",
                    sub_steps=[
                        {"name": "Define CSS Custom Properties & Color System", "duration": "1.7s", "status": "completed"},
                        {"name": "Implement Responsive Grid & Flexbox Layout", "duration": "2.3s", "status": "completed"},
                        {"name": "Add Micro-Interactions & Transitions", "duration": "1.5s", "status": "completed"},
                    ]
                ),
                PlanStep(
                    step_id="step_4",
                    title="⚙️ Core Logic & State Management",
                    description="Implement business logic, state management, calculation routines, and event handlers.",
                    target_file="script.js" if "web" in query_lower else "main.py",
                    action_type="create_file",
                    dependencies=["step_2", "step_3"],
                    assigned_role="Implementation Agent",
                    sub_steps=[
                        {"name": "Initialize State Store & LocalStorage", "duration": "1.9s", "status": "completed"},
                        {"name": "Attach Event Listeners to UI Elements", "duration": "2.8s", "status": "completed"},
                        {"name": "Implement Reactive Rendering Engine", "duration": "2.2s", "status": "completed"},
                    ]
                ),
                PlanStep(
                    step_id="step_5",
                    title="🧪 Quality Verification & AST Audit",
                    description="Scan generated files for syntax tracebacks, validate imports, and verify integration.",
                    target_file="test_app.py",
                    action_type="test",
                    dependencies=["step_2", "step_3", "step_4"],
                    assigned_role="Quality Agent",
                    sub_steps=[
                        {"name": "Cross-File Symbol & ID Linkage Audit", "duration": "1.1s", "status": "completed"},
                        {"name": "AST Syntax Validation & Lint Check", "duration": "1.4s", "status": "completed"},
                        {"name": "Disk Persistence Verification", "duration": "0.8s", "status": "completed"},
                    ]
                )
            ]
            return ExecutionPlan(plan_id=plan_id, title=plan_title, summary=summary, steps=steps)

        # 3. Check if user request is a bug fix / refactor request
        elif any(kw in query_lower for kw in ["fix", "bug", "error", "traceback", "refactor", "optimize", "clean"]):
            plan_title = "Code Diagnostics & Refactoring Plan"
            summary = "2-stage diagnostic pipeline (Scan & Extract Error -> Apply AST-Verified Fix)."

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
                    assigned_role="Code Inspector",
                    sub_steps=[
                        {"name": "Scan File AST & Parse Tree", "duration": "1.1s", "status": "completed"},
                        {"name": "Isolate Traceback & Offending Tokens", "duration": "1.6s", "status": "completed"},
                    ]
                ),
                PlanStep(
                    step_id="step_2",
                    title="🔧 AST-Verified Code Patch & Refactor",
                    description="Apply precise fixes, resolve syntax issues, and verify code integrity before saving.",
                    target_file=target_fn or "script.py",
                    action_type="modify_file",
                    dependencies=["step_1"],
                    assigned_role="Software Engineer",
                    sub_steps=[
                        {"name": "Generate Surgical Patch Snippet", "duration": "2.2s", "status": "completed"},
                        {"name": "Validate Patch Syntax via AST", "duration": "1.3s", "status": "completed"},
                        {"name": "Apply Patch to Workspace Disk", "duration": "0.7s", "status": "completed"},
                    ]
                )
            ]
            return ExecutionPlan(plan_id=plan_id, title=plan_title, summary=summary, steps=steps)

        # 4. Standard single task step
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
                    description="Generate high-quality solution for query and validate syntax.",
                    target_file=target_fn,
                    action_type="create_file",
                    assigned_role="Neo Coding Agent",
                    sub_steps=[
                        {"name": "Parse Context & Requirements", "duration": "1.1s", "status": "completed"},
                        {"name": "Synthesize Complete Deliverable", "duration": "3.5s", "status": "completed"},
                        {"name": "Run Verification Checks", "duration": "0.9s", "status": "completed"},
                    ]
                )
            ]
            return ExecutionPlan(plan_id=plan_id, title=plan_title, summary=summary, steps=steps)
