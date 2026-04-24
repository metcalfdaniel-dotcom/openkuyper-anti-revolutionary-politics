#!/usr/bin/env python3
"""
Dutch WordNet Integration for OpenKuyper

Provides semantic disambiguation, synonym discovery, and domain tagging
for Dutch theological and political terms using the Open Dutch Wordnet.

The underlying data comes from:
  - https://github.com/weRbelgium/wordnet.dutch (R wrapper)
  - https://github.com/MartenPostma/OpenDutchWordnet (original XML data)

License: CC BY-SA 4.0 (applies to WordNet data; our code is MIT)

Usage:
    from dutch_wordnet import DutchWordNet
    dwn = DutchWordNet("path/to/odwn_orbn_gwg-LMF_1.3.xml")
    
    # Look up a Dutch term
    results = dwn.lookup("soevereiniteit")
    
    # Get semantic field (synonyms, hypernyms, hyponyms)
    field = dwn.get_semantic_field("soevereiniteit")
    
    # Check domain tags
    domains = dwn.get_domains("genade")
"""

import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class DutchWordNet:
    """
    Python interface to the Open Dutch Wordnet (ODWN).
    
    Parses the LMF-format XML and provides query methods for:
    - Lexical entry lookup (lemmatized forms)
    - Synset retrieval (cognitive synonym groups)
    - Semantic relations (hypernymy, hyponymy, meronymy, etc.)
    - Domain and register tagging
    - Cross-lingual alignment (via ILI = Inter-Lingual Index to Princeton WordNet)
    """
    
    def __init__(self, xml_path: str):
        """Load and index the ODWN XML file."""
        self.xml_path = Path(xml_path)
        if not self.xml_path.exists():
            raise FileNotFoundError(f"ODWN XML not found: {xml_path}")
        
        self._tree = ET.parse(xml_path)
        self._root = self._tree.getroot()
        
        # Build indexes for fast lookup
        self._lemma_to_entries: Dict[str, List[ET.Element]] = defaultdict(list)
        self._synset_id_to_synset: Dict[str, ET.Element] = {}
        self._synset_id_to_entries: Dict[str, List[ET.Element]] = defaultdict(list)
        self._ili_to_synset: Dict[str, str] = {}  # ILI -> synset_id
        
        self._index()
    
    def _tag(self, name: str) -> str:
        """Return tag name, handling both namespaced and plain XML."""
        # Try namespaced first (original format), then plain
        return name
    
    def _find(self, elem: ET.Element, tag: str, ns: Optional[Dict] = None) -> Optional[ET.Element]:
        """Find child element, trying both namespaced and plain tags."""
        # Try with namespace
        if ns:
            result = elem.find(f"{{{ns['lmf']}}}{tag}", ns)
            if result is not None:
                return result
        # Try plain tag
        return elem.find(tag)
    
    def _iter(self, elem: ET.Element, tag: str, ns: Optional[str] = None) -> ET.Element:
        """Iterate over child elements, trying both namespaced and plain tags."""
        # Try with namespace
        found = False
        if ns:
            for child in elem.iter(f"{{{ns}}}{tag}"):
                found = True
                yield child
        if not found:
            # Try plain tag
            for child in elem.iter(tag):
                yield child
    
    def _index(self):
        """Build internal indexes from the XML tree."""
        ns = {"lmf": "http://www.w3.org/ns/lemon/lmf"}
        
        # Index LexicalEntries by lemma
        for entry in self._root.iter("LexicalEntry"):
            lemma_elem = entry.find("Lemma")
            if lemma_elem is not None:
                written_form = lemma_elem.get("writtenForm", "").lower()
                if written_form:
                    self._lemma_to_entries[written_form].append(entry)
            
            # Map senses to synsets
            for sense in entry.iter("Sense"):
                synset_id = sense.get("synset", "")
                if synset_id:
                    self._synset_id_to_entries[synset_id].append(entry)
        
        # Index Synsets
        for synset in self._root.iter("Synset"):
            synset_id = synset.get("id", "")
            if synset_id:
                self._synset_id_to_synset[synset_id] = synset
                ili = synset.get("ili", "")
                if ili:
                    self._ili_to_synset[ili] = synset_id
    
    def lookup(self, term: str) -> List[Dict]:
        """
        Look up a Dutch term and return all lexical entries with their senses.
        
        Returns list of dicts with keys:
          - lemma: str
          - pos: str (part of speech)
          - senses: list of {synset_id, definition, domain, provenance}
        """
        term = term.lower()
        entries = self._lemma_to_entries.get(term, [])
        results = []
        
        for entry in entries:
            lemma_elem = entry.find("Lemma")
            lemma = lemma_elem.get("writtenForm", term) if lemma_elem is not None else term
            pos = entry.get("partOfSpeech", "unknown")
            
            senses = []
            for sense in entry.iter("Sense"):
                synset_id = sense.get("synset", "")
                definition = sense.get("definition", "")
                provenance = sense.get("provenance", "")
                
                # Get domain from pragmatics if available
                domains = []
                pragmatics = sense.find("Pragmatics")
                if pragmatics is not None:
                    domains_elem = pragmatics.find("Domains")
                    if domains_elem is not None:
                        domains = [d.get("domain", "") for d in domains_elem]
                
                senses.append({
                    "synset_id": synset_id,
                    "definition": definition,
                    "provenance": provenance,
                    "domains": domains
                })
            
            results.append({
                "lemma": lemma,
                "pos": pos,
                "senses": senses
            })
        
        return results
    
    def get_synset(self, synset_id: str) -> Optional[Dict]:
        """
        Retrieve a synset by its ID.
        
        Returns dict with:
          - id: synset ID
          - ili: Inter-Lingual Index (links to Princeton WordNet)
          - gloss: definition/gloss
          - relations: list of {rel_type, target_synset_id}
          - members: list of lemma strings in this synset
        """
        synset = self._synset_id_to_synset.get(synset_id)
        if synset is None:
            return None
        
        result = {
            "id": synset_id,
            "ili": synset.get("ili", ""),
            "gloss": "",
            "relations": [],
            "members": []
        }
        
        # Get gloss from Definitions
        definitions = synset.find("Definitions")
        if definitions is not None:
            def_elem = definitions.find("Definition")
            if def_elem is not None:
                result["gloss"] = def_elem.get("gloss", "")
        
        # Get relations
        relations = synset.find("SynsetRelations")
        if relations is not None:
            for rel in relations:
                result["relations"].append({
                    "rel_type": rel.get("relType", ""),
                    "target": rel.get("target", "")
                })
        
        # Get member lemmas
        for entry in self._synset_id_to_entries.get(synset_id, []):
            lemma_elem = entry.find("Lemma")
            if lemma_elem is not None:
                result["members"].append(lemma_elem.get("writtenForm", ""))
        
        return result
    
    def get_semantic_field(self, term: str, depth: int = 1) -> Dict:
        """
        Build a semantic field around a term by following synset relations.
        
        Returns dict with:
          - term: input term
          - synsets: list of synset details
          - synonyms: flat list of synonymous lemmas
          - hypernyms: broader terms
          - hyponyms: narrower terms
          - related: other related terms
        """
        term = term.lower()
        entries = self._lemma_to_entries.get(term, [])
        
        field = {
            "term": term,
            "synsets": [],
            "synonyms": set(),
            "hypernyms": set(),
            "hyponyms": set(),
            "related": set()
        }
        
        visited_synsets = set()
        
        for entry in entries:
            for sense in entry.iter("Sense"):
                synset_id = sense.get("synset", "")
                if not synset_id or synset_id in visited_synsets:
                    continue
                visited_synsets.add(synset_id)
                
                synset_info = self.get_synset(synset_id)
                if synset_info:
                    field["synsets"].append(synset_info)
                    field["synonyms"].update(synset_info["members"])
                    
                    for rel in synset_info["relations"]:
                        rel_type = rel["rel_type"].lower()
                        target = rel["target"]
                        target_synset = self.get_synset(target)
                        if target_synset:
                            target_lemmas = target_synset["members"]
                            if "hypernym" in rel_type or "has_hyperonym" in rel_type:
                                field["hypernyms"].update(target_lemmas)
                            elif "hyponym" in rel_type or "has_hyponym" in rel_type:
                                field["hyponyms"].update(target_lemmas)
                            else:
                                field["related"].update(target_lemmas)
        
        # Remove the original term from synonyms
        field["synonyms"].discard(term)
        field["synonyms"] = sorted(field["synonyms"])
        field["hypernyms"] = sorted(field["hypernyms"])
        field["hyponyms"] = sorted(field["hyponyms"])
        field["related"] = sorted(field["related"])
        
        return field
    
    def get_domains(self, term: str) -> Set[str]:
        """Return all domain tags associated with a term."""
        term = term.lower()
        entries = self._lemma_to_entries.get(term, [])
        domains = set()
        
        for entry in entries:
            for sense in entry.iter("Sense"):
                pragmatics = sense.find("Pragmatics")
                if pragmatics is not None:
                    domains_elem = pragmatics.find("Domains")
                    if domains_elem is not None:
                        for d in domains_elem:
                            domain = d.get("domain", "")
                            if domain:
                                domains.add(domain)
        
        return domains
    
    def get_ili_mapping(self, term: str) -> List[str]:
        """
        Return Princeton WordNet ILI mappings for a Dutch term.
        These can be used to find English equivalents via Princeton WordNet.
        """
        term = term.lower()
        entries = self._lemma_to_entries.get(term, [])
        ilis = []
        
        for entry in entries:
            for sense in entry.iter("Sense"):
                synset_id = sense.get("synset", "")
                synset = self._synset_id_to_synset.get(synset_id)
                if synset is not None:
                    ili = synset.get("ili", "")
                    if ili:
                        ilis.append(ili)
        
        return ilis
    
    def suggest_translation_senses(self, term: str) -> List[Dict]:
        """
        For a given Dutch term, suggest possible English translation senses
        based on domain, gloss, and semantic relations.
        
        Returns list of candidate senses with:
          - definition (Dutch gloss)
          - domains
          - ili (Princeton WordNet link for English lookup)
          - semantic_field summary
        """
        results = []
        lookup_results = self.lookup(term)
        
        for entry in lookup_results:
            for sense in entry["senses"]:
                synset = self.get_synset(sense["synset_id"])
                if synset:
                    results.append({
                        "definition": synset.get("gloss", sense["definition"]),
                        "domains": sense["domains"],
                        "ili": synset.get("ili", ""),
                        "pos": entry["pos"],
                        "semantic_field": {
                            "synonyms": synset.get("members", [])[:10],
                            "relations": [r["rel_type"] for r in synset.get("relations", [])]
                        }
                    })
        
        return results


def demo():
    """Demonstration of Dutch WordNet capabilities."""
    import json
    
    # Example path - user must download ODWN XML separately
    xml_path = "reference/odwn/odwn_orbn_gwg-LMF_1.3.xml"
    
    if not Path(xml_path).exists():
        print(f"Please download the ODWN XML to {xml_path}")
        print("Source: https://github.com/MartenPostma/OpenDutchWordnet")
        return
    
    dwn = DutchWordNet(xml_path)
    
    # Demo with "soevereiniteit" (sovereignty)
    print("=" * 60)
    print("LOOKUP: soevereiniteit")
    print("=" * 60)
    results = dwn.lookup("soevereiniteit")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    print("SEMANTIC FIELD: genade (grace)")
    print("=" * 60)
    field = dwn.get_semantic_field("genade")
    print(f"Synonyms: {field['synonyms'][:10]}")
    print(f"Hypernyms: {field['hypernyms'][:10]}")
    print(f"Hyponyms: {field['hyponyms'][:10]}")
    
    print("\n" + "=" * 60)
    print("DOMAINS: kerk (church)")
    print("=" * 60)
    domains = dwn.get_domains("kerk")
    print(f"Domains: {domains}")


if __name__ == "__main__":
    demo()
