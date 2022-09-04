from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User
from .utils import paginator_page

CACHE_TIME = 20


@cache_page(CACHE_TIME, key_prefix='index_page')
@vary_on_cookie
def index(request):
    posts = Post.objects.all()
    template = 'posts/index.html'
    page_obj = paginator_page(request, posts)
    context = {
        'posts': posts,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = Post.objects.all()
    page_obj = paginator_page(request, posts)
    context = {
        'group': group,
        'posts': posts,
        'page_obj': page_obj,
    }
    template = 'posts/group_list.html'
    return render(request, template, context)


def profile(request, username):
    template = 'posts/profile.html'
    user_author = get_object_or_404(User, username=username)
    posts = Post.objects.filter(author=user_author)
    user_profile = User.objects.get(username=username)
    page_obj = paginator_page(request, posts)
    following = Follow.objects.filter(
        author=user_author.id,
        user=request.user.id
    ).exists()
    context = {
        'author': user_author,
        'posts': posts,
        'page_obj': page_obj,
        'user_profile': user_profile,
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    author = post.author
    template = 'posts/post_detail.html'
    form = CommentForm(request.POST or None)
    comment = post.comments.all()
    context = {
        'post': post,
        'author': author,
        'form': form,
        'comment': comment,
    }
    return render(request, template, context)


def post_create(request):
    template = 'posts/create_post.html'
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=post.author)
    context = {
        'form': form
    }
    return render(request, template, context)


def post_edit(request, post_id):
    template = 'posts/create_post.html'
    post = get_object_or_404(Post, pk=post_id)
    if request.method == 'POST':
        form = PostForm(
            request.POST or None,
            files=request.FILES or None,
            instance=post,
        )
        if form.is_valid():
            post = form.save()
            post.author = request.user
            return redirect('posts:post_detail', post_id)
    else:
        form = PostForm(instance=post)
        context = {
            'form': form,
            'post': post,
            'post_id': post_id,
            'is_edit': True,
        }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


def follow_index(request):
    if not request.user.is_authenticated:
        return redirect('/auth/login', request.user.username)
    post_list = Post.objects.filter(author__following__user=request.user)
    page_obj = paginator_page(request, post_list)
    template = 'posts/index.html'
    context = {'page_obj': page_obj}
    return render(request, template, context)


def profile_follow(request, username):
    if not request.user.is_authenticated:
        return redirect('/auth/login', request.user.username)
    user = request.user
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(
            user=user,
            author=author
        )
    return redirect('posts:profile', username)


def profile_unfollow(request, username):
    if not request.user.is_authenticated:
        return redirect('/auth/login', request.user.username)
    follow = Follow.objects.filter(
        user=request.user.id,
        author=get_object_or_404(User, username=username)
    )
    follow.delete()
    return redirect('posts:profile', username)
