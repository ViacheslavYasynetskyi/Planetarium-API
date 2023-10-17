import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from planetarium.models import AstronomyShow, ShowSession, PlanetariumDome, ShowTheme
from planetarium.serializers import (
    AstronomyShowListSerializer,
    AstronomyShowDetailSerializer,
)

ASTRONOMY_SHOW_URL = reverse("planetarium:astronomyshow-list")
SHOW_SESSION_URL = reverse("planetarium:showsession-list")


def sample_astronomy_show(**params):
    defaults = {
        "title": "test astronomy show",
        "description": "test description",
    }
    defaults.update(params)

    return AstronomyShow.objects.create(**defaults)


def sample_show_session(**params):
    planetarium_dome = PlanetariumDome.objects.create(
        name="dome 1", rows=8, seats_in_row=10
    )

    defaults = {
        "show_time": "2023-10-12 14:00:00",
        "astronomy_show": None,
        "planetarium_dome": planetarium_dome,
    }
    defaults.update(params)

    return ShowSession.objects.create(**defaults)


def image_upload_url(astronomy_show_id):
    """Return URL for recipe image upload"""
    return reverse("planetarium:astronomyshow-upload-image", args=[astronomy_show_id])


def detail_url(astronomy_show_id):
    return reverse("planetarium:astronomyshow-detail", args=[astronomy_show_id])


class UnauthenticatedAstronomyShowApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res = self.client.get(ASTRONOMY_SHOW_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedMovieApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "test@gmail.com",
            "testpassword",
        )
        self.client.force_authenticate(self.user)

    def test_list_movies(self):
        sample_astronomy_show()
        sample_astronomy_show()

        res = self.client.get(ASTRONOMY_SHOW_URL)

        movies = AstronomyShow.objects.order_by("id")
        serializer = AstronomyShowListSerializer(movies, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_filter_astronomy_show_by_show_theme(self):
        show_theme1 = ShowTheme.objects.create(name="ShowTheme 1")
        show_theme2 = ShowTheme.objects.create(name="ShowTheme 2")

        astronomy_show1 = sample_astronomy_show(title="Test Show 1")
        astronomy_show2 = sample_astronomy_show(title="Test Show 2")

        astronomy_show1.genres.add(show_theme1)
        astronomy_show2.genres.add(show_theme2)

        astronomy_show3 = sample_astronomy_show(
            title="Astronomy show without Show theme"
        )

        res = self.client.get(
            ASTRONOMY_SHOW_URL, {"genres": f"{show_theme1.id},{show_theme2.id}"}
        )

        serializer1 = AstronomyShowListSerializer(astronomy_show1)
        serializer2 = AstronomyShowListSerializer(astronomy_show2)
        serializer3 = AstronomyShowListSerializer(astronomy_show3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_filter_astronomy_shows_by_title(self):
        astronomy_show1 = sample_astronomy_show(title="Test title1")
        astronomy_show2 = sample_astronomy_show(title="Test title2")
        astronomy_show3 = sample_astronomy_show(title="No match")

        res = self.client.get(ASTRONOMY_SHOW_URL, {"title": "astronomyshow"})

        serializer1 = AstronomyShowListSerializer(astronomy_show1)
        serializer2 = AstronomyShowListSerializer(astronomy_show2)
        serializer3 = AstronomyShowListSerializer(astronomy_show3)

        self.assertIn(serializer1.data, res.data)
        self.assertIn(serializer2.data, res.data)
        self.assertNotIn(serializer3.data, res.data)

    def test_retrieve_astronomy_show_detail(self):
        astronomy_show = sample_astronomy_show()
        astronomy_show.genres.add(ShowTheme.objects.create(name="ShowTheme"))

        url = detail_url(astronomy_show.id)
        res = self.client.get(url)

        serializer = AstronomyShowDetailSerializer(astronomy_show)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_astronomy_show_forbidden(self):
        payload = {
            "title": "Test Astronomy Show",
            "description": "Test Description",
        }
        res = self.client.post(ASTRONOMY_SHOW_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAstronomyShowApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            "admin@gmail.com", "testpassword", is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_create_astronomy_show(self):
        payload = {
            "title": "Test Astronomy Show",
            "description": "Test Description",
        }
        res = self.client.post(ASTRONOMY_SHOW_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        astronomy_show = AstronomyShow.objects.get(id=res.data["id"])
        for key in payload.keys():
            self.assertEqual(payload[key], getattr(astronomy_show, key))

    def test_create_astronomy_show_with_show_themes(self):
        show_theme1 = ShowTheme.objects.create(name="Stars")
        show_theme2 = ShowTheme.objects.create(name="Sun")
        payload = {
            "title": "Andromeda",
            "show_theme": [show_theme1.id, show_theme2.id],
            "description": "About Andromeda galaxy",
        }
        res = self.client.post(ASTRONOMY_SHOW_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        astronomy_show = AstronomyShow.objects.get(id=res.data["id"])
        show_themes = astronomy_show.genres.all()
        self.assertEqual(show_themes.count(), 2)
        self.assertIn(show_theme1, show_themes)
        self.assertIn(show_theme2, show_themes)


class AstronomyShowImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.astronomy_show = sample_astronomy_show()
        self.show_session = sample_show_session(astronomy_show=self.astronomy_show)

    def tearDown(self):
        self.astronomy_show.image.delete()

    def test_upload_image_to_astronomy_show(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.astronomy_show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.astronomy_show.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.astronomy_show.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.astronomy_show.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_astronomy_show_list_should_not_work(self):
        url = ASTRONOMY_SHOW_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Test Astronomy Show",
                    "description": "Test Description",
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = AstronomyShow.objects.get(title="Test Astronomy Show")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_astronomy_show_detail(self):
        url = image_upload_url(self.astronomy_show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.astronomy_show.id))

        self.assertIn("image", res.data)

    def test_astronomy_show_url_is_shown_on_astronomy_show_list(self):
        url = image_upload_url(self.astronomy_show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(ASTRONOMY_SHOW_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_show_session_detail(self):
        url = image_upload_url(self.astronomy_show.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(SHOW_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())

    def test_put_astronomy_show_not_allowed(self):
        payload = {
            "title": "New astronomy_show",
            "description": "New description",
        }

        astronomy_show = sample_astronomy_show()
        url = detail_url(astronomy_show.id)

        res = self.client.put(url, payload)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_delete_astronomy_show_not_allowed(self):
        astronomy_show = sample_astronomy_show()
        url = detail_url(astronomy_show.id)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
