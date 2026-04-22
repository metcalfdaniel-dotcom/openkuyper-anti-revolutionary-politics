#!/usr/bin/env python3
"""
Comprehensive Kuyper Style Analyzer
Builds a unified vocabulary and style database from reference texts.
"""

import json
import re
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
import pdfplumber

# =============================================================================
# CONFIGURATION
# =============================================================================

REFERENCE_DIR = Path(__file__).parent.parent / "reference"
OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# Target texts
TEXTS = {
    "faith": {
        "file": "Faith - Abraham Kuyper.txt",
        "format": "txt",
        "title": "Faith",
        "year": 1905,
    },
    "lectures_on_calvinism": {
        "file": "Lectures on Calvinism - Abraham Kuyper.pdf",
        "format": "pdf",
        "title": "Lectures on Calvinism",
        "year": 1898,
    },
    "saved_by_grace": {
        "file": "Saved by Grace Alone - Abraham Kuyper.pdf",
        "format": "pdf",
        "title": "Saved by Grace Alone",
        "year": 1915,
    },
    "sanctifying_work": {
        "file": "The Sanctifying Work of the Hol - Abraham Kuyper.pdf",
        "format": "pdf",
        "title": "The Sanctifying Work of the Holy Spirit",
        "year": 1895,
    },
}

# Theological terminology clusters
THEOLOGICAL_CLUSTERS = {
    "Godhead_and_Persons": [
        "godhead", "godhood", "divine", "deity", "trinity", "triune", "person",
        "hypostasis", "essence", "ousia", "subsistence", "father", "son", "holy spirit",
        "spirit", "almighty", "jehovah", "lord", "creator", "sustainer"
    ],
    "Soteriology": [
        "salvation", "redemption", "atonement", "justification", "sanctification",
        "regeneration", "conversion", "repentance", "faith", "grace", "mercy",
        "forgiveness", "reconciliation", "adoption", "election", "predestination",
        "calling", "preservation", "glorification", "mediator", "intercessor"
    ],
    "Scripture_and_Revelation": [
        "scripture", "scriptures", "bible", "word", "revelation", "inspiration",
        "inspired", "canonical", "prophecy", "prophetic", "testament", "covenant",
        "gospel", "law", "commandment", "precept", "statute", "ordinance",
        "doctrine", "dogma", "confession", "creed", "catechism"
    ],
    "Church_and_Organism": [
        "church", "churches", "congregation", "assembly", "communion", "sacrament",
        "baptism", " Lord's supper", "eucharist", "preaching", "ministry", "minister",
        "pastor", "elder", "deacon", "bishop", "presbyter", "synod", "council",
        "denomination", "sect", " schism", "orthodoxy", "catholicity"
    ],
    "Grace_and_Operation": [
        "grace", "gracious", "operation", "operative", "efficacious", "effectual",
        "inward", "internal", "external", "means", "instrument", "vehicle",
        "channel", "conduit", "dispensation", "administration", "covenant",
        "testament", "dispensational"
    ],
    "Sphere_and_Sovereignty": [
        "sphere", "spheres", "sovereignty", "sovereign", "domain", "realm",
        "province", "jurisdiction", "authority", "autonomy", "independence",
        "sphere sovereignty", "sovereignty in own sphere", "calvinistic",
        "antirevolutionary", "christian", "historical", "principled"
    ],
    "State_and_Politics": [
        "state", "government", "govern", "political", "politics", "civil",
        "magistrate", "ruler", "authority", "power", "law", "legislation",
        "constitution", "constitutional", "revolution", "revolutionary",
        "antirevolutionary", "party", "movement", "principle", "system"
    ],
    "Anthropology_and_Psychology": [
        "soul", "spirit", "mind", "heart", "conscience", "consciousness",
        "faculty", "faculties", "power", "powers", "affection", "affections",
        "passion", "passions", "will", "intellect", "reason", "understanding",
        "imagination", "memory", "temperament", "disposition", "nature",
        "character", "personality", "self", "ego", "identity"
    ],
}

# Elevated/archaic vocabulary characteristic of Kuyper
ELEVATED_VOCABULARY = [
    "hence", "whereby", "wherein", "whereof", "wherewith", "whereunto",
    "thereby", "therein", "thereof", "thereon", "thereto", "thereunto",
    "hereby", "herein", "hereof", "hereto",
    "aforesaid", "foregoing", "abovementioned", "aforementioned",
    "nevertheless", "notwithstanding", "howbeit", "albeit",
    "persuasion", "certainty", "assurance", "confidence", "certitude",
    "testimony", "witness", "attestation", "deposition",
    "knowledge", "cognition", "apprehension", "comprehension", "perception",
    "being", "existence", "essence", "subsistence", "actuality",
    "principle", "ground", "foundation", "basis", "reason",
    "operation", "efficacy", "efficient", "instrumental", "mediate",
    "immediate", "direct", "indirect", "proximate", "remote",
    "sweeping", "grandiose", "magnificent", "sublime", "lofty",
    "architectonic", "systematic", "organic", "organism", "structure",
    "periodic", "period", "sentence", "clause", "member",
    "conception", "concept", "notion", "idea", "thought",
    "judgment", "inference", "conclusion", "deduction", "induction",
    "syllogism", "premise", "proposition", "axiom", "theorem",
]

# Connectives and rhetorical markers
CONNECTIVES = {
    "additive": ["and", "also", "moreover", "furthermore", "likewise", "similarly"],
    "adversative": ["but", "yet", "however", "nevertheless", "notwithstanding", "although", "though"],
    "causal": ["for", "because", "since", "therefore", "thus", "hence", "consequently"],
    "conditional": ["if", "unless", "provided", "supposing"],
    "concessive": ["although", "though", "while", "whereas", "albeit"],
    "illustrative": ["for example", "for instance", "namely", "viz", "i.e.", "e.g."],
    "summative": ["in sum", "in conclusion", "to conclude", "finally", "lastly"],
    "contrastive": ["on the contrary", "on the other hand", "conversely", "rather"],
}

# =============================================================================
# TEXT EXTRACTION
# =============================================================================

def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from PDF using pdfplumber."""
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        print(f"Error extracting {pdf_path}: {e}", file=sys.stderr)
        return ""
    return "\n\n".join(text_parts)


def load_text(text_key: str) -> str:
    """Load text for a given reference key."""
    info = TEXTS[text_key]
    file_path = REFERENCE_DIR / info["file"]
    
    if info["format"] == "pdf":
        return extract_text_from_pdf(file_path)
    else:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()


# =============================================================================
# SENTENCE ANALYSIS
# =============================================================================

def split_sentences(text: str) -> list:
    """Split text into sentences, handling abbreviations and edge cases."""
    # Protect common abbreviations
    text = re.sub(r'(Dr|Mr|Mrs|Ms|Prof|Rev|Hon|St|Ave|Blvd|Rd|Mt|Jr|Sr|Vol|Ch|pp|cf|viz|i\.e|e\.g)\.', r'\1<ABBREV>', text)
    
    # Split on sentence terminators
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    
    # Restore abbreviations
    sentences = [s.replace('<ABBREV>', '.') for s in sentences]
    
    # Clean and filter
    cleaned = []
    for s in sentences:
        s = s.strip()
        s = re.sub(r'\s+', ' ', s)
        if len(s) > 10 and any(c.isalpha() for c in s):
            cleaned.append(s)
    return cleaned


def analyze_sentences(sentences: list) -> dict:
    """Analyze sentence structure metrics."""
    lengths = [len(s.split()) for s in sentences]
    
    periodic_count = 0
    for s in sentences:
        words = s.split()
        # Heuristic: periodic sentence has subordinate clauses before main clause
        # Indicated by delayed main verb or initial connectives + comma before main clause
        if len(words) > 20:
            comma_positions = [i for i, w in enumerate(words) if ',' in w or w.endswith(',')]
            if comma_positions and comma_positions[-1] > len(words) * 0.6:
                # Main clause likely at end
                periodic_count += 1
    
    return {
        "total_sentences": len(sentences),
        "avg_length": round(sum(lengths) / max(len(lengths), 1), 2),
        "max_length": max(lengths) if lengths else 0,
        "min_length": min(lengths) if lengths else 0,
        "median_length": sorted(lengths)[len(lengths)//2] if lengths else 0,
        "long_sentences_30plus": sum(1 for l in lengths if l > 30),
        "long_sentences_50plus": sum(1 for l in lengths if l > 50),
        "very_long_sentences_75plus": sum(1 for l in lengths if l > 75),
        "periodic_estimate": periodic_count,
        "periodic_percentage": round(periodic_count / max(len(sentences), 1) * 100, 2),
    }


# =============================================================================
# VOCABULARY AND TERMINOLOGY ANALYSIS
# =============================================================================

def tokenize(text: str) -> list:
    """Simple tokenizer: lowercase, remove punctuation, split."""
    text = text.lower()
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    tokens = [t for t in text.split() if len(t) > 1]
    return tokens


def analyze_terminology(text: str, text_key: str) -> dict:
    """Analyze theological terminology clusters."""
    tokens = set(tokenize(text))
    results = {}
    
    for cluster, terms in THEOLOGICAL_CLUSTERS.items():
        found = []
        for term in terms:
            term_clean = term.lower().strip()
            if ' ' in term_clean:
                if term_clean in text.lower():
                    found.append(term)
            else:
                if term_clean in tokens:
                    found.append(term)
        
        # Count frequencies
        freq = {}
        for term in found:
            term_clean = term.lower().strip()
            if ' ' in term_clean:
                count = text.lower().count(term_clean)
            else:
                count = sum(1 for t in tokenize(text) if t == term_clean)
            freq[term] = count
        
        results[cluster] = {
            "terms_found": found,
            "count": len(found),
            "total_frequency": sum(freq.values()),
            "frequencies": freq,
        }
    
    return results


def analyze_elevated_vocabulary(text: str) -> dict:
    """Analyze elevated/archaic vocabulary usage."""
    tokens = tokenize(text)
    token_counts = Counter(tokens)
    
    results = {}
    for word in ELEVATED_VOCABULARY:
        word_lower = word.lower()
        count = token_counts.get(word_lower, 0)
        if count > 0:
            results[word] = count
    
    return dict(sorted(results.items(), key=lambda x: -x[1]))


def analyze_connectives(text: str) -> dict:
    """Analyze connective usage."""
    text_lower = text.lower()
    results = {}
    
    for category, words in CONNECTIVES.items():
        cat_counts = {}
        for word in words:
            # Use word boundary for single words, phrase match for multi
            if ' ' in word:
                count = text_lower.count(word)
            else:
                count = len(re.findall(rf'\b{re.escape(word)}\b', text_lower))
            if count > 0:
                cat_counts[word] = count
        results[category] = {
            "items": cat_counts,
            "total": sum(cat_counts.values()),
        }
    
    return results


def analyze_rhetorical_patterns(text: str) -> dict:
    """Analyze rhetorical and stylistic patterns."""
    return {
        "semicolons": text.count(';'),
        "colons": text.count(':'),
        "em_dashes": len(re.findall(r'—|--', text)),
        "parenthetical_asides": len(re.findall(r'\([^)]{10,200}\)', text)),
        "inverted_constructions": len(re.findall(r'^(?:Not|Never|Rarely|Seldom|Hardly|Scarcely|Only|So|Such)', text, re.MULTILINE | re.IGNORECASE)),
        "rhetorical_questions": len(re.findall(r'[?]', text)),
        "parallel_structures": len(re.findall(r'(?:not only[\s\w,]+but also|both[\s\w,]+and|either[\s\w,]+or|neither[\s\w,]+nor)', text, re.IGNORECASE)),
        "biblical_citations": len(re.findall(r'\b(?:Gen|Ex|Lev|Num|Deut|Josh|Judg|Ruth|1\s*Sam|2\s*Sam|1\s*Kgs|2\s*Kgs|1\s*Chr|2\s*Chr|Ezra|Neh|Est|Job|Ps|Prov|Eccl|Song|Isa|Jer|Lam|Ezek|Dan|Hos|Joel|Amos|Obad|Jonah|Mic|Nah|Hab|Zeph|Hag|Zech|Mal|Matt|Mark|Luke|John|Acts|Rom|1\s*Cor|2\s*Cor|Gal|Eph|Phil|Col|1\s*Thess|2\s*Thess|1\s*Tim|2\s*Tim|Titus|Phlm|Heb|Jas|1\s*Pet|2\s*Pet|1\s*John|2\s*John|3\s*John|Jude|Rev)\s*\d+[:.]\d+', text)),
        "latin_terms": len(re.findall(r'\b(?:a priori|a posteriori|ad hoc|de facto|de jure|in situ|in vitro|in vivo|ipso facto|per se|prima facie|pro forma|pro tempore|sui generis|mutatis mutandis|ceteris paribus|status quo|sub specie|a fortiori|ex nihilo|exegesis|hermeneutic|homiletics|ecclesiology|soteriology|eschatology|osteriology|pneumatology|christology|anthropology|hamartiology|angelology|demonology|theodicy|theogony|theophany)\b', text, re.IGNORECASE)),
    }


def analyze_collocations(text: str, n: int = 2) -> dict:
    """Find most common n-grams."""
    tokens = tokenize(text)
    
    # Filter out very common stop words for bigrams/trigrams
    stop_words = {'the', 'and', 'of', 'to', 'a', 'in', 'that', 'is', 'for', 'it', 'with', 'as', 'was', 'be', 'by', 'on', 'not', 'this', 'but', 'have', 'from', 'or', 'an', 'are', 'at', 'his', 'they', 'which', 'were', 'been', 'their', 'has', 'would', 'what', 'will', 'there', 'all', 'we', 'you', 'he', 'she', 'them', 'than', 'so', 'if', 'when', 'who', 'may', 'do', 'these', 'into', 'up', 'out', 'had', 'then', 'some', 'other', 'could', 'only', 'should', 'did', 'about', 'its', 'over', 'such', 'also', 'can', 'shall', 'more', 'her', 'him', 'how', 'no', 'way', 'my', 'very', 'after', 'before', 'where', 'why', 'most', 'many', 'those', 'being', 'every', 'through', 'much', 'both', 'any', 'down', 'too', 'own', 'just', 'because', 'each', 'now', 'between', 'under', 'again', 'further', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very'}
    
    filtered = [t for t in tokens if t not in stop_words and len(t) > 2]
    
    ngrams = []
    for i in range(len(filtered) - n + 1):
        ngrams.append(tuple(filtered[i:i+n]))
    
    counts = Counter(ngrams)
    return dict(counts.most_common(50))


def analyze_word_frequencies(text: str, top_n: int = 200) -> dict:
    """Analyze overall word frequencies, excluding stop words."""
    tokens = tokenize(text)
    
    stop_words = {'the', 'and', 'of', 'to', 'a', 'in', 'that', 'is', 'for', 'it', 'with', 'as', 'was', 'be', 'by', 'on', 'not', 'this', 'but', 'have', 'from', 'or', 'an', 'are', 'at', 'his', 'they', 'which', 'were', 'been', 'their', 'has', 'would', 'what', 'will', 'there', 'all', 'we', 'you', 'he', 'she', 'them', 'than', 'so', 'if', 'when', 'who', 'may', 'do', 'these', 'into', 'up', 'out', 'had', 'then', 'some', 'other', 'could', 'only', 'should', 'did', 'about', 'its', 'over', 'such', 'also', 'can', 'shall', 'more', 'her', 'him', 'how', 'no', 'way', 'my', 'very', 'after', 'before', 'where', 'why', 'most', 'many', 'those', 'being', 'every', 'through', 'much', 'both', 'any', 'down', 'too', 'own', 'just', 'because', 'each', 'now', 'between', 'under', 'again', 'further', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very'}
    
    filtered = [t for t in tokens if t not in stop_words and len(t) > 2]
    counts = Counter(filtered)
    return dict(counts.most_common(top_n))


# =============================================================================
# UNIFIED DATABASE BUILDER
# =============================================================================

def analyze_single_text(text_key: str) -> dict:
    """Run full analysis on a single text."""
    print(f"Analyzing: {TEXTS[text_key]['title']}...")
    
    text = load_text(text_key)
    if not text or len(text) < 1000:
        print(f"  WARNING: Text for {text_key} is very short or empty!")
        return None
    
    sentences = split_sentences(text)
    
    result = {
        "metadata": {
            "title": TEXTS[text_key]["title"],
            "year": TEXTS[text_key]["year"],
            "file": TEXTS[text_key]["file"],
            "total_chars": len(text),
            "total_words": len(tokenize(text)),
        },
        "sentence_structure": analyze_sentences(sentences),
        "terminology": analyze_terminology(text, text_key),
        "elevated_vocabulary": analyze_elevated_vocabulary(text),
        "connectives": analyze_connectives(text),
        "rhetorical_patterns": analyze_rhetorical_patterns(text),
        "bigrams": {f"{a}_{b}": c for (a, b), c in analyze_collocations(text, 2).items()},
        "trigrams": {f"{a}_{b}_{c}": c for (a, b, c), c in analyze_collocations(text, 3).items()},
        "word_frequencies": analyze_word_frequencies(text, 200),
    }
    
    print(f"  Sentences: {result['sentence_structure']['total_sentences']}")
    print(f"  Avg length: {result['sentence_structure']['avg_length']}")
    print(f"  Words: {result['metadata']['total_words']}")
    
    return result


def build_unified_database(results: dict) -> dict:
    """Build unified database from individual text analyses."""
    
    unified = {
        "project": "OpenKuyper Comprehensive Style Database",
        "version": "1.0",
        "texts_analyzed": list(results.keys()),
        "aggregated_metrics": {},
        "cross_text_patterns": {},
        "terminology_glossary": {},
        "style_rules": [],
        "dutch_to_english_mapping": {},
    }
    
    # Aggregate sentence metrics
    all_sentence_stats = [r["sentence_structure"] for r in results.values()]
    total_sentences = sum(s["total_sentences"] for s in all_sentence_stats)
    avg_avg_length = sum(s["avg_length"] for s in all_sentence_stats) / len(all_sentence_stats)
    total_periodic = sum(s["periodic_estimate"] for s in all_sentence_stats)
    
    unified["aggregated_metrics"] = {
        "total_sentences_across_all_texts": total_sentences,
        "average_sentence_length_mean": round(avg_avg_length, 2),
        "total_long_sentences_30plus": sum(s["long_sentences_30plus"] for s in all_sentence_stats),
        "total_long_sentences_50plus": sum(s["long_sentences_50plus"] for s in all_sentence_stats),
        "total_periodic_estimate": total_periodic,
        "periodic_percentage_mean": round(total_periodic / max(total_sentences, 1) * 100, 2),
    }
    
    # Cross-text terminology (terms that appear in multiple texts)
    terminology_cross = defaultdict(lambda: {"texts": [], "total_frequency": 0})
    for text_key, result in results.items():
        for cluster, data in result["terminology"].items():
            for term, freq in data.get("frequencies", {}).items():
                terminology_cross[term]["texts"].append(text_key)
                terminology_cross[term]["total_frequency"] += freq
                terminology_cross[term]["cluster"] = cluster
    
    # Keep terms that appear in 2+ texts
    core_terminology = {
        term: data for term, data in terminology_cross.items()
        if len(data["texts"]) >= 2
    }
    unified["cross_text_patterns"]["core_terminology"] = dict(sorted(
        core_terminology.items(),
        key=lambda x: -x[1]["total_frequency"
    ]))
    
    # Elevated vocabulary across texts
    elevated_cross = defaultdict(lambda: {"texts": [], "total": 0})
    for text_key, result in results.items():
        for word, count in result["elevated_vocabulary"].items():
            elevated_cross[word]["texts"].append(text_key)
            elevated_cross[word]["total"] += count
    
    unified["cross_text_patterns"]["core_elevated_vocabulary"] = dict(sorted(
        {w: d for w, d in elevated_cross.items() if len(d["texts"]) >= 2}.items(),
        key=lambda x: -x[1]["total"]
    ))
    
    # Connective patterns
    connective_cross = defaultdict(lambda: {"texts": [], "total": 0})
    for text_key, result in results.items():
        for cat, data in result["connectives"].items():
            for word, count in data.get("items", {}).items():
                connective_cross[word]["texts"].append(text_key)
                connective_cross[word]["total"] += count
                connective_cross[word]["category"] = cat
    
    unified["cross_text_patterns"]["core_connectives"] = dict(sorted(
        {w: d for w, d in connective_cross.items() if len(d["texts"]) >= 2}.items(),
        key=lambda x: -x[1]["total"]
    ))
    
    # Build Dutch-to-English mapping (heuristic based on terminology clusters)
    # This is a seed mapping that will need human refinement
    dutch_mapping = {
        # Theological core
        "geloof": {"english": "faith", "confidence": "high", "contexts": ["Soteriology", "Faith_and_Consciousness"]},
        "genade": {"english": "grace", "confidence": "high", "contexts": ["Soteriology", "Grace_and_Operation"]},
        "heiligmaking": {"english": "sanctification", "confidence": "high", "contexts": ["Soteriology"]},
        "rechtvaardiging": {"english": "justification", "confidence": "high", "contexts": ["Soteriology"]},
        "verlossing": {"english": "salvation", "confidence": "high", "contexts": ["Soteriology"]},
        "verzoening": {"english": "atonement", "confidence": "high", "contexts": ["Soteriology"]},
        "verkiezing": {"english": "election", "confidence": "high", "contexts": ["Soteriology"]},
        "voorzienigheid": {"english": "providence", "confidence": "high", "contexts": ["Godhead_and_Persons"]},
        "openbaring": {"english": "revelation", "confidence": "high", "contexts": ["Scripture_and_Revelation"]},
        "schrift": {"english": "Scripture", "confidence": "high", "contexts": ["Scripture_and_Revelation"]},
        "verbond": {"english": "covenant", "confidence": "high", "contexts": ["Scripture_and_Revelation"]},
        "kerk": {"english": "church", "confidence": "high", "contexts": ["Church_and_Organism"]},
        "sacrament": {"english": "sacrament", "confidence": "high", "contexts": ["Church_and_Organism"]},
        "doop": {"english": "baptism", "confidence": "high", "contexts": ["Church_and_Organism"]},
        "hemelvaart": {"english": "ascension", "confidence": "high", "contexts": ["Godhead_and_Persons"]},
        "wederkomst": {"english": "second coming", "confidence": "high", "contexts": ["Eschatology"]},
        "zonde": {"english": "sin", "confidence": "high", "contexts": ["Hamartiology"]},
        "schuld": {"english": "guilt", "confidence": "high", "contexts": ["Soteriology"]},
        
        # Sphere sovereignty / Political
        "sfeer": {"english": "sphere", "confidence": "high", "contexts": ["Sphere_and_Sovereignty"]},
        "soevereiniteit": {"english": "sovereignty", "confidence": "high", "contexts": ["Sphere_and_Sovereignty", "State_and_Politics"]},
        "soevereiniteit in eigen kring": {"english": "sphere sovereignty", "confidence": "high", "contexts": ["Sphere_and_Sovereignty"]},
        "staat": {"english": "state", "confidence": "high", "contexts": ["State_and_Politics"]},
        "overheid": {"english": "government", "confidence": "high", "contexts": ["State_and_Politics"]},
        "revolutie": {"english": "revolution", "confidence": "high", "contexts": ["State_and_Politics"]},
        "antirevolutionair": {"english": "antirevolutionary", "confidence": "high", "contexts": ["State_and_Politics"]},
        "beginsel": {"english": "principle", "confidence": "high", "contexts": ["State_and_Politics", "Sphere_and_Sovereignty"]},
        "grondwet": {"english": "constitution", "confidence": "high", "contexts": ["State_and_Politics"]},
        "recht": {"english": "law / right", "confidence": "medium", "contexts": ["State_and_Politics"], "note": "Polysemous: 'recht' means both law and right/justice"},
        "volk": {"english": "people / nation", "confidence": "medium", "contexts": ["State_and_Politics"], "note": "Often 'people' in organic sense, not just populace"},
        "natie": {"english": "nation", "confidence": "high", "contexts": ["State_and_Politics"]},
        "maatschappij": {"english": "society", "confidence": "high", "contexts": ["State_and_Politics"]},
        "gezin": {"english": "family", "confidence": "high", "contexts": ["Sphere_and_Sovereignty"]},
        "school": {"english": "school", "confidence": "high", "contexts": ["Sphere_and_Sovereignty"]},
        
        # Anthropological/Psychological
        "ziel": {"english": "soul", "confidence": "high", "contexts": ["Anthropology_and_Psychology"]},
        "geest": {"english": "spirit", "confidence": "high", "contexts": ["Anthropology_and_Psychology", "Godhead_and_Persons"], "note": "Polysemous: can refer to human spirit or Holy Spirit depending on capitalization"},
        "hart": {"english": "heart", "confidence": "high", "contexts": ["Anthropology_and_Psychology"]},
        "geweten": {"english": "conscience", "confidence": "high", "contexts": ["Anthropology_and_Psychology"]},
        "bewustzijn": {"english": "consciousness", "confidence": "high", "contexts": ["Anthropology_and_Psychology"]},
        "vermogen": {"english": "faculty / power", "confidence": "medium", "contexts": ["Anthropology_and_Psychology"]},
        "wil": {"english": "will", "confidence": "high", "contexts": ["Anthropology_and_Psychology"]},
        "verstand": {"english": "intellect / understanding", "confidence": "medium", "contexts": ["Anthropology_and_Psychology"]},
        "natuur": {"english": "nature", "confidence": "high", "contexts": ["Anthropology_and_Psychology"]},
        
        # Key Kuyperian phrases
        "algemeene genade": {"english": "common grace", "confidence": "high", "contexts": ["Grace_and_Operation"]},
        "bijzondere genade": {"english": "particular grace / special grace", "confidence": "high", "contexts": ["Grace_and_Operation"]},
        "levenssysteem": {"english": "life-system / life and thought system", "confidence": "high", "contexts": ["Sphere_and_Sovereignty"]},
        "wereldbeschouwing": {"english": "worldview / world-and-life view", "confidence": "high", "contexts": ["Sphere_and_Sovereignty"]},
        "gereformeerd": {"english": "Reformed / Calvinistic", "confidence": "high", "contexts": ["Church_and_Organism"]},
        "calvinistisch": {"english": "Calvinistic", "confidence": "high", "contexts": ["Church_and_Organism"]},
        "katholiek": {"english": "catholic / universal", "confidence": "medium", "contexts": ["Church_and_Organism"], "note": "Often means universal, not Roman Catholic"},
        
        # Rhetorical/structural
        "daarom": {"english": "therefore / hence", "confidence": "high", "contexts": ["Rhetorical"]},
        "zodat": {"english": "so that", "confidence": "high", "contexts": ["Rhetorical"]},
        "echter": {"english": "however / yet", "confidence": "high", "contexts": ["Rhetorical"]},
        "immers": {"english": "for / since / indeed", "confidence": "medium", "contexts": ["Rhetorical"], "note": "Kuyper uses 'immers' frequently for causal grounding"},
        "namelijk": {"english": "namely / that is to say", "confidence": "high", "contexts": ["Rhetorical"]},
        "wel": {"english": "indeed / truly / certainly", "confidence": "medium", "contexts": ["Rhetorical"], "note": "Modal particle, often concessive"},
        "toch": {"english": "yet / still / nevertheless", "confidence": "medium", "contexts": ["Rhetorical"]},
    }
    
    unified["dutch_to_english_mapping"] = dutch_mapping
    
    # Style rules derived from analysis
    unified["style_rules"] = [
        {
            "rule": "Preserve periodic sentence structure",
            "rationale": f"Kuyper uses periodic sentences in ~{round(unified['aggregated_metrics']['periodic_percentage_mean'], 1)}% of sentences. Main clause should often be delayed.",
            "priority": "critical",
            "example": "That we, standing as we do upon the foundation of Scripture, must nevertheless confess..."
        },
        {
            "rule": "Maintain elevated sentence length",
            "rationale": f"Average sentence length across texts is {unified['aggregated_metrics']['average_sentence_length_mean']} words. Modern English averages 15-20.",
            "priority": "critical",
            "example": None
        },
        {
            "rule": "Use archaic connectives and adverbials",
            "rationale": "'Hence', 'whereby', 'therein', 'nevertheless' are characteristic markers of Kuyper's prose.",
            "priority": "high",
            "example": "Hence it follows that..."
        },
        {
            "rule": "Preserve theological precision in terminology",
            "rationale": "Terms like 'justification', 'sanctification', 'covenant' have specific technical meanings that must not be modernized.",
            "priority": "critical",
            "example": "The covenant of grace"
        },
        {
            "rule": "Maintain sweeping architectonic scope",
            "rationale": "Kuyper moves from particular to universal, from historical to systematic. Do not truncate grand concluding clauses.",
            "priority": "high",
            "example": "...and thus we see how all things work together for the consummation of His eternal purpose."
        },
        {
            "rule": "Use semicolons for clause coordination",
            "rationale": "Kuyper uses semicolons to coordinate related independent clauses within sweeping sentences.",
            "priority": "medium",
            "example": "The state has its own sphere; the church has hers; and neither may trespass upon the other."
        },
        {
            "rule": "Preserve parenthetical asides",
            "rationale": f"Kuyper uses parenthetical qualifications frequently. These add nuance and qualification.",
            "priority": "medium",
            "example": "The principle (and here we touch the very heart of the matter) is..."
        },
        {
            "rule": "Do not modernize biblical citations",
            "rationale": "Preserve traditional abbreviations and formats (e.g., 'Rom. viii. 28', not 'Romans 8:28').",
            "priority": "medium",
            "example": "Cf. Eph. ii. 8"
        },
        {
            "rule": "Maintain Kuyper's use of first-person plural",
            "rationale": "Kuyper frequently uses 'we', 'our', 'us' to create solidarity with the reader and the Reformed tradition.",
            "priority": "high",
            "example": "We confess... We maintain..."
        },
        {
            "rule": "Preserve modal particles and rhetorical grounding",
            "rationale": "Dutch particles like 'immers', 'wel', 'toch' carry modal weight. English must capture the grounding/qualification, not just the propositional content.",
            "priority": "high",
            "example": "For (immers) we must not forget..."
        },
    ]
    
    return unified


def generate_markdown_report(unified: dict, individual_results: dict) -> str:
    """Generate a human-readable markdown report."""
    
    lines = []
    lines.append("# OpenKuyper Comprehensive Vocabulary & Style Database")
    lines.append("")
    lines.append(f"**Version:** {unified['version']}  ")
    lines.append(f"**Texts Analyzed:** {', '.join(unified['texts_analyzed'])}  ")
    lines.append(f"**Total Sentences:** {unified['aggregated_metrics']['total_sentences_across_all_texts']:,}  ")
    lines.append("")
    
    lines.append("## Aggregated Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    for key, value in unified["aggregated_metrics"].items():
        lines.append(f"| {key} | {value} |")
    lines.append("")
    
    lines.append("## Cross-Text Core Terminology")
    lines.append("")
    lines.append("Terms appearing in 2+ texts, sorted by total frequency:")
    lines.append("")
    lines.append("| Term | Cluster | Texts | Total Frequency |")
    lines.append("|------|---------|-------|-----------------|")
    for term, data in list(unified["cross_text_patterns"]["core_terminology"].items())[:50]:
        lines.append(f"| {term} | {data['cluster']} | {len(data['texts'])} | {data['total_frequency']} |")
    lines.append("")
    
    lines.append("## Core Elevated Vocabulary")
    lines.append("")
    lines.append("| Word | Texts | Total Uses |")
    lines.append("|------|-------|------------|")
    for word, data in list(unified["cross_text_patterns"]["core_elevated_vocabulary"].items())[:50]:
        lines.append(f"| {word} | {len(data['texts'])} | {data['total']} |")
    lines.append("")
    
    lines.append("## Core Connectives")
    lines.append("")
    lines.append("| Connective | Category | Texts | Total Uses |")
    lines.append("|------------|----------|-------|------------|")
    for word, data in list(unified["cross_text_patterns"]["core_connectives"].items())[:50]:
        lines.append(f"| {word} | {data['category']} | {len(data['texts'])} | {data['total']} |")
    lines.append("")
    
    lines.append("## Style Rules for Translation")
    lines.append("")
    for i, rule in enumerate(unified["style_rules"], 1):
        lines.append(f"### {i}. {rule['rule']}")
        lines.append(f"**Priority:** {rule['priority']}  ")
        lines.append(f"**Rationale:** {rule['rationale']}  ")
        if rule['example']:
            lines.append(f"**Example:** *{rule['example']}*  ")
        lines.append("")
    
    lines.append("## Dutch-to-English Seed Mapping")
    lines.append("")
    lines.append("| Dutch | English | Confidence | Contexts | Notes |")
    lines.append("|-------|---------|------------|----------|-------|")
    for dutch, data in unified["dutch_to_english_mapping"].items():
        contexts = ", ".join(data.get("contexts", []))
        note = data.get("note", "")
        lines.append(f"| {dutch} | {data['english']} | {data['confidence']} | {contexts} | {note} |")
    lines.append("")
    
    lines.append("## Per-Text Breakdown")
    lines.append("")
    for text_key, result in individual_results.items():
        meta = result["metadata"]
        sent = result["sentence_structure"]
        lines.append(f"### {meta['title']} ({meta['year']})")
        lines.append(f"- Words: {meta['total_words']:,}")
        lines.append(f"- Sentences: {sent['total_sentences']:,}")
        lines.append(f"- Avg sentence length: {sent['avg_length']}")
        lines.append(f"- Long sentences (30+ words): {sent['long_sentences_30plus']}")
        lines.append(f"- Periodic estimate: {sent['periodic_estimate']} ({sent['periodic_percentage']}%)")
        lines.append("")
    
    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 60)
    print("OpenKuyper Comprehensive Style Analyzer")
    print("=" * 60)
    print()
    
    # Analyze each text
    individual_results = {}
    for text_key in TEXTS:
        result = analyze_single_text(text_key)
        if result:
            individual_results[text_key] = result
    
    if not individual_results:
        print("ERROR: No texts could be analyzed.")
        sys.exit(1)
    
    print()
    print("-" * 40)
    print("Building unified database...")
    print("-" * 40)
    
    # Build unified database
    unified = build_unified_database(individual_results)
    
    # Save JSON outputs
    unified_path = OUTPUT_DIR / "unified_style_database.json"
    with open(unified_path, 'w', encoding='utf-8') as f:
        json.dump(unified, f, indent=2, ensure_ascii=False)
    print(f"Saved unified database: {unified_path}")
    
    individual_path = OUTPUT_DIR / "individual_text_analyses.json"
    with open(individual_path, 'w', encoding='utf-8') as f:
        json.dump(individual_results, f, indent=2, ensure_ascii=False)
    print(f"Saved individual analyses: {individual_path}")
    
    # Generate markdown report
    report = generate_markdown_report(unified, individual_results)
    report_path = OUTPUT_DIR / "COMPREHENSIVE_STYLE_DATABASE.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"Saved markdown report: {report_path}")
    
    print()
    print("=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"Texts analyzed: {len(individual_results)}")
    print(f"Total sentences: {unified['aggregated_metrics']['total_sentences_across_all_texts']:,}")
    print(f"Average sentence length: {unified['aggregated_metrics']['average_sentence_length_mean']}")
    print(f"Core terminology entries: {len(unified['cross_text_patterns']['core_terminology'])}")
    print(f"Dutch→English mappings: {len(unified['dutch_to_english_mapping'])}")
    print(f"Style rules: {len(unified['style_rules'])}")


if __name__ == "__main__":
    main()
