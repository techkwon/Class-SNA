import networkx as nx
import community as community_louvain
import pandas as pd
import numpy as np
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkAnalyzer:
    """소셜 네트워크 분석 기능을 제공하는 클래스"""
    
    def __init__(self, network_data):
        self.nodes_df = network_data["nodes"]
        self.edges_df = network_data["edges"]
        self.question_types = network_data.get("question_types", {})
        self.graph = None
        self.metrics = {}
        self.communities = None
        
        # 그래프 생성
        self._create_graph()
    
    def _create_graph(self):
        """네트워크 그래프 생성"""
        try:
            # NetworkX 그래프 객체 생성
            G = nx.DiGraph()  # 방향성 그래프
            
            # 노드 추가
            for _, row in self.nodes_df.iterrows():
                G.add_node(row["id"], label=row["label"])
            
            # 엣지 추가
            for _, row in self.edges_df.iterrows():
                if "weight" in row:
                    G.add_edge(row["from"], row["to"], weight=row["weight"])
                else:
                    G.add_edge(row["from"], row["to"], weight=1)
            
            self.graph = G
            logger.info(f"그래프 생성 완료: 노드 {G.number_of_nodes()}개, 엣지 {G.number_of_edges()}개")
            
        except Exception as e:
            logger.error(f"그래프 생성 실패: {str(e)}")
            raise Exception(f"네트워크 그래프 생성 중 오류가 발생했습니다: {str(e)}")
    
    def calculate_centrality(self):
        """중심성 지표 계산"""
        try:
            # 연결 중심성 (Degree Centrality)
            in_degree = nx.in_degree_centrality(self.graph)
            out_degree = nx.out_degree_centrality(self.graph)
            
            # 근접 중심성 (Closeness Centrality)
            try:
                closeness = nx.closeness_centrality(self.graph)
            except:
                # 연결되지 않은 그래프인 경우 약한 연결 컴포넌트에서 계산
                largest_wcc = max(nx.weakly_connected_components(self.graph), key=len)
                subgraph = self.graph.subgraph(largest_wcc)
                closeness = nx.closeness_centrality(subgraph)
                
                # 나머지 노드에 대해 0 값 설정
                for node in self.graph.nodes():
                    if node not in closeness:
                        closeness[node] = 0
            
            # 매개 중심성 (Betweenness Centrality)
            betweenness = nx.betweenness_centrality(self.graph)
            
            # 아이겐벡터 중심성 (Eigenvector Centrality)
            try:
                eigenvector = nx.eigenvector_centrality(self.graph, max_iter=1000)
            except:
                eigenvector = {node: 0 for node in self.graph.nodes()}
                logger.warning("아이겐벡터 중심성 계산 실패, 기본값 0으로 설정")
            
            # 중심성 지표 저장
            self.metrics = {
                "in_degree": in_degree,
                "out_degree": out_degree,
                "closeness": closeness,
                "betweenness": betweenness,
                "eigenvector": eigenvector
            }
            
            logger.info("중심성 지표 계산 완료")
            return self.metrics
            
        except Exception as e:
            logger.error(f"중심성 지표 계산 실패: {str(e)}")
            raise Exception(f"중심성 지표 계산 중 오류가 발생했습니다: {str(e)}")
    
    def detect_communities(self):
        """커뮤니티(하위 그룹) 탐지"""
        try:
            # 방향성 그래프를 무방향 그래프로 변환
            undirected_graph = self.graph.to_undirected()
            
            # Louvain 알고리즘을 사용한 커뮤니티 탐지
            communities = community_louvain.best_partition(undirected_graph)
            
            # 커뮤니티 정보 저장
            self.communities = communities
            
            # 커뮤니티별 노드 그룹화
            community_groups = {}
            for node, community_id in communities.items():
                if community_id not in community_groups:
                    community_groups[community_id] = []
                community_groups[community_id].append(node)
            
            logger.info(f"커뮤니티 탐지 완료: {len(community_groups)}개 커뮤니티 발견")
            return community_groups
            
        except Exception as e:
            logger.error(f"커뮤니티 탐지 실패: {str(e)}")
            raise Exception(f"커뮤니티 탐지 중 오류가 발생했습니다: {str(e)}")
    
    def identify_isolated_nodes(self, threshold=0.1):
        """소외 학생(연결이 적은 노드) 식별"""
        try:
            if not self.metrics:
                self.calculate_centrality()
            
            # 연결 중심성(수신)을 기준으로 소외 노드 식별
            in_degree = self.metrics["in_degree"]
            
            # 중심성 값 정렬
            sorted_in_degree = sorted(in_degree.items(), key=lambda x: x[1])
            
            # 임계값 이하의 노드를 소외 노드로 간주
            threshold_value = max(in_degree.values()) * threshold
            isolated_nodes = [node for node, value in in_degree.items() if value <= threshold_value]
            
            logger.info(f"소외 노드 식별 완료: {len(isolated_nodes)}개 노드 발견")
            return isolated_nodes
            
        except Exception as e:
            logger.error(f"소외 노드 식별 실패: {str(e)}")
            raise Exception(f"소외 노드 식별 중 오류가 발생했습니다: {str(e)}")
    
    def get_summary_statistics(self):
        """네트워크 요약 통계 계산"""
        try:
            # 그래프 기본 정보
            stats = {
                "nodes_count": self.graph.number_of_nodes(),
                "edges_count": self.graph.number_of_edges(),
                "density": nx.density(self.graph),
                "is_connected": nx.is_weakly_connected(self.graph),
                "average_clustering": nx.average_clustering(self.graph.to_undirected())
            }
            
            # 중심성 지표 통계
            if not self.metrics:
                self.calculate_centrality()
            
            for metric_name, metric_values in self.metrics.items():
                values = list(metric_values.values())
                stats[f"{metric_name}_mean"] = np.mean(values)
                stats[f"{metric_name}_std"] = np.std(values)
                stats[f"{metric_name}_max"] = np.max(values)
                
                # 중심성이 가장 높은 노드 식별
                max_node = max(metric_values.items(), key=lambda x: x[1])[0]
                stats[f"{metric_name}_max_node"] = max_node
            
            # 커뮤니티 정보
            if not self.communities:
                self.detect_communities()
            
            stats["community_count"] = len(set(self.communities.values()))
            
            logger.info("네트워크 요약 통계 계산 완료")
            return stats
            
        except Exception as e:
            logger.error(f"요약 통계 계산 실패: {str(e)}")
            raise Exception(f"요약 통계 계산 중 오류가 발생했습니다: {str(e)}")
    
    def get_node_attributes(self):
        """노드별 속성 데이터 취합"""
        try:
            # 노드 기본 정보 가져오기
            nodes_with_attrs = []
            
            for node in self.graph.nodes():
                # 노드 기본 정보
                node_info = {
                    "id": node,
                    "label": self.graph.nodes[node].get("label", node)
                }
                
                # 중심성 지표 추가
                if self.metrics:
                    for metric_name, metric_values in self.metrics.items():
                        node_info[metric_name] = metric_values.get(node, 0)
                
                # 커뮤니티 정보 추가
                if self.communities:
                    node_info["community"] = self.communities.get(node, -1)
                
                nodes_with_attrs.append(node_info)
            
            # 데이터프레임으로 변환
            nodes_df = pd.DataFrame(nodes_with_attrs)
            
            return nodes_df
            
        except Exception as e:
            logger.error(f"노드 속성 취합 실패: {str(e)}")
            raise Exception(f"노드 속성 취합 중 오류가 발생했습니다: {str(e)}") 