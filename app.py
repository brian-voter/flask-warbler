import os
from dotenv import load_dotenv

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, CsrfForm, UpdateUserForm
from models import db, connect_db, User, Message, bcrypt

load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
toolbar = DebugToolbarExtension(app)

connect_db(app)


#TODO: extract danger message to constant? or make flash a separate function?

ACCESS_UNAUTHORIZED_MSG = "Access unauthorized."


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


@app.before_request
def add_csrf_form_to_g():
    """Will add csrf form to flask global"""

    g.csrf_form = CsrfForm()


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Log out user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]




@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    do_logout()

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login and redirect to homepage on success."""

    form = LoginForm()

    if g.user:
        flash("You are already logged in!", 'info')
        return redirect("/")

    if form.validate_on_submit():
        user = User.authenticate(
            form.username.data,
            form.password.data,
        )

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.post('/logout')
def logout():
    """Handle logout of user and redirect to homepage."""

    form = g.csrf_form

    if form.validate_on_submit():
        do_logout()
        flash('Successfully Logged Out', "success")


    return redirect('/login')



##############################################################################
# General user routes:

@app.get('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    if not g.user:
        flash(ACCESS_UNAUTHORIZED_MSG, "danger")
        return redirect("/")

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.get('/users/<int:user_id>')
def show_user(user_id):
    """Show user profile."""

    if not g.user:
        flash(ACCESS_UNAUTHORIZED_MSG, "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)

    return render_template('users/show.html', user=user)

@app.get('/users/<int:user_id>/likes')
def show_user_liked_messages(user_id):
    """Display like messages on user page"""

    if not g.user:
        flash(ACCESS_UNAUTHORIZED_MSG, "danger")
        return redirect("/")

    return render_template('home.html',
                           messages=g.user.liked_messages,
                           from_end_point=f'/users/{g.user.id}/likes')



@app.get('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash(ACCESS_UNAUTHORIZED_MSG, "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.get('/users/<int:user_id>/followers')
def show_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash(ACCESS_UNAUTHORIZED_MSG, "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.post('/users/follow/<int:follow_id>')
def start_following(follow_id):
    """Add a follow for the currently-logged-in user.

    Redirect to following page for the current for the current user.
    """

    if not g.user:
        flash(ACCESS_UNAUTHORIZED_MSG, "danger")
        return redirect("/")

    form = g.csrf_form

    if form.validate_on_submit():
        followed_user = User.query.get_or_404(follow_id)
        g.user.following.append(followed_user)
        db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.post('/users/stop-following/<int:follow_id>')
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user.

    Redirect to following page for the current for the current user.
    """

    if not g.user:
        flash(ACCESS_UNAUTHORIZED_MSG, "danger")
        return redirect("/")


    form = g.csrf_form
    if form.validate_on_submit():
        followed_user = User.query.get_or_404(follow_id)
        g.user.following.remove(followed_user)
        db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    # make sure user is logged in
    if not g.user:
        flash(ACCESS_UNAUTHORIZED_MSG, "danger")
        return redirect("/")

    form = UpdateUserForm(obj=g.user)

    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        image_url = form.image_url.data
        header_image_url = form.header_image_url.data
        bio = form.bio.data
        password = form.password.data
        is_auth = bcrypt.check_password_hash(g.user.password, password)

        if is_auth:
            g.user.username = username
            g.user.email = email
            g.user.image_url = image_url
            g.user.header_image_url = header_image_url
            g.user.bio = bio
            db.session.commit()
            return redirect(f'/users/{g.user.id}')

        else:
            flash('Invalid Password', 'danger')
            return render_template("/users/edit.html", form=form, user_id=g.user.id)

    return render_template("/users/edit.html", form=form, user_id=g.user.id)

@app.post('/users/delete')
def delete_user():
    """Delete user.

    Redirect to signup page.
    """

    form = g.csrf_form

    if (not g.user) or (not form.validate_on_submit()):
        flash(ACCESS_UNAUTHORIZED_MSG, "danger")
        return redirect("/")

    do_logout()
    Message.query.filter(Message.user_id == g.user.id).delete()

    db.session.delete(g.user)
    db.session.commit()

    flash("Your account has been deleted!", "success")
    return redirect("/signup")



##############################################################################
# Messages routes:

@app.route('/messages/new', methods=["GET", "POST"])
def add_message():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash(ACCESS_UNAUTHORIZED_MSG, "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/create.html', form=form)


@app.get('/messages/<int:message_id>')
def show_message(message_id):
    """Show a message."""

    if not g.user:
        flash(ACCESS_UNAUTHORIZED_MSG, "danger")
        return redirect("/")

    msg = Message.query.get_or_404(message_id)
    return render_template('messages/show.html', message=msg)


@app.post('/messages/<int:message_id>/delete')
def delete_message(message_id):
    """Delete a message.

    Check that this message was written by the current user.
    Redirect to user page on success.
    """

    if not g.user:
        flash(ACCESS_UNAUTHORIZED_MSG, "danger")
        return redirect("/")

    form = g.csrf_form
    if form.validate_on_submit():

        msg = Message.query.get_or_404(message_id)

        if msg.user.id != g.user.id:
            flash(ACCESS_UNAUTHORIZED_MSG, "danger")
            return redirect(f"/users/{g.user.id}")

        db.session.delete(msg)
        db.session.commit()

    return redirect(f"/users/{g.user.id}")

@app.post('/messages/<int:msg_id>/toggle-like')
def toggle_liked_message(msg_id):
    """Toggles a message's liked status for the current user."""

    form = g.csrf_form

    if (not g.user) or (not form.validate_on_submit()):
        flash(ACCESS_UNAUTHORIZED_MSG, "danger")
        return redirect("/")

    message = Message.query.get(msg_id)

    if g.user in message.liked_by_users:
        message.liked_by_users.remove(g.user)
    else:
        message.liked_by_users.append(g.user)

    db.session.commit()

    #TODO: see if we can do this in WTforms
    return redirect(request.form['from-page'])



##############################################################################
# Homepage and error pages


@app.get('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of self & followed_users
    """

    if g.user:

        # the user ids for who we will display their messages on our homepage
        user_ids = [user.id for user in g.user.following]
        user_ids.append(g.user.id)

        messages = (Message.query
            .filter(Message.user_id.in_(user_ids))
            .order_by(Message.timestamp.desc())
            .limit(100).all())

        liked_messages = g.user.liked_messages

        return render_template(
            'home.html',
            messages=messages,
            liked_messages=liked_messages,
            from_end_point='/')

    else:
        return render_template('home-anon.html')


@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True
    return response
