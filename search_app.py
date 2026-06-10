import streamlit as st
import pandas as pd
import re
from suppl.pubmed_client import search_pubmed, fetch_article_abstracts

# ==============================================================================
# 1. 페이지 기본 설정 및 SEO 메타데이터 주입
# ==============================================================================
st.set_page_config(
    page_title="PubMed Scholar Search Engine",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# HTML meta tag 및 프리미엄 스타일링 (Google Fonts 포함) 주입
st.markdown(
    """
    <meta name="description" content="Discover biomedical literature using NCBI PubMed API. Filter by publication year, export search results, and browse detailed abstract metrics.">
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Inter:wght@300;400;500;600&display=swap');
    
    /* 글로벌 폰트 변경 */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* 타이틀 및 헤더 */
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
    }
    
    .main-title {
        background: linear-gradient(135deg, #6366F1 0%, #A855F7 50%, #EC4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        margin-bottom: 0.1rem;
        text-align: left;
    }
    
    .sub-title {
        color: #94A3B8;
        font-size: 1.15rem;
        margin-bottom: 2rem;
        font-weight: 300;
    }
    
    /* 커스텀 논문 카드 디자인 */
    .paper-card {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
        transition: all 0.3s ease;
    }
    .paper-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(168, 85, 247, 0.15);
        border-color: rgba(168, 85, 247, 0.3);
    }
    
    .paper-header {
        font-size: 1.35rem;
        font-weight: 600;
        color: #F8FAFC;
        line-height: 1.4;
        margin-bottom: 0.6rem;
    }
    
    .paper-author {
        font-size: 0.95rem;
        color: #E2E8F0;
        font-style: italic;
        margin-bottom: 0.4rem;
    }
    
    .paper-meta-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        align-items: center;
        font-size: 0.85rem;
        color: #94A3B8;
        margin-bottom: 0.8rem;
    }
    
    .custom-badge {
        background: rgba(168, 85, 247, 0.15);
        color: #D8B4FE;
        border: 1px solid rgba(168, 85, 247, 0.3);
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.75rem;
        text-transform: uppercase;
    }
    
    .journal-badge {
        background: rgba(99, 102, 241, 0.15);
        color: #C7D2FE;
        border: 1px solid rgba(99, 102, 241, 0.3);
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.75rem;
    }

    /* 링크 스타일 */
    .paper-link {
        color: #F472B6 !important;
        text-decoration: none !important;
        font-weight: 500;
        transition: color 0.2s ease;
    }
    .paper-link:hover {
        color: #EC4899 !important;
        text-decoration: underline !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 2. 애플리케이션 상태 초기화 (Session State)
# ==============================================================================
if "search_results" not in st.session_state:
    st.session_state.search_results = []
if "has_searched" not in st.session_state:
    st.session_state.has_searched = False
if "error_message" not in st.session_state:
    st.session_state.error_message = None

# ==============================================================================
# 3. Sidebar UI (설정 및 API 인증 정보)
# ==============================================================================
st.sidebar.markdown("<h2 style='font-family:Outfit;'>⚙️ Search Configuration</h2>", unsafe_allow_html=True)

# API 키 입력
api_key = st.sidebar.text_input(
    "NCBI API Key (Optional)",
    type="password",
    help="기입 시 속도 제한이 초당 3회에서 10회로 상향되어 더 쾌적하게 동작합니다.",
    key="ncbi_api_key_input"
)

# 정렬 기준
sort_options = {
    "Relevance (관련성 높은 순)": "relevance",
    "Publication Date (최신순)": "pub_date",
    "Author (저자 이름순)": "Author",
    "Journal (저널 이름순)": "JournalName",
    "Title (제목순)": "Title"
}
sort_by_label = st.sidebar.selectbox("Sort By", options=list(sort_options.keys()), index=0)
sort_by_value = sort_options[sort_by_label]

# 최대 검색 개수
max_results = st.sidebar.slider(
    "Max Results",
    min_value=5,
    max_value=100,
    value=20,
    step=5,
    help="검색 시 최대로 가져올 논문의 개수입니다."
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    <div style='font-size: 0.85rem; color: #94A3B8;'>
        <b>NCBI PubMed API</b>를 활용하여 의생명과학 논문 데이터를 실시간 검색합니다.<br><br>
        <i>Disclaimer:</i> 검색된 모든 논문의 저작권 및 사용조건은 각 논문의 출판 라이선스를 따릅니다.
    </div>
    """,
    unsafe_allow_html=True
)

# ==============================================================================
# 4. Main UI Header
# ==============================================================================
st.markdown("<h1 id='main-title' class='main-title'>🧬 PubMed Scholar Search</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-title'>의학 및 생명과학 연구 논문을 간편하게 검색하고 분석하는 대시보드</p>", unsafe_allow_html=True)

# ==============================================================================
# 5. 검색 컨트롤 영역
# ==============================================================================
col1, col2 = st.columns([5, 1])
with col1:
    search_query = st.text_input(
        "Search Query",
        placeholder="예: cancer immunotherapy, BRCA1, COVID-19 mRNA vaccine...",
        label_visibility="collapsed",
        key="search_query_input"
    )
with col2:
    search_button = st.button("Search", use_container_width=True, type="primary", key="search_btn")

# 검색 실행 로직
if search_button and search_query.strip():
    with st.spinner("PubMed 데이터베이스에서 논문을 검색 중입니다..."):
        try:
            st.session_state.error_message = None
            # 1단계: PMID 목록 조회
            pmids = search_pubmed(
                query=search_query,
                max_results=max_results,
                sort_by=sort_by_value,
                api_key=api_key
            )
            
            if pmids:
                # 2단계: 논문 세부 정보 획득
                articles = fetch_article_abstracts(pmids=pmids, api_key=api_key)
                st.session_state.search_results = articles
            else:
                st.session_state.search_results = []
            
            st.session_state.has_searched = True
        except Exception as e:
            st.session_state.error_message = str(e)
            st.session_state.search_results = []
            st.session_state.has_searched = True

# ==============================================================================
# 6. 결과 출력 & 분석 영역
# ==============================================================================
if st.session_state.error_message:
    st.error(f"⚠️ 검색을 수행하는 도중 오류가 발생했습니다:\n{st.session_state.error_message}")

elif st.session_state.has_searched:
    results = st.session_state.search_results
    
    if not results:
        st.warning("🔍 검색 조건에 일치하는 논문을 찾을 수 없습니다. 다른 검색어로 시도해보세요.")
    else:
        # 데이터프레임으로 변환 (필터링 및 분석용)
        df = pd.DataFrame(results)
        
        # 연도(pubyear) 분석 및 결측값 제거
        df['pubyear_clean'] = pd.to_numeric(df['pubyear'], errors='coerce')
        valid_years = df['pubyear_clean'].dropna().astype(int)
        
        # 필터 레이아웃
        st.markdown("<h3 style='font-family:Outfit;'>📊 Search Analytics & Filtering</h3>", unsafe_allow_html=True)
        
        col_metrics, col_filter = st.columns([1, 2])
        
        with col_metrics:
            # 주요 메트릭
            st.metric("Total Found", len(results))
            
            # 연도 필터 범위 계산
            if not valid_years.empty:
                min_year = int(valid_years.min())
                max_year = int(valid_years.max())
            else:
                min_year = 2000
                max_year = 2026
                
            if min_year == max_year:
                min_year -= 1 # 슬라이더 에러 방지용 범위 설정
                
        with col_filter:
            # 연도 슬라이더 필터
            selected_years = st.slider(
                "Filter by Publication Year",
                min_value=min_year,
                max_value=max_year,
                value=(min_year, max_year)
            )

        # 연도 필터 적용
        if not valid_years.empty:
            filtered_df = df[
                (df['pubyear_clean'].isna()) |  # 연도 파싱 안 된 경우 제외하지 않기 위해 허용
                ((df['pubyear_clean'] >= selected_years[0]) & (df['pubyear_clean'] <= selected_years[1]))
            ]
        else:
            filtered_df = df
            
        # 1. 연도별 통계 차트 (막대 그래프)
        if not valid_years.empty:
            chart_data = filtered_df['pubyear_clean'].dropna().value_counts().sort_index().reset_index()
            chart_data.columns = ['Year', 'Paper Count']
            chart_data['Year'] = chart_data['Year'].astype(str)
            
            # 깔끔하게 커스텀 차트 표시
            st.bar_chart(chart_data.set_index('Year'), height=150, color="#8B5CF6")
            
        # 2. CSV 내보내기 버튼 구성
        # 다운로드용 DataFrame 정제
        download_df = filtered_df.drop(columns=['pubyear_clean'])
        csv_data = download_df.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📥 Export Filtered Results to CSV",
            data=csv_data,
            file_name=f"pubmed_results_{search_query.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        st.markdown("<h3 style='font-family:Outfit; margin-top: 1.5rem;'>📝 Paper List</h3>", unsafe_allow_html=True)
        st.caption(f"Showing {len(filtered_df)} papers after filtering")
        
        # 3. 논문 카드 목록 렌더링
        for idx, row in filtered_df.iterrows():
            pmid = row['pmid']
            title = row['title'] or "No Title Available"
            authors = row['authors']
            journal = row['journal']
            pubdate = row['pubdate']
            doi = row['doi']
            abstract = row['abstract']
            
            # 카드 박스 HTML & 아코디언 컴포넌트
            # Streamlit Expander 안에 예쁜 카드 마크다운 형식으로 감쌈
            meta_str = f"<span class='custom-badge'>PMID: {pmid}</span>"
            if doi:
                meta_str += f"<span class='custom-badge'>DOI: {doi}</span>"
            if journal:
                meta_str += f"<span class='journal-badge'>{journal}</span>"
            meta_str += f" &nbsp;•&nbsp; 🗓️ {pubdate}"
            
            expander_title = f"[{pubdate.split(' ')[0]}] {title} - {authors.split(',')[0]} 등"
            
            with st.expander(expander_title, expanded=False):
                # 카드 내부 상세 정보 표기
                st.markdown(
                    f"""
                    <div style="margin-bottom: 0.5rem;">
                        <h4 style="margin: 0 0 0.5rem 0; color: #F1F5F9; font-size:1.2rem;">{title}</h4>
                        <div class="paper-author">{authors}</div>
                        <div class="paper-meta-row" style="margin-top: 0.5rem;">{meta_str}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # DOI/PMID 직접 바로가기 버튼 링크
                col_links = st.columns([1, 1, 4])
                with col_links[0]:
                    st.markdown(f"<a href='https://pubmed.ncbi.nlm.nih.gov/{pmid}/' target='_blank' class='paper-link'>🔗 PubMed Link</a>", unsafe_allow_html=True)
                with col_links[1]:
                    if doi:
                        st.markdown(f"<a href='https://doi.org/{doi}' target='_blank' class='paper-link'>🔗 DOI Link</a>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='color: #64748B; font-size: 0.9rem;'>No DOI Link</span>", unsafe_allow_html=True)
                
                st.markdown("---")
                st.markdown("**Abstract**")
                # 줄바꿈 유지
                st.write(abstract)
else:
    # 검색 전 상태 표시 (가이드라인 카드 제공)
    st.info("💡 사이드바의 설정을 조절하고 상단 검색창에 키워드를 입력해 PubMed 논문 검색을 시작해 보세요!")
    
    # 추천 키워드 영역
    st.markdown("<h3 style='font-family:Outfit; margin-top: 2rem;'>💡 Recommended Search Topics</h3>", unsafe_allow_html=True)
    col_rec1, col_rec2, col_rec3 = st.columns(3)
    
    with col_rec1:
        st.markdown(
            """
            <div class="paper-card">
                <h5>🧬 CRISPR Gene Editing</h5>
                <p style="font-size:0.85rem; color:#94A3B8; margin-bottom: 0px;">
                    CRISPR-Cas9 기술을 활용한 유전자 편집 치료 및 최신 연구 동향 검색
                </p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    with col_rec2:
        st.markdown(
            """
            <div class="paper-card">
                <h5>🧪 Cancer Immunotherapy</h5>
                <p style="font-size:0.85rem; color:#94A3B8; margin-bottom: 0px;">
                    면역관문 억제제(Checkpoint Inhibitors) 및 CAR-T 면역 치료 최신 지식 탐색
                </p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    with col_rec3:
        st.markdown(
            """
            <div class="paper-card">
                <h5>🧠 Alzheimer Disease</h5>
                <p style="font-size:0.85rem; color:#94A3B8; margin-bottom: 0px;">
                    알츠하이머 병의 병리학적 메커니즘 및 차세대 타겟 신약 후보 물질 검색
                </p>
            </div>
            """, 
            unsafe_allow_html=True
        )
