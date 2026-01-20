"""
LLM Parser - Tier 3 Intent Classification using Qwen3-1.7B

This module provides LLM-based intent classification as a fallback when
heuristic and adapt parsers fail to match user queries.

Features:
- Qwen3-1.7B model with Q4_K_M quantization
- Hybrid thinking mode support (fast vs reasoning)
- 5-second timeout per inference
- Graceful error handling
- Prometheus metrics integration
"""

import json
import time
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    logging.warning("llama-cpp-python not available. LLM tier will be disabled.")


class Qwen3Parser:
    """
    Qwen3-1.7B-based intent parser for natural language queries.
    
    Uses llama-cpp-python for CPU inference with Q4_K_M quantization.
    Supports both fast (non-thinking) and reasoning (thinking) modes.
    """
    
    def __init__(self, model_path: str, thinking_enabled: bool = False):
        """
        Initialize Qwen3Parser.
        
        Args:
            model_path: Path to GGUF model file
            thinking_enabled: Enable reasoning mode (slower but more accurate)
        """
        self.model_path = Path(model_path)
        self.thinking_enabled = thinking_enabled
        self.model: Optional[Llama] = None
        self.logger = logging.getLogger("enms_ovos_skill.llm_parser")
        
        # Model configuration
        self.context_size = 4096  # Reduced from 32K for speed
        self.max_tokens = 512  # Response limit
        self.temperature = 0.1  # Low temp for deterministic outputs
        self.timeout = 30.0  # 30-second timeout (increased from 5s - LLM needs 15-30s)
        
        # Metrics (can be exported to Prometheus)
        self.metrics = {
            "inferences_total": 0,
            "inferences_success": 0,
            "inferences_failure": 0,
            "inference_duration_ms": [],
            "timeout_count": 0
        }
    
    def load_model(self) -> None:
        """
        Load Qwen3-1.7B model into memory.
        
        Raises:
            FileNotFoundError: If model file doesn't exist
            RuntimeError: If llama-cpp-python not available or model fails to load
        """
        if not LLAMA_CPP_AVAILABLE:
            raise RuntimeError("llama-cpp-python not installed. Cannot load LLM.")
        
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {self.model_path}. "
                "Ensure model was downloaded during Docker build."
            )
        
        self.logger.info(
            f"Loading Qwen3-1.7B model from {self.model_path} "
            f"(thinking_mode={'ON' if self.thinking_enabled else 'OFF'})"
        )
        
        start = time.time()
        
        try:
            self.model = Llama(
                model_path=str(self.model_path),
                n_ctx=self.context_size,
                n_threads=4,  # Use 4 CPU cores
                n_batch=64,  # Minimum batch size (llama.cpp requires >=64)
                n_gpu_layers=0,  # CPU-only inference
                verbose=False
            )
            elapsed = time.time() - start
            self.logger.info(f"Model loaded successfully in {elapsed:.1f}s")
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise RuntimeError(f"Model loading failed: {e}")
    
    def parse(
        self,
        utterance: str,
        machines: List[str],
        intents: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse utterance and extract intent/entities using LLM.
        
        Args:
            utterance: User query text
            machines: List of valid machine names
            intents: List of valid intent types
        
        Returns:
            Dict with 'intent', 'machine', 'confidence' keys, or None on failure
        
        Example:
            >>> parser.parse(
            ...     "which machines waste electricity",
            ...     machines=["Compressor-1"],
            ...     intents=["ranking", "energy_query"]
            ... )
            {'intent': 'ranking', 'machine': None, 'confidence': 0.85}
        """
        if not self.model:
            self.logger.warning("Model not loaded. Skipping LLM parsing.")
            return None
        
        self.metrics["inferences_total"] += 1
        start = time.time()
        
        try:
            # Build prompt using llm_prompts module
            from .llm_prompts import build_intent_classification_prompt
            
            prompt = build_intent_classification_prompt(
                utterance=utterance,
                machines=machines,
                intents=intents,
                thinking_mode=self.thinking_enabled
            )
            
            # Call LLM with timeout
            self.logger.debug(f"LLM inference starting: '{utterance}'")
            
            response = self.model(
                prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stop=["</s>", "\n\n"],  # Stop tokens
                echo=False
            )
            
            elapsed_ms = (time.time() - start) * 1000
            
            # Check timeout
            if elapsed_ms > (self.timeout * 1000):
                self.logger.warning(
                    f"LLM inference timeout ({elapsed_ms:.0f}ms > {self.timeout*1000:.0f}ms)"
                )
                self.metrics["timeout_count"] += 1
                self.metrics["inferences_failure"] += 1
                return None
            
            # Parse JSON response
            text = response["choices"][0]["text"].strip()
            result = self._parse_json_response(text)
            
            if result:
                self.metrics["inferences_success"] += 1
                self.metrics["inference_duration_ms"].append(elapsed_ms)
                
                self.logger.info(
                    f"LLM parsed: intent={result.get('intent')}, "
                    f"machine={result.get('machine')}, "
                    f"confidence={result.get('confidence'):.2f}, "
                    f"latency={elapsed_ms:.0f}ms"
                )
                return result
            else:
                self.metrics["inferences_failure"] += 1
                return None
                
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            self.logger.error(f"LLM inference error after {elapsed_ms:.0f}ms: {e}")
            self.metrics["inferences_failure"] += 1
            return None
    
    def _parse_json_response(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse LLM JSON response and validate fields.
        
        Args:
            text: Raw LLM output text
        
        Returns:
            Validated dict or None if parsing fails
        """
        # Remove markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        try:
            data = json.loads(text)
            
            # Validate required fields
            if "intent" not in data:
                self.logger.warning(f"Missing 'intent' field in LLM response: {text}")
                return None
            
            # Validate confidence (default to 0.5 if missing)
            confidence = data.get("confidence", 0.5)
            if not (0.0 <= confidence <= 1.0):
                self.logger.warning(f"Invalid confidence value: {confidence}")
                confidence = 0.5
            
            return {
                "intent": data["intent"],
                "machine": data.get("machine"),
                "confidence": confidence,
                "entities": data.get("entities", {}),
                "tier": "llm"
            }
            
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse LLM JSON response: {e}\nText: {text}")
            return None
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get parser metrics for monitoring."""
        avg_duration = (
            sum(self.metrics["inference_duration_ms"]) / len(self.metrics["inference_duration_ms"])
            if self.metrics["inference_duration_ms"]
            else 0
        )
        
        return {
            "total_inferences": self.metrics["inferences_total"],
            "success_count": self.metrics["inferences_success"],
            "failure_count": self.metrics["inferences_failure"],
            "timeout_count": self.metrics["timeout_count"],
            "success_rate": (
                self.metrics["inferences_success"] / self.metrics["inferences_total"]
                if self.metrics["inferences_total"] > 0
                else 0.0
            ),
            "avg_duration_ms": round(avg_duration, 1),
            "thinking_enabled": self.thinking_enabled
        }
    
    def __repr__(self) -> str:
        return (
            f"Qwen3Parser(model_loaded={self.model is not None}, "
            f"thinking={self.thinking_enabled})"
        )
