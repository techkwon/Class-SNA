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
                try:
                    # 'id'와 'label' 필드가 있는지 확인
                    node_id = row["id"]
                    
                    # 노드 속성 딕셔너리 생성
                    node_attrs = {}
                    
                    # 'label' 필드가 있으면 추가
                    if 'label' in row:
                        node_attrs['label'] = row['label']
                    elif 'name' in row:
                        # 'label'이 없고 'name'이 있으면 이를 'label'로 사용
                        node_attrs['label'] = row['name']
                    else:
                        # 둘 다 없으면 ID를 문자열로 변환하여 사용
                        node_attrs['label'] = str(node_id)
                    
                    # 'group' 필드가 있으면 추가
                    if 'group' in row:
                        node_attrs['group'] = row['group']
                    
                    # 노드 추가
                    G.add_node(node_id, **node_attrs)
                
                except Exception as e:
                    logger.warning(f"노드 추가 중 오류 발생: {str(e)}, 행: {row}")
                    continue
            
            # 엣지 추가
            for _, row in self.edges_df.iterrows():
                try:
                    # 'from'과 'to' 필드가 있는지 확인
                    if 'from' in row and 'to' in row:
                        source = row['from']
                        target = row['to']
                    # 이전 형식의 'source'와 'target' 필드도 지원
                    elif 'source' in row and 'target' in row:
                        source = row['source']
                        target = row['target']
                    else:
                        logger.warning(f"엣지 필드 누락: {row}")
                        continue
                    
                    # 가중치 추가
                    if 'weight' in row:
                        weight = row['weight']
                    elif 'value' in row:
                        weight = row['value']
                    else:
                        weight = 1
                    
                    # 타입 정보 추가
                    edge_attrs = {'weight': weight}
                    if 'type' in row:
                        edge_attrs['type'] = row['type']
                    
                    # 엣지 추가 - 노드가 존재할 때만
                    if source in G and target in G:
                        G.add_edge(source, target, **edge_attrs)
                    else:
                        missing = []
                        if source not in G:
                            missing.append(f"source={source}")
                        if target not in G:
                            missing.append(f"target={target}")
                        logger.warning(f"존재하지 않는 노드를 참조하는 엣지: {', '.join(missing)}")
                
                except Exception as e:
                    logger.warning(f"엣지 추가 중 오류 발생: {str(e)}, 행: {row}")
                    continue
            
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
    
    def get_nodes(self):
        """그래프의, 모든 노드(학생 이름) 목록 반환"""
        return list(self.graph.nodes())
        
    def get_edges(self):
        """그래프의 모든 엣지(관계) 목록 반환
        반환 형식: [(from_node, to_node, weight), ...]
        """
        return [(u, v, data.get('weight', 1)) for u, v, data in self.graph.edges(data=True)]
        
    def get_communities(self):
        """각 커뮤니티에 속한 노드 목록을 반환
        반환 형식: {community_id: [node1, node2, ...], ...}
        """
        if self.communities is None:
            self.detect_communities()
            
        # 커뮤니티별 노드 목록 생성
        community_nodes = {}
        for node, community_id in self.communities.items():
            if community_id not in community_nodes:
                community_nodes[community_id] = []
            community_nodes[community_id].append(node)
            
        return community_nodes
        
    def get_community_colors(self):
        """각 노드의 커뮤니티 기반 색상 맵을 반환
        반환 형식: {node: color_hex, ...}
        """
        if self.communities is None:
            self.detect_communities()
            
        # 색상 팔레트 정의
        color_palette = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
        ]
        
        # 각 노드에 커뮤니티 기반 색상 할당
        node_colors = {}
        for node, community_id in self.communities.items():
            node_colors[node] = color_palette[community_id % len(color_palette)]
            
        return node_colors
        
    def get_centrality_metrics(self):
        """중심성 지표 반환
        아직 계산되지 않았다면 계산 후 반환합니다.
        
        반환 형식: {
            'in_degree': {node: value, ...},
            'out_degree': {node: value, ...},
            'betweenness': {node: value, ...},
            'closeness': {node: value, ...},
            ...
        }
        """
        # 중심성 지표가 없다면 계산
        if not self.metrics:
            self.calculate_centrality()
            
        return self.metrics
        
    def find_isolated_nodes(self, threshold=0):
        """고립된 노드 식별 (in_degree가 threshold 이하인 노드)
        
        Args:
            threshold (int): 이 값 이하의 in_degree를 가진 노드를 고립된 것으로 판단 (기본값: 0)
            
        Returns:
            list: 고립된 노드 목록
        """
        try:
            # 중심성 지표가 없다면 계산
            if not self.metrics:
                self.calculate_centrality()
                
            # in_degree가 threshold 이하인 노드 식별
            in_degree = self.metrics.get('in_degree', {})
            isolated_nodes = [node for node, value in in_degree.items() if value <= threshold]
            
            return isolated_nodes
            
        except Exception as e:
            logger.error(f"고립 노드 식별 중 오류 발생: {str(e)}")
            return [] 