from datetime import datetime

import pytest
from werkzeug.security import generate_password_hash

from app import app
from extensions import db
from models import User, Event


TEST_EMAIL_1 = "test_owner@example.com"
TEST_EMAIL_2 = "test_other@example.com"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()

        Event.query.filter(
            Event.user_id.in_(
                db.session.query(User.id).filter(
                    User.email.in_(
                        [TEST_EMAIL_1, TEST_EMAIL_2]
                    )
                )
            )
        ).delete(synchronize_session=False)

        User.query.filter(
            User.email.in_(
                [TEST_EMAIL_1, TEST_EMAIL_2]
            )
        ).delete(synchronize_session=False)

        db.session.commit()

    with app.test_client() as client:
        yield client

    with app.app_context():
        Event.query.filter(
            Event.user_id.in_(
                db.session.query(User.id).filter(
                    User.email.in_(
                        [TEST_EMAIL_1, TEST_EMAIL_2]
                    )
                )
            )
        ).delete(synchronize_session=False)

        User.query.filter(
            User.email.in_(
                [TEST_EMAIL_1, TEST_EMAIL_2]
            )
        ).delete(synchronize_session=False)

        db.session.commit()


def test_home_route(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Welcome To EventHub" in response.data


def test_login(client):
    with app.app_context():
        user = User(
            name="Test User",
            email=TEST_EMAIL_1,
            password_hash=generate_password_hash(
                "password123"
            )
        )

        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/login",
        data={
            "email": TEST_EMAIL_1,
            "password": "password123"
        },
        follow_redirects=True
    )

    assert response.status_code == 200
    assert b"You are now logged in." in response.data


def test_cannot_edit_another_users_event(client):
    with app.app_context():
        owner = User(
            name="Owner",
            email=TEST_EMAIL_1,
            password_hash=generate_password_hash(
                "password123"
            )
        )

        other_user = User(
            name="Other User",
            email=TEST_EMAIL_2,
            password_hash=generate_password_hash(
                "password123"
            )
        )

        db.session.add(owner)
        db.session.add(other_user)
        db.session.commit()

        event = Event(
            title="Test Event",
            short_description="This is a test event.",
            description="This is a longer test event description.",
            location="Tbilisi",
            date=datetime(2026, 10, 10, 18, 0),
            ticket_price=20,
            organizer="Test Organizer",
            category="Technology",
            user_id=owner.id
        )

        db.session.add(event)
        db.session.commit()

        event_id = event.id

    client.post(
        "/login",
        data={
            "email": TEST_EMAIL_2,
            "password": "password123"
        },
        follow_redirects=True
    )

    response = client.get(
        f"/events/{event_id}/edit"
    )

    assert response.status_code == 403