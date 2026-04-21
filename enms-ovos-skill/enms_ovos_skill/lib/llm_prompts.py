"""
LLM Prompt Templates for Intent Classification

Provides structured prompts for the configured Qwen GGUF model to classify
user intents and extract entities from natural language queries.
"""

from typing import List


def build_intent_classification_prompt(
    utterance: str,
    machines: List[str],
    intents: List[str],
    thinking_mode: bool = False
) -> str:
    """
    Build intent classification prompt for the configured Qwen model.
    
    Args:
        utterance: User query text
        machines: List of valid machine names
        intents: List of valid intent types
        thinking_mode: Enable reasoning mode (adds thinking instructions)
    
    Returns:
        Formatted prompt string with few-shot examples
    """
    
    # Format machine list (limit to first 20 for context size)
    machine_list = ", ".join(machines[:20])
    if len(machines) > 20:
        machine_list += f", ... ({len(machines)} total)"
    
    # Format intent list
    intent_list = ", ".join(intents[:30])
    if len(intents) > 30:
        intent_list += f", ... ({len(intents)} total)"
    
    mode_instruction = "/think" if thinking_mode else "/no_think"

    # Base prompt
    prompt = f"""You are an intent classifier for an industrial energy management system (EnMS).

Your task: classify the user's query and extract relevant entities.
Return exactly one compact JSON object and nothing else.
Use only the valid intents listed below.
Mode: {mode_instruction}

Valid intents: [{intent_list}]

Valid machines: [{machine_list}]

"""
    
    # Add thinking mode instructions
    if thinking_mode:
        prompt += """REASONING MODE: Think step-by-step before answering. Consider:
1. What is the user asking for? (energy data, power data, predictions, etc.)
2. Which machine(s) are mentioned? (exact name or fuzzy match)
3. What time period is implied? (current, historical, future)
4. What is the confidence level? (0.0-1.0)

"""
    
    # Add few-shot examples
    prompt += f"""Examples:

Query: "how much energy did compressor one use?"
Output: {{"intent": "energy_query", "machine": "Compressor-1", "confidence": 0.98}}

Query: "what's the power of boiler right now?"
Output: {{"intent": "power_query", "machine": "Boiler-1", "confidence": 0.95}}

Query: "which machines are wasting electricity?"
Output: {{"intent": "ranking", "machine": null, "confidence": 0.85}}

Query: "show me top 5 energy consumers"
Output: {{"intent": "ranking", "machine": null, "confidence": 0.92}}

Query: "predicted energy for compressor"
Output: {{"intent": "forecast", "machine": "Compressor-1", "confidence": 0.88}}

Query: "factory status"
Output: {{"intent": "factory_overview", "machine": null, "confidence": 0.99}}

Query: "give me a breakdown of where power is going"
Output: {{"intent": "ranking", "machine": null, "confidence": 0.80}}

Query: "how efficient is HVAC?"
Output: {{"intent": "performance", "machine": "HVAC-Main", "confidence": 0.85}}

Query: "are there any anomalies in the system?"
Output: {{"intent": "anomaly_detection", "machine": null, "confidence": 0.90}}

Query: "compare boiler 1 and boiler 2"
Output: {{"intent": "comparison", "machine": null, "confidence": 0.90}}

Query: "what time is it?"
Output: {{"intent": "unknown", "machine": null, "confidence": 0.10}}

"""
    
    # Add instructions
    prompt += f"""Instructions:
1. Normalize machine names (e.g., "compressor one" → "Compressor-1", "hvac" → "HVAC-Main")
2. Return confidence 0.0-1.0 (>0.7 = high confidence, 0.5-0.7 = medium, <0.5 = low)
3. If query is off-topic or unclear, use intent="unknown" with confidence < 0.5
4. Respond with ONLY valid JSON on a single line (no markdown, no analysis, no extra text)
5. Required fields: intent, machine (or null), confidence
6. If no machine is clearly mentioned, set machine to null

User query: "{utterance}"

Output:"""
    
    return prompt


def build_thinking_prompt(utterance: str) -> str:
    """
    Build prompt for reasoning mode (complex queries).
    
    This is for future enhancement - currently integrated into
    build_intent_classification_prompt via thinking_mode parameter.
    """
    return f"""Think step-by-step about this query:

"{utterance}"

Consider:
1. What is the user's goal?
2. What data do they need?
3. What calculations might be required?
4. How confident are you in your understanding?

Now classify the intent and provide your reasoning:"""
