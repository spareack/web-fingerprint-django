
from django.urls import path, include
from . import views

urlpatterns = {
    path('', views.HomeView.as_view()),
    path('set_secret_data', views.set_secret_data)
}