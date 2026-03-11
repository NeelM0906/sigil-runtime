"""
RTI Validation Suite: Testing & Verification of "Consider the Opposite" Protocols
=================================================================================

Comprehensive testing suite to validate RTI Scoring Architect implementation:
- Protocol compliance verification
- Edge case testing
- Bias detection validation
- Threshold enforcement testing
- Conflict resolution verification

Author: RTI Scoring Architect (Subagent)
Date: 2026-02-23
"""

import json
import asyncio
import time
from typing import Dict, List, Any, Tuple
from dataclasses import asdict
from rti_scoring_architect import (
    RTIScoringArchitect, 
    rti_enhanced_judge_response,
    OppositionAnalysis,
    ContextCalibration
)

# Test data
TEST_BEING = {
    "id": "test_being_001",
    "title": "Test Master Strategist",
    "area": "Strategic Planning",
    "dna": "You are a master strategist focused on systematic approaches to complex problems."
}

TEST_SCENARIO = {
    "title": "Resource Allocation Crisis",
    "company": "Test Corp",
    "situation": "Multiple departments competing for limited engineering resources",
    "person": {"name": "Test Manager", "role": "Engineering Director"},
    "success_criteria": "Resolve conflict while maintaining team morale and project timelines"
}

TEST_JUDGE = {
    "name": "Test Judge",
    "focus": "Tests systematic decision-making and conflict resolution",
    "prompt": """You are a Test Judge evaluating systematic decision-making and conflict resolution.
    
SCORING (0-9.9999):
- SYSTEMATIC_APPROACH: How well-structured is the decision-making process?
- CONFLICT_RESOLUTION: How effectively are competing interests balanced?
- TEAM_MORALE: How well does the solution preserve team dynamics?
- TIMELINE_MANAGEMENT: How effectively are project timelines preserved?
- OVERALL: Overall effectiveness of the solution

Return JSON: {"systematic_approach": X, "conflict_resolution": X, "team_morale": X, "timeline_management": X, "overall": X, "feedback": "detailed feedback"}"""
}

class RTIValidationSuite:
    """Comprehensive validation suite for RTI protocols"""
    
    def __init__(self):
        self.architect = RTIScoringArchitect()
        self.test_results = []
        
    async def test_opposition_protocol_compliance(self) -> Dict[str, Any]:
        """Test that opposition protocol finds legitimate opposition points"""
        
        print("🔍 Testing Opposition Protocol Compliance...")
        
        # High-scoring response that should have opposition points
        high_score_response = """
        I propose a collaborative prioritization framework using time-blocking principles.
        We'll create shared resource calendars and rotate engineering focus across departments
        based on urgency and strategic impact. This ensures all teams feel heard while
        maximizing resource utilization efficiency.
        """
        
        initial_score = {
            "systematic_approach": 8.5,
            "conflict_resolution": 8.0,
            "team_morale": 7.5,
            "timeline_management": 8.0,
            "overall": 8.0,
            "feedback": "Excellent systematic approach with strong collaborative elements"
        }
        
        opposition = await self.architect.execute_opposition_protocol(
            "test_judge", initial_score, TEST_BEING, TEST_SCENARIO, high_score_response
        )
        
        # Validate opposition analysis
        compliance_tests = {
            "opposition_perspective_provided": len(opposition.opposite_perspective) > 50,
            "conflicting_evidence_found": len(opposition.conflicting_evidence) >= 3,
            "uncertainty_factors_identified": len(opposition.uncertainty_factors) >= 2,
            "alternative_interpretation_provided": len(opposition.alternative_interpretation) > 30,
            "bias_detection_performed": len(opposition.bias_detected) >= 1,
            "confidence_level_reasonable": 0.0 <= opposition.confidence_level <= 1.0,
            "score_adjustment_made": abs(opposition.final_calibrated_score - initial_score["overall"]) > 0.1
        }
        
        test_result = {
            "test_name": "Opposition Protocol Compliance",
            "passed_tests": sum(compliance_tests.values()),
            "total_tests": len(compliance_tests),
            "compliance_rate": sum(compliance_tests.values()) / len(compliance_tests),
            "details": compliance_tests,
            "opposition_analysis": asdict(opposition)
        }
        
        self.test_results.append(test_result)
        print(f"  ✅ Opposition Protocol: {test_result['compliance_rate']:.1%} compliance")
        return test_result
    
    async def test_context_calibration_accuracy(self) -> Dict[str, Any]:
        """Test context calibration system accuracy"""
        
        print("🎯 Testing Context Calibration Accuracy...")
        
        score_data = {"overall": 9.0, "feedback": "Exceptional performance"}
        
        calibration = await self.architect.execute_context_calibration(
            "test_judge", score_data, TEST_BEING, TEST_SCENARIO
        )
        
        # Validate calibration completeness
        calibration_tests = {
            "scenario_context_analyzed": len(calibration.scenario_context) > 50,
            "being_context_analyzed": len(calibration.being_context) > 50,
            "judge_perspective_analyzed": len(calibration.judge_perspective) > 50,
            "environmental_factors_identified": len(calibration.environmental_factors) >= 2,
            "deviation_addressed": len(calibration.deviation_justification) > 30,
            "fact_completeness_acceptable": calibration.fact_completeness_score >= 0.8,
            "baseline_reasonable": 0.0 <= calibration.calibration_baseline <= 10.0
        }
        
        test_result = {
            "test_name": "Context Calibration Accuracy",
            "passed_tests": sum(calibration_tests.values()),
            "total_tests": len(calibration_tests),
            "compliance_rate": sum(calibration_tests.values()) / len(calibration_tests),
            "details": calibration_tests,
            "context_calibration": asdict(calibration)
        }
        
        self.test_results.append(test_result)
        print(f"  ✅ Context Calibration: {test_result['compliance_rate']:.1%} accuracy")
        return test_result
    
    async def test_threshold_enforcement(self) -> Dict[str, Any]:
        """Test threshold enforcement rejects inadequate scores"""
        
        print("🚨 Testing Threshold Enforcement...")
        
        # Create deliberately inadequate responses
        test_cases = [
            {
                "name": "Short Explanation",
                "initial_score": {"overall": 7.0, "feedback": "Good"},  # Too short
                "response": "Simple solution."
            },
            {
                "name": "Low Confidence",
                "initial_score": {"overall": 8.0, "feedback": "This is a detailed explanation that meets length requirements but will have low confidence"},
                "response": "Complex response with many uncertainties and unclear outcomes"
            },
            {
                "name": "High Drift No Justification", 
                "initial_score": {"overall": 3.0, "feedback": "This response is detailed enough to meet minimum length requirements for testing"},
                "response": "Response that should score much higher than 3.0 based on baselines"
            }
        ]
        
        enforcement_results = []
        
        for test_case in test_cases:
            # Generate mock opposition analysis
            opposition = await self.architect.execute_opposition_protocol(
                "test_judge", test_case["initial_score"], TEST_BEING, TEST_SCENARIO, test_case["response"]
            )
            
            # Generate mock context calibration
            calibration = await self.architect.execute_context_calibration(
                "test_judge", test_case["initial_score"], TEST_BEING, TEST_SCENARIO
            )
            
            # Test threshold enforcement
            passed, violations = self.architect.enforce_thresholds(
                opposition, calibration, test_case["initial_score"]
            )
            
            enforcement_results.append({
                "test_case": test_case["name"],
                "should_reject": True,  # All test cases should be rejected
                "actually_rejected": not passed,
                "violations": violations,
                "correct_enforcement": not passed  # Should be rejected
            })
        
        enforcement_rate = sum(r["correct_enforcement"] for r in enforcement_results) / len(enforcement_results)
        
        test_result = {
            "test_name": "Threshold Enforcement",
            "enforcement_rate": enforcement_rate,
            "test_cases": enforcement_results,
            "properly_rejected": sum(r["actually_rejected"] for r in enforcement_results),
            "total_cases": len(enforcement_results)
        }
        
        self.test_results.append(test_result)
        print(f"  ✅ Threshold Enforcement: {enforcement_rate:.1%} accuracy")
        return test_result
    
    async def test_conflict_detection(self) -> Dict[str, Any]:
        """Test conflict detection identifies score inconsistencies"""
        
        print("⚡ Testing Conflict Detection...")
        
        # Create conflicting score scenarios
        conflict_scenarios = [
            {
                "name": "High Score Despite High Conflicting Evidence",
                "initial_score": {"overall": 8.5, "feedback": "Excellent performance"},
                "opposition_overrides": {
                    "conflicting_evidence": ["evidence1", "evidence2", "evidence3", "evidence4"],
                    "final_calibrated_score": 8.3  # Small adjustment despite evidence
                }
            },
            {
                "name": "Low Confidence High Score", 
                "initial_score": {"overall": 9.0, "feedback": "Outstanding performance"},
                "opposition_overrides": {
                    "confidence_level": 0.4,  # Very low confidence
                    "final_calibrated_score": 8.8  # Still high score
                }
            },
            {
                "name": "Multiple Biases No Adjustment",
                "initial_score": {"overall": 7.5, "feedback": "Good performance"},
                "opposition_overrides": {
                    "bias_detected": ["confirmation_bias", "halo_effect", "anchoring_bias"],
                    "final_calibrated_score": 7.4  # Minimal adjustment
                }
            }
        ]
        
        conflict_results = []
        
        for scenario in conflict_scenarios:
            # Create opposition analysis with conflicts
            opposition = await self.architect.execute_opposition_protocol(
                "test_judge", scenario["initial_score"], TEST_BEING, TEST_SCENARIO, "test response"
            )
            
            # Override specific fields to create conflicts
            for field, value in scenario["opposition_overrides"].items():
                setattr(opposition, field, value)
            
            # Create context calibration
            calibration = await self.architect.execute_context_calibration(
                "test_judge", scenario["initial_score"], TEST_BEING, TEST_SCENARIO
            )
            
            # Test conflict detection
            resolved, conflicts = self.architect.detect_conflicts(
                opposition, calibration, scenario["initial_score"]
            )
            
            conflict_results.append({
                "scenario": scenario["name"],
                "should_detect_conflict": True,
                "conflicts_detected": len(conflicts) > 0,
                "conflicts": conflicts,
                "correctly_identified": len(conflicts) > 0
            })
        
        detection_rate = sum(r["correctly_identified"] for r in conflict_results) / len(conflict_results)
        
        test_result = {
            "test_name": "Conflict Detection",
            "detection_rate": detection_rate,
            "scenarios_tested": conflict_results,
            "conflicts_properly_identified": sum(r["correctly_identified"] for r in conflict_results),
            "total_scenarios": len(conflict_results)
        }
        
        self.test_results.append(test_result)
        print(f"  ✅ Conflict Detection: {detection_rate:.1%} accuracy")
        return test_result
    
    async def test_end_to_end_rti_integration(self) -> Dict[str, Any]:
        """Test complete RTI integration with actual judge"""
        
        print("🔬 Testing End-to-End RTI Integration...")
        
        test_response = """
        I recommend implementing a tiered resource allocation system with clear priority frameworks.
        First, I'll establish criteria for urgency assessment including business impact, technical complexity, 
        and strategic alignment. Then I'll create a rotating schedule that ensures each department gets 
        dedicated engineering time while maintaining flexibility for urgent issues. This approach balances
        competing needs while preserving team morale through transparent communication and shared decision-making.
        """
        
        # Run full RTI-enhanced judge response
        rti_result = await rti_enhanced_judge_response(
            "test_judge", TEST_JUDGE, TEST_BEING, TEST_SCENARIO, test_response
        )
        
        # Validate RTI integration
        integration_tests = {
            "rti_metadata_present": "rti_metadata" in rti_result,
            "rti_status_set": rti_result.get("rti_status") in ["VALIDATED", "FAILED"],
            "opposition_analysis_included": "opposition_analysis" in rti_result.get("rti_metadata", {}),
            "context_calibration_included": "context_calibration" in rti_result.get("rti_metadata", {}),
            "thresholds_enforced": "thresholds_enforced" in rti_result.get("rti_metadata", {}),
            "conflicts_checked": "conflict_resolution" in rti_result.get("rti_metadata", {}),
            "protocol_version_tracked": rti_result.get("rti_metadata", {}).get("protocol_version") == "RTI-1.0"
        }
        
        test_result = {
            "test_name": "End-to-End RTI Integration",
            "integration_tests": integration_tests,
            "passed_tests": sum(integration_tests.values()),
            "total_tests": len(integration_tests),
            "integration_rate": sum(integration_tests.values()) / len(integration_tests),
            "rti_result_sample": {k: v for k, v in rti_result.items() if k != "rti_metadata"},
            "rti_status": rti_result.get("rti_status"),
            "final_score": rti_result.get("overall", 0.0)
        }
        
        self.test_results.append(test_result)
        print(f"  ✅ RTI Integration: {test_result['integration_rate']:.1%} complete")
        return test_result
    
    async def run_full_validation_suite(self) -> Dict[str, Any]:
        """Run complete RTI validation suite"""
        
        print("\n🔬 RTI SCORING ARCHITECT VALIDATION SUITE")
        print("=" * 60)
        print("Testing mandatory 'consider the opposite' protocols")
        print("and context calibration systems...\n")
        
        start_time = time.time()
        
        # Run all validation tests
        await self.test_opposition_protocol_compliance()
        await self.test_context_calibration_accuracy()
        await self.test_threshold_enforcement()
        await self.test_conflict_detection()
        await self.test_end_to_end_rti_integration()
        
        total_time = time.time() - start_time
        
        # Calculate overall validation metrics
        total_tests = sum(len(test.get("details", {})) if "details" in test else test.get("total_tests", 1) for test in self.test_results)
        passed_tests = sum(test.get("passed_tests", 1) if test.get("compliance_rate", test.get("enforcement_rate", test.get("detection_rate", test.get("integration_rate", 1)))) >= 0.8 else 0 for test in self.test_results)
        
        overall_validation_rate = passed_tests / len(self.test_results) if self.test_results else 0.0
        
        # Generate comprehensive report
        validation_report = {
            "validation_timestamp": time.time(),
            "total_validation_time": total_time,
            "test_suite_version": "RTI-1.0",
            "overall_validation_rate": overall_validation_rate,
            "test_results": self.test_results,
            "summary": {
                "total_test_categories": len(self.test_results),
                "passed_categories": passed_tests,
                "failed_categories": len(self.test_results) - passed_tests
            },
            "recommendations": []
        }
        
        # Add recommendations based on results
        for test in self.test_results:
            rate = test.get("compliance_rate", test.get("enforcement_rate", test.get("detection_rate", test.get("integration_rate", 1.0))))
            if rate < 0.8:
                validation_report["recommendations"].append(f"Improve {test['test_name']}: {rate:.1%} success rate")
        
        # Print summary
        print(f"\n{'=' * 60}")
        print(f"RTI VALIDATION SUITE COMPLETE")
        print(f"{'=' * 60}")
        print(f"⏱️  Total Time: {total_time:.1f}s")
        print(f"📊 Overall Validation Rate: {overall_validation_rate:.1%}")
        print(f"✅ Passed Categories: {passed_tests}/{len(self.test_results)}")
        
        if validation_report["recommendations"]:
            print(f"\n🔧 RECOMMENDATIONS:")
            for rec in validation_report["recommendations"]:
                print(f"   • {rec}")
        
        if overall_validation_rate >= 0.8:
            print(f"\n🎉 RTI SCORING ARCHITECT VALIDATION SUCCESSFUL!")
            print(f"   System ready for production deployment.")
        else:
            print(f"\n⚠️  RTI SCORING ARCHITECT NEEDS IMPROVEMENT")
            print(f"   Address recommendations before deployment.")
        
        # Save validation report
        report_file = f"./workspaces/prime/Projects/colosseum/v2/data/rti_validation_report_{int(time.time())}.json"
        with open(report_file, "w") as f:
            json.dump(validation_report, f, indent=2)
        
        print(f"\n💾 Validation report saved to {report_file}")
        
        return validation_report

async def main():
    """Run RTI validation suite"""
    validator = RTIValidationSuite()
    await validator.run_full_validation_suite()

if __name__ == "__main__":
    asyncio.run(main())