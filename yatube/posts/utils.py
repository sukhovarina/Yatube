from django.core.paginator import Paginator

COUNT_POST_PAGE: int = 10


def paginator_page(request, posts):
    paginator = Paginator(posts, COUNT_POST_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
