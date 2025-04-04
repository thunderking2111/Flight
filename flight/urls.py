from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("query/places/<str:q>", views.query, name="query"),
    path("flight/", views.flight, name="flight"),
    path("review/", views.review, name="review"),
    path("flight/add/", views.add_flight, name="addflight"),
    path("flight/ticket/book/", views.book, name="book"),
    path("flight/ticket/payment/", views.payment, name="payment"),
    path('flight/ticket/api/<str:ref>', views.ticket_data, name="ticketdata"),
    path('flight/ticket/print/',views.get_ticket, name="getticket"),
    path('flight/bookings/', views.bookings, name="bookings"),
    path('flight/ticket/cancel/', views.cancel_ticket, name="cancelticket"),
    path('flight/ticket/resume/', views.resume_booking, name="resumebooking"),
    path('flight/chart/', views.flight_chart, name="flightchart"),
    path('flight/chart-table/', views.flight_chart_table, name="flightcharttable"),
    path('flight/book/', views.confirm_booking, name="bookflight"),
    path('contact/', views.contact, name="contact"),
    path('privacy-policy/', views.privacy_policy, name="privacypolicy"),
    path('terms-and-conditions/', views.terms_and_conditions, name="termsandconditions"),
    path('about-us/', views.about_us, name="aboutus"),
    path('totp_token_entry/', views.totp_token_entry, name="totp_token_entry"),
    path('totp_device_setup/', views.totp_device_setup, name="totp_device_setup"),
]
