"""
RTI Scoring Architect: Mandatory "Consider the Opposite" Protocols
==================================================================

This module implements comprehensive scoring reforms for the ACT-I Colosseum
with mandatory opposition protocols and context calibration systems.

Key Features:
- Mandatory "consider the opposite" protocols for ALL judge decisions
- Context calibration systems that require complete fact explanation
- Threshold enforcement preventing scores without full justification
- Conflict detection and resolution mechanisms
- Real-time calibration against established baselines

Author: RTI Scoring Architect (Subagent)
Date: 2026-02-23
"""

import json
import time
import asyncio
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
from openai import AsyncOpenAI

client = AsyncOpenAI()

@dataclass
class OppositionAnalysis:
    """Data structure for "consider the opposite" analysis"""
    original_score: float
    original_reasoning: str
    opposite_perspective: str
    conflicting_evidence: List[str]
    uncertainty_factors: List[str]
    alternative_interpretation: str
    final_calibrated_score: float
    confidence_level: float
    bias_detected: List[str]

@dataclass
class ContextCalibration:
    """Context calibration requirements for scoring"""
    scenario_context: str
    being_context: str
    judge_perspective: str
    environmental_factors: List[str]
    calibration_baseline: float
    deviation_justification: str
    fact_completeness_score: float

@dataclass
class ThresholdEnforcement:
    """Threshold enforcement data"""
    minimum_explanation_length: int
    required_evidence_points: int
    mandatory_fact_categories: List[str]
    conflict_resolution_required: bool
    calibration_drift_threshold: float

class RTIScoringArchitect:
    """
    RTI Scoring Architect implementing mandatory opposition protocols
    and comprehensive context calibration systems.
    """
    
    def __init__(self):
        self.threshold_config = ThresholdEnforcement(
            minimum_explanation_length=200,  # chars minimum
            required_evidence_points=3,
            mandatory_fact_categories=[
                "being_performance",
                "scenario_alignment", 
                "mastery_demonstration",
                "outcome_effectiveness"
            ],
            conflict_resolution_required=True,
            calibration_drift_threshold=1.0
        )
        
        self.calibration_baselines = self._load_calibration_baselines()
        
    def _load_calibration_baselines(self) -> Dict[str, float]:
        """Load calibration baselines for different judge types"""
        return {
            "formula_judge": 6.5,
            "sean_judge": 6.8,
            "outcome_judge": 7.0,
            "contamination_judge": 6.0,
            "human_judge": 6.5
        }
    
    async def execute_opposition_protocol(self, 
                                        judge_id: str, 
                                        initial_score: Dict[str, Any], 
                                        being: Dict[str, Any], 
                                        scenario: Dict[str, Any], 
                                        response: str) -> OppositionAnalysis:
        """
        Mandatory "consider the opposite" protocol for all judge decisions.
        NO SCORE is final without this analysis.
        """
        
        opposition_prompt = f"""
        MANDATORY OPPOSITION ANALYSIS - NO EXCEPTIONS
        
        You must analyze the OPPOSITE perspective of the initial scoring decision.
        
        INITIAL SCORE: {initial_score}
        BEING: {being['title']} ({being['area']})
        SCENARIO: {scenario['title']}
        RESPONSE: {response}
        
        REQUIRED OPPOSITION ANALYSIS:
        
        1. OPPOSITE PERSPECTIVE: What if this score is completely wrong? What evidence contradicts it?
        
        2. CONFLICTING EVIDENCE: List specific examples that could justify a LOWER score
        
        3. UNCERTAINTY FACTORS: What assumptions might be incorrect?
        
        4. ALTERNATIVE INTERPRETATION: How could this response be interpreted differently?
        
        5. BIAS DETECTION: What cognitive biases might have influenced the initial score?
        
        6. CALIBRATED FINAL SCORE: After considering opposition, what should the score be?
        
        7. CONFIDENCE LEVEL: How confident are you in this final score? (0.0-1.0)
        
        Return ONLY valid JSON in this format:
        {{
            "opposite_perspective": "detailed analysis",
            "conflicting_evidence": ["evidence1", "evidence2", "evidence3"],
            "uncertainty_factors": ["factor1", "factor2"],
            "alternative_interpretation": "alternative view",
            "bias_detected": ["bias1", "bias2"],
            "final_calibrated_score": 0.0,
            "confidence_level": 0.0
        }}
        
        CRITICAL: You MUST find legitimate opposition points. Generic analysis will be rejected.
        """
        
        try:
            response_obj = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a rigorous opposition analyst. Your job is to find legitimate flaws and alternative perspectives. Be thorough and specific."},
                    {"role": "user", "content": opposition_prompt}
                ],
                max_tokens=800,
                temperature=0.3
            )
            
            content = response_obj.choices[0].message.content
            
            # Clean JSON response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            
            opposition_data = json.loads(content.strip())
            
            return OppositionAnalysis(
                original_score=initial_score.get("overall", 0.0),
                original_reasoning=initial_score.get("feedback", ""),
                opposite_perspective=opposition_data["opposite_perspective"],
                conflicting_evidence=opposition_data["conflicting_evidence"],
                uncertainty_factors=opposition_data["uncertainty_factors"],
                alternative_interpretation=opposition_data["alternative_interpretation"],
                final_calibrated_score=opposition_data["final_calibrated_score"],
                confidence_level=opposition_data["confidence_level"],
                bias_detected=opposition_data["bias_detected"]
            )
            
        except Exception as e:
            # FAIL SAFE: No opposition analysis means no valid score
            return OppositionAnalysis(
                original_score=0.0,
                original_reasoning="FAILED OPPOSITION PROTOCOL",
                opposite_perspective="Opposition analysis required but failed",
                conflicting_evidence=["Protocol failure"],
                uncertainty_factors=["Analysis incomplete"],
                alternative_interpretation="No valid analysis",
                final_calibrated_score=0.0,
                confidence_level=0.0,
                bias_detected=["Analysis failure"]
            )
    
    async def execute_context_calibration(self, 
                                        judge_id: str, 
                                        score_data: Dict[str, Any], 
                                        being: Dict[str, Any], 
                                        scenario: Dict[str, Any]) -> ContextCalibration:
        """
        Context calibration system requiring ALL facts explanation.
        """
        
        baseline = self.calibration_baselines.get(judge_id, 6.0)
        
        calibration_prompt = f"""
        MANDATORY CONTEXT CALIBRATION - COMPLETE FACT ANALYSIS REQUIRED
        
        JUDGE: {judge_id}
        BASELINE EXPECTED SCORE: {baseline}
        ACTUAL SCORE: {score_data.get("overall", 0.0)}
        DEVIATION: {abs(score_data.get("overall", 0.0) - baseline)}
        
        BEING CONTEXT: {being['title']} - {being['area']}
        SCENARIO CONTEXT: {scenario['title']} - {scenario['situation']}
        
        REQUIRED COMPLETE FACT EXPLANATION:
        
        1. SCENARIO CONTEXT: How does the specific scenario context influence scoring?
        
        2. BEING CONTEXT: How does this being's specialization affect expected performance?
        
        3. JUDGE PERSPECTIVE: What is your specific judge perspective and how does it bias scoring?
        
        4. ENVIRONMENTAL FACTORS: What external factors might influence this score?
        
        5. CALIBRATION BASELINE: Why is this score above/below/at baseline expectations?
        
        6. DEVIATION JUSTIFICATION: If score deviates >1.0 from baseline, provide detailed justification
        
        7. FACT COMPLETENESS: Rate how completely you analyzed all available facts (0.0-1.0)
        
        Return ONLY valid JSON:
        {{
            "scenario_context_impact": "detailed analysis",
            "being_context_impact": "detailed analysis", 
            "judge_perspective_bias": "detailed analysis",
            "environmental_factors": ["factor1", "factor2"],
            "baseline_comparison": "detailed justification",
            "deviation_justification": "required if >1.0 deviation",
            "fact_completeness_score": 0.0
        }}
        
        CRITICAL: Fact completeness below 0.8 invalidates the score.
        """
        
        try:
            response_obj = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a rigorous context calibration analyst. Every score must be fully justified with complete fact analysis."},
                    {"role": "user", "content": calibration_prompt}
                ],
                max_tokens=600,
                temperature=0.3
            )
            
            content = response_obj.choices[0].message.content
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            
            calibration_data = json.loads(content.strip())
            
            return ContextCalibration(
                scenario_context=calibration_data["scenario_context_impact"],
                being_context=calibration_data["being_context_impact"],
                judge_perspective=calibration_data["judge_perspective_bias"],
                environmental_factors=calibration_data["environmental_factors"],
                calibration_baseline=baseline,
                deviation_justification=calibration_data["deviation_justification"],
                fact_completeness_score=calibration_data["fact_completeness_score"]
            )
            
        except Exception as e:
            # FAIL SAFE: No calibration means invalid score
            return ContextCalibration(
                scenario_context="CALIBRATION FAILED",
                being_context="CALIBRATION FAILED", 
                judge_perspective="CALIBRATION FAILED",
                environmental_factors=["Calibration failure"],
                calibration_baseline=baseline,
                deviation_justification="Analysis failed",
                fact_completeness_score=0.0
            )
    
    def enforce_thresholds(self, 
                          opposition_analysis: OppositionAnalysis, 
                          context_calibration: ContextCalibration, 
                          initial_score: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Enforce scoring thresholds - reject scores that don't meet requirements.
        """
        
        violations = []
        
        # Check minimum explanation length
        feedback = initial_score.get("feedback", "")
        if len(feedback) < self.threshold_config.minimum_explanation_length:
            violations.append(f"Explanation too short: {len(feedback)} < {self.threshold_config.minimum_explanation_length} chars")
        
        # Check evidence points
        if len(opposition_analysis.conflicting_evidence) < self.threshold_config.required_evidence_points:
            violations.append(f"Insufficient evidence points: {len(opposition_analysis.conflicting_evidence)} < {self.threshold_config.required_evidence_points}")
        
        # Check fact completeness
        if context_calibration.fact_completeness_score < 0.8:
            violations.append(f"Incomplete fact analysis: {context_calibration.fact_completeness_score} < 0.8")
        
        # Check confidence level
        if opposition_analysis.confidence_level < 0.6:
            violations.append(f"Low confidence in analysis: {opposition_analysis.confidence_level} < 0.6")
        
        # Check calibration drift
        drift = abs(initial_score.get("overall", 0.0) - context_calibration.calibration_baseline)
        if drift > self.threshold_config.calibration_drift_threshold:
            if not context_calibration.deviation_justification or len(context_calibration.deviation_justification) < 100:
                violations.append(f"Large calibration drift without justification: {drift}")
        
        return len(violations) == 0, violations
    
    def detect_conflicts(self, 
                        opposition_analysis: OppositionAnalysis, 
                        context_calibration: ContextCalibration, 
                        initial_score: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Detect unresolved conflicts in scoring analysis.
        """
        
        conflicts = []
        
        # Score vs opposition analysis conflict
        score_diff = abs(initial_score.get("overall", 0.0) - opposition_analysis.final_calibrated_score)
        if score_diff > 2.0:
            conflicts.append(f"Major score discrepancy: {score_diff} points between initial and opposition analysis")
        
        # High conflicting evidence but high final score
        if len(opposition_analysis.conflicting_evidence) >= 3 and opposition_analysis.final_calibrated_score > 7.0:
            conflicts.append("High conflicting evidence but high final score - unresolved contradiction")
        
        # Low confidence but definitive score
        if opposition_analysis.confidence_level < 0.7 and opposition_analysis.final_calibrated_score > 8.0:
            conflicts.append("Low confidence analysis but high definitive score")
        
        # High bias detection but no score adjustment
        if len(opposition_analysis.bias_detected) >= 2 and score_diff < 0.5:
            conflicts.append("Multiple biases detected but insufficient score adjustment")
        
        return len(conflicts) == 0, conflicts

async def rti_enhanced_judge_response(judge_key: str, 
                                    judge_data: Dict[str, Any], 
                                    being: Dict[str, Any], 
                                    scenario: Dict[str, Any], 
                                    response: str) -> Dict[str, Any]:
    """
    Enhanced judge response with mandatory RTI scoring protocols.
    
    NO SCORE is valid without:
    1. "Consider the opposite" analysis
    2. Complete context calibration  
    3. Threshold enforcement
    4. Conflict resolution
    """
    
    architect = RTIScoringArchitect()
    
    # Step 1: Get initial score (existing judge logic)
    initial_prompt = f"""BEING: {being['title']} ({being['area']})
SCENARIO: {scenario['title']} — {scenario['situation']}
SUCCESS CRITERIA: {scenario['success_criteria']}

THE BEING'S RESPONSE:
{response}

Score this response according to your criteria. Be rigorous. Be specific. Return ONLY valid JSON."""

    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": judge_data["prompt"]},
                {"role": "user", "content": initial_prompt}
            ],
            max_tokens=500,
            temperature=0.3
        )
        content = resp.choices[0].message.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        initial_score = json.loads(content.strip())
    except Exception as e:
        initial_score = {"error": str(e), "overall": 0.0, "feedback": "Initial scoring failed"}
    
    # Step 2: MANDATORY Opposition Protocol
    opposition_analysis = await architect.execute_opposition_protocol(
        judge_key, initial_score, being, scenario, response
    )
    
    # Step 3: MANDATORY Context Calibration
    context_calibration = await architect.execute_context_calibration(
        judge_key, initial_score, being, scenario
    )
    
    # Step 4: MANDATORY Threshold Enforcement
    thresholds_passed, threshold_violations = architect.enforce_thresholds(
        opposition_analysis, context_calibration, initial_score
    )
    
    # Step 5: MANDATORY Conflict Detection
    conflicts_resolved, detected_conflicts = architect.detect_conflicts(
        opposition_analysis, context_calibration, initial_score
    )
    
    # Step 6: Final Score Determination
    if not thresholds_passed or not conflicts_resolved:
        final_score = {
            "overall": 0.0,
            "feedback": "SCORE INVALIDATED - RTI Protocol Violations",
            "rti_status": "FAILED",
            "threshold_violations": threshold_violations,
            "detected_conflicts": detected_conflicts,
            "original_score": initial_score.get("overall", 0.0)
        }
    else:
        final_score = initial_score.copy()
        final_score["overall"] = opposition_analysis.final_calibrated_score
        final_score["rti_status"] = "VALIDATED"
        final_score["confidence_level"] = opposition_analysis.confidence_level
        final_score["fact_completeness"] = context_calibration.fact_completeness_score
    
    # Step 7: Comprehensive RTI Metadata
    final_score["rti_metadata"] = {
        "opposition_analysis": asdict(opposition_analysis),
        "context_calibration": asdict(context_calibration),
        "thresholds_enforced": {
            "passed": thresholds_passed,
            "violations": threshold_violations
        },
        "conflict_resolution": {
            "resolved": conflicts_resolved,
            "conflicts": detected_conflicts  
        },
        "processing_timestamp": time.time(),
        "protocol_version": "RTI-1.0"
    }
    
    return final_score

# Integration function to replace standard judge_response
async def judge_response_with_rti(judge_key: str, 
                                judge_data: Dict[str, Any], 
                                being: Dict[str, Any], 
                                scenario: Dict[str, Any], 
                                response: str) -> Dict[str, Any]:
    """
    Enhanced judge response function with mandatory RTI protocols.
    This replaces the standard judge_response function in tournament_v2.py
    """
    return await rti_enhanced_judge_response(judge_key, judge_data, being, scenario, response)

if __name__ == "__main__":
    print("RTI Scoring Architect initialized successfully!")
    print("\nKey Features Implemented:")
    print("✅ Mandatory 'consider the opposite' protocols")
    print("✅ Context calibration systems") 
    print("✅ Threshold enforcement requiring ALL facts explanation")
    print("✅ Conflict detection and resolution")
    print("✅ Real-time score validation")
    print("\nNO SCORE IS VALID WITHOUT COMPLETE RTI PROTOCOL EXECUTION")