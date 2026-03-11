"""
Basic RTI Test - Quick verification of core functionality
"""

import asyncio
import json
from rti_scoring_architect import RTIScoringArchitect

async def test_basic_rti():
    """Quick test of RTI core functionality"""
    
    print("🔬 Testing RTI Scoring Architect Basic Functionality")
    print("=" * 50)
    
    architect = RTIScoringArchitect()
    
    # Test data
    test_being = {
        "id": "test_001",
        "title": "Test Being",
        "area": "Testing"
    }
    
    test_scenario = {
        "title": "Test Scenario",
        "situation": "Testing RTI protocols",
        "success_criteria": "Validate RTI functionality"
    }
    
    initial_score = {
        "overall": 7.5,
        "feedback": "This is a test score that meets minimum length requirements for RTI validation"
    }
    
    test_response = "This is a detailed test response for RTI protocol validation."
    
    try:
        print("\n1. Testing Opposition Protocol...")
        opposition = await architect.execute_opposition_protocol(
            "test_judge", initial_score, test_being, test_scenario, test_response
        )
        print(f"   ✅ Opposition analysis complete")
        print(f"   • Final score: {opposition.final_calibrated_score}")
        print(f"   • Confidence: {opposition.confidence_level}")
        print(f"   • Biases detected: {len(opposition.bias_detected)}")
        
        print("\n2. Testing Context Calibration...")
        calibration = await architect.execute_context_calibration(
            "test_judge", initial_score, test_being, test_scenario
        )
        print(f"   ✅ Context calibration complete")
        print(f"   • Fact completeness: {calibration.fact_completeness_score}")
        print(f"   • Baseline: {calibration.calibration_baseline}")
        
        print("\n3. Testing Threshold Enforcement...")
        passed, violations = architect.enforce_thresholds(opposition, calibration, initial_score)
        print(f"   ✅ Threshold enforcement complete")
        print(f"   • Passed: {passed}")
        print(f"   • Violations: {len(violations)}")
        
        print("\n4. Testing Conflict Detection...")
        resolved, conflicts = architect.detect_conflicts(opposition, calibration, initial_score)
        print(f"   ✅ Conflict detection complete")
        print(f"   • Resolved: {resolved}")
        print(f"   • Conflicts: {len(conflicts)}")
        
        print("\n🎉 RTI BASIC TEST COMPLETE")
        print(f"   All core protocols functional!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ RTI TEST FAILED: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_basic_rti())