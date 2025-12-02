-- Cloud Optimizer Database Initialization Script
-- Creates database and sets up initial configuration

-- Ensure UTF8 encoding
SET client_encoding = 'UTF8';

-- Create extensions if they don't exist
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set search path
SET search_path TO public;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Cloud Optimizer database initialized successfully';
END $$;
