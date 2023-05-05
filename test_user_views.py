"""User View tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_user_views.py


import os
from unittest import TestCase

from models import db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ["DATABASE_URL"] = "postgresql:///warbler_test"

# Now we can import app

from app import app, CURR_USER_KEY

app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False

# This is a bit of hack, but don't use Flask DebugToolbar

app.config["DEBUG_TB_HOSTS"] = ["dont-show-debug-toolbar"]

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config["WTF_CSRF_ENABLED"] = False


class UserBaseViewTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)
        db.session.flush()

        m1 = Message(text="m1-text", user_id=u1.id)
        m2 = Message(text="m2-text", user_id=u2.id)

        db.session.add_all([m1, m2])
        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id
        self.m1_id = m1.id
        self.m2_id = m2.id

        self.client = app.test_client()


class UserAuthTestCase(UserBaseViewTestCase):
    def test_anon_get_homepage(self):
        with self.client as c:
            resp = c.get("/")

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<!-- home-anon template id -->", html)

    def test_anon_get_login(self):
        with self.client as c:
            resp = c.get("/login")

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<!-- login template id -->", html)

    def test_logged_in_get_homepage(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get("/")

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<!-- home template id -->", html)

    def test_do_login_success(self):
        with self.client as c:
            resp = c.post(
                "/login",
                data={"username": "u1", "password": "password"},
                follow_redirects=True,
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)

            self.assertIn("<!-- home template id -->", html)
            self.assertIn("Hello, u1", html)

    def test_do_login_failure(self):
        with self.client as c:
            # test with invalid password
            resp = c.post(
                "/login",
                data={"username": "u1", "password": "someabsolutenonsense"},
                follow_redirects=True,
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)

            self.assertIn("<!-- login template id -->", html)
            self.assertIn("Invalid credentials.", html)

            # test with invalid username
            resp = c.post(
                "/login",
                data={"username": "someabsolutenonsense", "password": "password"},
                follow_redirects=True,
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)

            self.assertIn("<!-- login template id -->", html)
            self.assertIn("Invalid credentials.", html)

    def test_anon_view_profile(self):
        with self.client as c:
            resp = c.get("/users/1", follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<!-- home-anon template id -->", html)
            self.assertIn("Access unauthorized.", html)

    def test_logged_view_profile(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id
            resp = c.get(f"/users/{self.u1_id}", follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<!-- show template id -->", html)
            self.assertIn("@u1", html)

            # FIXME: test follow/unfollow


class UserFollowTestCase(UserBaseViewTestCase):
    def test_follow_user(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(f"/users/follow/{self.u2_id}", follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)

            self.assertIn("<!-- users-following template id -->", html)
            self.assertIn("@u2", html)
            self.assertIn("Unfollow", html)

    def test_stop_following_user(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            c.post(f"/users/follow/{self.u2_id}", follow_redirects=True)

            resp = c.post(f"/users/stop-following/{self.u2_id}", follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)

            self.assertIn("<!-- users-following template id -->", html)
            self.assertNotIn("@u2", html)
            self.assertNotIn("Unfollow", html)


class UserEditProfileTestCase(UserBaseViewTestCase):
    def test_get_edit_page(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            # (this is actually the edit route: )
            resp = c.get("/users/profile")

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<!-- user edit template id -->", html)
            self.assertIn("u1", html)
            self.assertIn("u1@email.com", html)

    def test_edit_profile_success(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            # (this is actually the edit route: )
            resp = c.post(
                "/users/profile",
                data={
                    "username": "Test1234",
                    "email": "test@gmail.com",
                    "image_url": "",
                    "header_image_url": "",
                    "bio": "",
                    "password": "password",
                },
                follow_redirects=True,
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("<!-- user edit template id -->", html)
            self.assertIn("Test1234", html)

    def test_edit_profile_wrong_password(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            # (this is actually the edit route: )
            resp = c.post(
                "/users/profile",
                data={
                    "username": "Test1234",
                    "email": "test@gmail.com",
                    "image_url": "",
                    "header_image_url": "",
                    "bio": "",
                    "password": "absolutenonsense",
                },
                follow_redirects=True,
            )

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<!-- user edit template id -->", html)

            # new username should still be in the form
            self.assertIn("Test1234", html)
            self.assertIn("Invalid Password", html)