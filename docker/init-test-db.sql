-- Initialize test database schema for Intelligence-Builder platform
-- This schema matches the TECHNICAL_DESIGN.md specification

-- Create schema
CREATE SCHEMA IF NOT EXISTS intelligence;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Entities table
CREATE TABLE intelligence.entities (
    entity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'test',
    entity_type VARCHAR(100) NOT NULL,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    content TEXT,
    metadata JSONB DEFAULT '{}',
    tags TEXT[] DEFAULT '{}',
    domain VARCHAR(100),
    confidence DECIMAL(3,2) DEFAULT 1.0,
    source_document_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT valid_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

-- Relationships table
CREATE TABLE intelligence.relationships (
    relationship_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(100) NOT NULL DEFAULT 'test',
    from_entity_id UUID NOT NULL REFERENCES intelligence.entities(entity_id) ON DELETE CASCADE,
    to_entity_id UUID NOT NULL REFERENCES intelligence.entities(entity_id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    weight DECIMAL(3,2) DEFAULT 1.0,
    confidence DECIMAL(3,2) DEFAULT 1.0,
    properties JSONB DEFAULT '{}',
    evidence TEXT,
    domain VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,

    CONSTRAINT no_self_loop CHECK (from_entity_id != to_entity_id),
    CONSTRAINT valid_weight CHECK (weight >= 0 AND weight <= 1),
    CONSTRAINT valid_rel_confidence CHECK (confidence >= 0 AND confidence <= 1)
);

-- Patterns table
CREATE TABLE intelligence.patterns (
    pattern_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    domain VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    regex_pattern TEXT NOT NULL,
    output_type VARCHAR(100) NOT NULL,
    base_confidence DECIMAL(3,2) DEFAULT 0.75,
    priority VARCHAR(20) DEFAULT 'normal',
    version VARCHAR(20) DEFAULT '1.0.0',
    description TEXT,
    examples TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_pattern_name UNIQUE (domain, name, version)
);

-- Domains table
CREATE TABLE intelligence.domains (
    domain_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    version VARCHAR(20) NOT NULL,
    description TEXT,
    entity_types JSONB NOT NULL DEFAULT '[]',
    relationship_types JSONB NOT NULL DEFAULT '[]',
    depends_on TEXT[] DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for entities
CREATE INDEX idx_entities_tenant ON intelligence.entities(tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_type ON intelligence.entities(entity_type) WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_domain ON intelligence.entities(domain) WHERE deleted_at IS NULL;
CREATE INDEX idx_entities_name ON intelligence.entities(name) WHERE deleted_at IS NULL;

-- Indexes for relationships
CREATE INDEX idx_relationships_tenant ON intelligence.relationships(tenant_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_relationships_from ON intelligence.relationships(from_entity_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_relationships_to ON intelligence.relationships(to_entity_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_relationships_type ON intelligence.relationships(relationship_type) WHERE deleted_at IS NULL;

-- Indexes for patterns
CREATE INDEX idx_patterns_domain ON intelligence.patterns(domain) WHERE is_active = TRUE;
CREATE INDEX idx_patterns_category ON intelligence.patterns(category) WHERE is_active = TRUE;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA intelligence TO test;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA intelligence TO test;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA intelligence TO test;

-- ---------------------------------------------------------------------------
-- Legacy Smart-Scaffold tables (empty stubs so Alembic DROP TABLE succeeds)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS cg_entity_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS cg_entities (
    id SERIAL PRIMARY KEY,
    type_id INTEGER REFERENCES cg_entity_types(id),
    data JSONB DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS cg_relationship_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS cg_relationships (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES cg_entities(id),
    target_id INTEGER REFERENCES cg_entities(id),
    type_id INTEGER REFERENCES cg_relationship_types(id)
);

CREATE TABLE IF NOT EXISTS cg_chunks (
    id SERIAL PRIMARY KEY,
    content TEXT
);

CREATE TABLE IF NOT EXISTS cg_entity_chunks (
    id SERIAL PRIMARY KEY,
    entity_id INTEGER REFERENCES cg_entities(id),
    chunk_id INTEGER REFERENCES cg_chunks(id)
);

CREATE TABLE IF NOT EXISTS cg_documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS cg_document_sources (
    id SERIAL PRIMARY KEY,
    organization_id INTEGER REFERENCES organizations(id),
    url TEXT
);
