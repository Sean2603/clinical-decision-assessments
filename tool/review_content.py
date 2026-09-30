#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from collections import defaultdict

def review_blood_panels_and_assessments():
    issues = {
        'duplicates': [],
        'json_errors': [],
        'missing_fields': [],
        'improvements': [],
        'title_analysis': defaultdict(list)
    }
    
    all_items = {}
    
    # Review blood panels
    bp_dir = Path('blood_panels')
    for fp in sorted(bp_dir.glob('*.json')):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            all_items[str(fp)] = data
            
            # Check required fields
            required = ['stableId', 'title', 'version']
            for field in required:
                if field not in data:
                    issues['missing_fields'].append(f"{fp.name}: missing '{field}'")
            
            # Track title
            if 'title' in data:
                issues['title_analysis'][data['title']].append(str(fp))
                
        except json.JSONDecodeError as e:
            issues['json_errors'].append(f"{fp.name}: {str(e)}")
    
    # Review assessments
    ass_dir = Path('assessments')
    for fp in sorted(ass_dir.glob('*.json')):
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
            all_items[str(fp)] = data
            
            # Check required fields
            required = ['stableId', 'title', 'version']
            for field in required:
                if field not in data:
                    issues['missing_fields'].append(f"{fp.name}: missing '{field}'")
            
            # Track title
            if 'title' in data:
                issues['title_analysis'][data['title']].append(str(fp))
                
        except json.JSONDecodeError as e:
            issues['json_errors'].append(f"{fp.name}: {str(e)}")
    
    # Find duplicate titles
    for title, files in issues['title_analysis'].items():
        if len(files) > 1:
            issues['duplicates'].append(f"Title '{title}' appears in: {', '.join(files)}")
    
    # Analyze content
    for path, data in all_items.items():
        # Check for empty descriptions/text
        if 'description' in data and not data['description']:
            issues['improvements'].append(f"{Path(path).name}: empty description")
        
        # Check for minimal content
        if 'content' in data:
            content_str = json.dumps(data['content'])
            if len(content_str) < 100:
                issues['improvements'].append(f"{Path(path).name}: very short content")
        
        # Check if sections exist but are empty
        for key in ['symptoms', 'signs', 'results', 'content']:
            if key in data and isinstance(data[key], (list, dict)):
                if not data[key]:
                    issues['improvements'].append(f"{Path(path).name}: empty '{key}' field")
    
    return issues

if __name__ == '__main__':
    issues = review_blood_panels_and_assessments()
    
    print("=" * 60)
    print("CONTENT REVIEW: Blood Panels & Assessments")
    print("=" * 60)
    
    if issues['json_errors']:
        print("\n❌ JSON ERRORS:")
        for err in issues['json_errors']:
            print(f"  - {err}")
    
    if issues['missing_fields']:
        print("\n⚠️  MISSING FIELDS:")
        for err in issues['missing_fields']:
            print(f"  - {err}")
    
    if issues['duplicates']:
        print("\n🔄 DUPLICATE TITLES:")
        for dup in issues['duplicates']:
            print(f"  - {dup}")
    
    if issues['improvements']:
        print("\n💡 POTENTIAL IMPROVEMENTS:")
        for imp in sorted(set(issues['improvements'])):
            print(f"  - {imp}")
    
    if not any(issues.values()):
        print("\n✅ All items passed basic checks!")
    
    # Summary stats
    print("\n" + "=" * 60)
    print(f"Total Issues Found: {sum(len(v) if isinstance(v, list) else len(v) for v in issues.values() if v)}")
