from django.urls import path

from . import staff_views, views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("movies/<slug:slug>/", views.movie_detail, name="movie_detail"),
    path("screenings/<int:pk>/", views.screening_detail, name="screening_detail"),
    path("screenings/<int:pk>/preshow/", views.preshow, name="preshow"),
    path("booking/start/", views.booking_start, name="booking_start"),
    path("booking/extras/", views.booking_extras, name="booking_extras"),
    path("booking/find/", views.reservation_lookup, name="reservation_lookup"),
    path("checkout/", views.checkout, name="checkout"),
    path("booking/complete/<uuid:token>/", views.booking_complete, name="booking_complete"),
    path("ticket/<uuid:token>/", views.ticket, name="ticket"),
    path("ticket/<uuid:token>/check-in/", views.ticket_check_in, name="ticket_check_in"),
    path("ticket/<uuid:token>/qr.svg", views.ticket_qr, name="ticket_qr"),
    path("staff/scanner/", views.ticket_scanner, name="ticket_scanner"),
    path("staff/screenings/", staff_views.screening_dashboard_list, name="staff_screenings"),
    path("staff/screenings/<int:pk>/", staff_views.screening_dashboard, name="screening_dashboard"),
    path("staff/screenings/<int:pk>/live/", staff_views.screening_dashboard_live, name="screening_dashboard_live"),
]
