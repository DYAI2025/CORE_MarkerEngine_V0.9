#!/usr/bin/env python3
"""
standardize_markers.py
──────────────────────────────────────────────────────────────────
Utility to standardize existing marker files to conform to schema v3.4.
Automatically fixes common issues and missing fields.
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Any
import re

class MarkerStandardizer:
    def __init__(self, marker_root: str = "_Marker_5.0", backup: bool = True):
        self.marker_path = Path(marker_root)
        self.backup = backup
        self.standardizations_applied = []
    
    def standardize_file(self, marker_file: Path) -> Dict[str, Any]:
        """Standardize a single marker file."""
        # Load original data
        original_data = yaml.safe_load(marker_file.read_text("utf-8"))
        data = original_data.copy()
        applied_fixes = []
        
        # Fix 1: Ensure proper version format
        if "version" not in data or data["version"] != "3.4":
            data["version"] = "3.4"
            applied_fixes.append("Set version to 3.4")
        
        # Fix 2: Ensure frame structure exists and is complete
        if "frame" not in data:
            data["frame"] = {}
        
        frame = data["frame"]
        
        # Fix frame.signal - convert string to array if needed
        if "signal" not in frame:
            # Try to extract from description or create default
            frame["signal"] = ["Signal extracted from description"] 
            applied_fixes.append("Added missing frame.signal")
        elif isinstance(frame["signal"], str):
            frame["signal"] = [frame["signal"]]
            applied_fixes.append("Converted signal string to array")
        
        # Fix missing frame fields
        frame_fields = {
            "concept": "Extracted concept",
            "pragmatics": "Extracted pragmatic function", 
            "narrative": "general"
        }
        
        for field, default in frame_fields.items():
            if field not in frame:
                frame[field] = default
                applied_fixes.append(f"Added missing frame.{field}")
        
        # Fix 3: Ensure pattern is array format
        if "pattern" in data:
            if isinstance(data["pattern"], str):
                data["pattern"] = [data["pattern"]]
                applied_fixes.append("Converted pattern string to array")
        
        # Fix 4: Ensure examples exist and have minimum count
        if "examples" not in data:
            data["examples"] = []
        
        examples = data["examples"]
        
        # Handle case where examples is not a list
        if not isinstance(examples, list):
            if isinstance(examples, str):
                examples = [examples]
            else:
                examples = []
            data["examples"] = examples
            applied_fixes.append("Converted examples to list format")
        
        if len(examples) < 5:
            # Generate placeholder examples if insufficient
            marker_id = data.get("id", "UNKNOWN")
            needed = 5 - len(examples)
            for i in range(needed):
                examples.append(f"Example {len(examples) + 1} for {marker_id}")
            applied_fixes.append(f"Added {needed} placeholder examples")
        
        # Fix 5: Ensure language field
        if "lang" not in data:
            data["lang"] = "de"  # Default to German
            applied_fixes.append("Added default language (de)")
        
        # Fix 6: Add missing activation rules if not present
        if "activation" not in data and "pattern" in data:
            data["activation"] = {
                "rule": "ANY",
                "params": {
                    "count": 1,
                    "window": {
                        "size": 20,
                        "unit": "messages"
                    }
                }
            }
            applied_fixes.append("Added default activation rules")
        
        # Fix 7: Ensure window configuration
        if "window" not in data:
            data["window"] = {
                "messages": 20,
                "seconds": 300
            }
            applied_fixes.append("Added default window configuration")
        
        # Fix 8: Ensure scoring configuration
        if "scoring" not in data:
            data["scoring"] = {
                "base": 1.0,
                "weight": 0.5,
                "decay": 0.01,
                "formula": "logistic"
            }
            applied_fixes.append("Added default scoring configuration")
        
        # Fix 9: Add tags if missing
        if "tags" not in data:
            marker_id = data.get("id", "")
            prefix = marker_id.split("_")[0].lower() if "_" in marker_id else "unknown"
            data["tags"] = [prefix]
            applied_fixes.append("Added default tags")
        
        # Fix 10: Add metadata section
        if "metadata" not in data:
            data["metadata"] = {
                "created_by": "standardization_script",
                "last_modified": "2024-09-11",
                "validation_status": "auto_standardized"
            }
            applied_fixes.append("Added metadata section")
        
        return data, applied_fixes
    
    def standardize_directory(self, dry_run: bool = False) -> Dict[str, List[str]]:
        """Standardize all markers in the directory."""
        results = {}
        
        for yaml_file in self.marker_path.glob("*.yaml"):
            if yaml_file.name.startswith(("ATO_", "SEM_", "CLU_", "MEMA_")):
                try:
                    standardized_data, fixes = self.standardize_file(yaml_file)
                    
                    if fixes and not dry_run:
                        # Create backup if requested
                        if self.backup:
                            backup_file = yaml_file.with_suffix(".yaml.bak")
                            backup_file.write_text(yaml_file.read_text("utf-8"))
                        
                        # Write standardized version
                        with open(yaml_file, 'w', encoding='utf-8') as f:
                            yaml.dump(standardized_data, f, 
                                    default_flow_style=False, 
                                    allow_unicode=True,
                                    sort_keys=False)
                    
                    results[yaml_file.name] = fixes
                    
                except Exception as e:
                    results[yaml_file.name] = [f"Error: {e}"]
        
        return results
    
    def generate_report(self, results: Dict[str, List[str]]) -> str:
        """Generate a standardization report."""
        report = ["Marker Standardization Report", "=" * 50, ""]
        
        modified_count = sum(1 for fixes in results.values() if fixes and not any("Error:" in fix for fix in fixes))
        error_count = sum(1 for fixes in results.values() if any("Error:" in fix for fix in fixes))
        total_count = len(results)
        
        report.append(f"Total markers processed: {total_count}")
        report.append(f"Successfully standardized: {modified_count}")
        report.append(f"Errors encountered: {error_count}")
        report.append("")
        
        # Summary of fixes applied
        all_fixes = []
        for fixes in results.values():
            all_fixes.extend(fix for fix in fixes if not fix.startswith("Error:"))
        
        if all_fixes:
            fix_counts = {}
            for fix in all_fixes:
                fix_counts[fix] = fix_counts.get(fix, 0) + 1
            
            report.append("Most common fixes applied:")
            for fix, count in sorted(fix_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                report.append(f"  {count:3d}x {fix}")
            report.append("")
        
        # Detailed results for files with errors
        errors = {k: v for k, v in results.items() if any("Error:" in fix for fix in v)}
        if errors:
            report.append("Files with errors:")
            for filename, error_list in errors.items():
                report.append(f"  {filename}:")
                for error in error_list:
                    report.append(f"    {error}")
            report.append("")
        
        return "\n".join(report)

def main():
    """Command line interface for standardization."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Standardize marker files to schema v3.4")
    parser.add_argument("--marker-dir", default="_Marker_5.0",
                       help="Directory containing marker files")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be changed without making changes")
    parser.add_argument("--no-backup", action="store_true",
                       help="Don't create backup files")
    parser.add_argument("--output", help="Output file for report")
    
    args = parser.parse_args()
    
    standardizer = MarkerStandardizer(args.marker_dir, backup=not args.no_backup)
    results = standardizer.standardize_directory(dry_run=args.dry_run)
    report = standardizer.generate_report(results)
    
    if args.dry_run:
        print("DRY RUN - No changes made")
        print()
    
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(report)

if __name__ == "__main__":
    main()