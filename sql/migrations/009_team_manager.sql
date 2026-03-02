-- 009_team_manager.sql
-- Team Manager graph model: graphs, nodes, edges, layouts, variables, and pipelines.
-- Implements the BOMBA SR adaptation of ATM v0.7.2 concepts.
-- All tables use SQLite-native types and TEXT primary keys (UUIDs).
-- Multi-tenant isolation via tenant_id on every table.

-- team_graphs: top-level graph container
CREATE TABLE IF NOT EXISTS team_graphs (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- team_nodes: nodes within a graph
CREATE TABLE IF NOT EXISTS team_nodes (
    id TEXT PRIMARY KEY,
    graph_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('human','group','agent','skill','pipeline','context','note')),
    label TEXT NOT NULL DEFAULT '',
    config_json TEXT DEFAULT '{}',
    position_x REAL DEFAULT 0.0,
    position_y REAL DEFAULT 0.0,
    width REAL DEFAULT 200.0,
    height REAL DEFAULT 100.0,
    parent_node_id TEXT DEFAULT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (graph_id) REFERENCES team_graphs(id) ON DELETE CASCADE
);

-- team_edges: connections between nodes
CREATE TABLE IF NOT EXISTS team_edges (
    id TEXT PRIMARY KEY,
    graph_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    source_node_id TEXT NOT NULL,
    target_node_id TEXT NOT NULL,
    edge_type TEXT NOT NULL DEFAULT 'dependency',
    label TEXT DEFAULT '',
    metadata_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (graph_id) REFERENCES team_graphs(id) ON DELETE CASCADE,
    FOREIGN KEY (source_node_id) REFERENCES team_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_node_id) REFERENCES team_nodes(id) ON DELETE CASCADE
);

-- team_layouts: saved layout positions
CREATE TABLE IF NOT EXISTS team_layouts (
    id TEXT PRIMARY KEY,
    graph_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'default',
    layout_json TEXT DEFAULT '{}',
    is_default INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (graph_id) REFERENCES team_graphs(id) ON DELETE CASCADE
);

-- team_variables: graph-scoped variables
CREATE TABLE IF NOT EXISTS team_variables (
    id TEXT PRIMARY KEY,
    graph_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT DEFAULT '',
    var_type TEXT NOT NULL DEFAULT 'string' CHECK(var_type IN ('string','number','boolean','json','secret')),
    description TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (graph_id) REFERENCES team_graphs(id) ON DELETE CASCADE,
    UNIQUE(graph_id, key)
);

-- team_pipelines: ordered step sequences attached to pipeline nodes
CREATE TABLE IF NOT EXISTS team_pipelines (
    id TEXT PRIMARY KEY,
    graph_id TEXT NOT NULL,
    tenant_id TEXT NOT NULL,
    node_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    steps_json TEXT DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (graph_id) REFERENCES team_graphs(id) ON DELETE CASCADE,
    FOREIGN KEY (node_id) REFERENCES team_nodes(id) ON DELETE CASCADE
);

-- Indexes: tenant-scoped queries and foreign key lookups

CREATE INDEX IF NOT EXISTS idx_team_graphs_tenant ON team_graphs(tenant_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_team_nodes_graph ON team_nodes(graph_id, tenant_id);
CREATE INDEX IF NOT EXISTS idx_team_nodes_kind ON team_nodes(tenant_id, kind);
CREATE INDEX IF NOT EXISTS idx_team_edges_graph ON team_edges(graph_id, tenant_id);
CREATE INDEX IF NOT EXISTS idx_team_edges_source ON team_edges(source_node_id);
CREATE INDEX IF NOT EXISTS idx_team_edges_target ON team_edges(target_node_id);
CREATE INDEX IF NOT EXISTS idx_team_layouts_graph ON team_layouts(graph_id, tenant_id);
CREATE INDEX IF NOT EXISTS idx_team_variables_graph ON team_variables(graph_id, tenant_id);
CREATE INDEX IF NOT EXISTS idx_team_pipelines_graph ON team_pipelines(graph_id, tenant_id);
CREATE INDEX IF NOT EXISTS idx_team_pipelines_node ON team_pipelines(node_id);
