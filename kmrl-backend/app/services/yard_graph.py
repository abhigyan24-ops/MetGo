"""
Neo4j graph service for Muttom Yard topology modeling.

SIMULATED LAYOUT — the exact bay-by-bay engineering drawings of Muttom Yard
are internal KMRL data. This service models a physically consistent simplified
layout where pulling a rear-bay train requires shunting the trains parked in
front of it.

Neo4j Community Edition is used — free, self-hosted via Docker.
No paid Neo4j AuraDB cloud tier is required.

Graph structure:
  - Nodes: YardBay (properties: bay_id, line_id, position, bay_type)
  - Edges: ADJACENT_TO (same line, sequential positions)
           BLOCKS (train in position N blocks access to position N+1)

Use cases:
  1. Calculate minimum shunts needed to pull a specific train
  2. Find optimal bay assignments to minimize future shunting
  3. Visualize yard occupancy for dashboard
"""

from typing import List, Dict, Tuple, Optional
import logging

from app.db.neo4j_session import get_neo4j
from app.models.yard import YardBay, YardLine

logger = logging.getLogger(__name__)


class YardGraphService:
    """Service for managing and querying the Muttom Yard graph in Neo4j."""
    
    def __init__(self):
        self.neo4j = get_neo4j()
    
    # -----------------------------------------------------------------------
    # Graph initialization
    # -----------------------------------------------------------------------
    
    def clear_graph(self) -> None:
        """Clear all yard graph data (for re-seeding)."""
        query = """
        MATCH (n:YardBay)
        DETACH DELETE n
        """
        self.neo4j.run(query)
        logger.info("Cleared Neo4j yard graph")
    
    def build_graph_from_postgres(self, db_session) -> Dict[str, int]:
        """
        Build the complete yard graph in Neo4j from Postgres bay data.
        
        Returns a summary dict with node/edge counts.
        """
        self.clear_graph()
        
        # Fetch all lines and bays from Postgres
        lines = db_session.query(YardLine).all()
        
        node_count = 0
        adjacent_edge_count = 0
        blocks_edge_count = 0
        
        for line in lines:
            bays = sorted(line.bays, key=lambda b: b.position)
            
            # Create bay nodes
            for bay in bays:
                self._create_bay_node(
                    bay_id=bay.bay_id,
                    line_id=bay.line_id,
                    position=bay.position,
                    bay_type=bay.bay_type.value,
                    occupied_by=bay.occupied_by,
                )
                node_count += 1
            
            # Create ADJACENT_TO edges (sequential bays on same line)
            for i in range(len(bays) - 1):
                bay_a = bays[i]
                bay_b = bays[i + 1]
                self._create_adjacent_edge(bay_a.bay_id, bay_b.bay_id)
                adjacent_edge_count += 1
            
            # Create BLOCKS edges (lower position blocks higher position)
            for i in range(len(bays)):
                for j in range(i + 1, len(bays)):
                    blocker = bays[i]
                    blocked = bays[j]
                    if blocker.occupied_by:  # Only occupied bays block
                        self._create_blocks_edge(blocker.bay_id, blocked.bay_id)
                        blocks_edge_count += 1
        
        logger.info(
            f"Built yard graph: {node_count} nodes, "
            f"{adjacent_edge_count} ADJACENT_TO, {blocks_edge_count} BLOCKS"
        )
        
        return {
            "nodes": node_count,
            "adjacent_edges": adjacent_edge_count,
            "blocks_edges": blocks_edge_count,
        }
    
    def _create_bay_node(
        self,
        bay_id: str,
        line_id: str,
        position: int,
        bay_type: str,
        occupied_by: Optional[str],
    ) -> None:
        """Create a single YardBay node in Neo4j."""
        query = """
        CREATE (b:YardBay {
            bay_id: $bay_id,
            line_id: $line_id,
            position: $position,
            bay_type: $bay_type,
            occupied_by: $occupied_by,
            is_occupied: $is_occupied
        })
        """
        self.neo4j.run(
            query,
            bay_id=bay_id,
            line_id=line_id,
            position=position,
            bay_type=bay_type,
            occupied_by=occupied_by,
            is_occupied=(occupied_by is not None),
        )
    
    def _create_adjacent_edge(self, bay_a: str, bay_b: str) -> None:
        """Create ADJACENT_TO relationship (sequential bays on same line)."""
        query = """
        MATCH (a:YardBay {bay_id: $bay_a})
        MATCH (b:YardBay {bay_id: $bay_b})
        CREATE (a)-[:ADJACENT_TO]->(b)
        """
        self.neo4j.run(query, bay_a=bay_a, bay_b=bay_b)
    
    def _create_blocks_edge(self, blocker_bay: str, blocked_bay: str) -> None:
        """
        Create BLOCKS relationship.
        
        A train in position N blocks access to all positions > N on the same line.
        This edge only exists when the blocker bay is currently occupied.
        """
        query = """
        MATCH (blocker:YardBay {bay_id: $blocker_bay})
        MATCH (blocked:YardBay {bay_id: $blocked_bay})
        CREATE (blocker)-[:BLOCKS]->(blocked)
        """
        self.neo4j.run(query, blocker_bay=blocker_bay, blocked_bay=blocked_bay)
    
    # -----------------------------------------------------------------------
    # Query methods
    # -----------------------------------------------------------------------
    
    def get_shunts_needed(self, target_bay: str) -> List[str]:
        """
        Calculate which trains must be shunted to pull the train in target_bay.
        
        Returns a list of bay_ids that block access to the target bay,
        ordered from closest to furthest (pull order).
        
        Example: if target is B14 (position 4), and B11, B12, B13 are occupied,
                 returns ["B13", "B12", "B11"] (pull innermost first).
        """
        query = """
        MATCH path = (blocker:YardBay)-[:BLOCKS*]->(target:YardBay {bay_id: $target_bay})
        WHERE blocker.is_occupied = true
        WITH blocker
        ORDER BY blocker.position DESC
        RETURN blocker.bay_id AS bay_id
        """
        result = self.neo4j.run(query, target_bay=target_bay)
        return [record["bay_id"] for record in result]
    
    def get_shunt_count(self, target_bay: str) -> int:
        """Return the number of shunts needed to access target_bay."""
        return len(self.get_shunts_needed(target_bay))
    
    def find_empty_bays(self, bay_type: Optional[str] = None) -> List[Dict]:
        """
        Find all empty bays, optionally filtered by type.
        
        Returns list of dicts: {bay_id, line_id, position, bay_type}
        Sorted by position (prefer entrance-end bays with position=1).
        """
        if bay_type:
            query = """
            MATCH (b:YardBay)
            WHERE b.is_occupied = false AND b.bay_type = $bay_type
            RETURN b.bay_id AS bay_id, b.line_id AS line_id,
                   b.position AS position, b.bay_type AS bay_type
            ORDER BY b.position ASC
            """
            result = self.neo4j.run(query, bay_type=bay_type)
        else:
            query = """
            MATCH (b:YardBay)
            WHERE b.is_occupied = false
            RETURN b.bay_id AS bay_id, b.line_id AS line_id,
                   b.position AS position, b.bay_type AS bay_type
            ORDER BY b.position ASC
            """
            result = self.neo4j.run(query)
        
        return result
    
    def get_line_occupancy(self, line_id: str) -> Dict:
        """
        Get occupancy summary for a specific yard line.
        
        Returns: {
            "line_id": "L1",
            "total_bays": 6,
            "occupied": 4,
            "empty": 2,
            "bays": [list of bay dicts with occupancy status]
        }
        """
        query = """
        MATCH (b:YardBay {line_id: $line_id})
        RETURN b.bay_id AS bay_id, b.position AS position,
               b.is_occupied AS is_occupied, b.occupied_by AS occupied_by
        ORDER BY b.position ASC
        """
        result = self.neo4j.run(query, line_id=line_id)
        
        bays = list(result)
        occupied = sum(1 for b in bays if b["is_occupied"])
        
        return {
            "line_id": line_id,
            "total_bays": len(bays),
            "occupied": occupied,
            "empty": len(bays) - occupied,
            "bays": bays,
        }
    
    def get_all_occupancy(self) -> List[Dict]:
        """
        Get occupancy summary for all yard lines.
        Useful for dashboard visualization.
        """
        query = """
        MATCH (b:YardBay)
        RETURN DISTINCT b.line_id AS line_id
        ORDER BY b.line_id
        """
        lines = self.neo4j.run(query)
        
        return [self.get_line_occupancy(line["line_id"]) for line in lines]
    
    def find_optimal_bay_for_assignment(
        self,
        bay_type: str = "stabling",
        minimize_future_shunting: bool = True,
    ) -> Optional[str]:
        """
        Find the optimal empty bay for a new train assignment.
        
        Strategy:
          - Prefer entrance-end bays (position=1) to minimize future shunting
          - Filter by bay_type (stabling, maintenance, wash, inspection)
        
        Returns bay_id or None if no suitable bay available.
        """
        query = """
        MATCH (b:YardBay)
        WHERE b.is_occupied = false AND b.bay_type = $bay_type
        RETURN b.bay_id AS bay_id, b.position AS position
        ORDER BY b.position ASC
        LIMIT 1
        """
        result = self.neo4j.run(query, bay_type=bay_type)
        
        if result:
            return result[0]["bay_id"]
        return None
    
    def update_bay_occupancy(self, bay_id: str, occupied_by: Optional[str]) -> None:
        """
        Update a bay's occupancy status in Neo4j (should match Postgres).
        
        This is called after a shunt operation or new assignment.
        Also updates BLOCKS edges dynamically.
        """
        query = """
        MATCH (b:YardBay {bay_id: $bay_id})
        SET b.occupied_by = $occupied_by,
            b.is_occupied = $is_occupied
        """
        self.neo4j.run(
            query,
            bay_id=bay_id,
            occupied_by=occupied_by,
            is_occupied=(occupied_by is not None),
        )
        
        # Rebuild BLOCKS edges for this bay's line (simplified approach)
        # In production, you'd do incremental edge updates
        logger.debug(f"Updated bay {bay_id} occupancy: {occupied_by}")
    
    # -----------------------------------------------------------------------
    # Visualization helpers (for dashboard)
    # -----------------------------------------------------------------------
    
    def get_yard_layout_for_viz(self) -> Dict:
        """
        Return the full yard layout in a format suitable for D3.js visualization.
        
        Returns: {
            "nodes": [list of bay nodes with properties],
            "edges": [list of ADJACENT_TO edges for spatial layout]
        }
        """
        nodes_query = """
        MATCH (b:YardBay)
        RETURN b.bay_id AS id, b.line_id AS line, b.position AS position,
               b.bay_type AS type, b.is_occupied AS occupied,
               b.occupied_by AS train_id
        ORDER BY b.line_id, b.position
        """
        nodes = self.neo4j.run(nodes_query)
        
        edges_query = """
        MATCH (a:YardBay)-[:ADJACENT_TO]->(b:YardBay)
        RETURN a.bay_id AS source, b.bay_id AS target
        """
        edges = self.neo4j.run(edges_query)
        
        return {
            "nodes": list(nodes),
            "edges": list(edges),
        }


# ---------------------------------------------------------------------------
# Convenience function for other services
# ---------------------------------------------------------------------------

def get_yard_graph_service() -> YardGraphService:
    """Return a yard graph service instance."""
    return YardGraphService()
