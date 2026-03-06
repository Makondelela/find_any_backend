"""Test Gemini AI filtering"""
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

print(f"Loaded {len(jobs)} jobs")

# Load descriptions
print("Loading descriptions...")
with open('data_jobs_descriptions.json', 'r', encoding='utf-8') as f:
    descriptions_data = json.load(f)

print(f"Loaded {len(descriptions_data.get('descriptions', []))} descriptions")

# Test query
test_query = "2 years experience only"
print(f"\n{'='*60}")
print(f"Testing query: '{test_query}'")
print(f"{'='*60}\n")

result = filter_jobs_by_criteria(jobs, test_query, descriptions_data)

print(f"\n{'='*60}")
print(f"Results: {result['total_matches']} matches")
print(f"AI Enhanced: {result.get('ai_enhanced', False)}")
print(f"Experience Query: {result.get('experience_query', False)}")
print(f"User Years: {result.get('user_experience_years')}")
print(f"Strict Mode: {result.get('strict_mode', False)}")
print(f"Explanation: {result.get('explanation')}")
print(f"{'='*60}\n")

# Show first 5 matches
print("First 5 matching jobs:")
for i, job in enumerate(result['filtered_jobs'][:5], 1):
    print(f"\n{i}. {job.get('title')} at {job.get('company')}")
    print(f"   ID: {job.get('job_id')}")
    print(f"   Location: {job.get('location', 'N/A')}")
