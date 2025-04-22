from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class Deck(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    personas = models.ManyToManyField('Persona', related_name='decks', blank=True)
    last_reminder_sent = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.name
    
    def card_count(self):
        return self.cards.count()
    
class Card(models.Model):
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='cards')
    question = models.TextField()
    answer = models.TextField()
    times_reviewed = models.IntegerField(default=0)
    last_reviewed = models.DateTimeField(null=True, blank=True)
    next_review_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Card in {self.deck.name}"
    
    def get_review_interval(self):
        """Return the review interval in minutes based on times_reviewed"""
        if self.times_reviewed == 0:
            return 0  # First review
        elif self.times_reviewed == 1:
            return 1  # 1 minute
        elif self.times_reviewed == 2:
            return 2  # 2 minutes
        elif self.times_reviewed == 3:
            return 3  # 3 minutes
        elif self.times_reviewed == 4:
            return 4  # 4 minutes
        else:
            return 60 * 24 * 7  # 1 week (long-term memory)

class Persona(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personas')
    name = models.CharField(max_length=100)
    persona_type = models.CharField(max_length=100)
    tone = models.CharField(max_length=50)
    attachments = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'name']
        
    def __str__(self):
        return f"{self.name} ({self.persona_type})"
