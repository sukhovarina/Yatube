from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from posts.models import Comment, Follow, Group, Post

User = get_user_model()

TEST_POST_COUNT = 10


class PostViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.text_author = User.objects.create_user(username='text_author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.posts = [Post(
            author=cls.user,
            group=cls.group,
            text='Тестовый пост',
        ) for i in range(TEST_POST_COUNT)]
        Post.objects.bulk_create(cls.posts)
        cls.post = Post.objects.get(id=1)
        cls.client = Client()
        cls.client.force_login(cls.user)
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.follow_author = User.objects.create_user(username='follow-author')
        cls.template_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            (reverse(
                'posts:group_list', kwargs={'slug': f'{cls.group.slug}'}
            )): 'posts/group_list.html',
            (reverse(
                'posts:profile', kwargs={'username': f'{cls.user.username}'}
            )): 'posts/profile.html',
            (reverse(
                'posts:post_detail', kwargs={'post_id': f'{cls.post.id}'}
            )): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            (reverse(
                'posts:post_edit', kwargs={'post_id': f'{cls.post.id}'}
            )): 'posts/create_post.html',
        }

    def setUp(cls):
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in self.template_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        self.assertEqual(post_text_0, 'Тестовый пост')
        self.assertEqual(
            self.post.image,
            response.context['page_obj'][Post.objects.count() - 1].image
        )

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        ))
        first_object = response.context['page_obj'][0]
        post_author = first_object.author.username
        post_text = first_object.text
        post_group = first_object.group.title
        self.assertEqual(post_author, 'auth')
        self.assertEqual(post_text, 'Тестовый пост')
        self.assertEqual(post_group, 'Тестовая группа')
        self.assertEqual(
            self.post.image,
            response.context['page_obj'][Post.objects.count() - 1].image
        )

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
            reverse(
                'posts:profile', kwargs={'username': f'{PostViewsTest.user}'}
            )
        ))
        filter_posts = Post.objects.filter(author=self.user)
        context = response.context.get('posts')

        self.assertIsNotNone(context)
        self.assertEqual(context[0].text, self.post.text)
        self.assertEqual(context[0].author, self.post.author)
        self.assertEqual(context[0].group, self.post.group)
        self.assertEqual(
            filter_posts.count(), self.post.author.posts.count()
        )
        self.assertEqual(
            context[0].image,
            self.post.image,
        )

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        contexts = response.context['post']
        self.assertEqual(contexts, self.post)
        self.assertEqual(
            contexts.image,
            self.post.image
        )

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_field = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_field.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={
                'post_id': f'{self.post.id}'
            }
        ))
        form_field = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_field.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertTrue(response.context.get('is_edit'))
        self.assertEqual(response.context.get('post_id'), 1)

    def test_new_post_with_group_in_correct_pages(self):
        """Новый пост с группой отображается на правильных страницах"""
        new_group = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug-2',
            description='Тестовое описание 2',
        )
        new_post = Post.objects.create(
            author=self.user,
            text='Тестовый пост с новой группой',
            group=new_group,
        )
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertIn(new_post, response.context['page_obj'])
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': new_group.slug})
        )
        self.assertIn(new_post, response.context['page_obj'])
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        self.assertIn(new_post, response.context['page_obj'])

    def test_adding_comments_is_accessible_only_for_authorized_users(self):
        """Комментировать посты могут только авторизованные пользователи."""
        response = self.authorized_client.get(
            reverse(
                'posts:add_comment',
                kwargs={'post_id': self.post.id}
            )
        )
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_post_detail_shows_new_comment(self):
        """Комментарий появляется на странице поста."""
        comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            text='Тестовый текст комментария'
        )
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertIn(comment, response.context['comment'])

    def test_index_cache(self):
        """Шаблон страницы index хранит записи в кеше."""
        post_cache = Post.objects.create(
            author=self.user,
            text='Тестовый пост для проверки кеша',
        )
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        post_cache.delete()
        new_response = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertEqual(response.content, new_response.content)
        cache.clear()
        response_cleared = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(new_response.content, response_cleared.content)

    def test_follow_and_unfollow(self):
        """Авторизованный пользователь может
        подписываться на других пользователей."""
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.follow_author.username}
            )
        )
        self.assertTrue(
            Follow.objects.filter(
                user=self.user, author=self.follow_author
            ).exists()
        )

    def test_follow_and_unfollow_author(self):
        """Авторизованный пользователь может
        удалять авторов из подписок."""
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.follow_author.username}
            )
        )
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.follow_author.username}
            )
        )
        self.assertFalse(
            Follow.objects.filter(
                user=self.user, author=self.follow_author
            ).exists()
        )

    def test_new_post_in_correct_follow_pages(self):
        """Новая запись автора появляется в ленте подписчиков."""
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.follow_author.username}
        ))
        new_post = Post.objects.create(
            author=self.follow_author,
            text='Тестовый пост',
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertIn(new_post, response.context['page_obj'])

    def test_new_post_in_correct_follow_pages(self):
        """Новая запись автора не появляется в ленте тех, кто не подписан."""
        new_post = Post.objects.create(
            author=self.follow_author,
            text='Тестовый пост',
        )
        other_user = User.objects.create_user(username='other_user')
        other_authorized_client = Client()
        other_authorized_client.force_login(other_user)
        response = other_authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(new_post, response.context['page_obj'])


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test-author')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        TEST_POST_COUNT = 13
        posts = (
            Post(
                author=cls.user,
                text=f'Тестовый пост №{i}',
                group=cls.group) for i in range(TEST_POST_COUNT))
        Post.objects.bulk_create(posts)

    def test_pages_with_pagination_contain_ten_and_three_records(self):
        """Шаблоны страниц index, group_list, profile сформированы
        с правильным количеством записей."""
        pages_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        ]
        for reverse_name in pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertEqual(
                    len(response.context['page_obj']), settings.POSTS_NUMBER
                )
                response = self.authorized_client.get(reverse_name + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']),
                    Post.objects.count() - settings.POSTS_NUMBER
                )
