-- Life Archivist Database Schema
-- PostgreSQL 16+
-- 
-- This schema supports production-grade conversation management with:
-- - Conversation history and context
-- - Message threading and branching
-- - Citation tracking
-- - File attachments
-- - Multi-user support (future)
-- - Full-text search
-- - Performance optimizations

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- ============================================================================
-- CONVERSATIONS
-- ============================================================================

CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User/ownership (for future multi-user support)
    user_id VARCHAR(255) NOT NULL DEFAULT 'default',
    
    -- Conversation metadata
    title VARCHAR(500),  -- Auto-generated from first message
    model VARCHAR(100) NOT NULL,  -- llama3.2, gpt-4, etc.
    provider_id VARCHAR(255),  -- LLM provider ID (e.g., "my-openai"). NULL = use default
    
    -- Context management
    context_documents TEXT[] DEFAULT '{}',  -- Array of document IDs
    system_prompt TEXT,  -- Custom system prompt for this conversation
    
    -- Settings
    temperature FLOAT DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 2000,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,  -- For sorting by activity
    archived_at TIMESTAMPTZ,  -- Soft delete
    
    -- Extensible metadata (for future features)
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT valid_temperature CHECK (temperature >= 0 AND temperature <= 2),
    CONSTRAINT valid_max_tokens CHECK (max_tokens > 0 AND max_tokens <= 100000)
);

-- Indexes for conversations
CREATE INDEX idx_conversations_user_id ON conversations(user_id) WHERE archived_at IS NULL;
CREATE INDEX idx_conversations_updated_at ON conversations(updated_at DESC) WHERE archived_at IS NULL;
CREATE INDEX idx_conversations_last_message_at ON conversations(last_message_at DESC NULLS LAST) WHERE archived_at IS NULL;
CREATE INDEX idx_conversations_archived ON conversations(archived_at) WHERE archived_at IS NOT NULL;
CREATE INDEX idx_conversations_provider_id ON conversations(provider_id) WHERE provider_id IS NOT NULL;
CREATE INDEX idx_conversations_title_trgm ON conversations USING gin(title gin_trgm_ops);  -- Fuzzy search

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_conversations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_conversations_updated_at();

-- ============================================================================
-- MESSAGES
-- ============================================================================

CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Threading/branching support
    parent_message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
    sequence_number INTEGER NOT NULL,  -- Order within conversation
    
    -- Message content
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    
    -- AI-specific metadata (for assistant messages)
    model VARCHAR(100),  -- Can switch models mid-conversation
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    method VARCHAR(50),  -- 'rag', 'direct', 'hybrid', 'agent'
    
    -- Performance tracking
    tokens_used INTEGER,  -- For cost tracking
    latency_ms INTEGER,  -- Response time
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    edited_at TIMESTAMPTZ,  -- If user edits their question
    
    -- Extensible metadata
    metadata JSONB DEFAULT '{}',
    
    -- Constraints
    CONSTRAINT valid_role CHECK (role IN ('user', 'assistant', 'system')),
    CONSTRAINT valid_sequence CHECK (sequence_number >= 0)
);

-- Indexes for messages
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id, sequence_number);
CREATE INDEX idx_messages_created_at ON messages(created_at DESC);
CREATE INDEX idx_messages_parent_id ON messages(parent_message_id) WHERE parent_message_id IS NOT NULL;
CREATE INDEX idx_messages_role ON messages(role);
CREATE INDEX idx_messages_content_trgm ON messages USING gin(content gin_trgm_ops);  -- Full-text search

-- Trigger to update conversation's last_message_at
CREATE OR REPLACE FUNCTION update_conversation_last_message()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE conversations 
    SET last_message_at = NEW.created_at
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER messages_update_conversation
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_last_message();

-- ============================================================================
-- MESSAGE CITATIONS
-- ============================================================================

CREATE TABLE message_citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    
    -- Document reference
    document_id VARCHAR(255) NOT NULL,  -- Your document ID from vault
    chunk_id VARCHAR(255),  -- Specific chunk if available
    
    -- Citation metadata
    score FLOAT,  -- Relevance score (0-1)
    snippet TEXT,  -- Text snippet shown to user
    position INTEGER,  -- Order in citation list
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_score CHECK (score IS NULL OR (score >= 0 AND score <= 1)),
    CONSTRAINT valid_position CHECK (position >= 0)
);

-- Indexes for citations
CREATE INDEX idx_citations_message_id ON message_citations(message_id);
CREATE INDEX idx_citations_document_id ON message_citations(document_id);
CREATE INDEX idx_citations_score ON message_citations(score DESC NULLS LAST);

-- ============================================================================
-- MESSAGE ATTACHMENTS
-- ============================================================================

CREATE TABLE message_attachments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
    
    -- Document reference
    document_id VARCHAR(255) NOT NULL,  -- Reference to your vault
    
    -- Attachment metadata
    attachment_type VARCHAR(50) NOT NULL CHECK (attachment_type IN ('context', 'reference', 'upload')),
    display_name VARCHAR(500),  -- User-friendly name
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT valid_attachment_type CHECK (attachment_type IN ('context', 'reference', 'upload'))
);

-- Indexes for attachments
CREATE INDEX idx_attachments_message_id ON message_attachments(message_id);
CREATE INDEX idx_attachments_document_id ON message_attachments(document_id);
CREATE INDEX idx_attachments_type ON message_attachments(attachment_type);

-- ============================================================================
-- CONVERSATION PARTICIPANTS (for future collaboration)
-- ============================================================================

CREATE TABLE conversation_participants (
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    user_id VARCHAR(255) NOT NULL,
    
    -- Role-based access
    role VARCHAR(20) NOT NULL CHECK (role IN ('owner', 'editor', 'viewer')),
    
    -- Timestamps
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_viewed_at TIMESTAMPTZ,
    
    -- Primary key
    PRIMARY KEY (conversation_id, user_id),
    
    -- Constraints
    CONSTRAINT valid_participant_role CHECK (role IN ('owner', 'editor', 'viewer'))
);

-- Indexes for participants
CREATE INDEX idx_participants_user_id ON conversation_participants(user_id);
CREATE INDEX idx_participants_role ON conversation_participants(role);

-- ============================================================================
-- CONVERSATION TAGS (for organization)
-- ============================================================================

CREATE TABLE conversation_tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Tag information
    tag_name VARCHAR(100) NOT NULL,
    tag_color VARCHAR(7),  -- Hex color code
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_conversation_tag UNIQUE (conversation_id, tag_name)
);

-- Indexes for tags
CREATE INDEX idx_tags_conversation_id ON conversation_tags(conversation_id);
CREATE INDEX idx_tags_name ON conversation_tags(tag_name);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: Active conversations with message counts
CREATE VIEW active_conversations AS
SELECT 
    c.id,
    c.user_id,
    c.title,
    c.model,
    c.created_at,
    c.updated_at,
    c.last_message_at,
    COUNT(m.id) as message_count,
    MAX(m.created_at) as last_message_time
FROM conversations c
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE c.archived_at IS NULL
GROUP BY c.id;

-- View: Conversation summaries with first/last messages
CREATE VIEW conversation_summaries AS
SELECT 
    c.id,
    c.user_id,
    c.title,
    c.model,
    c.created_at,
    c.last_message_at,
    first_msg.content as first_message,
    last_msg.content as last_message,
    COUNT(m.id) as message_count
FROM conversations c
LEFT JOIN LATERAL (
    SELECT content 
    FROM messages 
    WHERE conversation_id = c.id 
    ORDER BY sequence_number ASC 
    LIMIT 1
) first_msg ON true
LEFT JOIN LATERAL (
    SELECT content 
    FROM messages 
    WHERE conversation_id = c.id 
    ORDER BY sequence_number DESC 
    LIMIT 1
) last_msg ON true
LEFT JOIN messages m ON c.id = m.conversation_id
WHERE c.archived_at IS NULL
GROUP BY c.id, first_msg.content, last_msg.content;

-- ============================================================================
-- FUNCTIONS FOR COMMON OPERATIONS
-- ============================================================================

-- Function: Get conversation with messages
CREATE OR REPLACE FUNCTION get_conversation_with_messages(
    p_conversation_id UUID,
    p_limit INTEGER DEFAULT 50,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    conversation_id UUID,
    conversation_title VARCHAR,
    message_id UUID,
    message_role VARCHAR,
    message_content TEXT,
    message_created_at TIMESTAMPTZ,
    message_sequence INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        c.id,
        c.title,
        m.id,
        m.role,
        m.content,
        m.created_at,
        m.sequence_number
    FROM conversations c
    LEFT JOIN messages m ON c.id = m.conversation_id
    WHERE c.id = p_conversation_id
    ORDER BY m.sequence_number ASC
    LIMIT p_limit
    OFFSET p_offset;
END;
$$ LANGUAGE plpgsql;

-- Function: Search conversations by content
CREATE OR REPLACE FUNCTION search_conversations(
    p_user_id VARCHAR,
    p_query TEXT,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
    conversation_id UUID,
    title VARCHAR,
    relevance FLOAT,
    last_message_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT DISTINCT
        c.id,
        c.title,
        similarity(c.title, p_query) + 
        MAX(similarity(m.content, p_query)) as relevance,
        c.last_message_at
    FROM conversations c
    LEFT JOIN messages m ON c.id = m.conversation_id
    WHERE c.user_id = p_user_id
      AND c.archived_at IS NULL
      AND (
          c.title % p_query OR
          m.content % p_query
      )
    GROUP BY c.id
    ORDER BY relevance DESC, c.last_message_at DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Create default user (for single-user mode)
-- This will be used until multi-user support is added
INSERT INTO conversations (id, user_id, title, model, metadata)
VALUES (
    '00000000-0000-0000-0000-000000000000',
    'default',
    'System Initialization',
    'system',
    '{"system": true, "hidden": true}'::jsonb
) ON CONFLICT DO NOTHING;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE conversations IS 'Stores conversation metadata and settings';
COMMENT ON TABLE messages IS 'Stores individual messages within conversations';
COMMENT ON TABLE message_citations IS 'Tracks which documents were cited in responses';
COMMENT ON TABLE message_attachments IS 'Tracks files attached to messages';
COMMENT ON TABLE conversation_participants IS 'Manages multi-user access to conversations';
COMMENT ON TABLE conversation_tags IS 'Organizes conversations with tags';

COMMENT ON COLUMN conversations.context_documents IS 'Array of document IDs to include in conversation context';
COMMENT ON COLUMN messages.sequence_number IS 'Order of message within conversation (0-indexed)';
COMMENT ON COLUMN messages.parent_message_id IS 'Enables conversation branching (tree structure)';
COMMENT ON COLUMN message_citations.score IS 'Relevance score from vector search (0-1)';
COMMENT ON COLUMN message_attachments.attachment_type IS 'context: auto-included, reference: user-attached, upload: new file';
