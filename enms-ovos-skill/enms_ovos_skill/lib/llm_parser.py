"""
LLM Parser - Tier 3 Intent Classification using a local Qwen GGUF model

This module provides LLM-based intent classification as a fallback when
heuristic and adapt parsers fail to match user queries.

Features:
- Qwen3.5-2B model with Q4_K_M quantization
- Hybrid thinking mode support (fast vs reasoning)
- 30-second timeout per inference
- Graceful error handling
- Prometheus metrics integration
"""

import json
import os
import time
import logging
import threading
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
    Qwen-based intent parser for natural language queries.
    
    Uses llama-cpp-python for CPU inference with Q4_K_M quantization.
    Supports both fast (non-thinking) and reasoning (thinking) modes.
    """

    INTENT_ALIASES = {
        "clarification_needed": "unknown",
        "anomaly_query": "anomaly_detection",
        "efficiency": "performance",
        "baseline_prediction": "forecast",
    }
    
    def __init__(self, model_path: str = "./models/Qwen3.5-2B-Q4_K_M.gguf", thinking_enabled: bool = False):
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
        self._inference_lock = threading.Lock()
        
        # Model configuration
        self.context_size = 4096  # Reduced from 32K for speed
        self.max_tokens = 64  # JSON classification should stay very short
        self.temperature = 0.0  # Deterministic intent classification
        self.timeout = 30.0  # 30-second timeout (increased from 5s - LLM needs 15-30s)
        self.stop_tokens = ["\n\n", "</s>", "<|im_end|>", "<|endoftext|>"]
        
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
        Load the configured GGUF model into memory.
        
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
            f"Loading LLM model from {self.model_path} "
            f"(thinking_mode={'ON' if self.thinking_enabled else 'OFF'})"
        )
        
        start = time.time()
        
        try:
            cpu_threads = max(4, min(8, os.cpu_count() or 4))
            self.model = Llama(
                model_path=str(self.model_path),
                n_ctx=self.context_size,
                n_threads=cpu_threads,
                n_batch=128,
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
        machines: Optional[List[str]] = None,
        intents: Optional[List[str]] = None
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
        machines = machines or [
            "Boiler-1", "Compressor-1", "Compressor-EU-1", "Conveyor-A",
            "HVAC-EU-North", "HVAC-Main", "Hydraulic-Pump-1", "Injection-Molding-1"
        ]
        intents = intents or [
            "power_query", "energy_query", "machine_status", "ranking",
            "factory_overview", "comparison", "forecast", "anomaly_detection",
            "baseline_models", "baseline_explanation", "driver_analysis", "kpi"
        ]
        
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
            text = self._call_llm(prompt)
            if not text:
                self.metrics["inferences_failure"] += 1
                return None
            
            elapsed_ms = (time.time() - start) * 1000
            
            # Check timeout
            if elapsed_ms > (self.timeout * 1000):
                self.logger.warning(
                    f"LLM inference timeout ({elapsed_ms:.0f}ms > {self.timeout*1000:.0f}ms)"
                )
                self.metrics["timeout_count"] += 1
                self.metrics["inferences_failure"] += 1
                return None
            
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

    def _call_llm(self, prompt: str) -> Optional[str]:
        """Run the local model and return raw text. Kept patchable for tests."""
        if not self.model:
            self.logger.warning("Model not loaded. Skipping LLM parsing.")
            return None

        # llama-cpp inference is not safe to run concurrently on the same model instance.
        with self._inference_lock:
            response = self.model(
                prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stop=self.stop_tokens,
                echo=False
            )
        return response["choices"][0]["text"].strip()
    
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

        if "</think>" in text:
            text = text.rsplit("</think>", 1)[1].strip()

        text = self._extract_first_json_object(text)
        
        try:
            data = json.loads(text)
            
            # Validate required fields
            if "intent" not in data:
                self.logger.warning(f"Missing 'intent' field in LLM response: {text}")
                return None

            raw_intent = str(data["intent"]).strip().lower()
            normalized_intent = self.INTENT_ALIASES.get(raw_intent, raw_intent)
            
            # Validate confidence (default to 0.5 if missing)
            confidence = float(data.get("confidence", 0.5))
            if not (0.0 <= confidence <= 1.0):
                self.logger.warning(f"Invalid confidence value: {confidence}")
                confidence = 0.5

            machine = data.get("machine")
            if isinstance(machine, str) and machine.strip().lower() in {"", "none", "null"}:
                machine = None
            
            result = {
                "intent": normalized_intent,
                "machine": machine,
                "confidence": confidence,
                "entities": data.get("entities", {}),
                "tier": "llm"
            }
            for key in (
                "metric", "limit", "machines", "time_range", "energy_source",
                "ranking_metric", "driver_name", "aggregation"
            ):
                if key in data:
                    result[key] = data[key]
            return result

        except (TypeError, ValueError) as e:
            self.logger.warning(f"Invalid LLM response payload: {e}\nText: {text}")
            return None
        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse LLM JSON response: {e}\nText: {text}")
            return None

    def _extract_first_json_object(self, text: str) -> str:
        """Extract the first balanced JSON object from mixed LLM output."""
        start = text.find("{")
        if start == -1:
            return text

        depth = 0
        in_string = False
        escaped = False
        for index in range(start, len(text)):
            char = text[index]
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return text[start:index + 1]

        return text[start:]
    
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
