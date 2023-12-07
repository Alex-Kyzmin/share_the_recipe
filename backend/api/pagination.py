from rest_framework.pagination import PageNumberPagination


class ProjectPagination(PageNumberPagination):
    """Пагинация проекта."""
    page_size_query_param = "limit"
    max_page_size = 10
    page_size = 6
