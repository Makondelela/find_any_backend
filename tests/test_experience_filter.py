"""Test experience-based filtering"""
import json
import logging
from ai_filtering import filter_jobs_by_criteria

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Load jobs
print("Loading jobs data...")
with open('data_jobs_combined.json', 'r', encoding='utf-8') as f:
    combined_data = json.load(f)
    jobs = combined_data.get('jobs', [])

print(f"Loaded {len(jobs)} jobs\n")

# Test different queries
test_queries = [
    "2 years experience only",
    "5 years experience",
    "junior data analyst",
    "senior developer",
]

for query in test_queries:
    print(f"\n{'='*70}")
    print(f"Query: '{query}'")
    print(f"{'='*70}")
    
    result = filter_jobs_by_criteria(jobs, query)
    
    print(f"\n✅ Results: {result['total_matches']} matches")
    print(f"📊 Explanation: {result['explanation']}")
    
    if result.get('breakdown'):
        stats = result['breakdown']
        print(f"\n📈 Breakdown:")
        print(f"   - Matched requirements: {stats['matched']}")
        print(f"   - No requirements: {stats['no_requirement']}")
        print(f"   - Too high: {stats['too_high']}")
        print(f"   - No data: {stats['no_data']}")
    
    if result['total_matches'] > 0:
        print(f"\n🔍 First 3 jobs:")
        for i, job in enumerate(result['filtered_jobs'][:3], 1):
            print(f"   {i}. {job.get('title')} at {job.get('company')}")
    
    print()
