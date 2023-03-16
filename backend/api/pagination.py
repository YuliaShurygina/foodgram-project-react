from rest_framework.pagination import PageNumberPagination
from backend.settings import DEFAULT_RECIPES_LIMIT


class CustomPageNumberPagination(PageNumberPagination):
    page_size_query_param = "limit"
    page_size = DEFAULT_RECIPES_LIMIT
