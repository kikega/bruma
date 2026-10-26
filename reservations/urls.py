from django.urls import path

from . import views

app_name = 'reservations'

urlpatterns = [
    path('', views.create_reservation, name='create'),
    path('disponibilidad/', views.check_availability, name='availability'),
]
