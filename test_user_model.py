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


class UserModelTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.commit()
        self.u1_id = u1.id
        self.u2_id = u2.id

        self.client = app.test_client()

    def tearDown(self):
        db.session.rollback()


    def test_user_model_init(self):
        u1 = User.query.get(self.u1_id)

        # User should have no messages & no followers
        self.assertEqual(len(u1.messages), 0)
        self.assertEqual(len(u1.followers), 0)


    def test_is_following(self):
        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)

        # set u1 to follow u2
        u2.followers.append(u1)

        self.assertTrue(u1.is_following(u2))
        self.assertTrue(u2.is_followed_by(u1))

        # using backref, set u2 to follow u1
        u2.following.append(u1)

        self.assertTrue(u2.is_following(u1))
        self.assertTrue(u1.is_followed_by(u2))


    def test_is_not_following(self):
        u1 = User.query.get(self.u1_id)
        u2 = User.query.get(self.u2_id)

        self.assertFalse(u1.is_following(u2))
        self.assertFalse(u2.is_followed_by(u1))

        # set u1 to follow u2
        u2.followers.append(u1)

        self.assertFalse(u2.is_following(u1))
        self.assertFalse(u1.is_followed_by(u2))


    def test_user_signup_success(self):
        u = User.signup("u", "u@gmail.com", "password", "")

        #TODO: check actual user/email is correct

        db.session.add(u)
        db.session.commit()

        self.assertEqual(User.query.count(), 3)
        self.assertNotEqual(u.password, "password")


    def test_user_signup_failure(self):

        # duplicate username
        u = User.signup("u1", "u@gmail.com", "password", "")

        db.session.add(u)

        with self.assertRaises(
            IntegrityError):

            db.session.commit()

        db.session.rollback()
        #TODO: break into two tests
        # duplicate email
        u3 = User.signup("u", "u1@email.com", "password", "")
        db.session.add(u3)

        with self.assertRaises(
            IntegrityError):

            db.session.commit()

    def test_user_authentication_valid(self):

        u1 = User.query.get(self.u1_id)

        self.assertTrue(u1.authenticate(u1.username, "password"))


    def test_user_authentication_invalid(self):

        u1 = User.query.get(self.u1_id)

        self.assertFalse(u1.authenticate("bad_username", "password"))
        self.assertFalse(u1.authenticate(u1.username, "bad_password"))






