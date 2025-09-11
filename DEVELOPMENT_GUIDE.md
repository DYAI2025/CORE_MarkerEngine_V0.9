# Marker Engine Development Guide

## Overview
This guide documents the enhanced marker engine architecture, bug fixes, and development recommendations for the CORE_MarkerEngine_V0.9 project.

## Fixed Issues

### 1. Schema Path Bug ✅ FIXED
**Problem**: The `MarkerEngine` class was hardcoded to look for schemas in a non-existent "schemata" directory.
**Solution**: Changed the default `schema_root` parameter from "schemata" to "SCH_" to match the actual directory structure.

### 2. Missing Master Schema ✅ FIXED
**Problem**: The engine expected `MASTER_SCH_CORE.json` but it didn't exist, causing silent schema loading failures.
**Solution**: Created `SCH_/MASTER_SCH_CORE.json` with proper configuration for active schemas, priorities, and fusion modes.

### 3. Schema ID Mismatches ✅ FIXED
**Problem**: Schema files had inconsistent ID formats that didn't match master schema expectations.
**Solution**: Standardized schema IDs in existing files to match the master schema configuration.

### 4. Poor Error Handling ✅ FIXED
**Problem**: Schema loading failed silently without informative error messages.
**Solution**: Enhanced `_load_schemata()` method with comprehensive error handling and logging.

## Architecture Overview

### Directory Structure
```
CORE_MarkerEngine_V0.9/
├── _Marker_5.0/          # 380+ marker definition files (YAML)
├── SCH_/                 # Schema definitions (JSON)
│   ├── MASTER_SCH_CORE.json
│   ├── SCH_marker.schema.v2.json
│   ├── SCH_fraud-markers.schema.json
│   └── SCH_relation_analyse_schema.json
├── DETECT_/              # Detector registry and configurations
├── templates/            # Standardized templates for new markers
│   ├── ATO_TEMPLATE.yaml
│   ├── SEM_TEMPLATE.yaml
│   ├── CLU_TEMPLATE.yaml
│   └── MEMA_TEMPLATE.yaml
├── plugins/              # Plugin system for custom detectors
├── marker_engine_core.py # Main engine implementation
├── schema_validator.py   # Schema validation utility
└── standardize_markers.py # Marker standardization tool
```

### Marker Hierarchy
1. **ATO_** (Atomare): Basic language elements and signals
2. **SEM_** (Semantische): Semantic patterns and meaning levels  
3. **CLU_** (Cluster): Pattern groups and behavioral clusters
4. **MEMA_** (Meta-Marker): Meta-level analysis patterns

### Schema Management
The system now uses a hierarchical schema management approach:
- **Master Schema** (`MASTER_SCH_CORE.json`): Defines active schemas, priorities, and fusion modes
- **Individual Schemas**: Validate specific marker types and categories
- **Template System**: Provides standardized templates for consistent marker creation

## Development Tools

### 1. Schema Validator
```bash
python schema_validator.py --marker-dir _Marker_5.0
```
- Validates markers against schema definitions
- Identifies structural issues and missing fields
- Generates comprehensive validation reports

### 2. Marker Standardizer
```bash
# Dry run to see what would be changed
python standardize_markers.py --dry-run

# Apply standardizations
python standardize_markers.py
```
- Automatically fixes common schema violations
- Adds missing required fields with sensible defaults
- Creates backups before modifications

### 3. Template System
Use the templates in `templates/` directory to create new markers:
- `ATO_TEMPLATE.yaml`: For basic language elements
- `SEM_TEMPLATE.yaml`: For semantic patterns
- `CLU_TEMPLATE.yaml`: For behavioral clusters
- `MEMA_TEMPLATE.yaml`: For meta-level patterns

## Development Recommendations

### 1. Immediate Actions
- [ ] Run standardization on existing markers: `python standardize_markers.py`
- [ ] Validate all markers: `python schema_validator.py --output validation_report.txt`
- [ ] Review and fix remaining validation errors manually
- [ ] Create missing detector implementations referenced in registry

### 2. Architecture Improvements

#### A. Enhanced Plugin System
```python
# Recommended plugin interface enhancement
class DetectorPlugin:
    def __init__(self, config):
        self.config = config
    
    def detect(self, text, context):
        """Return list of detected markers with confidence scores"""
        pass
    
    def validate_config(self):
        """Validate plugin configuration"""
        pass
```

#### B. Improved Scoring Engine
- Implement contextual scoring based on conversation history
- Add temporal decay functions for marker persistence
- Support for weighted marker combinations

#### C. Real-time Analysis Pipeline
```python
# Suggested real-time analysis architecture
class AnalysisPipeline:
    def __init__(self, engine):
        self.engine = engine
        self.context_buffer = []
    
    def process_message(self, message, user_context):
        """Process single message with context"""
        pass
    
    def get_session_summary(self, session_id):
        """Generate session-level insights"""
        pass
```

### 3. Quality Assurance

#### Testing Strategy
- Unit tests for each marker type
- Integration tests for the full analysis pipeline
- Performance tests with large marker sets
- Validation tests against known conversation patterns

#### Continuous Integration
- Automated schema validation on marker changes
- Performance regression testing
- Documentation generation from schema files

### 4. Advanced Features

#### A. Machine Learning Integration
- Train classifier models on validated markers
- Implement confidence scoring based on ML predictions
- Support for dynamic marker learning from feedback

#### B. Multi-language Support
- Extend schema to support language-specific patterns
- Implement language detection and routing
- Create language-specific marker templates

#### C. Analysis Dashboard
- Real-time visualization of marker detection
- Historical analysis trends
- Marker effectiveness metrics

## Usage Examples

### Basic Analysis
```python
from marker_engine_core import MarkerEngine

engine = MarkerEngine()
result = engine.analyze("Aber ich verstehe nicht, warum du das machst.")
print(f"Detected markers: {len(result['hits'])}")
```

### Custom Configuration
```python
engine = MarkerEngine(
    marker_root="_Marker_5.0",
    schema_root="SCH_", 
    detect_registry="DETECT_/DETECT_registry.json"
)
```

### Schema Validation
```python
from schema_validator import SchemaValidator

validator = SchemaValidator()
results = validator.validate_directory(Path("_Marker_5.0"))
print(validator.generate_report(results))
```

## Performance Considerations

### Current Metrics
- Schema loading: ~50ms for 5 schemas
- Marker loading: ~2s for 380+ markers
- Analysis time: ~10ms per message

### Optimization Opportunities
1. **Lazy Loading**: Load markers on-demand rather than at startup
2. **Compiled Patterns**: Pre-compile regex patterns for better performance
3. **Caching**: Cache frequently used marker combinations
4. **Parallel Processing**: Parallelize detector execution

## Future Roadmap

### Version 4.0 Goals
- [ ] Complete marker standardization (target: 95% compliance)
- [ ] Enhanced plugin architecture with hot-reloading
- [ ] Machine learning integration for pattern recognition
- [ ] Multi-language support framework
- [ ] Real-time analysis dashboard
- [ ] API service with rate limiting and authentication

### Version 4.1 Goals
- [ ] Advanced therapeutic insights generation
- [ ] Integration with external NLP services
- [ ] Conversation flow analysis
- [ ] Predictive relationship health scoring

## Contributing Guidelines

### Adding New Markers
1. Use appropriate template from `templates/` directory
2. Validate with `schema_validator.py`
3. Test with sample conversations
4. Document examples and edge cases

### Modifying Schemas
1. Update schema files in `SCH_/` directory
2. Update `MASTER_SCH_CORE.json` if needed
3. Run validation on existing markers
4. Update templates and documentation

### Performance Optimization
1. Profile with representative data
2. Measure before and after performance
3. Add benchmarks for regression testing
4. Document performance characteristics

## Support and Troubleshooting

### Common Issues
1. **Schema loading failures**: Check file paths and JSON syntax
2. **Marker validation errors**: Use `schema_validator.py` for diagnosis
3. **Performance issues**: Profile with smaller marker sets first

### Debug Information
Enable debug logging by setting environment variable:
```bash
export MARKER_ENGINE_DEBUG=1
```

### Getting Help
- Review this documentation
- Check existing issues in the repository
- Run validation tools for specific error diagnosis
- Create minimal reproducible examples for bug reports