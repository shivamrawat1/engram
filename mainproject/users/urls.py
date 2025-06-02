from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

app_name = 'users'

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('decks/', views.decks, name='decks'),
    path('tutor/', views.tutor, name='tutor'),
    path('tutor/chat/', views.tutor_chat, name='tutor_chat'),
    path('personas/', views.personas_view, name='personas'),
    path('getting-started/', views.getting_started, name='getting_started'),
    path('create-deck/', views.create_deck, name='create_deck'),
    path('rename-deck/<int:deck_id>/', views.rename_deck, name='rename_deck'),
    path('delete-deck/<int:deck_id>/', views.delete_deck, name='delete_deck'),
    path('deck/<int:deck_id>/', views.deck_detail, name='deck_detail'),
    path('deck/<int:deck_id>/create-card/', views.create_card, name='create_card'),
    path('card/<int:card_id>/edit/', views.edit_card, name='edit_card'),
    path('card/<int:card_id>/delete/', views.delete_card, name='delete_card'),
    path('deck/<int:deck_id>/review/', views.review_deck, name='review_deck'),
    path('card/<int:card_id>/mark-reviewed/', views.mark_card_reviewed, name='mark_card_reviewed'),
    path('personas/create/', views.create_persona, name='create_persona'),
    path('personas/<int:persona_id>/', views.get_persona, name='get_persona'),
    path('personas/<int:persona_id>/update/', views.update_persona, name='update_persona'),
    path('personas/<int:persona_id>/delete/', views.delete_persona, name='delete_persona'),
    path('decks/<int:deck_id>/personas/', views.deck_personas, name='deck_personas'),
    path('decks/<int:deck_id>/update-personas/', views.update_deck_personas, name='update_deck_personas'),
    path('deck/<int:deck_id>/review-failed/', views.review_failed_cards, name='review_failed_cards'),
    path('card/<int:card_id>/reset-streak/', views.reset_card_streak, name='reset_card_streak'),
    path('deck/<int:deck_id>/questions/', views.deck_questions, name='deck_questions'),
    path('deck/<int:deck_id>/analyze/', views.analyze_deck, name='analyze_deck'),
    path('analyze-card/', views.analyze_card, name='analyze_card'),
    path('review/', views.review, name='review'),
    path('review/start/', views.start_interleaved_review, name='start_interleaved_review'),
    path('review/card/<int:card_id>/mark-reviewed/', views.mark_interleaved_card_reviewed, name='mark_interleaved_card_reviewed'),
]
