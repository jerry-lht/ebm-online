"""Seven-domain RoB method using five LLM domains plus baseline fallbacks."""

from ebm_backend.online_pipeline.infrastructure.methods.risk_of_bias.method_onestep_llm.method import Method, build_method

__all__ = ["Method", "build_method"]
