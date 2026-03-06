"""Test various AI filtering queries"""
import json
import logging
from ai_filtering import filter_jobs_by_criteria

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Load data
print("Loading jobs data...")
with open('data_jobs_combined.json', 'r', encoding='utf-8') as f:
    combined_data = json.load(f)
    jobs = combined_data.get('jobs', [])

with open('data_jobs_descriptions.json', 'r', encoding='utf-8') as f:
    descriptions_data = json.load(f)

print(f"Loaded {len(jobs)} jobs with {len(descriptions_data.get('descriptions', []))} descriptions\n")

# Test different queries
test_queries = [
    "5 years experience",  # Should include jobs with no req + up to 5 years
    "junior data analyst",  # Should find entry-level positions
    "python developer",  # Non-experience query
]

for query in test_queries:
    print(f"\n{'='*60}")
    print(f"Query: '{query}'")
    print(f"{'='*60}")
    
    result = filter_jobs_by_criteria(jobs, query, descriptions_data)
    
    print(f"Matches: {result['total_matches']}")
    print(f"AI Enhanced: {result.get('ai_enhanced', False)}")
    print(f"Explanation: {result.get('explanation')}")
    
    if result['total_matches'] > 0:
        print(f"\nFirst 3 jobs:")
        for i, job in enumerate(result['filtered_jobs'][:3], 1):
            print(f"  {i}. {job.get('title')} at {job.get('company')}")
    
    print()
