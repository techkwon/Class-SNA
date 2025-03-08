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
        self.original_nodes = network_data.get("original_nodes", self.nodes_df)
        self.edges_df = network_data["edges"]
        self.question_types = network_data.get("question_types", {})
        self.graph = None
        self.metrics = {}
        self.communities = None
        
        # 이름 매핑 저장
        self.id_mapping = network_data.get("id_mapping", {})  # 이름 -> ID
        self.name_mapping = network_data.get("name_mapping", {})  # ID -> 이름
        self.romanized_mapping = network_data.get("romanized_mapping", {})  # 이름 -> 로마자
        self.reverse_romanized = network_data.get("reverse_romanized", {})  # 로마자 -> 이름
        
        # Gemini 개선 데이터 저장
        self.gemini_enhanced = network_data.get("gemini_enhanced", False)
        self.node_scores = network_data.get("node_scores", {})
        self.enhanced_edge_weights = network_data.get("enhanced_edge_weights", {})
        self.gemini_communities = network_data.get("gemini_communities", {})
        
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
                # 각 값이 리스트인 경우 처리
                processed_values = []
                max_value = 0
                max_node = None
                
                for node, value in metric_values.items():
                    # 리스트 타입 처리
                    if isinstance(value, list):
                        if value:  # 리스트가 비어있지 않은 경우
                            processed_value = value[0]
                        else:
                            processed_value = 0
                    else:
                        processed_value = value
                    
                    # 숫자 형태로 변환 (문자열인 경우)
                    try:
                        processed_value = float(processed_value)
                    except (ValueError, TypeError):
                        processed_value = 0
                        
                    processed_values.append(processed_value)
                    
                    # 최대값 노드 업데이트
                    if processed_value > max_value:
                        max_value = processed_value
                        max_node = node
                        
                # 통계 계산
                if processed_values:
                    stats[f"{metric_name}_mean"] = np.mean(processed_values)
                    stats[f"{metric_name}_std"] = np.std(processed_values)
                    stats[f"{metric_name}_max"] = np.max(processed_values)
                else:
                    stats[f"{metric_name}_mean"] = 0
                    stats[f"{metric_name}_std"] = 0
                    stats[f"{metric_name}_max"] = 0
                
                # 중심성이 가장 높은 노드 저장
                if max_node is not None:
                    stats[f"{metric_name}_max_node"] = str(max_node)
                else:
                    stats[f"{metric_name}_max_node"] = ""
            
            # 커뮤니티 정보 추가
            if self.communities:
                stats["num_communities"] = len(self.communities)
                
                # 커뮤니티 크기 통계
                community_sizes = []
                for community_id, members in self.communities.items():
                    # 멤버가 리스트가 아닌 경우 처리
                    if isinstance(members, list):
                        size = len(members)
                    else:
                        size = 1  # 단일 멤버로 간주
                    community_sizes.append(size)
                
                if community_sizes:
                    stats["community_size_mean"] = np.mean(community_sizes)
                    stats["community_size_std"] = np.std(community_sizes)
                    stats["community_size_max"] = np.max(community_sizes)
            else:
                stats["num_communities"] = 0
                stats["community_size_mean"] = 0
                stats["community_size_std"] = 0
                stats["community_size_max"] = 0
                
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
        """커뮤니티 멤버십 정보 반환"""
        if not hasattr(self, 'communities') or not self.communities:
            self.detect_communities()
            
        # 안전한 복사본 생성 (모든 키를 문자열로 변환)
        safe_communities = {}
        
        if self.communities:
            for comm_id, members in self.communities.items():
                # 커뮤니티 ID를 문자열로 변환 (안전한 처리)
                safe_comm_id = str(comm_id)
                
                # 멤버가 리스트인지 확인
                if isinstance(members, list):
                    safe_communities[safe_comm_id] = members.copy()
                elif isinstance(members, set):
                    safe_communities[safe_comm_id] = list(members)
                else:
                    # 단일 값인 경우 리스트로 감싸기
                    safe_communities[safe_comm_id] = [members]
        
        return safe_communities
        
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
    
    def generate_summary(self):
        """네트워크 분석 요약 텍스트 생성"""
        try:
            if self.graph is None or self.graph.number_of_nodes() == 0:
                return "네트워크 데이터가 없습니다."
            
            # 기본 통계
            num_nodes = self.graph.number_of_nodes()
            num_edges = self.graph.number_of_edges()
            density = nx.density(self.graph)
            
            # 중심성 지표 분석
            if not self.metrics:
                self.calculate_centrality()
            
            # 가장 중요한 노드 식별
            top_nodes = {}
            if 'in_degree' in self.metrics:
                in_degree = self.metrics['in_degree']
                top_in = sorted(in_degree.items(), key=lambda x: x[1], reverse=True)[:3]
                top_nodes['인기도'] = [f"{node} ({value:.3f})" for node, value in top_in]
            
            if 'betweenness' in self.metrics:
                betweenness = self.metrics['betweenness']
                top_betw = sorted(betweenness.items(), key=lambda x: x[1], reverse=True)[:3]
                top_nodes['매개 중심성'] = [f"{node} ({value:.3f})" for node, value in top_betw]
            
            # 커뮤니티 정보
            if self.communities is None:
                self.detect_communities()
            
            community_info = {}
            if self.communities:
                for comm_id, members in self.communities.items():
                    # 커뮤니티 멤버가 리스트가 아니라 정수일 수 있으므로 타입 확인
                    if isinstance(members, list):
                        community_info[comm_id] = len(members)
                    else:
                        # 리스트가 아니면 개수를 1로 설정
                        community_info[comm_id] = 1
                        # 정수를 리스트로 변환하여 일관성 유지
                        self.communities[comm_id] = [str(members)]
            
            # 요약 텍스트 생성
            summary = []
            summary.append(f"### 네트워크 기본 정보")
            summary.append(f"- **학생 수**: {num_nodes}명")
            summary.append(f"- **관계 수**: {num_edges}개")
            summary.append(f"- **네트워크 밀도**: {density:.4f}")
            
            if top_nodes:
                summary.append(f"\n### 주요 학생 분석")
                
                if '인기도' in top_nodes:
                    summary.append(f"- **인기가 가장 많은 학생**:")
                    for node in top_nodes['인기도']:
                        summary.append(f"  - {node}")
                
                if '매개 중심성' in top_nodes:
                    summary.append(f"- **매개 역할이 큰 학생**:")
                    for node in top_nodes['매개 중심성']:
                        summary.append(f"  - {node}")
            
            if community_info:
                summary.append(f"\n### 그룹 분석")
                summary.append(f"- **발견된 그룹 수**: {len(community_info)}개")
                
                for comm_id, size in community_info.items():
                    members = self.communities[comm_id]
                    # members가 리스트인지 확인
                    if isinstance(members, list):
                        # 최대 5개 멤버만 표시
                        display_members = members[:5]
                        # 더 많은 멤버가 있으면 '...' 추가
                        ellipsis = ', ...' if len(members) > 5 else ''
                        summary.append(f"- **그룹 {comm_id}**: {size}명 ({', '.join(display_members)}{ellipsis})")
                    else:
                        # 리스트가 아닌 경우
                        summary.append(f"- **그룹 {comm_id}**: 1명 ({members})")
            
            return "\n".join(summary)
            
        except Exception as e:
            logger.error(f"네트워크 요약 생성 중 오류: {str(e)}")
            return "네트워크 요약을 생성하는 중 오류가 발생했습니다." 