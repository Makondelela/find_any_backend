"""
Verify Experience Extraction Accuracy
======================================
Check random jobs to verify experience data matches descriptions
"""

import json
import random

# Load both files
print("Loading data...")
with open('data/data_jobs_experience.json', 'r', encoding='utf-8') as f:
    exp_data = json.load(f)

with open('data/data_jobs_descriptions.json', 'r', encoding='utf-8') as f:
    desc_data = json.load(f)

# Create lookup dictionaries
exp_lookup = {item['job_id']: item for item in exp_data['experience']}
desc_lookup = {item['job_id']: item['description'] for item in desc_data['descriptions']}

# Select random jobs to verify
print("\n" + "="*80)
print("VERIFYING EXPERIENCE EXTRACTION")
print("="*80)

# Check some jobs with experience requirements
jobs_with_exp = [item for item in exp_data['experience'] if item['has_requirement']]
sample_with_exp = random.sample(jobs_with_exp, min(5, len(jobs_with_exp)))

print("\n📋 JOBS WITH EXPERIENCE REQUIREMENTS:\n")
for idx, job in enumerate(sample_with_exp, 1):
    job_id = job['job_id']
    description = desc_lookup.get(job_id, "")
    
    print(f"{idx}. Job ID: {job_id}")
    print(f"   Extracted: {job['level']} level, {job['min_years']}-{job['max_years']} years")
    print(f"   Raw text found: '{job['raw_text']}'")
    print(f"   Description snippet:")
    # Find and show the relevant part of description
    desc_lower = description.lower()
    raw_text = job['raw_text'].lower() if job['raw_text'] else ""
    if raw_text and raw_text in desc_lower:
        idx_pos = desc_lower.find(raw_text)
        start = max(0, idx_pos - 50)
        end = min(len(description), idx_pos + len(raw_text) + 50)
        snippet = description[start:end]
        print(f"   ...{snippet}...")
    else:
        # Show first 200 chars
        print(f"   {description[:200]}...")
    print()

# Check some jobs WITHOUT experience requirements
jobs_no_exp = [item for item in exp_data['experience'] if not item['has_requirement']]
sample_no_exp = random.sample(jobs_no_exp, min(3, len(jobs_no_exp)))

print("\n📋 JOBS WITHOUT EXPERIENCE REQUIREMENTS:\n")
for idx, job in enumerate(sample_no_exp, 1):
    job_id = job['job_id']
    description = desc_lookup.get(job_id, "")
    
    print(f"{idx}. Job ID: {job_id}")
    print(f"   Extracted: No experience requirement")
    print(f"   Description snippet: {description[:200]}...")
    print()

# Check specific test cases
print("\n" + "="*80)
print("SPECIFIC TEST CASES")
print("="*80)

test_cases = [
    "2341954",  # Intermediate Data Engineer (should have requirement)
    "2340040",  # Junior Data Scientist
]

for job_id in test_cases:
    if job_id in exp_lookup:
        exp = exp_lookup[job_id]
        desc = desc_lookup.get(job_id, "")
        
        print(f"\nJob ID: {job_id}")
        print(f"Extracted Experience: {exp['level']} ({exp['min_years']}-{exp['max_years']} years)")
        print(f"Raw text: '{exp['raw_text']}'")
        print(f"Full Description:\n{desc[:500]}...\n")

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Total jobs: {exp_data['metadata']['total_jobs']}")
print(f"With requirements: {exp_data['metadata']['jobs_with_experience']} ({exp_data['metadata']['jobs_with_experience']/exp_data['metadata']['total_jobs']*100:.1f}%)")
print(f"Without requirements: {exp_data['metadata']['jobs_without_experience']} ({exp_data['metadata']['jobs_without_experience']/exp_data['metadata']['total_jobs']*100:.1f}%)")
