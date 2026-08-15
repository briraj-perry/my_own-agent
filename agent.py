"""Root-level agent compatibility shim.

This module provides backward-compatible imports for the agent package.
All actual agent logic lives in the agent/ package directory.
"""

from agent import NeoAgentCore, ClawAgentEngine

__all__ = ["NeoAgentCore", "ClawAgentEngine"]