# Intelligence-Builder (IB) Platform - Strategic Design

**Version:** 1.0
**Date:** 2025-11-30
**Status:** Design Phase
**Based On:** Legacy Cloud_Optimizer GraphRAG designs (97.4% quality score, 850ms response time)

---

## Executive Summary

Intelligence-Builder (IB) is the **intelligence platform** that provides knowledge management, search, NLU, and answer generation capabilities. It is deployed as a bundled component with Cloud Optimizer.

### IB Responsibilities

| Component | Requirements | Current State |
|-----------|--------------|---------------|
| Knowledge Ingestion | KNG-001 to KNG-014 | 85% exists in legacy |
| Hybrid Search | SRH-001 to SRH-006 | 95% exists (850ms) |
| NLU | NLU-001 to NLU-006 | 70% exists |
| Answer Generation | ANS-001 to ANS-008 | 75% exists |
| Feedback Loop | FBK-001 to FBK-007 | 55% exists |
| Ontology Management | ONT-001 to ONT-008 | 50% exists |

### Performance Baselines (From Legacy)

```
GraphRAG Pipeline: 850ms (72% faster than 3s target)
Memory Usage: 24.8MB (95% under limit)
P95 Intent Analysis: 179ms
P95 Context Retrieval: 285ms
P95 Answer Generation: 156ms
Quality Score: 97.4%
```

---

## 1. Architecture Overview

### IB Platform Structure

```
ib_platform/
├── __init__.py
├── sdk.py                      # Public SDK interface
├── config.py                   # Platform configuration
│
├── graph/                      # Graph Database Layer
│   ├── __init__.py
│   ├── protocol.py            # GraphProtocol interface
│   ├── backends/
│   │   ├── postgres_cte.py    # PostgreSQL CTE backend
│   │   └── memgraph.py        # Memgraph backend (optional)
│   ├── models.py              # Node, Edge, SubGraph
│   └── traversal.py           # Graph traversal utilities
│
├── ingestion/                  # KNG-* Requirements
│   ├── __init__.py
│   ├── registry.py            # KNG-001: Source registry
│   ├── document_processor.py  # KNG-002: Document ingestion
│   ├── delta_processor.py     # KNG-006: Incremental updates
│   ├── sources/
│   │   ├── cve.py            # KNG-003: CVE ingestion
│   │   ├── cis.py            # KNG-004: CIS benchmarks
│   │   └── aws_pricing.py    # KNG-005: Pricing data
│   └── quality.py             # KNG-011: Quality scoring
│
├── patterns/                   # Pattern Detection
│   ├── __init__.py
│   ├── engine.py              # Pattern detection engine
│   ├── entity_extractor.py    # KNG-007: Entity extraction
│   └── matcher.py             # Pattern matching
│
├── search/                     # SRH-* Requirements
│   ├── __init__.py
│   ├── vector_search.py       # SRH-001: Vector similarity
│   ├── graph_retrieval.py     # SRH-002: Graph-enhanced
│   ├── hybrid_ranker.py       # SRH-003: Hybrid ranking
│   ├── mode_selector.py       # SRH-004: Search modes
│   ├── context_builder.py     # SRH-005: Context assembly
│   └── cache.py               # SRH-006: Performance cache
│
├── nlu/                        # NLU-* Requirements
│   ├── __init__.py
│   ├── intent_classifier.py   # NLU-001: Intent parsing
│   ├── domain_classifier.py   # NLU-002: Domain classification
│   ├── query_ner.py           # NLU-003: Entity extraction
│   ├── reformulator.py        # NLU-004: Query reformulation
│   ├── temporal_parser.py     # NLU-005: Temporal understanding
│   └── decomposer.py          # NLU-006: Query decomposition
│
├── generation/                 # ANS-* Requirements
│   ├── __init__.py
│   ├── synthesizer.py         # ANS-001: Multi-source synthesis
│   ├── confidence.py          # ANS-002: Confidence scoring
│   ├── alternatives.py        # ANS-003: Alternative answers
│   ├── ranker.py              # ANS-004: Ranked recommendations
│   ├── remediation.py         # ANS-005: Remediation steps
│   ├── evidence.py            # ANS-006: Evidence chains
│   ├── formatter.py           # ANS-007: Answer formatting
│   └── cross_domain.py        # ANS-008: Cross-domain insights
│
├── feedback/                   # FBK-* Requirements
│   ├── __init__.py
│   ├── capture.py             # FBK-001: Feedback capture
│   ├── classifier.py          # FBK-002: Feedback classification
│   ├── routing.py             # FBK-003: Expert routing
│   ├── pipeline.py            # FBK-004: Feedback-to-knowledge
│   ├── resolution.py          # FBK-005: Conflict resolution
│   └── metrics.py             # FBK-006/007: Metrics & analytics
│
├── ontology/                   # ONT-* Requirements
│   ├── __init__.py
│   ├── schema.py              # ONT-001: Ontology schema
│   ├── entity_types.py        # ONT-002: Entity type management
│   ├── relationship_types.py  # ONT-003: Relationship types
│   ├── synonyms.py            # ONT-004: Synonym management
│   ├── resolution.py          # ONT-005: Entity resolution
│   ├── versioning.py          # ONT-006: Ontology versioning
│   ├── validation.py          # ONT-007: Ontology validation
│   └── io.py                  # ONT-008: Import/export
│
├── embeddings/
│   ├── __init__.py
│   ├── generator.py           # KNG-009: Embedding generation
│   └── cache.py               # Embedding cache
│
├── domains/                    # Domain System
│   ├── __init__.py
│   ├── base.py                # Domain base class
│   ├── registry.py            # Domain registry
│   ├── security/              # Security domain
│   │   ├── __init__.py
│   │   ├── patterns.py
│   │   └── entities.py
│   └── cost/                  # Cost domain
│       ├── __init__.py
│       ├── patterns.py
│       └── entities.py
│
└── api/                       # Internal API (for CO)
    ├── __init__.py
    └── routes.py              # FastAPI routes (if separate)
```

---

## 2. Knowledge Ingestion System (KNG-*)

### Design Goals

Based on legacy `src/services/graphrag/` and `src/services/semantic/`:
- **Incremental updates**: Process only changed data (KNG-006)
- **Quality scoring**: Rank entities by source authority (KNG-011)
- **Deduplication**: Merge duplicate entities (KNG-010)

### Architecture

```
                    ┌─────────────────────────────────────┐
                    │         Source Registry              │
                    │    (cron schedules, credentials)     │
                    └──────────────┬──────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
   │ CVE Source  │         │ CIS Source  │         │ AWS Pricing │
   │ (NVD/CVE)   │         │ (Benchmarks)│         │   Source    │
   └──────┬──────┘         └──────┬──────┘         └──────┬──────┘
          │                        │                        │
          └────────────────────────┼────────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │       Document Processor             │
                    │  - Parse, chunk, extract metadata   │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │       Entity Extractor               │
                    │  - Pattern-based NER                │
                    │  - Ontology-guided extraction       │
                    └──────────────┬──────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
          ▼                        ▼                        ▼
   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
   │  Embedding  │         │ Relationship│         │   Quality   │
   │  Generator  │         │   Mapper    │         │   Scorer    │
   └──────┬──────┘         └──────┬──────┘         └──────┬──────┘
          │                        │                        │
          └────────────────────────┼────────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │       Deduplication Engine           │
                    │  - Fuzzy matching                   │
                    │  - Entity resolution                │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │         Graph Storage                │
                    │  - Nodes with embeddings            │
                    │  - Edges with relationships         │
                    │  - Version history                  │
                    └─────────────────────────────────────┘
```

### Key Data Models

```python
@dataclass
class KnowledgeSource:
    """KNG-001: Source registry entry."""
    source_id: str
    name: str
    source_type: SourceType  # CVE, CIS, AWS_PRICING, DOCUMENT
    url: Optional[str]
    credentials: Optional[Dict[str, str]]  # Encrypted
    schedule: str  # Cron expression
    last_sync: Optional[datetime]
    status: SourceStatus
    metadata: Dict[str, Any]


@dataclass
class KnowledgeEntity:
    """Extracted knowledge entity."""
    entity_id: str
    entity_type: str  # From ontology
    name: str
    attributes: Dict[str, Any]
    embedding: Optional[List[float]]  # 384-dim or 1536-dim
    source_id: str
    quality_score: float  # 0.0 - 1.0
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass
class EntityRelationship:
    """KNG-008: Relationship between entities."""
    relationship_id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str  # From ontology
    confidence: float
    evidence: List[str]  # Source citations
```

### Migration from Legacy

| Legacy File | New Location | Changes |
|-------------|--------------|---------|
| `src/services/graphrag/` | `ib_platform/search/` | Refactor into modules |
| `src/services/semantic/` | `ib_platform/embeddings/` | Keep embedding logic |
| `src/models/knowledge_base.py` | `ib_platform/graph/models.py` | Enhance schema |

---

## 3. Hybrid Search System (SRH-*)

### Design Goals

Based on legacy orchestrator achieving **850ms response time, 97.4% quality**:
- **Vector search**: Semantic similarity using embeddings (SRH-001)
- **Graph traversal**: Multi-hop relationship exploration (SRH-002)
- **Hybrid ranking**: Combine scores intelligently (SRH-003)

### Query Orchestrator Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Query Orchestrator                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Query     │  │  Strategy   │  │    Execution Engine     │  │
│  │ Classifier  │─▶│  Selector   │─▶│  (Parallel Execution)   │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│ Vector Search │     │ Graph Search  │     │ Keyword Search│
│ (pgvector)    │     │ (CTE/Cypher)  │     │ (Full-text)   │
└───────┬───────┘     └───────┬───────┘     └───────┬───────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │  Hybrid Ranker    │
                    │  (Score fusion)   │
                    └─────────┬─────────┘
                              │
                              ▼
                    ┌───────────────────┐
                    │ Context Builder   │
                    │ (Assemble result) │
                    └───────────────────┘
```

### Query Classification (From Legacy Design)

```python
class QueryType(Enum):
    """Query types for routing decisions."""
    FACTUAL = "factual"           # 40% - Direct lookup
    ANALYTICAL = "analytical"     # 25% - Pattern analysis
    RELATIONAL = "relational"     # 15% - Entity relationships
    TEMPORAL = "temporal"         # 10% - Time-based queries
    AGGREGATION = "aggregation"   # 5%  - Counts, sums
    COMPARISON = "comparison"     # 3%  - Side-by-side
    MULTI_HOP = "multi_hop"       # 2%  - Complex reasoning


class QueryComplexity(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"       # 60% - Single operation
    MODERATE = "moderate"   # 30% - 2-3 operations
    COMPLEX = "complex"     # 10% - Multi-step reasoning


class SearchStrategy(Enum):
    """Retrieval strategies."""
    VECTOR_ONLY = "vector_only"           # Fast semantic search
    GRAPH_ONLY = "graph_only"             # Relationship-focused
    HYBRID_VECTOR_FIRST = "hybrid_vf"     # Vector then graph expand
    HYBRID_GRAPH_FIRST = "hybrid_gf"      # Graph then vector enrich
    PARALLEL_HYBRID = "parallel"          # Both in parallel
```

### Strategy Selection Logic

```python
def select_strategy(query_type: QueryType, complexity: QueryComplexity) -> SearchStrategy:
    """Select optimal strategy based on query characteristics."""

    strategy_matrix = {
        QueryType.FACTUAL: {
            QueryComplexity.SIMPLE: SearchStrategy.VECTOR_ONLY,
            QueryComplexity.MODERATE: SearchStrategy.HYBRID_VECTOR_FIRST,
            QueryComplexity.COMPLEX: SearchStrategy.PARALLEL_HYBRID,
        },
        QueryType.RELATIONAL: {
            QueryComplexity.SIMPLE: SearchStrategy.GRAPH_ONLY,
            QueryComplexity.MODERATE: SearchStrategy.HYBRID_GRAPH_FIRST,
            QueryComplexity.COMPLEX: SearchStrategy.PARALLEL_HYBRID,
        },
        QueryType.TEMPORAL: {
            QueryComplexity.SIMPLE: SearchStrategy.GRAPH_ONLY,
            QueryComplexity.MODERATE: SearchStrategy.GRAPH_ONLY,
            QueryComplexity.COMPLEX: SearchStrategy.PARALLEL_HYBRID,
        },
        # ... other types
    }

    return strategy_matrix.get(query_type, {}).get(
        complexity, SearchStrategy.PARALLEL_HYBRID
    )
```

### Hybrid Ranking Algorithm (SRH-003)

```python
def hybrid_rank(
    vector_results: List[SearchResult],
    graph_results: List[SearchResult],
    weights: RankingWeights
) -> List[SearchResult]:
    """
    Combine vector and graph results using weighted fusion.

    Score = (w_vector * vector_score) + (w_graph * graph_score) + (w_recency * recency_score)
    """
    combined = {}

    for result in vector_results:
        combined[result.entity_id] = RankedResult(
            entity_id=result.entity_id,
            vector_score=result.score,
            graph_score=0.0,
            recency_score=calculate_recency(result.updated_at)
        )

    for result in graph_results:
        if result.entity_id in combined:
            combined[result.entity_id].graph_score = result.score
        else:
            combined[result.entity_id] = RankedResult(
                entity_id=result.entity_id,
                vector_score=0.0,
                graph_score=result.score,
                recency_score=calculate_recency(result.updated_at)
            )

    # Calculate final scores
    for result in combined.values():
        result.final_score = (
            weights.vector * result.vector_score +
            weights.graph * result.graph_score +
            weights.recency * result.recency_score
        )

    return sorted(combined.values(), key=lambda r: r.final_score, reverse=True)
```

---

## 4. Natural Language Understanding (NLU-*)

### Design Goals

Based on legacy `src/services/graphrag/intent_analyzer.py`:
- **Intent classification**: 7 query types with confidence (NLU-001)
- **Domain detection**: Security, cost, compliance, performance (NLU-002)
- **Entity extraction**: Ontology-guided NER (NLU-003)

### NLU Pipeline

```
User Query: "What AWS Lambda security vulnerabilities were discovered last month?"
                                        │
                                        ▼
                    ┌───────────────────────────────────┐
                    │       Intent Classifier           │
                    │  Output: FACTUAL (0.85)           │
                    └───────────────────┬───────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────┐
                    │       Domain Classifier           │
                    │  Output: SECURITY (0.92)          │
                    └───────────────────┬───────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────┐
                    │       Entity Extractor            │
                    │  Output: [AWS Lambda, CVE]        │
                    └───────────────────┬───────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────┐
                    │       Temporal Parser             │
                    │  Output: date_range(last_month)   │
                    └───────────────────┬───────────────┘
                                        │
                                        ▼
                    ┌───────────────────────────────────┐
                    │       Query Decomposer            │
                    │  Output: [find_service, find_cve] │
                    └───────────────────────────────────┘
```

### Intent Classification Model

```python
@dataclass
class IntentClassification:
    """NLU-001: Query intent classification result."""
    query_type: QueryType
    confidence: float  # 0.0 - 1.0
    complexity: QueryComplexity
    reasoning: str  # Explanation for classification


class IntentClassifier:
    """Classify query intent using pattern matching and ML."""

    # Pattern-based classification (fast path)
    INTENT_PATTERNS = {
        QueryType.FACTUAL: [
            r"what is\s+",
            r"define\s+",
            r"explain\s+",
            r"describe\s+",
        ],
        QueryType.RELATIONAL: [
            r"how (?:is|are) .+ related to",
            r"relationship between",
            r"connected to",
            r"depends on",
        ],
        QueryType.TEMPORAL: [
            r"when did",
            r"since\s+",
            r"before\s+",
            r"after\s+",
            r"last (?:week|month|year)",
        ],
        QueryType.COMPARISON: [
            r"compare\s+",
            r"difference between",
            r"vs\.?\s+",
            r"better than",
        ],
    }

    async def classify(self, query: str) -> IntentClassification:
        """Classify query intent."""
        # Fast path: Pattern matching
        for query_type, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    return IntentClassification(
                        query_type=query_type,
                        confidence=0.85,
                        complexity=self._assess_complexity(query),
                        reasoning=f"Matched pattern: {pattern}"
                    )

        # Slow path: ML-based classification (if patterns don't match)
        return await self._ml_classify(query)
```

---

## 5. Answer Generation Engine (ANS-*)

### Design Goals

Based on legacy `LLM_ANSWER_SYNTHESIS_STRATEGIC_DESIGN.md`:
- **Multi-source synthesis**: Combine context intelligently (ANS-001)
- **Confidence scoring**: Calibrate to answer quality (ANS-002)
- **Evidence chains**: Preserve citations (ANS-006)

### Answer Generation Pipeline

```
Search Results (Context)
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│                    Answer Generator                             │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────────┐  │
│  │  Context    │  │   LLM       │  │    Post-Processing    │  │
│  │  Preparer   │─▶│  Synthesizer│─▶│    (Format, Cite)     │  │
│  └─────────────┘  └─────────────┘  └───────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                      Answer Object                              │
│  - text: str                                                   │
│  - confidence: float                                           │
│  - evidence: List[Citation]                                    │
│  - alternatives: List[Answer] (if confidence < 0.8)            │
│  - recommendations: List[Recommendation]                       │
│  - remediation_steps: List[Step] (for security findings)       │
└────────────────────────────────────────────────────────────────┘
```

### LLM Model Selection Strategy

```python
class ModelSelector:
    """Select optimal LLM based on query complexity and cost."""

    MODEL_PROFILES = {
        "local_fast": {
            "model": "llama3.1:8b",
            "latency_ms": 200,
            "cost_per_1k": 0.0,
            "quality": 0.75,
            "use_for": [QueryComplexity.SIMPLE],
        },
        "local_quality": {
            "model": "llama3.1:70b",
            "latency_ms": 800,
            "cost_per_1k": 0.0,
            "quality": 0.85,
            "use_for": [QueryComplexity.MODERATE],
        },
        "cloud_gpt35": {
            "model": "gpt-3.5-turbo",
            "latency_ms": 400,
            "cost_per_1k": 0.002,
            "quality": 0.88,
            "use_for": [QueryComplexity.MODERATE],
        },
        "cloud_gpt4": {
            "model": "gpt-4-turbo",
            "latency_ms": 600,
            "cost_per_1k": 0.03,
            "quality": 0.95,
            "use_for": [QueryComplexity.COMPLEX],
        },
    }

    def select(
        self,
        complexity: QueryComplexity,
        prefer_local: bool = True,
        max_latency_ms: int = 1000
    ) -> str:
        """Select optimal model for query."""
        candidates = [
            (name, profile)
            for name, profile in self.MODEL_PROFILES.items()
            if complexity in profile["use_for"]
            and profile["latency_ms"] <= max_latency_ms
        ]

        if prefer_local:
            local = [c for c in candidates if c[1]["cost_per_1k"] == 0]
            if local:
                return max(local, key=lambda c: c[1]["quality"])[0]

        return max(candidates, key=lambda c: c[1]["quality"])[0]
```

### Answer Confidence Scoring (ANS-002)

```python
def calculate_confidence(
    search_results: SearchResults,
    llm_response: LLMResponse,
    evidence_count: int
) -> float:
    """
    Calculate answer confidence from multiple signals.

    Factors:
    - Search result quality (relevance scores)
    - Evidence coverage (how many sources support answer)
    - LLM confidence (if provided)
    - Source authority (quality scores of cited entities)
    """
    base_confidence = 0.5

    # Search quality contribution (0-0.25)
    avg_relevance = sum(r.score for r in search_results.results) / len(search_results.results)
    search_contrib = avg_relevance * 0.25

    # Evidence coverage contribution (0-0.15)
    evidence_contrib = min(evidence_count / 5, 1.0) * 0.15

    # Source authority contribution (0-0.10)
    authority_scores = [r.entity.quality_score for r in search_results.results if hasattr(r.entity, 'quality_score')]
    authority_contrib = (sum(authority_scores) / len(authority_scores) if authority_scores else 0.5) * 0.10

    return min(base_confidence + search_contrib + evidence_contrib + authority_contrib, 1.0)
```

---

## 6. Feedback Loop System (FBK-*)

### Design Goals

- **Capture feedback**: All user interactions (FBK-001)
- **Route to experts**: Based on domain and confidence (FBK-003)
- **Update knowledge**: Convert validated feedback to entities (FBK-004)

### Feedback Pipeline

```
User Feedback
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                  Feedback Capture                            │
│  - thumbs up/down                                           │
│  - corrections                                              │
│  - evidence validation                                      │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Feedback Classifier                         │
│  Type: FACTUAL_ERROR | OUTDATED | WRONG_EVIDENCE | OTHER    │
└─────────────────────────────┬───────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
┌───────────────────────┐       ┌───────────────────────┐
│  High Confidence      │       │  Low Confidence       │
│  (Auto-process)       │       │  (Expert Review)      │
└───────────┬───────────┘       └───────────┬───────────┘
            │                               │
            │                               ▼
            │                   ┌───────────────────────┐
            │                   │    Expert Queue       │
            │                   │  (Domain-based)       │
            │                   └───────────┬───────────┘
            │                               │
            └───────────────┬───────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Feedback-to-Knowledge Pipeline                  │
│  - Validate correction                                      │
│  - Update entity or relationship                            │
│  - Increment version                                        │
│  - Log audit trail                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Ontology Management System (ONT-*)

### Design Goals

- **Schema definition**: Entity types, relationships, constraints (ONT-001-003)
- **Entity resolution**: Canonical entity matching (ONT-005)
- **Versioning**: Track changes with rollback (ONT-006)

### Ontology Schema

```python
@dataclass
class EntityType:
    """ONT-002: Entity type definition."""
    type_id: str
    name: str
    parent_type: Optional[str]  # Inheritance
    attributes: List[AttributeDefinition]
    constraints: List[Constraint]
    examples: List[str]


@dataclass
class RelationshipType:
    """ONT-003: Relationship type definition."""
    type_id: str
    name: str
    source_types: List[str]  # Allowed source entity types
    target_types: List[str]  # Allowed target entity types
    cardinality: Cardinality  # ONE_TO_ONE, ONE_TO_MANY, MANY_TO_MANY
    attributes: List[AttributeDefinition]


@dataclass
class Synonym:
    """ONT-004: Synonym/alias entry."""
    canonical_name: str
    aliases: List[str]
    entity_type: str
    context: Optional[str]  # Domain context for disambiguation
```

### Entity Resolution Engine (ONT-005)

```python
class EntityResolver:
    """Resolve text mentions to canonical entities."""

    async def resolve(
        self,
        mention: str,
        context: Optional[str] = None,
        entity_type_hint: Optional[str] = None
    ) -> Optional[Entity]:
        """
        Resolve a text mention to a canonical entity.

        Steps:
        1. Exact match in entity names
        2. Synonym lookup
        3. Fuzzy matching (Levenshtein)
        4. Context-aware disambiguation
        """
        # Step 1: Exact match
        entity = await self._exact_match(mention)
        if entity:
            return entity

        # Step 2: Synonym lookup
        canonical = await self._lookup_synonym(mention)
        if canonical:
            return await self._exact_match(canonical)

        # Step 3: Fuzzy match
        candidates = await self._fuzzy_match(mention, threshold=0.85)
        if len(candidates) == 1:
            return candidates[0]

        # Step 4: Context disambiguation
        if context and len(candidates) > 1:
            return await self._disambiguate(candidates, context)

        return None
```

---

## 8. IB SDK Interface

### Public API for Cloud Optimizer

```python
# ib_platform/sdk.py

class IBPlatformSDK:
    """
    Public SDK interface for Cloud Optimizer to interact with IB Platform.

    All CO code should use this SDK rather than importing IB internals.
    """

    def __init__(self, config: IBConfig):
        self._search = HybridSearchEngine(config)
        self._nlu = NLUPipeline(config)
        self._generator = AnswerGenerator(config)
        self._ingestion = IngestionPipeline(config)
        self._feedback = FeedbackPipeline(config)
        self._ontology = OntologyManager(config)

    # --- Knowledge Operations ---

    async def ingest_document(
        self,
        document: Document,
        source_id: str
    ) -> IngestionResult:
        """KNG-002: Ingest a document into the knowledge graph."""
        return await self._ingestion.process_document(document, source_id)

    async def query_knowledge(
        self,
        query: str,
        search_mode: SearchMode = SearchMode.HYBRID,
        max_results: int = 10
    ) -> SearchResults:
        """SRH-001-006: Execute a knowledge query."""
        return await self._search.search(query, search_mode, max_results)

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Retrieve a single entity by ID."""
        return await self._search.get_entity(entity_id)

    # --- NLU Operations ---

    async def parse_intent(self, query: str) -> IntentClassification:
        """NLU-001: Parse query intent."""
        return await self._nlu.classify_intent(query)

    async def classify_domain(self, query: str) -> DomainClassification:
        """NLU-002: Classify query domain."""
        return await self._nlu.classify_domain(query)

    async def extract_entities(self, text: str) -> List[EntityMention]:
        """NLU-003: Extract entity mentions from text."""
        return await self._nlu.extract_entities(text)

    # --- Answer Generation ---

    async def generate_answer(
        self,
        query: str,
        context: Optional[SearchResults] = None
    ) -> Answer:
        """ANS-001-008: Generate an answer for a query."""
        if context is None:
            context = await self.query_knowledge(query)
        return await self._generator.generate(query, context)

    async def get_recommendations(
        self,
        finding: Finding,
        max_recommendations: int = 5
    ) -> List[Recommendation]:
        """ANS-004: Get ranked recommendations for a finding."""
        return await self._generator.get_recommendations(finding, max_recommendations)

    async def get_remediation(
        self,
        vulnerability_id: str
    ) -> Optional[RemediationSteps]:
        """ANS-005: Get remediation steps for a vulnerability."""
        return await self._generator.get_remediation(vulnerability_id)

    # --- Feedback Operations ---

    async def submit_feedback(self, feedback: Feedback) -> FeedbackResult:
        """FBK-001: Submit user feedback."""
        return await self._feedback.capture(feedback)

    # --- Ontology Operations ---

    async def resolve_entity(
        self,
        mention: str,
        context: Optional[str] = None
    ) -> Optional[Entity]:
        """ONT-005: Resolve a text mention to canonical entity."""
        return await self._ontology.resolve(mention, context)
```

---

## 9. Database Schema

### IB Platform Tables

```sql
-- ib_platform schema
CREATE SCHEMA IF NOT EXISTS ib_platform;

-- Knowledge Sources (KNG-001)
CREATE TABLE ib_platform.knowledge_sources (
    source_id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    url TEXT,
    credentials JSONB,  -- Encrypted
    schedule VARCHAR(100),  -- Cron expression
    last_sync TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'active',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Knowledge Entities (Graph Nodes)
CREATE TABLE ib_platform.entities (
    entity_id UUID PRIMARY KEY,
    entity_type VARCHAR(100) NOT NULL,
    name VARCHAR(500) NOT NULL,
    attributes JSONB DEFAULT '{}',
    embedding vector(384),  -- pgvector
    source_id UUID REFERENCES ib_platform.knowledge_sources(source_id),
    quality_score FLOAT DEFAULT 0.5,
    version INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Entity Relationships (Graph Edges)
CREATE TABLE ib_platform.relationships (
    relationship_id UUID PRIMARY KEY,
    source_entity_id UUID REFERENCES ib_platform.entities(entity_id),
    target_entity_id UUID REFERENCES ib_platform.entities(entity_id),
    relationship_type VARCHAR(100) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    evidence JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ontology Schema (ONT-001)
CREATE TABLE ib_platform.ontology_entity_types (
    type_id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_type VARCHAR(100),
    attributes JSONB DEFAULT '[]',
    constraints JSONB DEFAULT '[]',
    version INT DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Synonyms (ONT-004)
CREATE TABLE ib_platform.synonyms (
    synonym_id UUID PRIMARY KEY,
    canonical_name VARCHAR(500) NOT NULL,
    alias VARCHAR(500) NOT NULL,
    entity_type VARCHAR(100),
    context VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User Feedback (FBK-001)
CREATE TABLE ib_platform.feedback (
    feedback_id UUID PRIMARY KEY,
    query_id UUID,
    entity_id UUID,
    feedback_type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    user_id UUID,
    status VARCHAR(50) DEFAULT 'pending',
    resolution JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_entities_embedding ON ib_platform.entities
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_entities_type ON ib_platform.entities(entity_type);
CREATE INDEX idx_relationships_source ON ib_platform.relationships(source_entity_id);
CREATE INDEX idx_relationships_target ON ib_platform.relationships(target_entity_id);
CREATE INDEX idx_synonyms_alias ON ib_platform.synonyms(alias);
```

---

## 10. Implementation Phases

### Phase 2: IB Core (Weeks 6-10)

| Week | Focus | Requirements |
|------|-------|--------------|
| 6-7 | Knowledge Ingestion | KNG-001 to KNG-008 |
| 7-8 | Hybrid Search | SRH-001 to SRH-006 |
| 8-9 | Embeddings & Quality | KNG-009 to KNG-014 |
| 9-10 | Testing & Integration | All KNG-*, SRH-* |

### Phase 4: IB Advanced (Weeks 21-26)

| Week | Focus | Requirements |
|------|-------|--------------|
| 21-22 | NLU Enhancement | NLU-001 to NLU-006 |
| 22-23 | Answer Generation | ANS-001 to ANS-008 |

### Phase 5: IB Extended (Weeks 27-30)

| Week | Focus | Requirements |
|------|-------|--------------|
| 27-28 | Feedback Loop | FBK-001 to FBK-007 |
| 28-30 | Ontology Management | ONT-001 to ONT-008 |

---

## 11. Migration from Legacy

### File Mapping

| Legacy | New IB Location | Notes |
|--------|-----------------|-------|
| `src/services/graphrag/orchestrator.py` | `ib_platform/search/orchestrator.py` | Refactor |
| `src/services/graphrag/intent_analyzer.py` | `ib_platform/nlu/intent_classifier.py` | Enhance |
| `src/services/graphrag/answer_generator.py` | `ib_platform/generation/synthesizer.py` | Add LLM |
| `src/services/graphrag/knowledge_graph_adapter.py` | `ib_platform/graph/backends/postgres_cte.py` | Keep |
| `src/services/graphrag/context_retriever.py` | `ib_platform/search/context_builder.py` | Refactor |
| `src/services/graphrag/cache/` | `ib_platform/search/cache.py` | Keep |
| `src/services/semantic/` | `ib_platform/embeddings/` | Keep |
| `src/models/knowledge_base.py` | `ib_platform/graph/models.py` | Enhance |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-30 | Initial IB strategic design based on legacy GraphRAG |
