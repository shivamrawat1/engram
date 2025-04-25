from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from .models import Deck, Card, Persona  # Import the models
from django.utils import timezone
import random
from django.db import models
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
import openai
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from datetime import timedelta
import io
import requests
from PIL import Image
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
import os
import uuid
from django.db.models import Q

# Create your views here.

def landing_page(request):
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    return render(request, 'users/landing_page.html')

def register(request):
    if request.user.is_authenticated:
        return redirect('users:dashboard')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('users:login')
    else:
        form = UserCreationForm()
    return render(request, 'users/register.html', {'form': form})

# Add this new view for logout
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully!')
    return redirect('users:landing_page')

@login_required
def dashboard(request):
    return render(request, 'users/dashboard.html')

@login_required
def decks(request):
    user_decks = Deck.objects.filter(user=request.user)
    return render(request, 'users/decks.html', {'decks': user_decks})

@login_required
def create_deck(request):
    if request.method == 'POST':
        name = request.POST.get('deck_name')
        if name:
            deck = Deck.objects.create(name=name, user=request.user)
            return redirect('users:decks')
        else:
            messages.error(request, 'Please provide a name for the deck.')
    return redirect('users:decks')

@login_required
def rename_deck(request, deck_id):
    if request.method == 'POST':
        try:
            deck = Deck.objects.get(id=deck_id, user=request.user)
            new_name = request.POST.get('deck_name')
            if new_name:
                deck.name = new_name
                deck.save()
            else:
                messages.error(request, 'Please provide a name for the deck.')
        except Deck.DoesNotExist:
            messages.error(request, 'Deck not found.')
    return redirect('users:decks')

@login_required
def delete_deck(request, deck_id):
    try:
        deck = Deck.objects.get(id=deck_id, user=request.user)
        deck.delete()
    except Deck.DoesNotExist:
        messages.error(request, 'Deck not found.')
    return redirect('users:decks')

@login_required
def tutor(request):
    # Get all decks for the user to populate the dropdown
    decks = Deck.objects.filter(user=request.user)
    return render(request, 'users/tutor.html', {'decks': decks})

@login_required
def personas(request):
    return render(request, 'users/personas.html')

@login_required
def getting_started(request):
    return render(request, 'users/getting_started.html')

@login_required
def deck_detail(request, deck_id):
    try:
        deck = Deck.objects.get(id=deck_id, user=request.user)
        cards = Card.objects.filter(deck=deck)
        
        # Pass the current time to the template for comparison
        now = timezone.now()
        
        return render(request, 'users/deck_detail.html', {
            'deck': deck, 
            'cards': cards,
            'now': now
        })
    except Deck.DoesNotExist:
        messages.error(request, 'Deck not found.')
        return redirect('users:decks')

@login_required
def create_card(request, deck_id):
    try:
        deck = Deck.objects.get(id=deck_id, user=request.user)
        if request.method == 'POST':
            question = request.POST.get('question')
            answer = request.POST.get('answer')
            if question and answer:
                Card.objects.create(deck=deck, question=question, answer=answer)
                return redirect('users:deck_detail', deck_id=deck_id)
            else:
                messages.error(request, 'Please provide both question and answer.')
        return redirect('users:deck_detail', deck_id=deck_id)
    except Deck.DoesNotExist:
        messages.error(request, 'Deck not found.')
        return redirect('users:decks')

@login_required
def edit_card(request, card_id):
    try:
        card = Card.objects.get(id=card_id)
        # Make sure the user owns the card (via the deck)
        if card.deck.user != request.user:
            messages.error(request, 'You do not have permission to edit this card.')
            return redirect('users:decks')
            
        if request.method == 'POST':
            question = request.POST.get('question')
            answer = request.POST.get('answer')
            if question and answer:
                card.question = question
                card.answer = answer
                card.save()
                return redirect('users:deck_detail', deck_id=card.deck.id)
            else:
                messages.error(request, 'Please provide both question and answer.')
        return redirect('users:deck_detail', deck_id=card.deck.id)
    except Card.DoesNotExist:
        messages.error(request, 'Card not found.')
        return redirect('users:decks')

@login_required
def delete_card(request, card_id):
    try:
        card = Card.objects.get(id=card_id)
        # Make sure the user owns the card (via the deck)
        if card.deck.user != request.user:
            messages.error(request, 'You do not have permission to delete this card.')
            return redirect('users:decks')
            
        deck_id = card.deck.id
        card.delete()
        return redirect('users:deck_detail', deck_id=deck_id)
    except Card.DoesNotExist:
        messages.error(request, 'Card not found.')
        return redirect('users:decks')

@login_required
def review_deck(request, deck_id):
    try:
        deck = Deck.objects.get(id=deck_id, user=request.user)
        all_cards = Card.objects.filter(deck=deck)
        
        if not all_cards.exists():
            # No cards in the deck at all
            return render(request, 'users/review_deck.html', {
                'deck': deck,
                'no_cards_to_review': True,
                'reviewed_cards': 0,
                'remembered_cards': 0,
                'total_cards': 0,
                'due_cards': 0,
                'failed_cards_count': 0
            })
        
        # Get cards that are due for review (next_review_time is null or in the past)
        current_time = timezone.now()
        due_cards = all_cards.filter(
            models.Q(next_review_time__isnull=True) | 
            models.Q(next_review_time__lte=current_time)
        )
        
        # Count failed cards (consecutive_correct = 0 but have been reviewed before)
        failed_cards_count = all_cards.filter(consecutive_correct=0, last_reviewed__isnull=False).count()
        
        if not due_cards.exists():
            # All cards have been reviewed - show congratulations message
            return render(request, 'users/review_deck.html', {
                'deck': deck,
                'no_cards_to_review': True,
                'reviewed_cards': all_cards.filter(last_reviewed__isnull=False).count(),
                'remembered_cards': all_cards.filter(consecutive_correct__gt=0).count(),
                'total_cards': all_cards.count(),
                'due_cards': 0,
                'failed_cards_count': failed_cards_count
            })
        
        # Prioritize cards:
        # 1. Never reviewed (last_reviewed is null)
        # 2. Failed cards (consecutive_correct = 0 and last_reviewed is not null)
        # 3. Cards due the longest
        never_reviewed = due_cards.filter(last_reviewed__isnull=True)
        if never_reviewed.exists():
            card_to_review = never_reviewed.first()
        else:
            failed_cards = due_cards.filter(consecutive_correct=0, last_reviewed__isnull=False)
            if failed_cards.exists():
                card_to_review = failed_cards.first()
            else:
                # Get the card that's been due the longest
                card_to_review = due_cards.order_by('next_review_time').first()
        
        # Never show the "all reviewed" modal during the review process
        all_reviewed = False
        
        return render(request, 'users/review_deck.html', {
            'deck': deck,
            'card': card_to_review,
            'all_reviewed': all_reviewed,
            'no_cards_to_review': False,
            'total_cards': all_cards.count(),
            'reviewed_cards': all_cards.filter(last_reviewed__isnull=False).count(),
            'due_cards': due_cards.count(),
            'remembered_cards': all_cards.filter(consecutive_correct__gt=0).count(),
            'failed_cards_count': failed_cards_count
        })
    except Deck.DoesNotExist:
        messages.error(request, 'Deck not found.')
        return redirect('users:decks')

@login_required
def mark_card_reviewed(request, card_id):
    try:
        card = Card.objects.get(id=card_id)
        # Make sure the user owns the card (via the deck)
        if card.deck.user != request.user:
            messages.error(request, 'You do not have permission to review this card.')
            return redirect('users:decks')
            
        # Get the quality rating from the form (0-5 scale)
        quality = int(request.POST.get('quality', '0'))
        current_time = timezone.now()
        
        # Store the old interval for display purposes
        old_interval = card.current_interval
        
        # Calculate the next interval using SM-15 algorithm
        next_interval_days = card.calculate_next_interval(quality)
        
        # Update card review status
        if quality >= 3:  # Correct response
            card.times_reviewed += 1
            
            # Set next review time based on the interval
            if next_interval_days > 0:
                card.next_review_time = current_time + timezone.timedelta(days=next_interval_days)
                
                # Add a message to show the new interval
                if next_interval_days == 1:
                    messages.success(request, f'Correct! Next review tomorrow. (Quality: {quality}/5)')
                else:
                    messages.success(request, f'Correct! Next review in {next_interval_days} days. (Quality: {quality}/5)')
            else:
                # If interval is 0, review again in 10 minutes
                card.next_review_time = current_time + timezone.timedelta(minutes=10)
                messages.success(request, f'Correct! Next review in 10 minutes. (Quality: {quality}/5)')
        else:  # Incorrect response
            # Reset times_reviewed for compatibility with existing code
            card.times_reviewed = 0
            
            # For incorrect responses, show again after a short delay based on quality
            if quality == 0:  # Complete blackout
                delay_minutes = 1  # Review very soon
            elif quality == 1:  # Incorrect but recognized
                delay_minutes = 5  # A bit longer delay
            else:  # quality == 2, almost correct
                delay_minutes = 10  # Even longer delay
                
            card.next_review_time = current_time + timezone.timedelta(minutes=delay_minutes)
            messages.warning(request, f'You will see this card again in {delay_minutes} minutes. (Quality: {quality}/5)')
        
        # Update the current interval
        card.current_interval = next_interval_days
        card.last_reviewed = current_time
        card.save()
        
        # Redirect to review another card
        return redirect('users:review_deck', deck_id=card.deck.id)
    except Card.DoesNotExist:
        messages.error(request, 'Card not found.')
        return redirect('users:decks')

@login_required
def personas_view(request):
    """View for the personas page"""
    personas = Persona.objects.filter(user=request.user)
    return render(request, 'users/personas.html', {'personas': personas})

@login_required
@require_POST
def create_persona(request):
    """API endpoint to create a new persona"""
    try:
        data = json.loads(request.body)
        
        # Create the persona
        persona = Persona.objects.create(
            user=request.user,
            name=data['name'],
            persona_type=data['persona_type'],
            tone=data['tone'],
            attachments=data.get('attachments', [])
        )
        
        # Return the created persona data
        return JsonResponse({
            'id': persona.id,
            'name': persona.name,
            'persona_type': persona.persona_type,
            'tone': persona.tone,
            'attachments': persona.attachments
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_GET
def get_persona(request, persona_id):
    """API endpoint to get a persona's details"""
    try:
        persona = Persona.objects.get(id=persona_id, user=request.user)
        return JsonResponse({
            'id': persona.id,
            'name': persona.name,
            'persona_type': persona.persona_type,
            'tone': persona.tone,
            'attachments': persona.attachments
        })
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona not found'}, status=404)

@login_required
@require_POST
def update_persona(request, persona_id):
    """API endpoint to update a persona"""
    try:
        data = json.loads(request.body)
        persona = Persona.objects.get(id=persona_id, user=request.user)
        
        # Update the persona fields
        persona.name = data['name']
        persona.persona_type = data['persona_type']
        persona.tone = data['tone']
        persona.attachments = data.get('attachments', [])
        persona.save()
        
        return JsonResponse({
            'id': persona.id,
            'name': persona.name,
            'persona_type': persona.persona_type,
            'tone': persona.tone,
            'attachments': persona.attachments
        })
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def delete_persona(request, persona_id):
    """API endpoint to delete a persona"""
    try:
        persona = Persona.objects.get(id=persona_id, user=request.user)
        persona.delete()
        return JsonResponse({'success': True})
    except Persona.DoesNotExist:
        return JsonResponse({'error': 'Persona not found'}, status=404)

@login_required
def deck_personas(request, deck_id):
    """Get all personas for a user and the ones attached to a specific deck"""
    try:
        deck = Deck.objects.get(id=deck_id, user=request.user)
        all_personas = Persona.objects.filter(user=request.user)
        deck_personas = deck.personas.all()
        
        return JsonResponse({
            'all_personas': list(all_personas.values('id', 'name', 'persona_type', 'tone')),
            'deck_personas': list(deck_personas.values_list('id', flat=True))
        })
    except Deck.DoesNotExist:
        return JsonResponse({'error': 'Deck not found'}, status=404)

@login_required
def update_deck_personas(request, deck_id):
    """Update the personas attached to a deck"""
    try:
        deck = Deck.objects.get(id=deck_id, user=request.user)
        
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                persona_ids = data.get('persona_ids', [])
                
                # Log the received data for debugging
                print(f"Received persona_ids: {persona_ids}")
                
                # Clear existing personas and add the selected ones
                deck.personas.clear()
                if persona_ids:
                    personas = Persona.objects.filter(id__in=persona_ids, user=request.user)
                    print(f"Found personas: {list(personas.values_list('id', 'name'))}")
                    deck.personas.add(*personas)
                
                # Return the updated personas
                updated_personas = deck.personas.all()
                return JsonResponse({
                    'success': True,
                    'personas': list(updated_personas.values('id', 'name'))
                })
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
        else:
            return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
            
    except Deck.DoesNotExist:
        return JsonResponse({'error': 'Deck not found'}, status=404)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=400)

def generate_reminder_email(persona, deck, due_cards_count):
    """Generate personalized email content for reminders"""
    # Check if OpenAI should be used and is configured
    use_openai = getattr(settings, 'USE_OPENAI_FOR_EMAILS', True)
    has_api_key = hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY
    
    if getattr(settings, 'EMAIL_DEBUG', False):
        print(f"[EMAIL DEBUG] Generating email for persona {persona.name}")
        print(f"[EMAIL DEBUG] Use OpenAI: {use_openai}, API key configured: {bool(has_api_key)}")
    
    # If OpenAI is disabled or not configured, use fallback immediately
    if not use_openai or not has_api_key:
        if getattr(settings, 'EMAIL_DEBUG', False):
            print(f"[EMAIL DEBUG] Using fallback email template (OpenAI not used)")
        return generate_fallback_email(persona, deck, due_cards_count)
    
    try:
        # Import the OpenAI client using the new API format
        from openai import OpenAI
        
        # Configure OpenAI API
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Get sample questions from the due cards (up to 3)
        due_cards = deck.cards.filter(next_review_time__lte=timezone.now())[:3]
        sample_questions = [card.question for card in due_cards]
        
        # Create the prompt for OpenAI
        prompt = f"""
        Create a very short, catchy email reminder to review flashcards.
        
        The email should be written in the style of {persona.persona_type} with a {persona.tone} tone.
        
        The email should remind the user that they have {due_cards_count} cards due for review in their deck named "{deck.name}".
        
        Use these sample questions from the deck to personalize the email:
        {', '.join(sample_questions)}
        
        The email should be extremely concise (2-3 lines maximum) and attention-grabbing.
        
        Format the email in markdown with a subject line, greeting, body, and sign-off.
        """
        
        if getattr(settings, 'EMAIL_DEBUG', False):
            print(f"[EMAIL DEBUG] Sending prompt to OpenAI: {prompt[:100]}...")
        
        # Call OpenAI API using the new format
        response = client.chat.completions.create(
            model="gpt-4",  # or whatever model you prefer
            messages=[
                {"role": "system", "content": "You are a helpful assistant that writes extremely concise, personalized emails."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7
        )
        
        # Extract the generated email content using the new response format
        email_content = response.choices[0].message.content
        
        if getattr(settings, 'EMAIL_DEBUG', False):
            print(f"[EMAIL DEBUG] Received response from OpenAI: {len(email_content)} chars")
        
        # Parse the markdown to extract subject and body
        lines = email_content.strip().split('\n')
        subject = lines[0].replace('Subject:', '').replace('#', '').strip()
        body = '\n'.join(lines[1:])
        
        if getattr(settings, 'EMAIL_DEBUG', False):
            print(f"[EMAIL DEBUG] Extracted subject: {subject}")
            print(f"[EMAIL DEBUG] Email body length: {len(body)} chars")
        
        # Return the email data
        return {
            'subject': subject,
            'body': body,
            # Add a flag to indicate if we should include an image
            'include_image': 'images' in persona.attachments,
            'sample_questions': sample_questions
        }
    except Exception as e:
        if getattr(settings, 'EMAIL_DEBUG', False):
            import traceback
            print(f"[EMAIL DEBUG] Error generating email: {str(e)}")
            print(f"[EMAIL DEBUG] {traceback.format_exc()}")
        
        # Use fallback if OpenAI fails
        return generate_fallback_email(persona, deck, due_cards_count)

def generate_fallback_email(persona, deck, due_cards_count):
    """Generate a fallback email when OpenAI is not available"""
    if getattr(settings, 'EMAIL_DEBUG', False):
        print(f"[EMAIL DEBUG] Generating fallback email for persona {persona.name}")
    
    # Get sample questions from the due cards (up to 2)
    due_cards = deck.cards.filter(next_review_time__lte=timezone.now())[:2]
    sample_questions = [card.question for card in due_cards]
    
    # Create different templates based on persona type
    templates = {
        'Friendly': {
            'subject': f"Quick review needed: {deck.name}",
            'body': f"Hey! {due_cards_count} cards waiting, including '{sample_questions[0] if sample_questions else 'your flashcards'}'. Review now?"
        },
        'Professional': {
            'subject': f"{due_cards_count} cards due: {deck.name}",
            'body': f"Time for a quick review of '{sample_questions[0] if sample_questions else deck.name}' and {due_cards_count-1} other cards."
        },
        'Motivational': {
            'subject': f"Can you answer this? {sample_questions[0][:30] + '...' if sample_questions else deck.name}",
            'body': f"Challenge yourself! {due_cards_count} questions waiting for your brilliant mind."
        },
        'Humorous': {
            'subject': f"Your flashcards miss you!",
            'body': f"Your cards are getting dusty! Can you still answer '{sample_questions[0] if sample_questions else 'your questions'}'? Find out now!"
        }
    }
    
    # Get the template based on persona type or use a default one
    template = templates.get(persona.persona_type, templates['Friendly'])
    
    # Adjust tone based on persona tone
    if persona.tone.lower() == 'urgent' and 'urgent' not in template['subject'].lower():
        template['subject'] = f"URGENT: {template['subject']}"
    
    if getattr(settings, 'EMAIL_DEBUG', False):
        print(f"[EMAIL DEBUG] Generated fallback subject: {template['subject']}")
    
    return {
        'subject': template['subject'],
        'body': template['body'],
        'include_image': 'images' in persona.attachments,
        'sample_questions': sample_questions
    }

def generate_image_for_persona(persona, deck):
    """Generate an image for the reminder email based on persona and deck"""
    try:
        if not settings.OPENAI_API_KEY or not getattr(settings, 'USE_OPENAI_FOR_EMAILS', True):
            print("OpenAI API key not configured or disabled for emails")
            return None
            
        # Get a sample question from the deck to use in the prompt
        due_cards = deck.cards.filter(next_review_time__lte=timezone.now())[:1]
        sample_question = due_cards[0].question if due_cards else deck.name
            
        # Create a prompt based on the persona, deck, and actual card content
        prompt = f"Create a visually striking, attention-grabbing image related to this flashcard question: '{sample_question}'. "
        
        # Adjust the prompt based on persona type and tone
        if persona.persona_type == "Friend":
            prompt += f"Make it friendly and approachable, with a {persona.tone} vibe."
        elif persona.persona_type == "Coach":
            prompt += f"Make it motivational and encouraging, with a {persona.tone} style."
        elif persona.persona_type == "Teacher":
            prompt += f"Make it educational and informative, with a {persona.tone} approach."
        else:
            prompt += f"Style it with a {persona.tone} aesthetic."
            
        prompt += " The image should be eye-catching and make the viewer curious to learn more. Make it compact and not too wide."
            
        # Call OpenAI API to generate the image
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",  # Square format
            quality="standard",
            n=1,
        )
        
        # Get the image URL from the response
        image_url = response.data[0].url
        
        # Download the image
        image_response = requests.get(image_url)
        if image_response.status_code == 200:
            # Process the image to reduce its size
            try:
                img = Image.open(io.BytesIO(image_response.content))
                
                # Resize the image to be smaller (600px width max)
                max_width = 600
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.LANCZOS)
                
                # Save the resized image to a bytes buffer
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=85)  # Reduce quality for smaller file size
                buffer.seek(0)
                
                return buffer.getvalue()
            except Exception as img_error:
                print(f"Error processing image: {str(img_error)}")
                # Return the original image if processing fails
                return image_response.content
        else:
            print(f"Failed to download image: {image_response.status_code}")
            return None
            
    except Exception as e:
        print(f"Error generating image: {str(e)}")
        return None

def generate_audio_for_persona(persona, deck):
    """Generate an audio clip for the reminder email based on persona and deck"""
    try:
        if not settings.OPENAI_API_KEY or not getattr(settings, 'USE_OPENAI_FOR_EMAILS', True):
            print("OpenAI API key not configured or disabled for emails")
            return None
            
        # Get sample questions from the due cards (up to 2)
        due_cards = deck.cards.filter(next_review_time__lte=timezone.now())[:2]
        sample_questions = [card.question for card in due_cards]
        
        # Import the OpenAI client
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # First, generate the script for the audio
        prompt = f"""
        Create a short, engaging script for an audio reminder about reviewing flashcards.
        
        The audio should be in the style of {persona.persona_type} with a {persona.tone} tone.
        
        Reference this specific content from the flashcards: {', '.join(sample_questions)}
        
        The script should be attention-grabbing and motivate the user to review their '{deck.name}' deck.
        
        The script MUST be at least 30-40 words long to ensure it's 8-10 seconds when spoken.
        Do not make it too short - a single word or phrase is not acceptable.
        """
        
        if getattr(settings, 'EMAIL_DEBUG', False):
            print(f"[EMAIL DEBUG] Sending audio script prompt to OpenAI")
        
        # Get the script from GPT
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that writes engaging audio scripts that are 30-40 words long (8-10 seconds when spoken)."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7
        )
        
        script = response.choices[0].message.content.strip()
        
        # Ensure the script is long enough
        if len(script.split()) < 20:
            # If too short, add more content
            script += f" Don't forget to review your {deck.name} deck today. These questions are waiting for you. Take a few minutes to strengthen your knowledge!"
        
        if getattr(settings, 'EMAIL_DEBUG', False):
            print(f"[EMAIL DEBUG] Generated audio script ({len(script.split())} words): {script}")
        
        # Select voice based on persona type
        voice_mapping = {
            "Friend": "nova",
            "Coach": "onyx",
            "Teacher": "echo",
            "Professional": "fable",
            "Motivational": "shimmer",
            "Humorous": "alloy"
        }
        
        voice = voice_mapping.get(persona.persona_type, "nova")
        
        if getattr(settings, 'EMAIL_DEBUG', False):
            print(f"[EMAIL DEBUG] Using voice: {voice} for persona type: {persona.persona_type}")
        
        # Generate the audio using OpenAI's text-to-speech
        try:
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=script
            )
            
            # Get the audio data
            audio_data = response.content
            
            # Verify we got enough audio data (at least 10KB for a decent clip)
            if len(audio_data) < 10000:
                if getattr(settings, 'EMAIL_DEBUG', False):
                    print(f"[EMAIL DEBUG] Warning: Audio data seems too small ({len(audio_data)} bytes)")
                
                # Try again with a simpler, guaranteed script
                fallback_script = f"Hello! This is a reminder to review your {deck.name} flashcards. You have questions like {sample_questions[0] if sample_questions else 'your study materials'} waiting for you. Please take a moment to review them now!"
                
                response = client.audio.speech.create(
                    model="tts-1",
                    voice=voice,
                    input=fallback_script
                )
                audio_data = response.content
                
                if getattr(settings, 'EMAIL_DEBUG', False):
                    print(f"[EMAIL DEBUG] Generated fallback audio ({len(audio_data)} bytes)")
            
            return {
                'data': audio_data,
                'script': script
            }
            
        except Exception as audio_error:
            if getattr(settings, 'EMAIL_DEBUG', False):
                print(f"[EMAIL DEBUG] Error in TTS API call: {str(audio_error)}")
            
            # Try with a much simpler script as a last resort
            try:
                very_simple_script = f"Time to review your flashcards!"
                response = client.audio.speech.create(
                    model="tts-1",
                    voice="alloy",  # Use a reliable voice
                    input=very_simple_script
                )
                return {
                    'data': response.content,
                    'script': very_simple_script
                }
            except:
                return None
            
    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None

def send_review_reminders():
    """Send reminder emails for decks with due cards (limited to one per day per deck)"""
    now = timezone.now()
    reminders_sent = 0
    
    # Get all personas
    personas = Persona.objects.all()
    
    # For each persona, check if they need to send reminders
    for persona in personas:
        # Get decks associated with this persona
        decks = persona.decks.all()
        
        for deck in decks:
            # Check if we've already sent a reminder today
            if deck.last_reminder_sent and (now - deck.last_reminder_sent).days < 1:
                continue
                
            # Count due cards
            due_cards_count = deck.cards.filter(
                next_review_time__lte=now
            ).count()
            
            # Only send reminder if there are due cards
            if due_cards_count == 0:
                continue
            
            # Generate email content
            email_data = generate_reminder_email(persona, deck, due_cards_count)
            
            # Prepare the email
            subject = email_data['subject']
            
            # Debug the persona attachments
            if getattr(settings, 'EMAIL_DEBUG', False):
                print(f"[EMAIL DEBUG] Persona {persona.name} attachments: {persona.attachments}")
            
            # Check what attachment types are available - case insensitive check
            available_attachments = []
            if any(att.lower() == 'images' for att in persona.attachments) if isinstance(persona.attachments, list) else 'images' in str(persona.attachments).lower():
                available_attachments.append('images')
            if any(att.lower() == 'audio' for att in persona.attachments) if isinstance(persona.attachments, list) else 'audio' in str(persona.attachments).lower():
                available_attachments.append('audio')
            
            # Randomly select one attachment type if any are available
            selected_attachment = random.choice(available_attachments) if available_attachments else None
            
            # Set flags based on the randomly selected attachment
            include_image = selected_attachment == 'images'
            include_audio = selected_attachment == 'audio'
            
            if getattr(settings, 'EMAIL_DEBUG', False):
                print(f"[EMAIL DEBUG] Available attachments: {available_attachments}")
                print(f"[EMAIL DEBUG] Randomly selected attachment: {selected_attachment}")
                print(f"[EMAIL DEBUG] Include image: {include_image}")
                print(f"[EMAIL DEBUG] Include audio: {include_audio}")
            
            # Create the review URL - use absolute URL that will work in emails
            # For production, this should use the site's domain
            base_url = "http://127.0.0.1:8000" if settings.DEBUG else "https://yourdomain.com"
            review_url = f"{base_url}/users/deck/{deck.id}/review/"
            
            # Clean up the email body - remove markdown formatting
            clean_body = email_data['body']
            clean_body = clean_body.replace('**', '')  # Remove bold markers
            clean_body = '\n'.join([line for line in clean_body.split('\n') if line.strip()])  # Remove empty lines
            
            # Create HTML version with a button/link to the deck
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .content {{ margin-bottom: 30px; font-size: 18px; text-align: center; }}
                    .review-button {{ background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; margin-top: 15px; }}
                    .review-button:hover {{ background-color: #2980b9; }}
                    img {{ max-width: 100%; height: auto; margin: 20px 0; }}
                    .signature {{ margin-top: 20px; font-style: italic; text-align: center; }}
                    .audio-player {{ margin: 20px 0; text-align: center; }}
                </style>
            </head>
            <body>
                <div class="content">
                    {clean_body}
                </div>
                <div style="text-align: center;">
                    <a href="{review_url}" class="review-button">Review Now</a>
                </div>
                {f'<div><img src="cid:reminder_image.jpg" alt="Reminder Image"></div>' if include_image else ''}
                {f'<div class="audio-player"><p>Listen to your personalized reminder:</p><audio controls><source src="cid:reminder_audio.mp3" type="audio/mpeg">Your browser does not support the audio element.</audio></div>' if include_audio else ''}
            </body>
            </html>
            """
            
            try:
                # For local development, always send to a specific email
                recipient_email = 'shivam@uni.minerva.edu' if settings.DEBUG else deck.user.email
                
                if getattr(settings, 'EMAIL_DEBUG', False):
                    print(f"[EMAIL DEBUG] Sending email to {recipient_email}")
                    print(f"[EMAIL DEBUG] Subject: {subject}")
                    if include_image:
                        print(f"[EMAIL DEBUG] Including AI-generated image")
                    if include_audio:
                        print(f"[EMAIL DEBUG] Including AI-generated audio")
                
                # Create the email message
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=f"{clean_body}\n\nReview now: {review_url}",  # Plain text version with direct link
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient_email]
                )
                
                # Add the HTML version
                email.attach_alternative(html_content, "text/html")
                
                # Check if we should include an image
                if include_image:
                    # Generate and attach an image
                    image_data = generate_image_for_persona(persona, deck)
                    if image_data:
                        # Create a MIMEImage object with the image data
                        image = MIMEImage(image_data)
                        # Set the Content-ID header
                        image.add_header('Content-ID', '<reminder_image.jpg>')
                        # Add the image to the email
                        email.attach(image)
                
                # Check if we should include audio
                if include_audio:
                    if getattr(settings, 'EMAIL_DEBUG', False):
                        print(f"[EMAIL DEBUG] Generating audio for persona {persona.name}")
                    
                    # Generate and attach an audio clip
                    audio_result = generate_audio_for_persona(persona, deck)
                    if audio_result and 'data' in audio_result:
                        if getattr(settings, 'EMAIL_DEBUG', False):
                            print(f"[EMAIL DEBUG] Successfully generated audio, attaching to email")
                        
                        # Create a MIMEAudio object with the audio data
                        audio = MIMEAudio(audio_result['data'], _subtype='mp3')
                        # Set the Content-ID header
                        audio.add_header('Content-ID', '<reminder_audio.mp3>')
                        # Add the audio to the email
                        email.attach(audio)
                        
                        # Also attach the audio as a regular attachment so it can be downloaded
                        email.attach('reminder.mp3', audio_result['data'], 'audio/mpeg')
                        
                        if getattr(settings, 'EMAIL_DEBUG', False):
                            print(f"[EMAIL DEBUG] Audio script: {audio_result.get('script', 'No script available')}")
                    else:
                        if getattr(settings, 'EMAIL_DEBUG', False):
                            print(f"[EMAIL DEBUG] Failed to generate audio")
                
                # Send the email
                email.send(fail_silently=False)
                
                # Update the last reminder sent time
                deck.last_reminder_sent = now
                deck.save()
                
                reminders_sent += 1
                print(f"Sent reminder for deck '{deck.name}' to {recipient_email}")
            except Exception as e:
                print(f"Failed to send reminder for deck '{deck.name}': {str(e)}")
                if getattr(settings, 'EMAIL_DEBUG', False):
                    import traceback
                    print(f"[EMAIL DEBUG] Exception details: {traceback.format_exc()}")
    
    if getattr(settings, 'EMAIL_DEBUG', False):
        print(f"[EMAIL DEBUG] Total reminders sent: {reminders_sent}")
    
    return reminders_sent

@login_required
def review_failed_cards(request, deck_id):
    try:
        deck = Deck.objects.get(id=deck_id, user=request.user)
        
        # Get cards that were failed (consecutive_correct = 0 but have been reviewed before)
        failed_cards = Card.objects.filter(
            deck=deck,
            consecutive_correct=0,
            last_reviewed__isnull=False
        )
        
        if not failed_cards.exists():
            messages.info(request, "No failed cards to review.")
            return redirect('users:deck_detail', deck_id=deck_id)
        
        # Get the first failed card to review
        card_to_review = failed_cards.first()
        
        # Count all cards in the deck
        all_cards = Card.objects.filter(deck=deck)
        
        return render(request, 'users/review_deck.html', {
            'deck': deck,
            'card': card_to_review,
            'all_reviewed': False,
            'no_cards_to_review': False,
            'total_cards': all_cards.count(),
            'reviewed_cards': all_cards.filter(last_reviewed__isnull=False).count(),
            'due_cards': failed_cards.count(),
            'remembered_cards': all_cards.filter(consecutive_correct__gt=0).count(),
            'failed_cards_count': failed_cards.count(),
            'reviewing_failed_cards': True
        })
    except Deck.DoesNotExist:
        messages.error(request, 'Deck not found.')
        return redirect('users:decks')

@login_required
def reset_card_streak(request, card_id):
    try:
        card = Card.objects.get(id=card_id)
        # Make sure the user owns the card (via the deck)
        if card.deck.user != request.user:
            messages.error(request, 'You do not have permission to reset this card.')
            return redirect('users:decks')
            
        # Reset the card's progress
        card.times_reviewed = 0
        card.consecutive_correct = 0
        card.current_interval = 0
        card.easiness_factor = 2.5  # Reset to default
        card.next_review_time = timezone.now()  # Make it due immediately
        card.save()
        
        messages.success(request, 'Card streak has been reset.')
        return redirect('users:deck_detail', deck_id=card.deck.id)
    except Card.DoesNotExist:
        messages.error(request, 'Card not found.')
        return redirect('users:decks')

@login_required
@require_POST
def tutor_chat(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '')
        context = data.get('context', {})
        is_initial = data.get('initial', False)
        
        # Get API key from environment variable
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return JsonResponse({'response': 'API key not configured. Please contact the administrator.'})
        
        # Configure OpenAI client
        client = openai.OpenAI(api_key=api_key)
        
        # Prepare system message based on context
        system_message = "You are a helpful tutor who assists students with their questions. Provide clear, concise, and educational responses."
        
        # If this is deck-based learning, fetch the deck content
        if context and context.get('type') == 'deck' and is_initial:
            deck_id = context.get('deckId')
            question_ids = context.get('questionIds', [])
            
            try:
                deck = Deck.objects.get(id=deck_id, user=request.user)
                
                # Get cards based on selected questions or all cards if none selected
                if question_ids:
                    cards = Card.objects.filter(deck=deck, id__in=question_ids)
                else:
                    cards = Card.objects.filter(deck=deck)
                
                # Format cards for the AI
                cards_content = []
                for card in cards:
                    cards_content.append({
                        'question': card.question,
                        'answer': card.answer
                    })
                
                # Create a specialized system message with the deck content
                system_message = f"""
                You are a helpful tutor who assists students with learning content from their flashcards.
                
                The student wants to learn about the deck: "{context.get('deckName')}"
                
                Here are the flashcards from this deck:
                
                {json.dumps(cards_content, indent=2)}
                
                Their learning goal is: {context.get('goal')}
                
                First, provide a brief overview of the topics covered in these flashcards.
                Then, suggest a structured approach to learning this material.
                Be engaging, educational, and thorough in your explanations.
                """
                
            except Deck.DoesNotExist:
                return JsonResponse({'response': 'Deck not found. Please select a valid deck.'})
                
        # If this is new topic learning and initial request
        elif context and context.get('type') == 'new_topic' and is_initial:
            topic = context.get('topic')
            aspect = context.get('aspect', '')
            
            system_message = f"""
            You are a helpful tutor who creates personalized learning plans.
            
            The student wants to learn about: {topic}
            {f'With a focus on: {aspect}' if aspect else ''}
            
            Create a structured learning plan with the following:
            1. A brief introduction to the topic
            2. 4-6 key subtopics or concepts they should learn, organized in a logical sequence
            3. For each subtopic, provide a very brief description (1-2 sentences)
            4. End with a question asking if they want to start with the first subtopic or if they'd prefer a different approach
            
            Be engaging, encouraging, and adapt to their level of interest.
            """
        
        # For ongoing conversations, include the context in the user message
        elif context:
            if context.get('type') == 'deck':
                user_message = f"[Context: Learning about deck '{context.get('deckName')}' with goal: {context.get('goal')}] {user_message}"
            elif context.get('type') == 'new_topic':
                user_message = f"[Context: Learning about {context.get('topic')}{' focusing on ' + context.get('aspect') if context.get('aspect') else ''}] {user_message}"
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # You can change this to a different model if needed
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=1000
        )
        
        # Extract the response text
        ai_response = response.choices[0].message.content
        
        return JsonResponse({'response': ai_response})
    
    except Exception as e:
        print(f"Error in tutor_chat: {str(e)}")
        return JsonResponse({'response': f"Sorry, an error occurred: {str(e)}"}, status=500)

@login_required
def deck_questions(request, deck_id):
    """API endpoint to get questions from a deck"""
    try:
        deck = Deck.objects.get(id=deck_id, user=request.user)
        cards = Card.objects.filter(deck=deck)
        
        questions = [{'id': card.id, 'question': card.question} for card in cards]
        
        return JsonResponse({'questions': questions})
    except Deck.DoesNotExist:
        return JsonResponse({'error': 'Deck not found'}, status=404)

@login_required
def analyze_deck(request, deck_id):
    """API endpoint to analyze a deck's content and suggest knowledge gaps"""
    try:
        deck = Deck.objects.get(id=deck_id, user=request.user)
        cards = Card.objects.filter(deck=deck)
        
        if not cards.exists():
            return JsonResponse({
                'analysis': 'Your deck is empty. Add some cards to get an analysis.'
            })
        
        # Get API key from environment variable or settings
        api_key = os.environ.get('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            return JsonResponse({
                'analysis': 'AI analysis is not available. Please contact the administrator.'
            })
        
        # Configure OpenAI client
        client = openai.OpenAI(api_key=api_key)
        
        # Format cards for the AI
        cards_content = []
        for card in cards:
            cards_content.append({
                'question': card.question,
                'answer': card.answer
            })
        
        # Create the prompt for OpenAI
        prompt = f"""
        Analyze this flashcard deck titled "{deck.name}" and identify potential knowledge gaps.
        
        Here are the existing flashcards:
        {json.dumps(cards_content, indent=2)}
        
        Based on these cards, suggest 3-4 additional topics or concepts that would complement 
        the existing content and fill knowledge gaps. Focus on content-based recommendations, 
        not study patterns.
        
        Your response should be concise (around 150 words) and formatted as a simple HTML list 
        with a brief introduction and conclusion. Do not include any markdown formatting.
        """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # You can use gpt-4 for better results if available
            messages=[
                {"role": "system", "content": "You are a helpful educational assistant that analyzes flashcard content and identifies knowledge gaps."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        # Extract the analysis
        analysis = response.choices[0].message.content.strip()
        
        return JsonResponse({'analysis': analysis})
    
    except Deck.DoesNotExist:
        return JsonResponse({'error': 'Deck not found'}, status=404)
    except Exception as e:
        print(f"Error analyzing deck: {str(e)}")
        return JsonResponse({'error': f"An error occurred: {str(e)}"}, status=500)

@login_required
def analyze_card(request):
    """API endpoint to analyze a flashcard for quality"""
    try:
        if request.method != 'POST':
            return JsonResponse({'error': 'Only POST method is allowed'}, status=405)
            
        data = json.loads(request.body)
        question = data.get('question', '')
        answer = data.get('answer', '')
        
        if not question or not answer:
            return JsonResponse({'error': 'Both question and answer are required'}, status=400)
        
        # Get API key from environment variable or settings
        api_key = os.environ.get('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', None)
        if not api_key:
            return JsonResponse({
                'analysis': 'AI analysis is not available. Please contact the administrator.'
            })
        
        # Configure OpenAI client
        client = openai.OpenAI(api_key=api_key)
        
        # Create the prompt for OpenAI - simplified to focus on suggestions only
        prompt = f"""
        Analyze this flashcard based on these three core properties:

        1. Atomic — tests one clear idea, no bundling multiple facts together.
        2. Clear prompt — question is precise and forces active retrieval, not recognition.
        3. Stable answer — answer is unambiguous, doesn't vary over time or context.

        Question: {question}
        Answer: {answer}

        Do NOT provide ratings. Instead, provide specific suggestions to improve the card based on these properties.
        Keep your response concise (around 100-150 words) and format it as simple HTML.
        Focus only on practical suggestions for improvement.
        """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful educational assistant that provides concise, practical suggestions to improve flashcards."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.7
        )
        
        # Extract the analysis
        analysis = response.choices[0].message.content.strip()
        
        return JsonResponse({'analysis': analysis})
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Error analyzing card: {str(e)}")
        return JsonResponse({'error': f"An error occurred: {str(e)}"}, status=500)

@login_required
def review(request):
    """View for interleaved review across multiple decks"""
    # Check if there's an active review session
    session_id = request.session.get('interleaved_review_session_id')
    
    if session_id and request.session.get('interleaved_review_active'):
        # Continue existing session
        return continue_interleaved_review(request, session_id)
    else:
        # Start new session setup
        # Get all decks with due cards
        now = timezone.now()
        decks = Deck.objects.filter(user=request.user)
        
        decks_with_due_cards = []
        for deck in decks:
            due_count = deck.cards.filter(
                Q(next_review_time__lte=now) | Q(next_review_time__isnull=True)
            ).count()
            
            if due_count > 0:
                deck.due_count = due_count
                decks_with_due_cards.append(deck)
        
        # Check if there are any cards to review
        if not decks_with_due_cards:
            return render(request, 'users/review.html', {
                'no_cards_to_review': True
            })
        
        return render(request, 'users/review.html', {
            'setup_mode': True,
            'decks_with_due_cards': decks_with_due_cards
        })

@login_required
def start_interleaved_review(request):
    """Start an interleaved review session with selected decks"""
    if request.method != 'POST':
        return redirect('users:review')
    
    # Get selected decks
    selected_deck_ids = request.POST.getlist('selected_decks')
    if not selected_deck_ids:
        messages.error(request, 'Please select at least one deck to review.')
        return redirect('users:review')
    
    # Get review options
    shuffle_cards = request.POST.get('shuffle_cards') == 'on'
    
    # Create a new session ID
    session_id = str(uuid.uuid4())
    
    # Get due cards from selected decks
    now = timezone.now()
    due_cards = []
    
    for deck_id in selected_deck_ids:
        deck = get_object_or_404(Deck, id=deck_id, user=request.user)
        
        # Get due cards from this deck
        deck_cards = list(deck.cards.filter(
            Q(next_review_time__lte=now) | Q(next_review_time__isnull=True)
        ))
        
        due_cards.extend(deck_cards)
    
    if not due_cards:
        messages.info(request, 'No cards due for review in the selected decks.')
        return redirect('users:review')
    
    # Sort or shuffle cards based on user preference
    if shuffle_cards:
        # Shuffle for variety
        random.shuffle(due_cards)
    else:
        # Sort by due date (most overdue first)
        due_cards.sort(key=lambda card: (
            # Cards with review time in the past come first (most overdue first)
            card.next_review_time is not None and card.next_review_time < now,
            # Then cards that have never been reviewed
            card.next_review_time is None,
            # Then by actual review time
            card.next_review_time or timezone.now()
        ), reverse=True)
    
    # Store card IDs in session
    card_ids = [card.id for card in due_cards]
    request.session['interleaved_review_cards'] = card_ids
    request.session['interleaved_review_session_id'] = session_id
    request.session['interleaved_review_active'] = True
    request.session['interleaved_review_total'] = len(card_ids)
    request.session['interleaved_review_decks'] = selected_deck_ids
    
    # Redirect to the review page to start the session
    return redirect('users:review')

@login_required
def continue_interleaved_review(request, session_id):
    """Continue an existing interleaved review session"""
    # Get remaining cards
    card_ids = request.session.get('interleaved_review_cards', [])
    
    if not card_ids:
        # Session is complete
        total_cards = request.session.get('interleaved_review_total', 0)
        deck_ids = request.session.get('interleaved_review_decks', [])
        
        # Clear session data
        request.session['interleaved_review_active'] = False
        request.session['interleaved_review_cards'] = []
        
        # Get unique decks covered
        decks_covered = len(set(deck_ids))
        
        return render(request, 'users/review.html', {
            'session_complete': True,
            'total_cards': total_cards,
            'decks_covered': decks_covered
        })
    
    # Get the next card
    card_id = card_ids[0]
    try:
        card = get_object_or_404(Card, id=card_id, deck__user=request.user)
        
        # Calculate progress
        total_cards = request.session.get('interleaved_review_total', 0)
        remaining_cards = len(card_ids)
        reviewed_cards = total_cards - remaining_cards
        progress_percentage = (reviewed_cards / total_cards) * 100 if total_cards > 0 else 0
        
        return render(request, 'users/review.html', {
            'card': card,
            'session_id': session_id,
            'remaining_cards': remaining_cards,
            'total_cards': total_cards,
            'progress_percentage': progress_percentage
        })
    except:
        # If there's an issue with the card, remove it and continue
        if card_id in card_ids:
            card_ids.remove(card_id)
            request.session['interleaved_review_cards'] = card_ids
        
        # Redirect to try the next card
        return redirect('users:review')

@login_required
def mark_interleaved_card_reviewed(request, card_id):
    """Mark a card as reviewed in an interleaved review session"""
    if request.method != 'POST':
        return redirect('users:review')
    
    # Get the card
    card = get_object_or_404(Card, id=card_id, deck__user=request.user)
    
    # Get the quality rating
    quality = int(request.POST.get('quality', 0))
    
    # Update the card using the SM-15 algorithm (same as in mark_card_reviewed)
    now = timezone.now()
    
    # Calculate the next interval
    next_interval = card.calculate_next_interval(quality)
    
    # Update card fields
    card.times_reviewed += 1
    card.last_reviewed = now
    card.current_interval = next_interval
    
    # Set next review time
    if next_interval == 0:
        # If interval is 0, review again today (in 10 minutes)
        card.next_review_time = now + timezone.timedelta(minutes=10)
    else:
        # Otherwise, set to the calculated interval in days
        card.next_review_time = now + timezone.timedelta(days=next_interval)
    
    card.save()
    
    # Remove this card from the session's review list
    card_ids = request.session.get('interleaved_review_cards', [])
    if card_id in card_ids:
        card_ids.remove(card_id)
        request.session['interleaved_review_cards'] = card_ids
    
    # Continue to the next card
    return redirect('users:review')
