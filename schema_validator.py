#!/usr/bin/env python3
"""
schema_validator.py
──────────────────────────────────────────────────────────────────
Validation utility for marker files against schema definitions.
Helps ensure consistency and catches structural issues early.
"""

import yaml
import json
import jsonschema
from pathlib import Path
from typing import Dict, List, Any, Tuple

class SchemaValidator:
    def __init__(self, schema_root: str = "SCH_"):
        self.schema_path = Path(schema_root)
        self.schemas = {}
        self.load_schemas()
    
    def load_schemas(self):
        """Load all schema definitions."""
        for file in self.schema_path.glob("SCH_*.json"):
            try:
                data = json.loads(file.read_text("utf-8"))
                schema_id = data.get("$id", file.stem)
                self.schemas[schema_id] = data
            except Exception as e:
                print(f"Error loading schema {file}: {e}")
    
    def validate_marker(self, marker_file: Path) -> Tuple[bool, List[str]]:
        """Validate a single marker file against the appropriate schema."""
        errors = []
        
        try:
            # Load marker data
            marker_data = yaml.safe_load(marker_file.read_text("utf-8"))
            
            # Determine schema based on marker prefix
            marker_id = marker_data.get("id", "")
            schema_url = "https://example.org/schemas/marker/v3.2"
            
            if schema_url not in self.schemas:
                errors.append(f"Schema not found: {schema_url}")
                return False, errors
            
            # Validate against schema
            try:
                jsonschema.validate(marker_data, self.schemas[schema_url])
            except jsonschema.ValidationError as e:
                errors.append(f"Schema validation failed: {e.message}")
                if e.absolute_path:
                    errors.append(f"  Path: {' -> '.join(str(p) for p in e.absolute_path)}")
            except jsonschema.SchemaError as e:
                errors.append(f"Schema error: {e.message}")
            
            # Additional custom validations
            errors.extend(self._custom_validations(marker_data))
            
        except Exception as e:
            errors.append(f"Error processing file: {e}")
        
        return len(errors) == 0, errors
    
    def _custom_validations(self, marker_data: Dict[str, Any]) -> List[str]:
        """Custom validation rules beyond JSON schema."""
        errors = []
        
        marker_id = marker_data.get("id", "")
        
        # Check ID format
        if not marker_id:
            errors.append("Missing marker ID")
        elif not any(marker_id.startswith(prefix) for prefix in ["ATO_", "SEM_", "CLU_", "MEMA_"]):
            errors.append(f"Invalid marker ID prefix: {marker_id}")
        
        # Check required examples
        examples = marker_data.get("examples", [])
        if len(examples) < 5:
            errors.append(f"Insufficient examples: {len(examples)} (minimum 5 required)")
        
        # Check pattern or composed_of requirement
        has_pattern = "pattern" in marker_data
        has_composed = "composed_of" in marker_data
        has_detect_class = "detect_class" in marker_data
        
        if not (has_pattern or has_composed or has_detect_class):
            errors.append("Marker must have either 'pattern', 'composed_of', or 'detect_class'")
        
        # Validate frame structure
        frame = marker_data.get("frame", {})
        required_frame_fields = ["signal", "concept", "pragmatics", "narrative"]
        for field in required_frame_fields:
            if field not in frame:
                errors.append(f"Missing frame field: {field}")
        
        return errors
    
    def validate_directory(self, marker_dir: Path) -> Dict[str, Tuple[bool, List[str]]]:
        """Validate all markers in a directory."""
        results = {}
        
        for yaml_file in marker_dir.glob("*.yaml"):
            if yaml_file.name.startswith(("ATO_", "SEM_", "CLU_", "MEMA_")):
                valid, errors = self.validate_marker(yaml_file)
                results[yaml_file.name] = (valid, errors)
        
        return results
    
    def generate_report(self, results: Dict[str, Tuple[bool, List[str]]]) -> str:
        """Generate a validation report."""
        report = ["Marker Validation Report", "=" * 50, ""]
        
        valid_count = sum(1 for valid, _ in results.values() if valid)
        total_count = len(results)
        
        report.append(f"Total markers: {total_count}")
        report.append(f"Valid markers: {valid_count}")
        report.append(f"Invalid markers: {total_count - valid_count}")
        report.append("")
        
        # Group by status
        valid_markers = []
        invalid_markers = []
        
        for filename, (valid, errors) in results.items():
            if valid:
                valid_markers.append(filename)
            else:
                invalid_markers.append((filename, errors))
        
        if valid_markers:
            report.append("Valid Markers:")
            report.extend(f"  ✓ {marker}" for marker in sorted(valid_markers))
            report.append("")
        
        if invalid_markers:
            report.append("Invalid Markers:")
            for marker, errors in sorted(invalid_markers):
                report.append(f"  ✗ {marker}")
                for error in errors:
                    report.append(f"    - {error}")
                report.append("")
        
        return "\n".join(report)

def main():
    """Command line interface for validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate marker files against schemas")
    parser.add_argument("--marker-dir", default="_Marker_5.0", 
                       help="Directory containing marker files")
    parser.add_argument("--schema-dir", default="SCH_", 
                       help="Directory containing schema files")
    parser.add_argument("--output", help="Output file for report")
    
    args = parser.parse_args()
    
    validator = SchemaValidator(args.schema_dir)
    results = validator.validate_directory(Path(args.marker_dir))
    report = validator.generate_report(results)
    
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Report written to {args.output}")
    else:
        print(report)

if __name__ == "__main__":
    main()