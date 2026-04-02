"""
Network Analyzer

Builds and analyzes networks of companies based on co-bidding relationships.
Identifies suspicious clusters and hidden connections.
"""

import networkx as nx
import pandas as pd
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass
from loguru import logger


@dataclass
class NetworkMetrics:
    """Metrics for a single node in the network."""
    node_id: str
    degree: int
    degree_centrality: float
    betweenness_centrality: float
    clustering_coefficient: float
    community_id: Optional[int] = None


class NetworkAnalyzer:
    """
    Analyzes co-bidding networks to detect suspicious relationships.
    """
    
    def __init__(self):
        self.graph: nx.Graph = nx.Graph()
        self.communities: List[Set[str]] = []
        self.node_metrics: Dict[str, NetworkMetrics] = {}
    
    def build_co_bidding_network(
        self,
        tenders_df: pd.DataFrame,
        min_co_bids: int = 2
    ) -> nx.Graph:
        """
        Build network where edges represent co-bidding relationships.
        
        Args:
            tenders_df: DataFrame with 'bidder_ids' column (list of bidder IDs)
            min_co_bids: Minimum number of co-bids to create an edge
        
        Returns:
            NetworkX graph
        """
        self.graph = nx.Graph()
        
        # Get all unique companies
        all_companies = set()
        for bidders in tenders_df['bidder_ids'].dropna():
            if isinstance(bidders, list):
                all_companies.update([b for b in bidders if b])
        
        # Add nodes
        for company_id in all_companies:
            self.graph.add_node(company_id)
        
        # Count co-bidding occurrences
        co_bid_counts = defaultdict(int)
        
        for bidders in tenders_df['bidder_ids'].dropna():
            if not isinstance(bidders, list):
                continue
            
            # Get unique bidders
            bidders = [b for b in set(bidders) if b]
            
            # Count pairs
            for i, b1 in enumerate(bidders):
                for b2 in bidders[i+1:]:
                    # Always store with smaller ID first
                    key = tuple(sorted([b1, b2]))
                    co_bid_counts[key] += 1
        
        # Add edges for pairs that meet threshold
        for (b1, b2), count in co_bid_counts.items():
            if count >= min_co_bids:
                self.graph.add_edge(b1, b2, weight=count)
        
        logger.info(f"Built network: {self.graph.number_of_nodes()} nodes, "
                   f"{self.graph.number_of_edges()} edges")
        
        return self.graph
    
    def calculate_metrics(self) -> Dict[str, NetworkMetrics]:
        """Calculate network metrics for all nodes."""
        if len(self.graph.nodes()) == 0:
            return {}
        
        # Calculate centralities
        degree_centrality = nx.degree_centrality(self.graph)
        clustering = nx.clustering(self.graph)
        
        try:
            betweenness = nx.betweenness_centrality(self.graph)
        except Exception:
            betweenness = {n: 0.0 for n in self.graph.nodes()}
        
        # Build metrics dict
        self.node_metrics = {}
        
        for node in self.graph.nodes():
            self.node_metrics[node] = NetworkMetrics(
                node_id=node,
                degree=self.graph.degree(node),
                degree_centrality=degree_centrality.get(node, 0),
                betweenness_centrality=betweenness.get(node, 0),
                clustering_coefficient=clustering.get(node, 0),
            )
        
        return self.node_metrics
    
    def detect_communities(self) -> List[Set[str]]:
        """
        Detect communities using Louvain algorithm.
        Returns list of sets, each containing node IDs in a community.
        """
        if len(self.graph.nodes()) == 0:
            return []
        
        try:
            # Use connected components as a simple community detection
            # For a more sophisticated approach, use python-louvain library
            self.communities = [
                set(c) for c in nx.connected_components(self.graph)
                if len(c) >= 3  # Only communities with 3+ members
            ]
            
            # Assign community IDs to node metrics
            for i, community in enumerate(self.communities):
                for node in community:
                    if node in self.node_metrics:
                        self.node_metrics[node].community_id = i
            
            logger.info(f"Found {len(self.communities)} communities (3+ members)")
            
        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            self.communities = []
        
        return self.communities
    
    def get_subgraph_for_contractor(
        self,
        contractor_id: str,
        depth: int = 2,
        max_nodes: int = 50
    ) -> Tuple[nx.Graph, List[str]]:
        """
        Get subgraph centered on a contractor.
        
        Args:
            contractor_id: Center node ID
            depth: How many hops from center
            max_nodes: Maximum nodes to return
        
        Returns:
            Tuple of (subgraph, list of node IDs)
        """
        if contractor_id not in self.graph:
            return nx.Graph(), []
        
        # BFS to get neighbors up to depth
        nodes = {contractor_id}
        frontier = {contractor_id}
        
        for _ in range(depth):
            next_frontier = set()
            for node in frontier:
                neighbors = set(self.graph.neighbors(node))
                next_frontier.update(neighbors - nodes)
            nodes.update(next_frontier)
            frontier = next_frontier
            
            if len(nodes) >= max_nodes:
                break
        
        # Limit to max_nodes, prioritizing by degree
        if len(nodes) > max_nodes:
            # Always include the center
            other_nodes = nodes - {contractor_id}
            degrees = {n: self.graph.degree(n) for n in other_nodes}
            sorted_nodes = sorted(degrees.keys(), key=lambda n: degrees[n], reverse=True)
            nodes = {contractor_id} | set(sorted_nodes[:max_nodes-1])
        
        subgraph = self.graph.subgraph(nodes).copy()
        
        return subgraph, list(nodes)
    
    def get_suspicious_clusters(
        self,
        tenders_df: pd.DataFrame,
        min_cluster_size: int = 3,
        min_total_value: float = 1000000
    ) -> pd.DataFrame:
        """
        Identify clusters with high combined win values.
        These are potential collusion networks.
        """
        suspicious = []
        
        for i, community in enumerate(self.communities):
            if len(community) < min_cluster_size:
                continue
            
            # Calculate aggregate stats for this cluster
            cluster_wins = tenders_df[tenders_df['winner_id'].isin(community)]
            total_value = cluster_wins['award_value'].sum()
            total_wins = len(cluster_wins)
            
            if total_value < min_total_value:
                continue
            
            # Calculate average risk
            avg_risk = cluster_wins['risk_score'].mean() if 'risk_score' in cluster_wins.columns else None
            
            suspicious.append({
                'cluster_id': i,
                'size': len(community),
                'member_ids': list(community)[:10],  # Limit to first 10
                'total_wins': total_wins,
                'total_value': total_value,
                'avg_risk_score': avg_risk,
            })
        
        return pd.DataFrame(suspicious).sort_values('total_value', ascending=False)
    
    def get_co_bidding_pairs(
        self,
        min_co_bids: int = 3,
        limit: int = 100
    ) -> List[Dict]:
        """Get top co-bidding pairs by frequency."""
        pairs = []
        
        for u, v, data in self.graph.edges(data=True):
            weight = data.get('weight', 1)
            if weight >= min_co_bids:
                pairs.append({
                    'contractor_a_id': u,
                    'contractor_b_id': v,
                    'co_bid_count': weight,
                })
        
        # Sort by count and limit
        pairs.sort(key=lambda x: x['co_bid_count'], reverse=True)
        return pairs[:limit]
    
    def analyze_contractor(self, contractor_id: str) -> Dict:
        """Get complete network analysis for a contractor."""
        if contractor_id not in self.graph:
            return {
                'in_network': False,
                'connections': 0,
                'metrics': None,
                'community_size': 0,
            }
        
        metrics = self.node_metrics.get(contractor_id)
        community_id = metrics.community_id if metrics else None
        community = self.communities[community_id] if community_id is not None else set()
        
        # Get direct connections
        neighbors = list(self.graph.neighbors(contractor_id))
        
        return {
            'in_network': True,
            'connections': len(neighbors),
            'neighbor_ids': neighbors[:20],  # Limit
            'metrics': {
                'degree': metrics.degree if metrics else 0,
                'degree_centrality': metrics.degree_centrality if metrics else 0,
                'betweenness_centrality': metrics.betweenness_centrality if metrics else 0,
                'clustering_coefficient': metrics.clustering_coefficient if metrics else 0,
            },
            'community_id': community_id,
            'community_size': len(community),
        }


# Singleton instance
network_analyzer = NetworkAnalyzer()
