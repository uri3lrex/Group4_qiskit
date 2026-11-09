"""
# TUTORIAL 9: Project 2 Kickoff
# Week 9
"""

print("PROJECT 2 KICKOFF")
print("=" * 50)

print("""
GROUP FORMATION:
- Form groups of 4 students
- Assign variant numbers (1-25)
- Review common template

VARIANT ALLOCATION:
Each group receives:
1. Variant specification (JSON file)
2. Platform parameters
3. Domain-specific requirements
4. Autograder test suite

TEMPLATE WALKTHROUGH:
- Part A: Quantum Subsystem Design (30%, autograded)
- Part B: Scalability Analysis (20%, manual)
- Part C: Security Analysis (20%, manual)
- Part D: Group Report & Presentation (30%, manual)

PROJECT PLANNING:
Week 8-9: Setup, design, initial implementation
Week 10-11: Core development, testing
Week 12: Integration, report writing
Week 13: Presentation preparation, submission

DELIVERABLES:
1. Python code (autograded)
2. Technical report (10 pages)
3. Presentation (10 minutes)
4. Group contribution statement
""")

# Example variant loading
import json

# Simulate loading a variant
example_variant = {
    "variant_id": "D1-P3",
    "domain_name": "Quantum Key Distribution Network",
    "platform_name": "Photonic",
    "protocol": "BB84",
    "distance_km": 200,
    "loss_db_per_km": 0.05,
    "detector_efficiency": 0.8
}

print("\nExample variant (D1-P3):")
for key, value in example_variant.items():
    print(f"  {key}: {value}")
