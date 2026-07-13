from app.services.indexing_service import IndexingService
from app.services.search_engine import SearchEngine


search_engine = SearchEngine()
indexing_service = IndexingService(search_engine)