
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Companies & Workspaces
CREATE TABLE IF NOT EXISTS companies (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    name VARCHAR(255) NOT NULL,
    markets JSONB NOT NULL DEFAULT '["KSA", "EG"]',
    currency_primary VARCHAR(10) DEFAULT 'SAR',
    currency_secondary VARCHAR(10) DEFAULT 'EGP',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Users & Roles (RBAC)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    company_id VARCHAR(64) REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('super_admin', 'marketing_lead', 'compliance_officer', 'finance_approver', 'viewer')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Ramadan Campaign Strategy & Problems
CREATE TABLE IF NOT EXISTS campaigns (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    company_id VARCHAR(64) REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    phase VARCHAR(100) NOT NULL, -- 'Pre-Ramadan Launch', 'Week 1 Iftar Essentials', 'Laylat Al-Qadr Giving', 'Eid Countdown'
    budget_total_sar NUMERIC(14, 2) NOT NULL,
    budget_total_egp NUMERIC(14, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('draft', 'pending_approval', 'active', 'paused', 'completed')),
    kpi_targets JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Atomic Tasks & Problems Assigned to Agents
CREATE TABLE IF NOT EXISTS campaign_tasks (
    id VARCHAR(64) PRIMARY KEY, -- e.g. 'TASK-CONTENT-KSA-001'
    campaign_id VARCHAR(64) REFERENCES campaigns(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL CHECK (category IN ('orchestration', 'tool_use', 'safety', 'hitl', 'memory', 'observability', 'multimodal')),
    assigned_agent VARCHAR(100) NOT NULL, -- e.g. 'ContentArchitect', 'ChannelDeployer'
    title VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    expected_outcome JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'blocked_hitl')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Agent Execution Runs
CREATE TABLE IF NOT EXISTS agent_runs (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    task_id VARCHAR(64) REFERENCES campaign_tasks(id) ON DELETE CASCADE,
    framework_name VARCHAR(100) NOT NULL, -- 'langgraph', 'crewai', 'autogen', 'native', etc.
    model_name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('running', 'success', 'failed', 'timeout')),
    duration_ms NUMERIC(10, 2) DEFAULT 0,
    prompt_tokens INT DEFAULT 0,
    completion_tokens INT DEFAULT 0,
    cost_usd NUMERIC(10, 6) DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE
);

-- 6. Agent Messages & Event Stream (Execution Trajectory)
CREATE TABLE IF NOT EXISTS agent_messages (
    id BIGSERIAL PRIMARY KEY,
    run_id VARCHAR(64) REFERENCES agent_runs(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    message_type VARCHAR(50) NOT NULL CHECK (message_type IN ('thought', 'tool_call', 'tool_response', 'agent_message', 'decision', 'delegation')),
    content TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. Product Catalog (Real E-Commerce Items)
CREATE TABLE IF NOT EXISTS products (
    sku VARCHAR(64) PRIMARY KEY,
    name_en VARCHAR(255) NOT NULL,
    name_ar VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    regular_price_sar NUMERIC(10, 2),
    ramadan_price_sar NUMERIC(10, 2),
    regular_price_egp NUMERIC(10, 2),
    ramadan_price_egp NUMERIC(10, 2),
    discount_percent INT DEFAULT 0,
    colors JSONB DEFAULT '[]',
    branches_ksa JSONB DEFAULT '[]',
    branches_eg JSONB DEFAULT '[]',
    description_en TEXT,
    description_ar TEXT
);

-- 8. Customer Master & Consent (Saudi PDPL & Egypt Law 151)
CREATE TABLE IF NOT EXISTS customers (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    national_id VARCHAR(64),
    phone VARCHAR(64),
    email VARCHAR(255),
    market VARCHAR(10) NOT NULL CHECK (market IN ('KSA', 'EG')),
    consent_status VARCHAR(50) NOT NULL CHECK (consent_status IN ('opted_in', 'opted_out', 'unsubscribed')),
    consent_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 9. Immutable Compliance Audit Ledger
CREATE TABLE IF NOT EXISTS consent_audit_log (
    id VARCHAR(64) PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    customer_id VARCHAR(64) NOT NULL,
    action VARCHAR(100) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    jurisdiction VARCHAR(50) NOT NULL,
    details TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 10. Human-In-The-Loop Approval Gates
CREATE TABLE IF NOT EXISTS approval_gates (
    gate_id VARCHAR(64) PRIMARY KEY,
    task_id VARCHAR(64) REFERENCES campaign_tasks(id) ON DELETE CASCADE,
    gate_type VARCHAR(100) NOT NULL,
    action_description TEXT NOT NULL,
    shift_amount NUMERIC(14, 2),
    shift_ratio NUMERIC(5, 4),
    required_role VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'auto_approved')),
    context JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(255)
);

-- Indexes for high-performance querying
CREATE INDEX IF NOT EXISTS idx_agent_messages_run_id ON agent_messages(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_task_id ON agent_runs(task_id);
CREATE INDEX IF NOT EXISTS idx_campaign_tasks_campaign_id ON campaign_tasks(campaign_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_customers_market ON customers(market);
CREATE INDEX IF NOT EXISTS idx_customers_consent ON customers(consent_status);
CREATE INDEX IF NOT EXISTS idx_audit_customer ON consent_audit_log(customer_id);
