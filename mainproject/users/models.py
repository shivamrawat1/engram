from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import math

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
    
    # SM-15 algorithm specific fields
    easiness_factor = models.FloatField(default=2.5)  # Initial easiness factor
    consecutive_correct = models.IntegerField(default=0)  # Count of consecutive correct answers
    current_interval = models.IntegerField(default=0)  # Current interval in days
    
    def __str__(self):
        return f"Card in {self.deck.name}"
    
    def get_review_interval(self):
        """Return the review interval in minutes based on SM-15 algorithm"""
        # This is now a legacy method, kept for compatibility
        # The actual interval calculation happens in the mark_reviewed method
        if self.current_interval == 0:
            return 0  # First review
        else:
            # Convert days to minutes for compatibility with existing code
            return self.current_interval * 24 * 60
    
    def calculate_next_interval(self, quality):
        """
        Calculate the next interval using the SM-15 algorithm
        
        quality: Integer from 0-5 representing how well the card was remembered
        0-2: Incorrect response (different levels of difficulty)
        3-5: Correct response (different levels of ease)
        
        Returns the next interval in days
        """
        if quality < 3:
            # If response was incorrect, reset consecutive count
            self.consecutive_correct = 0
            return 0  # Review again soon (same day)
        else:
            # Update easiness factor based on quality of response
            # The formula adjusts the easiness factor based on how well the card was remembered
            self.easiness_factor = max(1.3, self.easiness_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
            
            # Increment consecutive correct count
            self.consecutive_correct += 1
            
            # Calculate next interval based on consecutive correct answers
            if self.consecutive_correct == 1:
                # First correct response
                return 1  # 1 day
            elif self.consecutive_correct == 2:
                # Second correct response
                return 6  # 6 days
            else:
                # For subsequent correct responses, multiply the previous interval by the easiness factor
                new_interval = round(self.current_interval * self.easiness_factor)
                return max(new_interval, self.current_interval + 1)  # Ensure interval increases

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
