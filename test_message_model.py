"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from models import db, User, Message, Follow
from sqlalchemy.exc import IntegrityError

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ["DATABASE_URL"] = "postgresql:///warbler_test"

# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()


class MessageModelTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)
        db.session.flush()

        message_1 = Message(text = 'test message 1', user_id = u1.id)
        message_2 = Message(text = 'test message 2', user_id = u2.id)

        db.session.add(message_1)
        db.session.add(message_2)
        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id

        self.client = app.test_client()

    def tearDown(self):
        db.session.rollback()

    def test_text_in_message(self):

        u1 = User.query.get(self.u1_id)
        m1 = u1.messages[0]

        self.assertEqual(m1.text, 'test message 1')

    def test_user_created_messages(self):

        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)

        m1 = u1.messages[0]
        m2 = u2.messages[0]

        self.assertIn(m1, u1.messages)
        self.assertNotIn(m2, u1.messages)

    def test_user_liked_messages(self):

        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)
        m2 = u2.messages[0]

        m2.liked_by_users.append(u1)

        self.assertIn(u1, m2.liked_by_users)
        self.assertIn(m2, u1.liked_messages)



