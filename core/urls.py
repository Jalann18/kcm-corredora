# core/urls.py
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('propiedades/', views.propiedad_list, name='propiedad_list'),
    path('propiedades/<slug:slug>/', views.propiedad_detail, name='propiedad_detail'),
    path('contacto/', views.contacto, name='contacto'),
    path('quiero-publicar/', views.quiero_publicar, name='quiero_publicar'),
    path('nosotros/', views.nosotros, name='nosotros'),
]
