"""Team Manager Service -- graph-based team topology management.

Implements CRUD for graphs, nodes, edges, layouts, variables, and pipelines.
Provides validation (cycle detection, edge-kind constraints) and deploy plan
generation for agent orchestration.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

from bomba_sr.storage.db import RuntimeDB, dict_from_row


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_NODE_KINDS = {"human", "group", "agent", "skill", "pipeline", "context", "note"}
VALID_EDGE_TYPES = {"reports_to", "delegates_to", "feeds", "uses", "triggers", "annotates"}

# Edge types that must be acyclic (hierarchical relationships).
CYCLE_EDGE_TYPES = {"reports_to", "delegates_to"}

# Constraints: which source-kind -> target-kind pairs are valid per edge type.
# None value means "any kind is allowed".
EDGE_KIND_CONSTRAINTS: dict[str, list[tuple[set[str], set[str]]] | None] = {
    "reports_to": [
        ({"human", "agent", "group"}, {"human", "group"}),
    ],
    "delegates_to": [
        ({"human", "agent", "group"}, {"agent", "skill", "pipeline"}),
    ],
    "feeds": None,  # any -> any
    "uses": [
        ({"agent", "pipeline"}, {"skill", "context"}),
    ],
    "triggers": [
        ({"agent", "skill", "pipeline"}, {"agent", "skill", "pipeline"}),
    ],
    "annotates": [
        ({"note"}, VALID_NODE_KINDS),
    ],
}


class TeamManagerService:
    """Service layer for team graph management.

    Receives only ``RuntimeDB`` as dependency.  All public methods include
    ``tenant_id`` as the first parameter for multi-tenant isolation.
    """

    def __init__(self, db: RuntimeDB) -> None:
        self.db = db
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------

    def _ensure_schema(self) -> None:
        self.db.script(
            """
            CREATE TABLE IF NOT EXISTS team_graphs (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL DEFAULT '',
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS team_nodes (
                id TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                label TEXT NOT NULL DEFAULT '',
                config_json TEXT DEFAULT '{}',
                position_x REAL DEFAULT 0.0,
                position_y REAL DEFAULT 0.0,
                width REAL DEFAULT 200.0,
                height REAL DEFAULT 100.0,
                parent_node_id TEXT DEFAULT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (graph_id) REFERENCES team_graphs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS team_edges (
                id TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                source_node_id TEXT NOT NULL,
                target_node_id TEXT NOT NULL,
                edge_type TEXT NOT NULL DEFAULT 'dependency',
                label TEXT DEFAULT '',
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                FOREIGN KEY (graph_id) REFERENCES team_graphs(id) ON DELETE CASCADE,
                FOREIGN KEY (source_node_id) REFERENCES team_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (target_node_id) REFERENCES team_nodes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS team_layouts (
                id TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT 'default',
                layout_json TEXT DEFAULT '{}',
                is_default INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (graph_id) REFERENCES team_graphs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS team_variables (
                id TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT DEFAULT '',
                var_type TEXT NOT NULL DEFAULT 'string',
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (graph_id) REFERENCES team_graphs(id) ON DELETE CASCADE,
                UNIQUE(graph_id, key)
            );

            CREATE TABLE IF NOT EXISTS team_pipelines (
                id TEXT PRIMARY KEY,
                graph_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                steps_json TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (graph_id) REFERENCES team_graphs(id) ON DELETE CASCADE,
                FOREIGN KEY (node_id) REFERENCES team_nodes(id) ON DELETE CASCADE
            );

            -- Indexes
            CREATE INDEX IF NOT EXISTS idx_team_graphs_tenant
                ON team_graphs(tenant_id, updated_at);
            CREATE INDEX IF NOT EXISTS idx_team_nodes_graph
                ON team_nodes(graph_id, tenant_id);
            CREATE INDEX IF NOT EXISTS idx_team_nodes_kind
                ON team_nodes(tenant_id, kind);
            CREATE INDEX IF NOT EXISTS idx_team_edges_graph
                ON team_edges(graph_id, tenant_id);
            CREATE INDEX IF NOT EXISTS idx_team_edges_source
                ON team_edges(source_node_id);
            CREATE INDEX IF NOT EXISTS idx_team_edges_target
                ON team_edges(target_node_id);
            CREATE INDEX IF NOT EXISTS idx_team_layouts_graph
                ON team_layouts(graph_id, tenant_id);
            CREATE INDEX IF NOT EXISTS idx_team_variables_graph
                ON team_variables(graph_id, tenant_id);
            CREATE INDEX IF NOT EXISTS idx_team_pipelines_graph
                ON team_pipelines(graph_id, tenant_id);
            CREATE INDEX IF NOT EXISTS idx_team_pipelines_node
                ON team_pipelines(node_id);
            """
        )
        self.db.commit()

    # ==================================================================
    # Graph CRUD
    # ==================================================================

    def create_graph(
        self,
        tenant_id: str,
        workspace_id: str,
        name: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        now = self._now()
        graph_id = self._uuid()
        self.db.execute(
            """
            INSERT INTO team_graphs (id, tenant_id, workspace_id, name, description, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                graph_id,
                tenant_id,
                workspace_id,
                name,
                description,
                json.dumps(metadata or {}),
                now,
                now,
            ),
        )
        self.db.commit()
        return self.get_graph(tenant_id, graph_id)  # type: ignore[return-value]

    def get_graph(self, tenant_id: str, graph_id: str) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM team_graphs WHERE tenant_id = ? AND id = ?",
            (tenant_id, graph_id),
        ).fetchone()
        if row is None:
            return None
        return self._graph_row(row)

    def list_graphs(self, tenant_id: str, workspace_id: str | None = None) -> list[dict]:
        if workspace_id is not None:
            rows = self.db.execute(
                "SELECT * FROM team_graphs WHERE tenant_id = ? AND workspace_id = ? ORDER BY updated_at DESC",
                (tenant_id, workspace_id),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM team_graphs WHERE tenant_id = ? ORDER BY updated_at DESC",
                (tenant_id,),
            ).fetchall()
        return [self._graph_row(r) for r in rows]

    def update_graph(
        self,
        tenant_id: str,
        graph_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        existing = self.get_graph(tenant_id, graph_id)
        if existing is None:
            raise ValueError(f"graph not found: {graph_id}")

        new_name = name if name is not None else existing["name"]
        new_desc = description if description is not None else existing["description"]
        new_meta = metadata if metadata is not None else existing["metadata"]

        self.db.execute(
            """
            UPDATE team_graphs
            SET name = ?, description = ?, metadata_json = ?, updated_at = ?
            WHERE tenant_id = ? AND id = ?
            """,
            (
                new_name,
                new_desc,
                json.dumps(new_meta),
                self._now(),
                tenant_id,
                graph_id,
            ),
        )
        self.db.commit()
        return self.get_graph(tenant_id, graph_id)  # type: ignore[return-value]

    def delete_graph(self, tenant_id: str, graph_id: str) -> dict:
        existing = self.get_graph(tenant_id, graph_id)
        if existing is None:
            return {"deleted": False}
        self.db.execute(
            "DELETE FROM team_graphs WHERE tenant_id = ? AND id = ?",
            (tenant_id, graph_id),
        )
        self.db.commit()
        return {"deleted": True}

    # ==================================================================
    # Node CRUD
    # ==================================================================

    def add_node(
        self,
        tenant_id: str,
        graph_id: str,
        kind: str,
        label: str,
        config: dict[str, Any] | None = None,
        position_x: float = 0.0,
        position_y: float = 0.0,
    ) -> dict:
        if kind not in VALID_NODE_KINDS:
            raise ValueError(f"invalid node kind: {kind!r} (valid: {sorted(VALID_NODE_KINDS)})")

        # Ensure graph exists for this tenant.
        if self.get_graph(tenant_id, graph_id) is None:
            raise ValueError(f"graph not found: {graph_id}")

        now = self._now()
        node_id = self._uuid()
        self.db.execute(
            """
            INSERT INTO team_nodes
                (id, graph_id, tenant_id, kind, label, config_json, position_x, position_y, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                node_id,
                graph_id,
                tenant_id,
                kind,
                label,
                json.dumps(config or {}),
                position_x,
                position_y,
                now,
                now,
            ),
        )
        self.db.commit()
        return self.get_node(tenant_id, node_id)  # type: ignore[return-value]

    def get_node(self, tenant_id: str, node_id: str) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM team_nodes WHERE tenant_id = ? AND id = ?",
            (tenant_id, node_id),
        ).fetchone()
        if row is None:
            return None
        return self._node_row(row)

    def list_nodes(self, tenant_id: str, graph_id: str, kind: str | None = None) -> list[dict]:
        if kind is not None:
            rows = self.db.execute(
                "SELECT * FROM team_nodes WHERE tenant_id = ? AND graph_id = ? AND kind = ? ORDER BY created_at",
                (tenant_id, graph_id, kind),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM team_nodes WHERE tenant_id = ? AND graph_id = ? ORDER BY created_at",
                (tenant_id, graph_id),
            ).fetchall()
        return [self._node_row(r) for r in rows]

    def update_node(
        self,
        tenant_id: str,
        node_id: str,
        *,
        label: str | None = None,
        config: dict[str, Any] | None = None,
        position_x: float | None = None,
        position_y: float | None = None,
    ) -> dict:
        existing = self.get_node(tenant_id, node_id)
        if existing is None:
            raise ValueError(f"node not found: {node_id}")

        new_label = label if label is not None else existing["label"]
        new_config = config if config is not None else existing["config"]
        new_x = position_x if position_x is not None else existing["position_x"]
        new_y = position_y if position_y is not None else existing["position_y"]

        self.db.execute(
            """
            UPDATE team_nodes
            SET label = ?, config_json = ?, position_x = ?, position_y = ?, updated_at = ?
            WHERE tenant_id = ? AND id = ?
            """,
            (
                new_label,
                json.dumps(new_config),
                new_x,
                new_y,
                self._now(),
                tenant_id,
                node_id,
            ),
        )
        self.db.commit()
        return self.get_node(tenant_id, node_id)  # type: ignore[return-value]

    def delete_node(self, tenant_id: str, node_id: str) -> dict:
        existing = self.get_node(tenant_id, node_id)
        if existing is None:
            return {"deleted": False}
        self.db.execute(
            "DELETE FROM team_nodes WHERE tenant_id = ? AND id = ?",
            (tenant_id, node_id),
        )
        self.db.commit()
        return {"deleted": True}

    # ==================================================================
    # Edge CRUD
    # ==================================================================

    def add_edge(
        self,
        tenant_id: str,
        graph_id: str,
        source_node_id: str,
        target_node_id: str,
        edge_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        if edge_type not in VALID_EDGE_TYPES:
            raise ValueError(f"invalid edge_type: {edge_type!r} (valid: {sorted(VALID_EDGE_TYPES)})")

        if source_node_id == target_node_id:
            raise ValueError("self-loops are not allowed")

        # Verify both nodes exist in the same graph.
        source = self.get_node(tenant_id, source_node_id)
        target = self.get_node(tenant_id, target_node_id)
        if source is None:
            raise ValueError(f"source node not found: {source_node_id}")
        if target is None:
            raise ValueError(f"target node not found: {target_node_id}")
        if source["graph_id"] != graph_id:
            raise ValueError(f"source node {source_node_id} does not belong to graph {graph_id}")
        if target["graph_id"] != graph_id:
            raise ValueError(f"target node {target_node_id} does not belong to graph {graph_id}")

        now = self._now()
        edge_id = self._uuid()
        self.db.execute(
            """
            INSERT INTO team_edges
                (id, graph_id, tenant_id, source_node_id, target_node_id, edge_type, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge_id,
                graph_id,
                tenant_id,
                source_node_id,
                target_node_id,
                edge_type,
                json.dumps(metadata or {}),
                now,
            ),
        )
        self.db.commit()
        return self._edge_row(
            self.db.execute(
                "SELECT * FROM team_edges WHERE tenant_id = ? AND id = ?",
                (tenant_id, edge_id),
            ).fetchone()
        )

    def list_edges(self, tenant_id: str, graph_id: str, edge_type: str | None = None) -> list[dict]:
        if edge_type is not None:
            rows = self.db.execute(
                "SELECT * FROM team_edges WHERE tenant_id = ? AND graph_id = ? AND edge_type = ? ORDER BY created_at",
                (tenant_id, graph_id, edge_type),
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM team_edges WHERE tenant_id = ? AND graph_id = ? ORDER BY created_at",
                (tenant_id, graph_id),
            ).fetchall()
        return [self._edge_row(r) for r in rows]

    def delete_edge(self, tenant_id: str, edge_id: str) -> dict:
        row = self.db.execute(
            "SELECT id FROM team_edges WHERE tenant_id = ? AND id = ?",
            (tenant_id, edge_id),
        ).fetchone()
        if row is None:
            return {"deleted": False}
        self.db.execute(
            "DELETE FROM team_edges WHERE tenant_id = ? AND id = ?",
            (tenant_id, edge_id),
        )
        self.db.commit()
        return {"deleted": True}

    # ==================================================================
    # Layout CRUD
    # ==================================================================

    def save_layout(
        self,
        tenant_id: str,
        graph_id: str,
        layout: dict[str, Any],
        is_default: bool = False,
    ) -> dict:
        if self.get_graph(tenant_id, graph_id) is None:
            raise ValueError(f"graph not found: {graph_id}")

        now = self._now()
        layout_id = self._uuid()

        # If marking as default, clear existing defaults for this graph.
        if is_default:
            self.db.execute(
                "UPDATE team_layouts SET is_default = 0 WHERE tenant_id = ? AND graph_id = ?",
                (tenant_id, graph_id),
            )

        self.db.execute(
            """
            INSERT INTO team_layouts (id, graph_id, tenant_id, name, layout_json, is_default, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                layout_id,
                graph_id,
                tenant_id,
                "default" if is_default else "custom",
                json.dumps(layout),
                1 if is_default else 0,
                now,
            ),
        )
        self.db.commit()
        return self._layout_row(
            self.db.execute(
                "SELECT * FROM team_layouts WHERE tenant_id = ? AND id = ?",
                (tenant_id, layout_id),
            ).fetchone()
        )

    def get_default_layout(self, tenant_id: str, graph_id: str) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM team_layouts WHERE tenant_id = ? AND graph_id = ? AND is_default = 1 ORDER BY created_at DESC LIMIT 1",
            (tenant_id, graph_id),
        ).fetchone()
        if row is None:
            return None
        return self._layout_row(row)

    def list_layouts(self, tenant_id: str, graph_id: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM team_layouts WHERE tenant_id = ? AND graph_id = ? ORDER BY created_at DESC",
            (tenant_id, graph_id),
        ).fetchall()
        return [self._layout_row(r) for r in rows]

    # ==================================================================
    # Variable CRUD
    # ==================================================================

    def set_variable(
        self,
        tenant_id: str,
        graph_id: str,
        key: str,
        value: str,
        var_type: str = "string",
    ) -> dict:
        if self.get_graph(tenant_id, graph_id) is None:
            raise ValueError(f"graph not found: {graph_id}")

        now = self._now()
        # Upsert: try update first, insert if not found.
        existing = self.db.execute(
            "SELECT id FROM team_variables WHERE tenant_id = ? AND graph_id = ? AND key = ?",
            (tenant_id, graph_id, key),
        ).fetchone()

        if existing is not None:
            self.db.execute(
                """
                UPDATE team_variables
                SET value = ?, var_type = ?, updated_at = ?
                WHERE tenant_id = ? AND graph_id = ? AND key = ?
                """,
                (value, var_type, now, tenant_id, graph_id, key),
            )
        else:
            var_id = self._uuid()
            self.db.execute(
                """
                INSERT INTO team_variables (id, graph_id, tenant_id, key, value, var_type, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (var_id, graph_id, tenant_id, key, value, var_type, "", now, now),
            )
        self.db.commit()

        row = self.db.execute(
            "SELECT * FROM team_variables WHERE tenant_id = ? AND graph_id = ? AND key = ?",
            (tenant_id, graph_id, key),
        ).fetchone()
        return self._variable_row(row)

    def list_variables(self, tenant_id: str, graph_id: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM team_variables WHERE tenant_id = ? AND graph_id = ? ORDER BY key",
            (tenant_id, graph_id),
        ).fetchall()
        return [self._variable_row(r) for r in rows]

    def delete_variable(self, tenant_id: str, graph_id: str, key: str) -> dict:
        row = self.db.execute(
            "SELECT id FROM team_variables WHERE tenant_id = ? AND graph_id = ? AND key = ?",
            (tenant_id, graph_id, key),
        ).fetchone()
        if row is None:
            return {"deleted": False}
        self.db.execute(
            "DELETE FROM team_variables WHERE tenant_id = ? AND graph_id = ? AND key = ?",
            (tenant_id, graph_id, key),
        )
        self.db.commit()
        return {"deleted": True}

    # ==================================================================
    # Pipeline CRUD
    # ==================================================================

    def save_pipeline(
        self,
        tenant_id: str,
        graph_id: str,
        node_id: str,
        steps: list[dict[str, Any]],
    ) -> dict:
        if self.get_graph(tenant_id, graph_id) is None:
            raise ValueError(f"graph not found: {graph_id}")

        node = self.get_node(tenant_id, node_id)
        if node is None:
            raise ValueError(f"node not found: {node_id}")

        now = self._now()
        # Upsert: update existing pipeline for this node, or insert new.
        existing = self.db.execute(
            "SELECT id FROM team_pipelines WHERE tenant_id = ? AND node_id = ?",
            (tenant_id, node_id),
        ).fetchone()

        if existing is not None:
            self.db.execute(
                """
                UPDATE team_pipelines
                SET steps_json = ?, updated_at = ?
                WHERE tenant_id = ? AND node_id = ?
                """,
                (json.dumps(steps), now, tenant_id, node_id),
            )
        else:
            pipeline_id = self._uuid()
            self.db.execute(
                """
                INSERT INTO team_pipelines (id, graph_id, tenant_id, node_id, name, steps_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (pipeline_id, graph_id, tenant_id, node_id, "", json.dumps(steps), now, now),
            )
        self.db.commit()
        return self.get_pipeline(tenant_id, node_id)  # type: ignore[return-value]

    def get_pipeline(self, tenant_id: str, node_id: str) -> dict | None:
        row = self.db.execute(
            "SELECT * FROM team_pipelines WHERE tenant_id = ? AND node_id = ?",
            (tenant_id, node_id),
        ).fetchone()
        if row is None:
            return None
        return self._pipeline_row(row)

    def list_pipelines(self, tenant_id: str, graph_id: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT * FROM team_pipelines WHERE tenant_id = ? AND graph_id = ? ORDER BY created_at",
            (tenant_id, graph_id),
        ).fetchall()
        return [self._pipeline_row(r) for r in rows]

    # ==================================================================
    # Validation
    # ==================================================================

    def validate_graph(self, tenant_id: str, graph_id: str) -> dict:
        """Validate a graph for structural integrity.

        Returns ``{"valid": bool, "errors": [...], "warnings": [...]}``.
        """
        errors: list[str] = []
        warnings: list[str] = []

        graph = self.get_graph(tenant_id, graph_id)
        if graph is None:
            return {"valid": False, "errors": ["graph not found"], "warnings": []}

        nodes = self.list_nodes(tenant_id, graph_id)
        edges = self.list_edges(tenant_id, graph_id)
        nodes_by_id = {n["id"]: n for n in nodes}

        if not nodes:
            warnings.append("graph has no nodes")

        # Required field checks.
        for node in nodes:
            if not node.get("label", "").strip():
                warnings.append(f"node {node['id']} has an empty label")

        # Cycle detection on hierarchical edges.
        cycle_errors = self._check_no_cycles(edges, CYCLE_EDGE_TYPES)
        errors.extend(cycle_errors)

        # Edge kind constraints.
        constraint_errors = self._check_edge_kind_constraints(nodes_by_id, edges)
        errors.extend(constraint_errors)

        # Dangling edge references (should not happen with FKs, but check anyway).
        for edge in edges:
            if edge["source_node_id"] not in nodes_by_id:
                errors.append(f"edge {edge['id']} references missing source node {edge['source_node_id']}")
            if edge["target_node_id"] not in nodes_by_id:
                errors.append(f"edge {edge['id']} references missing target node {edge['target_node_id']}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

    @staticmethod
    def _check_no_cycles(edges: list[dict], cycle_edge_types: set[str]) -> list[str]:
        """Iterative DFS cycle detection on edges of the given types.

        Returns a list of error strings (empty if acyclic).
        """
        errors: list[str] = []

        # Build adjacency list for relevant edges only.
        adj: dict[str, list[str]] = defaultdict(list)
        all_nodes: set[str] = set()
        for edge in edges:
            if edge["edge_type"] in cycle_edge_types:
                src = edge["source_node_id"]
                tgt = edge["target_node_id"]
                adj[src].append(tgt)
                all_nodes.add(src)
                all_nodes.add(tgt)

        if not all_nodes:
            return errors

        # Iterative DFS with three-color marking:
        #   0 = white (unvisited), 1 = gray (in current path), 2 = black (done)
        color: dict[str, int] = {n: 0 for n in all_nodes}

        for start in all_nodes:
            if color[start] != 0:
                continue

            # Stack entries: (node, iterator_index)
            stack: list[tuple[str, int]] = [(start, 0)]
            color[start] = 1  # gray

            while stack:
                node, idx = stack[-1]
                neighbors = adj.get(node, [])

                if idx < len(neighbors):
                    # Advance iterator for current node.
                    stack[-1] = (node, idx + 1)
                    neighbor = neighbors[idx]

                    if color[neighbor] == 1:
                        # Back edge detected -> cycle.
                        # Reconstruct cycle path from stack.
                        cycle_path = [n for n, _ in stack]
                        cycle_start_idx = next(
                            i for i, (n, _) in enumerate(stack) if n == neighbor
                        )
                        cycle_nodes = [n for n, _ in stack[cycle_start_idx:]] + [neighbor]
                        errors.append(
                            f"cycle detected in {'/'.join(sorted(cycle_edge_types))} edges: "
                            f"{' -> '.join(cycle_nodes)}"
                        )
                        # Continue DFS to find additional cycles.
                    elif color[neighbor] == 0:
                        color[neighbor] = 1
                        stack.append((neighbor, 0))
                else:
                    # Done with all neighbors of this node.
                    color[node] = 2  # black
                    stack.pop()

        return errors

    @staticmethod
    def _check_edge_kind_constraints(
        nodes_by_id: dict[str, dict],
        edges: list[dict],
    ) -> list[str]:
        """Validate that each edge connects valid source/target node kinds."""
        errors: list[str] = []

        for edge in edges:
            etype = edge["edge_type"]
            constraints = EDGE_KIND_CONSTRAINTS.get(etype)
            if constraints is None:
                # No constraints for this edge type (any -> any).
                continue

            src_node = nodes_by_id.get(edge["source_node_id"])
            tgt_node = nodes_by_id.get(edge["target_node_id"])
            if src_node is None or tgt_node is None:
                # Missing node -- will be caught by dangling reference check.
                continue

            src_kind = src_node["kind"]
            tgt_kind = tgt_node["kind"]

            allowed = False
            for valid_source_kinds, valid_target_kinds in constraints:
                if src_kind in valid_source_kinds and tgt_kind in valid_target_kinds:
                    allowed = True
                    break

            if not allowed:
                errors.append(
                    f"edge {edge['id']} ({etype}): "
                    f"invalid kind pair {src_kind!r} -> {tgt_kind!r}"
                )

        return errors

    # ==================================================================
    # Deploy plan
    # ==================================================================

    def build_deploy_plan(self, tenant_id: str, graph_id: str) -> dict:
        """Build a deployment plan from the graph.

        Returns a dict with:
          - graph_id
          - deploy_order: topologically sorted node_ids (agent nodes)
          - agent_tasks: list of task dicts for each agent
          - variable_bindings: all graph variables as key->value dict
          - primers: dict of node_id -> primer text
        """
        graph = self.get_graph(tenant_id, graph_id)
        if graph is None:
            raise ValueError(f"graph not found: {graph_id}")

        nodes = self.list_nodes(tenant_id, graph_id)
        edges = self.list_edges(tenant_id, graph_id)
        variables = self.list_variables(tenant_id, graph_id)
        nodes_by_id = {n["id"]: n for n in nodes}

        # Filter agent nodes.
        agent_nodes = [n for n in nodes if n["kind"] == "agent"]
        agent_ids = {n["id"] for n in agent_nodes}

        # Build adjacency for topological sort on delegates_to and triggers edges
        # among agent nodes only.
        adj: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {n["id"]: 0 for n in agent_nodes}
        for edge in edges:
            if edge["edge_type"] in ("delegates_to", "triggers"):
                src = edge["source_node_id"]
                tgt = edge["target_node_id"]
                if src in agent_ids and tgt in agent_ids:
                    adj[src].append(tgt)
                    in_degree[tgt] = in_degree.get(tgt, 0) + 1

        # Kahn's algorithm for topological sort.
        queue: deque[str] = deque()
        for nid, deg in in_degree.items():
            if deg == 0:
                queue.append(nid)

        deploy_order: list[str] = []
        while queue:
            nid = queue.popleft()
            deploy_order.append(nid)
            for neighbor in adj.get(nid, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If cycle prevented full ordering, append remaining agents.
        ordered_set = set(deploy_order)
        for n in agent_nodes:
            if n["id"] not in ordered_set:
                deploy_order.append(n["id"])

        # Variable bindings.
        variable_bindings = {v["key"]: v["value"] for v in variables}

        # Generate primers and agent tasks.
        primers: dict[str, str] = {}
        agent_tasks: list[dict[str, Any]] = []

        for nid in deploy_order:
            node = nodes_by_id[nid]
            config = node.get("config", {})

            # Build primer: describe the agent's role and connections.
            primer_lines = [
                f"Agent: {node['label']}",
                f"Node ID: {nid}",
                f"Kind: {node['kind']}",
            ]

            # Describe outgoing delegations/triggers.
            delegates = []
            triggers = []
            feeds_from = []
            for edge in edges:
                if edge["source_node_id"] == nid and edge["edge_type"] == "delegates_to":
                    tgt = nodes_by_id.get(edge["target_node_id"])
                    if tgt:
                        delegates.append(tgt["label"])
                if edge["source_node_id"] == nid and edge["edge_type"] == "triggers":
                    tgt = nodes_by_id.get(edge["target_node_id"])
                    if tgt:
                        triggers.append(tgt["label"])
                if edge["target_node_id"] == nid and edge["edge_type"] == "feeds":
                    src = nodes_by_id.get(edge["source_node_id"])
                    if src:
                        feeds_from.append(src["label"])

            if delegates:
                primer_lines.append(f"Delegates to: {', '.join(delegates)}")
            if triggers:
                primer_lines.append(f"Triggers: {', '.join(triggers)}")
            if feeds_from:
                primer_lines.append(f"Receives data from: {', '.join(feeds_from)}")

            if variable_bindings:
                primer_lines.append(f"Variables: {', '.join(variable_bindings.keys())}")

            primer = "\n".join(primer_lines)
            primers[nid] = primer

            # Build agent task dict.
            goal = config.get("goal", f"Execute role: {node['label']}")
            done_when = config.get("done_when", [f"{node['label']} completed its assigned work"])
            if isinstance(done_when, str):
                done_when = [done_when]
            model_id = config.get("model_id")
            workspace_root = config.get("workspace_root")

            agent_tasks.append({
                "node_id": nid,
                "label": node["label"],
                "goal": goal,
                "done_when": done_when,
                "model_id": model_id,
                "workspace_root": workspace_root,
                "primer": primer,
            })

        return {
            "graph_id": graph_id,
            "deploy_order": deploy_order,
            "agent_tasks": agent_tasks,
            "variable_bindings": variable_bindings,
            "primers": primers,
        }

    # ==================================================================
    # Row converters (private)
    # ==================================================================

    @staticmethod
    def _graph_row(row) -> dict:
        return {
            "id": str(row["id"]),
            "tenant_id": str(row["tenant_id"]),
            "workspace_id": str(row["workspace_id"]),
            "name": str(row["name"]),
            "description": str(row["description"] or ""),
            "metadata": json.loads(row["metadata_json"] or "{}"),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    @staticmethod
    def _node_row(row) -> dict:
        return {
            "id": str(row["id"]),
            "graph_id": str(row["graph_id"]),
            "tenant_id": str(row["tenant_id"]),
            "kind": str(row["kind"]),
            "label": str(row["label"] or ""),
            "config": json.loads(row["config_json"] or "{}"),
            "position_x": float(row["position_x"]) if row["position_x"] is not None else 0.0,
            "position_y": float(row["position_y"]) if row["position_y"] is not None else 0.0,
            "width": float(row["width"]) if row["width"] is not None else 200.0,
            "height": float(row["height"]) if row["height"] is not None else 100.0,
            "parent_node_id": str(row["parent_node_id"]) if row["parent_node_id"] else None,
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    @staticmethod
    def _edge_row(row) -> dict:
        return {
            "id": str(row["id"]),
            "graph_id": str(row["graph_id"]),
            "tenant_id": str(row["tenant_id"]),
            "source_node_id": str(row["source_node_id"]),
            "target_node_id": str(row["target_node_id"]),
            "edge_type": str(row["edge_type"]),
            "label": str(row["label"] or ""),
            "metadata": json.loads(row["metadata_json"] or "{}"),
            "created_at": str(row["created_at"]),
        }

    @staticmethod
    def _layout_row(row) -> dict:
        return {
            "id": str(row["id"]),
            "graph_id": str(row["graph_id"]),
            "tenant_id": str(row["tenant_id"]),
            "name": str(row["name"]),
            "layout": json.loads(row["layout_json"] or "{}"),
            "is_default": bool(row["is_default"]),
            "created_at": str(row["created_at"]),
        }

    @staticmethod
    def _variable_row(row) -> dict:
        return {
            "id": str(row["id"]),
            "graph_id": str(row["graph_id"]),
            "tenant_id": str(row["tenant_id"]),
            "key": str(row["key"]),
            "value": str(row["value"] or ""),
            "var_type": str(row["var_type"]),
            "description": str(row["description"] or ""),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    @staticmethod
    def _pipeline_row(row) -> dict:
        return {
            "id": str(row["id"]),
            "graph_id": str(row["graph_id"]),
            "tenant_id": str(row["tenant_id"]),
            "node_id": str(row["node_id"]),
            "name": str(row["name"] or ""),
            "steps": json.loads(row["steps_json"] or "[]"),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }

    # ==================================================================
    # Utilities (private)
    # ==================================================================

    @staticmethod
    def _uuid() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
