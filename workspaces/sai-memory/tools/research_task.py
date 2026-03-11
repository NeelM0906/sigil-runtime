import os, sys, json
sys.path.append('~/.openclaw/workspace-memory/tools')

try:
    from supabase_memory import SaiMemory
    mem = SaiMemory('memory')
    mem.wake_up()
    
    # Payload 1: Guardian Cluster
    payload1 = {
        'cluster_family': 'Intelligence & Analytics',
        'cluster_name': 'Guardian',
        'position_name': 'Predictive Churn Analyst',
        'mastery_definition': 'Operates exclusively at 9.999 precision predicting structural relationship breakdowns before they occur.',
        'core_skills': ['Vector Database Architecture', 'LLM Parameter Constraints', 'Statistical Pattern Recognition'],
        'textbooks_references': ['High-Dimensional Mathematics', 'Behavioral Economics for Scaling'],
        'tools_platforms': ['Pinecone', 'Supabase', 'OpenRouter', 'n8n'],
        "formula_overlay": "The 3Ms (Measuring, Monitoring, Maximization)",
        "example_scenario": "Scenario where a 0.8% parameter shift forces the system to stop labeling and start diagnosing root human fears.",
        "common_failures": "Reporting the failure instead of naming the invisible cause of the failure."
    }
    
    # Payload 2: ValueEngine Cluster
    payload2 = {
        'cluster_family': 'Economics',
        'cluster_name': 'ValueEngine',
        'position_name': 'Director of Cart Economics',
        'mastery_definition': 'Models friction limits using behavioral data to maximize AOV seamlessly.',
        'core_skills': ['Checkout Friction Analysis', 'UI/UX Conversion Optimization'],
        'textbooks_references': ['Influence: The Psychology of Persuasion', 'Thinking, Fast and Slow'],
        'tools_platforms': ['Hyros', 'Stripe', 'HighLevel'],
        "formula_overlay": "Level 5 Listening & The 4 Energies",
        "example_scenario": "Applying Aspirational Energy at checkout to dissolve price resistance silently.",
        "common_failures": "Lowering price instead of proving massive external value."
    }

    mem.remember('position_mastery', json.dumps(payload1), 'web_research', 10)
    mem.remember('position_mastery', json.dumps(payload2), 'web_research', 10)
    print('SUCCESS: Database successfully seeded with new Oracle and ValueEngine matrix constraints.')
except Exception as e:
    print(f'Error: {e}')
