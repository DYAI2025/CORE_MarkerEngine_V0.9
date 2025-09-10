#!/usr/bin/env python3
"""
marker_engine_core.py
─────────────────────────────────────────────────────────────────
Lean-Deep 3.4-konformer Engine-Kern.
Lädt Marker-Definitionen (ATO_/SEM_/CLU_/MEMA_ Präfix), wendet Detektoren aus Registry an,
führt Scoring und Fusion nach Master-Schema durch. Gibt strukturierte Ergebnisse.
"""

from pathlib import Path
import yaml
import json
import importlib
import re
import datetime
import numpy as np
from typing import Dict, List, Any, Optional

from numeric_normalizer_plugin import NumericNormalizerPlugin

# --------------------------------------------------------------
PRFX_LEVELS = ("ATO_", "SEM_", "CLU_", "MEMA_")

class MarkerEngine:
    def __init__(self,
                 marker_root: str = "_Marker_5.0",
                 schema_root: str = "schemata",
                 detect_registry: str = "DETECT_/DETECT_registry.json",
                 plugin_root: str = "plugins"):

        self.marker_path   = Path(marker_root)
        self.schema_path   = Path(schema_root)
        self.plugin_root   = Path(plugin_root)
        self.detect_registry = Path(detect_registry)

        # interne Caches
        self.markers : Dict[str, Dict[str, Any]] = {}
        self.schemas : Dict[str, Dict[str, Any]] = {}
        self.active_schemas : List[Dict[str, Any]] = []
        self.schema_priority : Dict[str, float] = {}
        self.fusion_mode : str = "multiply"
        self.detectors: List[Dict[str, Any]]     = []
        self.plugins  : Dict[str, Any]           = {}

        self._load_markers()
        self._load_schemata()
        self._load_detectors()

    # ----------------------------------------------------------
    # Loader
    # ----------------------------------------------------------
    def _load_markers(self):
        """Lädt alle Marker aus dem Marker-Verzeichnis."""
        for file in self.marker_path.glob("*.yaml"):
            try:
                data = yaml.safe_load(file.read_text("utf-8"))
                if data and "id" in data:
                    self.markers[data["id"]] = data
            except yaml.YAMLError as e:
                print(f"Error parsing YAML file {file}: {e}")
                continue

    def _load_schemata(self):
        """Lädt alle Schemata + Master-Schema für Fusion/Prioritäten."""
        for file in self.schema_path.glob("SCH_*.json"):
            data = json.loads(file.read_text("utf-8"))
            schema_id = data.get("$id") or data.get("id")
            if schema_id: self.schemas[schema_id] = data
        master_path = self.schema_path / "MASTER_SCH_CORE.json"
        if master_path.exists():
            master = json.loads(master_path.read_text("utf-8"))
            self.active_schemas = [self.schemas[sch] for sch in master["active_schemata"]]
            self.schema_priority = master.get("priority", {})
            self.fusion_mode = master.get("fusion", "multiply")

    def _load_detectors(self):
        """Lädt alle Detektoren aus Registry, inkl. optionaler Plugins."""
        if self.detect_registry.exists():
            reg = json.loads(self.detect_registry.read_text("utf-8"))
            # Sort detectors by priority and then by id
            sorted_detectors = sorted(reg.get("detectors", []), key=lambda x: (x.get("priority", 99), x.get("id")))
            for entry in sorted_detectors:
                self.detectors.append(entry)
                if entry.get("module") == "plugin":
                    plugin_path = (self.plugin_root / Path(entry["file_path"]).name)
                    spec = importlib.util.spec_from_file_location(entry["id"], plugin_path)
                    mod  = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)  # type: ignore
                    self.plugins[entry["id"]] = mod
        
        # Load custom detectors
        self.detectors.append({"id": "plugin.numeric.normalizer", "module": "custom", "priority": 2})
        self.plugins["plugin.numeric.normalizer"] = NumericNormalizerPlugin()


    # ----------------------------------------------------------
    # Haupt­methode
    # ----------------------------------------------------------
    def analyze(self, text: str, hits: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        if hits is None:
            hits = []

        # 1) Detector-Registry anwenden (Präfix-Fire)
        for det in self.detectors:
            if det.get("module") == "regex":
                file_path = Path(det["file_path"])
                if not file_path.is_absolute():
                    file_path = Path.cwd() / file_path
                spec = json.loads(file_path.read_text("utf-8"))
                pattern = re.compile(spec["rule"]["pattern"], re.IGNORECASE)
                if pattern.search(text):
                    hits.append({"marker": spec["fires_marker"], "source": det["id"]})

            elif det.get("module") == "plugin":
                plugin = self.plugins[det["id"]]
                result = plugin.run(text)
                hits.extend({"marker": m, "source": det["id"]} for m in result.get("fires", []))
            elif det.get("module") == "custom":
                plugin = self.plugins[det["id"]]
                result = plugin.run(text)
                hits.extend(result)

        # 2) Pattern-basierte Marker (nur Level 1, atomic)
        for marker_id, marker in self.markers.items():
            if marker_id.startswith("ATO_") and "pattern" in marker:
                pats = marker.get("pattern", [])
                if isinstance(pats, str): pats = [pats]
                for pat in pats:
                    if pat and re.search(pat, text, re.IGNORECASE):
                        hits.append({"marker": marker_id, "source": "pattern"})
                        break

        # 3) Schema-Fusion (Scoring/Priorisierung)
        final_scores: Dict[str, float] = {}
        for hit in hits:
            m = self.markers.get(hit["marker"])
            if not m: continue
            
            scoring = m.get("scoring", {})
            base = scoring.get("base", 1.0)
            weight = scoring.get("weight", 1.0)
            decay = scoring.get("decay", 0.0)
            formula = scoring.get("formula", "linear")

            if formula == "linear":
                raw = base * weight
            elif formula == "logistic":
                raw = base * (1 / (1 + np.exp(-weight)))
            else:
                raw = base * weight

            for sch in self.active_schemas:
                prio = self.schema_priority.get(Path(sch["id"]).name + ".json", 1.0)
                if self.fusion_mode == "multiply":
                    raw *= prio
                elif self.fusion_mode == "sum":
                    raw += prio

            final_scores[hit["marker"]] = final_scores.get(hit["marker"], 0) + raw

        return {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "hits": hits,
            "scores": final_scores
        }

    def analyze_conversation(self, messages: List[Dict[str, Any]], window: Dict[str, int], options: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes a conversation with a sliding window."""
        all_hits = []
        window_size = window.get("size", 30)
        overlap = window.get("overlap", 0)
        
        # Create sliding windows
        for i in range(0, len(messages), window_size - overlap):
            chunk = messages[i:i + window_size]
            if len(chunk) < window_size // 2:  # Skip very small chunks
                continue
                
            text = " ".join([m["text"] for m in chunk])
            result = self.analyze(text)
            
            # Add message IDs to hits for evidence tracking
            for hit in result["hits"]:
                hit["msg_ids"] = [m["id"] for m in chunk]
                hit["span"] = ""  # Could be enhanced to include actual text spans
                
            all_hits.extend(result["hits"])

        # Activation Engine with evidence cascade
        activated_markers = []
        for marker_id, marker in self.markers.items():
            if "activation" in marker:
                activation = marker["activation"]
                rule = activation.get("rule")
                params = activation.get("params", {})
                composed_of = marker.get("composed_of", [])
                
                if rule == "ANY":
                    count = 0
                    triggering_hits = []
                    for hit in all_hits:
                        if hit["marker"] in composed_of:
                            count += 1
                            triggering_hits.append(hit)
                    if count >= params.get("count", 1):
                        activated_markers.append({
                            "marker_id": marker_id,
                            "source": "activation",
                            "evidence": triggering_hits,
                            "rule": rule,
                            "params": params
                        })
                elif rule == "ALL":
                    present = all(any(hit["marker"] == c for hit in all_hits) for c in composed_of)
                    if present:
                        triggering_hits = [hit for hit in all_hits if hit["marker"] in composed_of]
                        activated_markers.append({
                            "marker_id": marker_id,
                            "source": "activation",
                            "evidence": triggering_hits,
                            "rule": rule,
                            "params": params
                        })
                elif rule == "AT_LEAST":
                    count = 0
                    triggering_hits = []
                    for hit in all_hits:
                        if hit["marker"] in composed_of:
                            count += 1
                            triggering_hits.append(hit)
                    if count >= params.get("count", 1):
                        activated_markers.append({
                            "marker_id": marker_id,
                            "source": "activation",
                            "evidence": triggering_hits,
                            "rule": rule,
                            "params": params
                        })
                elif rule == "WEIGHTED_AND":
                    # Implement weighted AND logic
                    total_weight = 0.0
                    triggering_hits = []
                    for component in composed_of:
                        component_hits = [hit for hit in all_hits if hit["marker"] == component]
                        if component_hits:
                            # Get weight from combination or default to 1.0
                            weight = 1.0
                            if "combination" in marker and "components" in marker["combination"]:
                                for comp in marker["combination"]["components"]:
                                    if isinstance(comp, dict) and comp.get("marker_id") == component:
                                        weight = comp.get("weight", 1.0)
                                        break
                            total_weight += weight
                            triggering_hits.extend(component_hits)
                    
                    threshold = params.get("threshold", 0.5)
                    if total_weight >= threshold:
                        activated_markers.append({
                            "marker_id": marker_id,
                            "source": "activation",
                            "evidence": triggering_hits,
                            "rule": rule,
                            "params": params
                        })
                elif rule == "X_OF_Y":
                    # Implement X of Y logic
                    x = params.get("x", 1)
                    y = params.get("y", len(composed_of))
                    present_count = 0
                    triggering_hits = []
                    
                    for component in composed_of:
                        component_hits = [hit for hit in all_hits if hit["marker"] == component]
                        if component_hits:
                            present_count += 1
                            triggering_hits.extend(component_hits)
                    
                    if present_count >= x:
                        activated_markers.append({
                            "marker_id": marker_id,
                            "source": "activation",
                            "evidence": triggering_hits,
                            "rule": rule,
                            "params": params
                        })
                elif rule == "SUM_WEIGHT":
                    # Implement sum weight logic
                    total_weight = 0.0
                    triggering_hits = []
                    
                    for component in composed_of:
                        component_hits = [hit for hit in all_hits if hit["marker"] == component]
                        if component_hits:
                            # Get weight from combination or default to 1.0
                            weight = 1.0
                            if "combination" in marker and "components" in marker["combination"]:
                                for comp in marker["combination"]["components"]:
                                    if isinstance(comp, dict) and comp.get("marker_id") == component:
                                        weight = comp.get("weight", 1.0)
                                        break
                            total_weight += weight * len(component_hits)
                            triggering_hits.extend(component_hits)
                    
                    threshold = params.get("threshold", 1.0)
                    if total_weight >= threshold:
                        activated_markers.append({
                            "marker_id": marker_id,
                            "source": "activation",
                            "evidence": triggering_hits,
                            "rule": rule,
                            "params": params
                        })
                elif rule == "AT_LEAST_DISTINCT":
                    # Implement distinct component logic
                    distinct_components = set()
                    triggering_hits = []
                    
                    for hit in all_hits:
                        if hit["marker"] in composed_of:
                            distinct_components.add(hit["marker"])
                            triggering_hits.append(hit)
                    
                    if len(distinct_components) >= params.get("count", 1):
                        activated_markers.append({
                            "marker_id": marker_id,
                            "source": "activation",
                            "evidence": triggering_hits,
                            "rule": rule,
                            "params": params
                        })
                elif rule == "FREQUENCY":
                    # Implement frequency logic
                    count = params.get("count", 1)
                    window_size = params.get("window", 5)  # Default window of 5 messages
                    
                    # Count occurrences in recent messages (simplified)
                    recent_hits = [hit for hit in all_hits if hit["marker"] in composed_of]
                    
                    if len(recent_hits) >= count:
                        activated_markers.append({
                            "marker_id": marker_id,
                            "source": "activation",
                            "evidence": recent_hits,
                            "rule": rule,
                            "params": params
                        })

        # Add activated markers to hits
        for activated in activated_markers:
            all_hits.append({
                "marker": activated["marker_id"],
                "source": activated["source"],
                "evidence": activated["evidence"],
                "rule": activated["rule"],
                "params": activated["params"]
            })
        
        return {"summary": "Conversation analysis complete.", "hits": all_hits}

# -----------------------------------------------------------------
if __name__ == "__main__":
    eng = MarkerEngine()
    sample = "Ich weiß normalerweise, was ich will, aber hier bin ich mir nicht sicher. 50k"
    import pprint
    pprint.pprint(eng.analyze(sample))
