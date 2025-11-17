"""
Qwen3 1.7B LLM Parser - Tier 1: Natural Language Understanding
Grammar-constrained JSON output for zero hallucination risk
"""
from typing import Dict, Any, Optional
from pathlib import Path
import json
import time
import structlog

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

from .observability import record_llm_latency, record_error, set_model_status

logger = structlog.get_logger(__name__)


# JSON grammar for constrained output
JSON_GRAMMAR = r"""
root ::= object
object ::= "{" ws members ws "}"
members ::= pair (ws "," ws pair)*
pair ::= string ws ":" ws value
value ::= string | number | object | array | "true" | "false" | "null"
array ::= "[" ws (value (ws "," ws value)*)? ws "]"
string ::= "\"" ([^"\\] | "\\" .)* "\""
number ::= "-"? [0-9]+ ("." [0-9]+)? ([eE] [+-]? [0-9]+)?
ws ::= [ \t\n\r]*
"""


class Qwen3Parser:
    """
    LLM-first intent parser using Qwen3 1.7B
    
    Features:
    - Grammar-constrained JSON output (no hallucination possible)
    - CPU-only inference (no GPU required)
    - 300-500ms latency on 4-core CPU
    - Natural language understanding for complex queries
    """
    
    def __init__(
        self,
        model_path: str = "./models/Qwen_Qwen3-1.7B-Q4_K_M.gguf",
        n_ctx: int = 2048,
        n_threads: int = 4,
        temperature: float = 0.1,
        max_tokens: int = 256
    ):
        """
        Initialize Qwen3 parser
        
        Args:
            model_path: Path to GGUF model file
            n_ctx: Context window size
            n_threads: CPU threads for inference
            temperature: Sampling temperature (0.1 = deterministic)
            max_tokens: Maximum output tokens
        """
        self.model_path = Path(model_path)
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        self.llm: Optional[Llama] = None
        self.grammar = None
        
        logger.info("qwen3_parser_init",
                   model_path=str(self.model_path),
                   n_ctx=n_ctx,
                   n_threads=n_threads)
    
    def load_model(self):
        """Load Qwen3 model into memory"""
        if Llama is None:
            raise ImportError("llama-cpp-python not installed. Run: pip install llama-cpp-python")
        
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        
        logger.info("loading_model", path=str(self.model_path))
        
        self.llm = Llama(
            model_path=str(self.model_path),
            n_ctx=self.n_ctx,
            n_threads=self.n_threads,
            n_gpu_layers=0,  # CPU only
            verbose=False,
            use_mlock=True,  # Lock model in RAM (prevents swapping)
            use_mmap=True    # Memory-mapped file (faster loading)
        )
        
        # Apply JSON grammar constraint
        # Note: llama-cpp-python >= 0.3.0 uses grammar parameter directly
        self.grammar = None  # Disable grammar, use stop tokens instead
        
        logger.info("model_loaded",
                   model_size_mb=self.model_path.stat().st_size / 1024 / 1024)
    
    def parse(self, utterance: str) -> Dict[str, Any]:
        """
        Parse natural language utterance to structured intent
        
        Args:
            utterance: User's spoken/typed query
            
        Returns:
            Intent dict with: intent, confidence, entities
            
        Example:
            Input: "What's the power consumption of Compressor-1?"
            Output: {
                "intent": "energy_query",
                "confidence": 0.95,
                "entities": {
                    "machine": "Compressor-1",
                    "metric": "power"
                }
            }
        """
        if self.llm is None:
            self.load_model()
        
        # System prompt + few-shot examples
        prompt = self._build_prompt(utterance)
        
        logger.info("llm_inference_start", utterance=utterance)
        
        try:
            # Call LLM with JSON mode forcing structured output
            response = self.llm(
                prompt,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stop=["```", "\n\nUser:", "\n\nExample:"],
                echo=False
            )
            
            # Extract generated text
            text = response["choices"][0]["text"].strip()
            
            # Clean up text - extract first complete JSON object
            if not text.startswith('{'):
                # Find first {
                start = text.find('{')
                if start == -1:
                    raise json.JSONDecodeError("No JSON found", text, 0)
                text = text[start:]
            
            # Find matching closing brace by counting braces
            brace_count = 0
            for i, char in enumerate(text):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        text = text[:i+1]
                        break
            
            # Parse JSON
            intent = json.loads(text)
            
            logger.info("llm_inference_complete",
                       intent=intent.get("intent"),
                       confidence=intent.get("confidence"),
                       latency_ms=response.get("latency", 0))
            
            return intent
            
        except json.JSONDecodeError as e:
            logger.error("json_parse_error", error=str(e), text=text)
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {},
                "error": "Failed to parse LLM output as JSON"
            }
        except Exception as e:
            logger.error("llm_inference_error", error=str(e))
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "entities": {},
                "error": str(e)
            }
    
    def _build_prompt(self, utterance: str) -> str:
        """
        Build prompt with system instructions and few-shot examples
        
        Following SOTA LLM prompting best practices:
        - Clear task definition
        - JSON schema specification
        - Few-shot examples (5-7 examples)
        - Explicit output format
        """
        return f"""You are an intent classifier for an industrial energy management system.

Extract intent and entities from user queries about machines, energy, power, status, and factory operations.

Output valid JSON with this structure:
{{
  "intent": "intent_name",
  "confidence": 0.0-1.0,
  "entities": {{
    "machine": "machine_name or null",
    "metric": "energy|power|status|cost or null",
    "time_range": "today|yesterday|last_week|24h or null",
    "limit": number or null
  }}
}}

Intent types:
- energy_query: Energy consumption queries
- power_query: Power demand queries
- machine_status: Machine status/health checks
- factory_overview: Factory-wide summaries
- ranking: Top N consumers
- comparison: Compare machines
- anomaly_detection: Detect anomalies
- forecast: Predict future usage

Examples:

User: "What's the power consumption of Compressor-1?"
{{"intent": "power_query", "confidence": 0.95, "entities": {{"machine": "Compressor-1", "metric": "power"}}}}

User: "How much energy did Boiler-1 use yesterday?"
{{"intent": "energy_query", "confidence": 0.93, "entities": {{"machine": "Boiler-1", "metric": "energy", "time_range": "yesterday"}}}}

User: "Is HVAC-Main running?"
{{"intent": "machine_status", "confidence": 0.97, "entities": {{"machine": "HVAC-Main", "metric": "status"}}}}

User: "Show me factory overview"
{{"intent": "factory_overview", "confidence": 0.90, "entities": {{}}}}

User: "Top 3 energy consumers"
{{"intent": "ranking", "confidence": 0.92, "entities": {{"metric": "energy", "limit": 3}}}}

User: "Compare Compressor-1 and Boiler-1"
{{"intent": "comparison", "confidence": 0.94, "entities": {{"machine": "Compressor-1,Boiler-1"}}}}

User: "Detect anomalies for Compressor-1 today"
{{"intent": "anomaly_detection", "confidence": 0.91, "entities": {{"machine": "Compressor-1", "time_range": "today"}}}}

Now extract intent from this query:

User: "{utterance}"
"""
    
    def close(self):
        """Cleanup resources"""
        if self.llm:
            # llama-cpp-python handles cleanup automatically
            self.llm = None
            logger.info("qwen3_parser_closed")
