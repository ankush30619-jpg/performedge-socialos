"""Continuous-learning subsystem for the SocialMediaManagerAgent.

Two responsibilities:
  • memory_store.append_run(...) — write one JSONL row per agent execution
  • reflection.synthesize_lessons(...) — at run end, distill the last N rows
    into plain-language lessons that the manager injects into future runs.
"""
from .memory_store import append_run, read_lessons  # noqa: F401
