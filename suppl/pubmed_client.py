import time
import xml.etree.ElementTree as ET
import requests

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# 글로벌 변수를 활용하여 마지막 요청 시간을 기록하여 Rate Limit를 자동 조절합니다.
_LAST_REQUEST_TIME = 0.0

def _wait_for_rate_limit(api_key: str = None):
    """
    NCBI API 호출 제한을 준수하기 위한 딜레이 처리 함수입니다.
    - API Key가 없을 경우: 초당 최대 3회 (요청 간격 최소 0.35초)
    - API Key가 있을 경우: 초당 최대 10회 (요청 간격 최소 0.1초)
    """
    global _LAST_REQUEST_TIME
    min_delay = 0.1 if api_key else 0.35
    elapsed = time.time() - _LAST_REQUEST_TIME
    if elapsed < min_delay:
        time.sleep(min_delay - elapsed)
    _LAST_REQUEST_TIME = time.time()

def _get_api_params(api_key: str = None) -> dict:
    """NCBI API 공통 파라미터를 생성합니다."""
    params = {}
    if api_key and api_key.strip():
        params["api_key"] = api_key.strip()
    return params

def search_pubmed(
    query: str,
    max_results: int = 10,
    sort_by: str = "relevance",
    api_key: str = None
) -> list[str]:
    """
    주어진 쿼리에 부합하는 PubMed ID(PMID) 목록을 검색하여 반환합니다.
    
    Args:
        query: 검색어 (Boolean 연산자 및 MeSH term 지원)
        max_results: 검색 결과 최대 개수
        sort_by: 정렬 기준 ('relevance', 'pub_date', 'Author', 'JournalName', 'Title')
        api_key: NCBI API 키 (선택 사항)
    
    Returns:
        PMID 문자열 리스트
    """
    if not query.strip():
        return []
        
    _wait_for_rate_limit(api_key)
    
    # E-utility 정렬 기준 이름 맵핑
    # (PubMed e-utilities는 pub_date 외에도 'pub_date', 'relevance' 등을 지원)
    url = f"{EUTILS_BASE}/esearch.fcgi"
    params = _get_api_params(api_key) | {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "sort": sort_by,
        "retmode": "json"
    }
    
    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if "esearchresult" in data and "idlist" in data["esearchresult"]:
            return data["esearchresult"]["idlist"]
        return []
    except Exception as e:
        # 에러 발생 시 UI에서 처리할 수 있도록 빈 리스트 반환 혹은 예외 전파
        raise RuntimeError(f"PubMed 검색 중 오류가 발생했습니다: {str(e)}")

def fetch_article_abstracts(
    pmids: list[str],
    api_key: str = None
) -> list[dict]:
    """
    PMID 목록에 해당하는 논문들의 상세 메타데이터 및 초록을 가져옵니다.
    
    Args:
        pmids: PMID 문자열 리스트
        api_key: NCBI API 키 (선택 사항)
        
    Returns:
        논문 정보 딕셔너리 리스트
    """
    if not pmids:
        return []
        
    _wait_for_rate_limit(api_key)
    
    url = f"{EUTILS_BASE}/efetch.fcgi"
    params = _get_api_params(api_key) | {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract"
    }
    
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        xml_data = response.content
    except Exception as e:
        raise RuntimeError(f"PubMed 논문 상세 정보를 가져오는 중 오류가 발생했습니다: {str(e)}")

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        raise RuntimeError("NCBI EFetch XML 데이터를 파싱하는 데 실패했습니다.")

    results = []
    for article in root.iter("PubmedArticle"):
        pmid_elem = article.find(".//PMID")
        if pmid_elem is None:
            continue

        art = article.find(".//Article")
        if art is None:
            continue

        # 저자 목록 파싱
        authors = []
        for author in art.findall(".//AuthorList/Author"):
            last = author.findtext("LastName") or ""
            init = author.findtext("Initials") or ""
            name = f"{last} {init}".strip() if last else author.findtext("CollectiveName") or ""
            if name:
                authors.append(name)

        # 초록 파싱 (Structured abstract 지원 포함)
        abstract_parts = []
        for at in art.findall(".//Abstract/AbstractText"):
            label = at.get("Label")
            text = "".join(at.itertext())
            if label:
                abstract_parts.append(f"{label}: {text}")
            else:
                abstract_parts.append(text)
        abstract = "\n".join(abstract_parts) if abstract_parts else ""

        # DOI 찾기
        doi = None
        for eid in art.findall("ELocationID"):
            if eid.get("EIdType") == "doi":
                doi = eid.text
                break
        
        # 만약 ELocationID에 없으면 ArticleIdList에서 검색
        if not doi:
            for art_id in article.findall(".//ArticleIdList/ArticleId"):
                if art_id.get("IdType") == "doi":
                    doi = art_id.text
                    break

        # 저널 및 출판일 파싱
        journal_elem = art.find(".//Journal")
        journal = None
        pubdate = None
        pubyear = None
        if journal_elem is not None:
            journal = journal_elem.findtext("Title")
            pd = journal_elem.find(".//PubDate")
            if pd is not None:
                year = pd.findtext("Year") or ""
                month = pd.findtext("Month") or ""
                day = pd.findtext("Day") or ""
                medline = pd.findtext("MedlineDate") or ""
                pubdate = f"{year} {month} {day}".strip() if year else medline
                
                # 연도 필터링을 위한 연도 파싱 시도 (숫자 4자리 추출)
                if year:
                    pubyear = year
                elif medline:
                    import re
                    match = re.search(r"\b(19|20)\d{2}\b", medline)
                    if match:
                        pubyear = match.group(0)

        results.append({
            "pmid": pmid_elem.text,
            "title": art.findtext("ArticleTitle"),
            "authors": ", ".join(authors) if authors else "Unknown Authors",
            "journal": journal or "Unknown Journal",
            "pubdate": pubdate or "Unknown Date",
            "pubyear": pubyear,
            "doi": doi or "",
            "abstract": abstract or "No abstract available."
        })

    return results
