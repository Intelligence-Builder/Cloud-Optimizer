# Epic 5: Smart-Scaffold Integration & Cutover

## Overview

Migrate Smart-Scaffold to use Intelligence-Builder for knowledge graph functionality while preserving local context system and workflow coordination.

**Duration**: 2-3 weeks
**Priority**: Medium
**Dependencies**: Epic 4 (Remaining Pillars) complete

## Objectives

1. Migrate Smart-Scaffold knowledge graph to IB platform
2. Integrate SS context system with IB entities
3. Complete production cutover with validation

## Architecture After Migration

```
Smart-Scaffold
├── Local Systems (PostgreSQL)
│   ├── Context records (revision-controlled)
│   ├── Workflow events (temporal)
│   └── Session state
│
└── Intelligence-Builder Platform (via SDK)
    ├── Issues, PRs, commits as entities
    ├── Relationships (implements, tests, modifies)
    ├── Vector search for similar issues
    └── Graph traversal for implementation paths
```

## Deliverables

### 5.1 Smart-Scaffold KG Migration
- Analyze current SS KG schema
- Map SS entities to IB entity types
- Create migration scripts
- Plan hybrid operation period

### 5.2 Context System Integration
- Port context system to work with IB
- Maintain local JSON context
- Create context-to-entity sync
- Preserve workflow coordination

### 5.3 Production Cutover
- Deploy IB with all domains
- Migrate SS to use IB
- Run parallel operation period
- Validate data integrity
- Complete cutover
- Archive old KG code

## Acceptance Criteria

- [ ] SS uses IB for knowledge graph operations
- [ ] Context system works with IB
- [ ] No data loss during migration
- [ ] Performance meets requirements (< 200ms API response)
- [ ] All integration tests passing
- [ ] Workflow coordination maintained
- [ ] Old KG code archived

## Sub-Tasks

1. KG Schema Analysis & Mapping (Week 1)
2. Migration Scripts (Week 1)
3. Context System Integration (Week 1-2)
4. Parallel Operation Testing (Week 2)
5. Production Cutover (Week 2-3)
