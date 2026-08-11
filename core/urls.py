from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("movies/<slug:slug>/", views.movie_detail, name="movie_detail"),
    path("screenings/<int:pk>/", views.screening_detail, name="screening_detail"),
    path("booking/start/", views.booking_start, name="booking_start"),
    path("booking/extras/", views.booking_extras, name="booking_extras"),
    path("checkout/", views.checkout, name="checkout"),
    path("booking/complete/<uuid:token>/", views.booking_complete, name="booking_complete"),
    path("ticket/<uuid:token>/", views.ticket, name="ticket"),
    path("ticket/<uuid:token>/qr.svg", views.ticket_qr, name="ticket_qr"),
]
