import logging
import os

import requests
from dotenv import load_dotenv

from flask import Flask, render_template, redirect, url_for, flash, abort, request
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, login_manager
from models import User, Event
from forms import RegistrationForm, LoginForm, EventForm, DeleteForm, ProfileForm
from flask_login import current_user, login_required, login_user, logout_user

load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

app = Flask(__name__)

file_handler = logging.FileHandler('../eventhub.log')

file_handler.setLevel(logging.INFO)

file_handler.setFormatter(
    logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
    )
)

app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "eventhub-secret-key")
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///eventhub.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager.init_app(app)

login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

PROFILE_PICTURE_FOLDER = os.path.join(
    app.root_path,
    "static",
    "profile_pics"
)

os.makedirs(
    PROFILE_PICTURE_FOLDER,
    exist_ok=True
)

def get_profile_picture(user_id):
    extensions = [
        "jpg",
        "jpeg",
        "png"
    ]

    for extension in extensions:
        filename = f"user_{user_id}.{extension}"

        path = os.path.join(
            PROFILE_PICTURE_FOLDER,
            filename
        )

        if os.path.exists(path):
            return f"profile_pics/{filename}"

    return None
def save_profile_picture(picture, user_id):
    extension = os.path.splitext(
        picture.filename
    )[1].lower()

    for filename in os.listdir(
        PROFILE_PICTURE_FOLDER
    ):
        if filename.startswith(
            f"user_{user_id}."
        ):
            old_path = os.path.join(
                PROFILE_PICTURE_FOLDER,
                filename
            )

            os.remove(old_path)

    filename = f"user_{user_id}{extension}"

    picture_path = os.path.join(
        PROFILE_PICTURE_FOLDER,
        filename
    )

    picture.save(picture_path)

def get_weather(location):
    if not OPENWEATHER_API_KEY:
        return None

    geocoding_url = ("https://api.openweathermap.org/geo/1.0/direct")

    geocoding_params = {
        "q": location,
        "limit": 1,
        "appid": OPENWEATHER_API_KEY,
    }

    try:
        geocoding_response = requests.get(
            geocoding_url,
            params=geocoding_params,
            timeout=5
        )

        geocoding_response.raise_for_status()

        locations = geocoding_response.json()

        if not locations:
            return None

        latitude = locations[0]["lat"]
        longitude = locations[0]["lon"]

        weather_url = ("https://api.openweathermap.org/data/2.5/weather")

        weather_params = {
            "lat": latitude,
            "lon": longitude,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }

        weather_response = requests.get(
            weather_url,
            params=weather_params,
            timeout=5
        )

        weather_response.raise_for_status()

        data = weather_response.json()

        return {
            "temperature": data["main"]["temp"],
            "description": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
        }

    except requests.RequestException as error:
        app.logger.error(
            "Weather API request failed: %s",
            type(error).__name__
        )

        return None

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/about')
def about():
    return render_template("about.html")

@app.route("/profile")
@login_required
def profile():
    user_events = Event.query.filter_by(
        user_id=current_user.id
    ).order_by(Event.date.asc()).all()

    profile_picture = get_profile_picture(
        current_user.id
    )

    return render_template(
        "profile.html",
        user_events=user_events,
        profile_picture=profile_picture
    )

@app.route("/users/<int:user_id>")
def user_profile(user_id):
    user = db.get_or_404(User, user_id)

    user_events = Event.query.filter_by(
        user_id=user.id,
    ).order_by(Event.date.asc()).all()

    return render_template(
        "user_profile.html",
        user=user,
        user_events=user_events
    )

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = ProfileForm()

    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.email = form.email.data.lower()

        if form.picture.data:
            save_profile_picture(
                form.picture.data,
                current_user.id
            )

        db.session.commit()

        flash("Profile updated successfully", "success")

        return redirect(url_for("profile"))

    if request.method == "GET":
        form.name.data = current_user.name
        form.email.data = current_user.email

    return render_template(
        "edit_profile.html",
        form=form,
    )

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)

        user = User(name=form.name.data, email=form.email.data.lower(), password_hash=hashed_password)

        db.session.add(user)
        db.session.commit()

        app.logger.info(
            "New user registered with ID %s",
            user.id
        )

        flash('Your account has been created! You are now able to log in.', 'success')

        return redirect(url_for('home'))

    return render_template("register.html", form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()

        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)

            app.logger.info(
                "User %s logged in",
                user.id
            )

            flash('You are now logged in.', 'success')

            return redirect(url_for('home'))

        app.logger.warning(
            "Failed login attempt"
        )

        flash('Invalid username or password.', 'danger')

    return render_template("login.html", form=form)

@app.route('/logout')
@login_required
def logout():
    user_id = current_user.id

    logout_user()

    app.logger.info(
        "User %s logged out",
        user_id
    )

    flash('You have been logged out.', 'success')

    return redirect(url_for('home'))

@app.route('/events/new', methods=['GET', 'POST'])
@login_required
def add_event():
    form = EventForm()

    if form.validate_on_submit():
        event = Event(
            title=form.title.data,
            short_description=form.short_description.data,
            description=form.description.data,
            location=form.location.data,
            date=form.date.data,
            ticket_price=form.ticket_price.data,
            organizer=form.organizer.data,
            category=form.category.data,
            user_id=current_user.id,
        )

        db.session.add(event)
        db.session.commit()

        app.logger.info(
            "Event %s created by user %s",
            event.id,
            current_user.id
        )

        flash('Event has been added.', 'success')

        return redirect(url_for('events'))

    return render_template(
        "add_event.html",
        form=form,
    )

@app.route("/events")
def events():
    selected_category = request.args.get("category", "")
    selected_sort = request.args.get("sort", "newest")

    query = Event.query

    if selected_category:
        query = query.filter_by(category=selected_category)

    if selected_sort == "date_desc":
        query = query.order_by(Event.date.desc())

    elif selected_sort == "newest":
        query = query.order_by(Event.created_at.desc())

    elif selected_sort == "oldest":
        query = query.order_by(Event.created_at.asc())

    elif selected_sort == "price_low":
        query = query.order_by(Event.ticket_price.asc())

    elif selected_sort == "price_high":
        query = query.order_by(Event.ticket_price.desc())

    else:
        query = query.order_by(Event.date.asc())

    all_events = query.all()

    categories = [
        "Music",
        "Technology",
        "Sport",
        "Art",
        "Education",
        "Other"
    ]

    return render_template(
        "events.html",
        events=all_events,
        categories=categories,
        selected_category=selected_category,
        selected_sort=selected_sort,
    )

@app.route("/events/<int:event_id>")
def event_detail(event_id):
    event = db.get_or_404(Event, event_id)
    delete_form = DeleteForm()

    weather = get_weather(event.location)

    return render_template(
        "event_detail.html",
        event=event,
        delete_form=delete_form,
        weather=weather
    )

@app.route("/events/<int:event_id>/edit", methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    event = db.get_or_404(Event, event_id)

    if event.user_id != current_user.id:
        app.logger.warning(
            "User %s tried to edit event %s without permission",
            current_user.id,
            event_id
        )

        abort(403)

    form = EventForm(obj=event)

    if form.validate_on_submit():
        event.title = form.title.data
        event.short_description = form.short_description.data
        event.description = form.description.data
        event.location = form.location.data
        event.date = form.date.data
        event.ticket_price = form.ticket_price.data
        event.organizer = form.organizer.data
        event.category = form.category.data

        db.session.commit()

        app.logger.info(
            "Event %s updated by user %s",
            event.id,
            current_user.id
        )

        flash('Event has been updated.', 'success')

        return redirect(url_for('event_detail', event_id=event.id))

    form.submit.label.text = 'Update Event'

    return render_template("edit_event.html", form=form, event=event)

@app.route("/events/<int:event_id>/delete", methods=['POST'])
@login_required
def delete_event(event_id):
    event = db.get_or_404(Event, event_id)

    if event.user_id != current_user.id:
        app.logger.warning(
            "User %s tried to delete event %s without permission",
            current_user.id,
            event.id
        )
        abort(403)

    form = DeleteForm()

    if form.validate_on_submit():

        db.session.delete(event)
        db.session.commit()

        app.logger.info(
            "Event %s deleted by user %s",
            event_id,
            current_user.id
        )

        flash('Event has been deleted.', 'success')

        return redirect(url_for('events'))

    abort(400)

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(error):
    db.session.rollback()

    return render_template("500.html"), 500



if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(debug=True)