"""Big Integration tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_integration.py


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


class IntegrationBaseTestCase(TestCase):
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


class IntegrationTestCase(IntegrationBaseTestCase):
    """This integration test verifies that deleting objects which are referred to by other objects
    is successful (cascade on delete)"""

    def test_integration_delete_cascade(self):
        with self.client as c:

            # LOGIN AS U1
            c.post(
                "/login",
                data={'username': 'u1', 'password': 'password'},
                follow_redirects = True)

            # POST A MESSAGE
            c.post(
                "/messages/new",
                data={'text': 'test text 1234'},
                follow_redirects = True)

            # U1 FOLLOWS U2
            c.post(
                f"/users/follow/{self.u2_id}",
                follow_redirects = True)

            # U1 LIKES M2
            c.post(
                f"/messages/{self.m2_id}/toggle-like",
                data={'from-page': f'/messages/{self.m2_id}'},
                follow_redirects = True)

            # U1 LOGS OUT
            c.post(
                "/logout",
                follow_redirects = True)



            # LOGIN AS U2
            c.post(
                "/login",
                data={'username': 'u2', 'password': 'password'},
                follow_redirects = True)

            # U2 FOLLOWS U1
            c.post(
                f"/users/follow/{self.u1_id}",
                follow_redirects = True)

            # U2 LIKES M1
            c.post(
                f"/messages/{self.m1_id}/toggle-like",
                data={'from-page': f'/messages/{self.m1_id}'},
                follow_redirects = True)


            # U2 LOGS OUT
            c.post(
                "/logout",
                follow_redirects = True)


            # U1 LOGS BACK IN
            c.post(
                "/login",
                data={'username': 'u1', 'password': 'password'},
                follow_redirects = True)


            # U1 DELETES SELF
            resp = c.post(
                f"/users/delete",
                follow_redirects = True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("<!-- signup template id -->", html)
            self.assertIn("Your account has been deleted!", html)
