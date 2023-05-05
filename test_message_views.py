"""Message View tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"

# Now we can import app

from app import app, CURR_USER_KEY

app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

# This is a bit of hack, but don't use Flask DebugToolbar

app.config['DEBUG_TB_HOSTS'] = ['dont-show-debug-toolbar']

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageBaseViewTestCase(TestCase):
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


class MessageAddViewTestCase(MessageBaseViewTestCase):
    def test_add_message(self):
        # Since we need to change the session to mimic logging in,
        # we need to use the changing-session trick:
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            # Now, that session setting is saved, so we can have
            # the rest of ours test
            resp = c.post("/messages/new", data={"text": "Hello"})

            self.assertEqual(resp.status_code, 302)

            Message.query.filter_by(text="Hello").one()

    def test_post_message_failure(self):
        with self.client as c:
            resp = c.post(
                "/messages/new",
                data={'text': 'test text 1234'},
                follow_redirects = True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)

            self.assertIn("<!-- home-anon template id -->", html)
            self.assertIn("Access unauthorized.", html)

    def test_post_message_success(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(
                "/messages/new",
                data={'text': 'test text 1234'},
                follow_redirects = True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)

            self.assertIn("<!-- show template id -->", html)
            self.assertIn("test text 1234", html)

class MessageDeleteTestCase(MessageBaseViewTestCase):

    def test_delete__message_logged_in(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        resp = c.post(
                f"/messages/{self.m1_id}/delete",
                follow_redirects = True)

        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("<!-- show template id -->", html)
        self.assertNotIn("m1-text", html)

    def test_delete__message_logged_out(self):
        with self.client as c:

            resp = c.post(
                    f"/messages/{self.m1_id}/delete",
                    follow_redirects = True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<!-- home-anon template id -->", html)
            self.assertIn("Access unauthorized.", html)

    def test_delete_other_user_message(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.post(
                    f"/messages/{self.m2_id}/delete",
                    follow_redirects = True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<!-- show template id -->", html)
            self.assertIn("Access unauthorized.", html)

            #TESTING NOT DELETED FROM FRONTEND
            resp = c.get(f'/messages/{self.m2_id}')

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("m2-text", html)

            #TESTING NOT DELETED FROM DATABASE
            m2 = Message.query.get(self.m2_id)

            self.assertEqual(m2.text, "m2-text")

class MessageLikeTestCase(MessageBaseViewTestCase):

    def test_liking_message(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        resp = c.post(
                    f"/messages/{self.m2_id}/toggle-like",
                    data = {'from-page': f'/messages/{self.m2_id}'},
                    follow_redirects = True)

        # check if the star is filled in upon a like
        html = resp.get_data(as_text=True)

        self.assertIn('filled-gold', html)

    def test_disliking_message(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        m2 = Message.query.get(self.m2_id)
        u1 = User.query.get(self.u1_id)
        u1.liked_messages.append(m2)
        db.session.commit()

        resp = c.post(
                    f"/messages/{self.m2_id}/toggle-like",
                    data = {'from-page': f'/messages/{self.m2_id}'},
                    follow_redirects = True)

        html = resp.get_data(as_text=True)

        # star should be present but not filled in
        self.assertNotIn('filled-gold', html)
        self.assertIn("bi-star", html)
