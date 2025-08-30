"""JCYL Explore API v2.1 client."""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def clean_html_text(text: str) -> str:
    """Remove HTML tags and clean up text."""
    if not text or text == "Dato no disponible":
        return text
    
    # Remove HTML tags
    clean = re.sub('<[^<]+?>', '', text)
    
    # Replace common HTML entities
    replacements = {
        '&nbsp;': ' ',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
        '&apos;': "'"
    }
    
    for entity, char in replacements.items():
        clean = clean.replace(entity, char)
    
    # Clean up multiple whitespaces and newlines
    clean = re.sub(r'\s+', ' ', clean)
    clean = clean.strip()
    
    return clean


def format_user_friendly_date(date_string: str) -> str:
    """Convert API date format to user-friendly format."""
    if not date_string or date_string == "Dato no disponible":
        return "Dato no disponible"
    
    try:
        # Parse ISO format: 2025-08-12T11:14:26.781000+00:00
        if 'T' in date_string:
            # Remove timezone and microseconds for simpler parsing
            date_part = date_string.split('T')[0]
            dt = datetime.strptime(date_part, '%Y-%m-%d')
        else:
            # Handle simple date format: 2025-08-12
            dt = datetime.strptime(date_string[:10], '%Y-%m-%d')
        
        # Format to Spanish date format
        months = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]
        
        day = dt.day
        month = months[dt.month - 1]
        year = dt.year
        
        return f"{day} de {month} de {year}"
        
    except (ValueError, IndexError) as e:
        logger.warning(f"Could not parse date '{date_string}': {e}")
        # Fallback: return just the date part if available
        if len(date_string) >= 10:
            return date_string[:10]
        return "Fecha no disponible"


class Dataset(BaseModel):
    dataset_id: str
    title: str = Field(default="Dato no disponible")
    description: Optional[str] = Field(default="Dato no disponible")
    publisher: Optional[str] = Field(default="Dato no disponible")
    license: Optional[str] = Field(default="Dato no disponible")
    modified: Optional[str] = Field(default="Dato no disponible")
    data_processed: Optional[str] = Field(default="Dato no disponible")
    metadata_processed: Optional[str] = Field(default="Dato no disponible")
    records_count: Optional[int] = Field(default=0)
    themes: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


def create_dataset_from_api(data: dict) -> Dataset:
    """Create Dataset from API response data."""
    metas = data.get("metas", {}).get("default", {})
    
    # Helper function to get string value
    def get_string_value(field_data, default="Dato no disponible"):
        if isinstance(field_data, str):
            return clean_html_text(field_data)
        elif isinstance(field_data, list) and field_data:
            return clean_html_text(field_data[0])
        return default
    
    # Helper function to get list value
    def get_list_value(field_data, default=None):
        if default is None:
            default = []
        if isinstance(field_data, list):
            return field_data
        elif isinstance(field_data, str):
            return [field_data]
        return default
    
    return Dataset(
        dataset_id=data.get("dataset_id", ""),
        title=get_string_value(metas.get("title")),
        description=get_string_value(metas.get("description")),
        publisher=get_string_value(metas.get("publisher")),
        license=get_string_value(metas.get("license")),
        modified=metas.get("modified", "Dato no disponible"),
        data_processed=metas.get("data_processed", "Dato no disponible"),
        metadata_processed=metas.get("metadata_processed", "Dato no disponible"),
        records_count=metas.get("records_count", 0),
        themes=get_list_value(metas.get("theme")),
        keywords=get_list_value(metas.get("keyword"))
    )


class Facet(BaseModel):
    name: str
    count: int


class ExportFormat(BaseModel):
    format: str
    url: str


class Attachment(BaseModel):
    href: str
    title: Optional[str] = Field(default="Dato no disponible")
    description: Optional[str] = Field(default="Dato no disponible")


class JCYLAPIClient:
    def __init__(self, base_url: str = "https://analisis.datosabiertos.jcyl.es"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        # Simple cache to store consistent totals per theme/search
        self._total_cache = {}

    async def close(self) -> None:
        await self.client.aclose()

    def _build_url(self, path: str) -> str:
        return urljoin(self.base_url, path)

    async def _get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            raise

    async def get_catalog_facets(self, facet: str, refine: Optional[Dict[str, str]] = None) -> List[Facet]:
        url = self._build_url("/api/explore/v2.1/catalog/facets")
        params = {"facet": facet, "lang": "es"}
        
        if refine:
            for key, value in refine.items():
                params[f"refine.{key}"] = value

        try:
            data = await self._get(url, params)
            facets = []
            for facet_data in data.get("facets", []):
                if facet_data.get("name") == facet:
                    for facet_item in facet_data.get("facets", []):
                        facets.append(Facet(
                            name=facet_item.get("name", "Dato no disponible"),
                            count=facet_item.get("count", 0)
                        ))
                    break
            return facets
        except Exception as e:
            logger.error(f"Error getting facets for {facet}: {e}")
            return []

    async def get_themes(self) -> List[Facet]:
        return await self.get_catalog_facets("default.theme")
    
    async def get_themes_with_real_counts(self) -> List[Facet]:
        """Get themes with accurate counts based on actual filterable datasets."""
        # First get the theme names from facets
        theme_facets = await self.get_catalog_facets("default.theme")
        
        # Then calculate real counts for each theme
        corrected_themes = []
        for theme_facet in theme_facets:
            try:
                # Get actual count for this theme
                datasets, real_count = await self.get_datasets(theme=theme_facet.name, limit=1, offset=0)
                # Create corrected facet with real count
                corrected_theme = Facet(name=theme_facet.name, count=real_count)
                corrected_themes.append(corrected_theme)
                logger.info(f"Theme '{theme_facet.name}': API facet={theme_facet.count}, real={real_count}")
            except Exception as e:
                logger.warning(f"Could not get real count for theme '{theme_facet.name}': {e}")
                # Fallback to original facet count
                corrected_themes.append(theme_facet)
        
        # Sort by count (descending) like the original
        corrected_themes.sort(key=lambda x: x.count, reverse=True)
        return corrected_themes

    async def get_keywords(self, theme: Optional[str] = None) -> List[Facet]:
        refine = {"default.theme": theme} if theme else None
        return await self.get_catalog_facets("default.keyword", refine)

    async def get_datasets(
        self, 
        theme: Optional[str] = None, 
        keyword: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        order_by: str = "-metadata_processed",
        search: Optional[str] = None
    ) -> tuple[List[Dataset], int]:
        url = self._build_url("/api/explore/v2.1/catalog/datasets")
        
        # When filtering by theme or search, we need multiple API calls to get enough results
        # since API filtering is broken and we filter client-side
        max_api_limit = 100  # API limit we discovered through testing
        
        if theme or search:
            # Create cache key for this specific query
            cache_key = f"total_{theme or 'no_theme'}_{search or 'no_search'}_{keyword or 'no_keyword'}"
            
            # Check if we already have a cached total for this query
            if cache_key in self._total_cache and offset == 0:
                # For first page, we might already have the total cached
                # But we still need to collect data for this specific page
                logger.info(f"Found cached total for {cache_key}: {self._total_cache[cache_key]}")
            
            # For filtered requests, we'll make multiple API calls to collect enough results
            all_matching_datasets = []
            current_offset = 0
            target_datasets = limit + offset  # Total we need including offset
            
            while len(all_matching_datasets) < target_datasets and current_offset < 1000:  # Safety limit
                params = {
                    "lang": "es",
                    "limit": max_api_limit,
                    "offset": current_offset,
                    "order_by": order_by
                }
                
                if keyword:
                    params["refine.default.keyword"] = keyword
                
                try:
                    logger.info(f"Fetching batch: offset={current_offset}, limit={max_api_limit}")
                    data = await self._get(url, params)
                    batch_results = data.get("results", [])
                    total_count = data.get('total_count', 0)
                    
                    if not batch_results:
                        break  # No more results
                    
                    # Filter this batch
                    batch_matching = []
                    for dataset_data in batch_results:
                        try:
                            dataset = create_dataset_from_api(dataset_data)
                            
                            # Validation
                            if not dataset.dataset_id or len(dataset.dataset_id) > 200:
                                continue
                            
                            # Theme filtering - only include if theme matches exactly
                            if theme:
                                if not dataset.themes:
                                    # Skip datasets with no themes - they don't belong to any category
                                    continue
                                    
                                theme_lower = theme.lower()
                                dataset_themes_lower = [t.lower() for t in dataset.themes]
                                
                                matches = False
                                for dataset_theme in dataset_themes_lower:
                                    if (theme_lower in dataset_theme or 
                                        dataset_theme in theme_lower or
                                        theme_lower == dataset_theme):
                                        matches = True
                                        break
                                
                                if not matches:
                                    # Fuzzy matching for common variations
                                    fuzzy_matches = {
                                        'sector público': ['sector', 'publico', 'gobierno', 'administracion'],
                                        'salud': ['sanidad', 'sanitario', 'hospital', 'medico'],
                                        'educación': ['educacion', 'escolar', 'universidad', 'formacion'],
                                        'medio ambiente': ['medioambiente', 'ambiental', 'ecologia', 'sostenible'],
                                        'transporte': ['vehiculo', 'carretera', 'movilidad'],
                                        'energía': ['energia', 'electrico', 'renovable', 'consumo'],
                                    }
                                    
                                    for category, keywords_list in fuzzy_matches.items():
                                        if theme_lower == category.lower():
                                            for kw in keywords_list:
                                                for dataset_theme in dataset_themes_lower:
                                                    if kw in dataset_theme:
                                                        matches = True
                                                        break
                                                if matches:
                                                    break
                                            if matches:
                                                break
                                
                                if not matches:
                                    continue
                            
                            # Search filtering - Enhanced search with synonyms
                            if search:
                                search_lower = search.lower()
                                searchable_text = " ".join([
                                    dataset.title.lower() if dataset.title else "",
                                    dataset.description.lower() if dataset.description else "",
                                    " ".join(dataset.keywords).lower() if dataset.keywords else "",
                                    " ".join(dataset.themes).lower() if dataset.themes else "",
                                    dataset.publisher.lower() if dataset.publisher else ""
                                ])
                                
                                # Synonym/related terms mapping for better search
                                synonym_map = {
                                    'clinica': ['salud', 'medicina', 'hospital', 'sanitario', 'medico'],
                                    'clínica': ['salud', 'medicina', 'hospital', 'sanitario', 'medico'],
                                    'hospital': ['salud', 'medicina', 'clinica', 'sanitario', 'medico'],
                                    'medicina': ['salud', 'clinica', 'hospital', 'sanitario', 'medico'],
                                    'medico': ['salud', 'medicina', 'clinica', 'hospital', 'sanitario'],
                                    'sanitario': ['salud', 'medicina', 'clinica', 'hospital', 'medico'],
                                    'escuela': ['educacion', 'educativo', 'enseñanza', 'colegio', 'instituto'],
                                    'colegio': ['educacion', 'educativo', 'enseñanza', 'escuela', 'instituto'],
                                    'universidad': ['educacion', 'educativo', 'enseñanza', 'universitario'],
                                    'trabajo': ['empleo', 'laboral', 'ocupacion', 'profesional'],
                                    'empleo': ['trabajo', 'laboral', 'ocupacion', 'profesional'],
                                    'transporte': ['movilidad', 'vehiculo', 'autobus', 'tren', 'carretera'],
                                    'economia': ['economico', 'financiero', 'presupuesto', 'gasto', 'inversion'],
                                    'turismo': ['turistico', 'hotel', 'alojamiento', 'visitante']
                                }
                                
                                # Get all search terms including synonyms
                                all_search_terms = search_lower.split()
                                for term in search_lower.split():
                                    if term in synonym_map:
                                        all_search_terms.extend(synonym_map[term])
                                
                                found_match = False
                                
                                # 1. Check for exact phrase match (highest priority)
                                if search_lower in searchable_text:
                                    found_match = True
                                # 2. Check if all original terms are present (high priority)  
                                elif all(term in searchable_text for term in search_lower.split()):
                                    found_match = True
                                # 3. Check if any original term is present (medium priority)
                                elif any(term in searchable_text for term in search_lower.split()):
                                    found_match = True
                                # 4. Check synonyms (medium-low priority)
                                elif any(term in searchable_text for term in all_search_terms):
                                    found_match = True
                                # 5. Check for partial word matches (lowest priority)
                                else:
                                    for term in all_search_terms:
                                        if len(term) >= 3:  # Only for terms 3+ chars
                                            # Check if term is part of any word in searchable text
                                            words = searchable_text.split()
                                            if any(term in word for word in words):
                                                found_match = True
                                                break
                                
                                if not found_match:
                                    continue
                            
                            batch_matching.append(dataset)
                            
                        except Exception as e:
                            logger.warning(f"Skipping dataset due to parsing error: {e}")
                            continue
                    
                    all_matching_datasets.extend(batch_matching)
                    current_offset += max_api_limit
                    
                    logger.info(f"Batch complete: found {len(batch_matching)} matching datasets, total so far: {len(all_matching_datasets)}")
                    
                    # If this batch had very few results, we probably won't find many more
                    if len(batch_results) < max_api_limit:
                        break
                    
                except Exception as e:
                    logger.error(f"Error in batch fetch at offset {current_offset}: {e}")
                    break
            
            # Determine final total to return
            if cache_key in self._total_cache:
                # Use cached total for consistency across pages
                consistent_total = self._total_cache[cache_key]
                logger.info(f"Using cached total: {consistent_total} for {cache_key}")
            else:
                # Calculate total for the first time
                total_datasets_found = len(all_matching_datasets)
                
                # Check if we've likely found all datasets for this theme
                reached_end = (current_offset > 0 and len(batch_results) < max_api_limit)
                hit_safety_limit = (current_offset >= 1000)
                
                if reached_end or hit_safety_limit:
                    # We've scanned comprehensively, use exact count
                    consistent_total = total_datasets_found
                    logger.info(f"Complete scan finished: using exact count {consistent_total}")
                else:
                    # Still more data to scan, but make a conservative estimate
                    if current_offset > 0:
                        scan_ratio = total_datasets_found / current_offset
                        # Conservative estimate: assume we've seen at least 60% of matching datasets
                        min_total_estimate = int(total_datasets_found / 0.6)
                        api_based_estimate = int(total_count * scan_ratio * 0.9)
                        consistent_total = max(min_total_estimate, api_based_estimate, total_datasets_found)
                    else:
                        consistent_total = total_datasets_found
                    
                    logger.info(f"Partial scan: using conservative estimate {consistent_total} (found {total_datasets_found}, scanned {current_offset})")
                
                # Cache the calculated total for future requests
                self._total_cache[cache_key] = consistent_total
                logger.info(f"Cached total {consistent_total} for key: {cache_key}")
            
            # Apply pagination to our collected results
            paginated_datasets = all_matching_datasets[offset:offset + limit]
            
            logger.info(f"Filtered search complete: returning {len(paginated_datasets)} datasets, consistent total: {consistent_total}")
            return paginated_datasets, consistent_total
        
        else:
            # No filtering needed, use regular API call
            params = {
                "lang": "es",
                "limit": limit,
                "offset": offset,
                "order_by": order_by
            }
            
            if keyword:
                params["refine.default.keyword"] = keyword
            
            try:
                logger.info(f"Getting datasets with params: {params}")
                data = await self._get(url, params)
                total_count = data.get('total_count', 0)
                logger.info(f"API returned {total_count} total datasets, {len(data.get('results', []))} in this page")
                
                datasets = []
                for dataset_data in data.get("results", []):
                    try:
                        dataset = create_dataset_from_api(dataset_data)
                        if dataset.dataset_id and len(dataset.dataset_id) <= 200:
                            datasets.append(dataset)
                    except Exception as e:
                        logger.warning(f"Skipping dataset due to parsing error: {e}")
                        continue
                
                return datasets, total_count
            except Exception as e:
                logger.error(f"Error getting datasets: {e}")
                return [], 0

    async def get_dataset_info(self, dataset_id: str) -> Optional[Dataset]:
        url = self._build_url(f"/api/explore/v2.1/catalog/datasets/{dataset_id}")
        params = {"lang": "es"}

        try:
            data = await self._get(url, params)
            return create_dataset_from_api(data)
        except Exception as e:
            logger.error(f"Error getting dataset {dataset_id}: {e}")
            return None

    async def get_dataset_exports(self, dataset_id: str) -> List[ExportFormat]:
        url = self._build_url(f"/api/explore/v2.1/catalog/datasets/{dataset_id}/exports")
        try:
            data = await self._get(url)
            exports = []
            
            # The API returns links with rel attributes, not exports array
            links_data = data.get("links", [])
            
            for link in links_data:
                rel = link.get("rel", "")
                href = link.get("href", "")
                
                # Skip the 'self' link, process format links
                if rel and rel != "self" and href:
                    # rel contains the format name (csv, json, xlsx, etc.)
                    exports.append(ExportFormat(format=rel, url=href))
            
            return exports
        except Exception as e:
            logger.error(f"Error getting exports for dataset {dataset_id}: {e}")
            return []

    async def get_dataset_attachments(self, dataset_id: str) -> List[Attachment]:
        url = self._build_url(f"/api/explore/v2.1/catalog/datasets/{dataset_id}/attachments")
        
        try:
            data = await self._get(url)
            attachments = []
            for attachment_data in data.get("attachments", []):
                try:
                    attachment = Attachment(**attachment_data)
                    attachments.append(attachment)
                except Exception as e:
                    logger.warning(f"Error parsing attachment: {e}")
                    continue
            return attachments
        except Exception as e:
            logger.error(f"Error getting attachments for dataset {dataset_id}: {e}")
            return []

    async def get_dataset_records_count(self, dataset_id: str) -> int:
        url = self._build_url(f"/api/explore/v2.1/catalog/datasets/{dataset_id}/records")
        params = {"limit": 0, "select": "count(*)"}
        
        try:
            data = await self._get(url, params)
            return data.get("total_count", 0)
        except Exception as e:
            logger.error(f"Error getting records count for dataset {dataset_id}: {e}")
            return 0

    def get_dataset_web_url(self, dataset_id: str) -> str:
        return self._build_url(f"/explore/dataset/{dataset_id}")