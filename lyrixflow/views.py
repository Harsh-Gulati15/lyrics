from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import json
from django.utils.text import slugify
from django.shortcuts import render, get_object_or_404, redirect
import time # For placeholder delay
from .lyrics_generator import get_rapper_lyrics
from .models import UserProfile,ChatSession, ChatMessage
from .data import GENRE_ARTIST_MAP
from django.templatetags.static import static # Import the static tag function
from django.shortcuts import render
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST



def index_view(request):
    return render(request, 'lyrixflow/index.html')


@login_required
def genre_dashboard_view(request):
    genres_for_template = []
    
    genre_images = {
        "Hip-Hop": static('genres/hiphop.jpg'),
        "Desi Hip-Hop": static('genres/desihiphop.jpg'),
        "Pop": static('genres/pop.jpg'),
        "Rock": static('genres/rock.jpg'),
        "Electronic": static('genres/electronic.jpg'),
        "Bollywood": static('genres/bollywood.jpg'),
    }
    default_image = static('other_images/mic.png')

    for genre_name, artists in GENRE_ARTIST_MAP.items():
        sample_artists = [artist['name'] for artist in artists[:3]]
        
        genres_for_template.append({
            'name': genre_name,
            'description': f"{len(artists)} artists available",
            'image_url': genre_images.get(genre_name, default_image),
            'sample_artists': sample_artists,
            'url': reverse('artist_selection', kwargs={'genre_slug': slugify(genre_name)})
        })

    context = {
        'genres_json': json.dumps(genres_for_template)
    }
    return render(request, 'lyrixflow/genre_dashboard.html', context)

@login_required
def artist_selection_view(request, genre_slug):
    genre_name_display = None
    artists_for_genre = []
    
    # Find the genre and its artists from your data map
    for g_name, art_list in GENRE_ARTIST_MAP.items():
        if slugify(g_name) == genre_slug:
            genre_name_display = g_name
            artists_for_genre = art_list
            break

    if not genre_name_display:
        messages.error(request, f"Genre '{genre_slug}' not found.")
        return redirect('dashboard') # Redirect back to the genre dashboard

    context = {
        'genre_name': genre_name_display,
        # 'artists' context is not strictly needed by this template, but good to keep
        'artists': artists_for_genre, 
        # The JSON version is what the JavaScript will use
        'artists_json': json.dumps(artists_for_genre)
    }
    return render(request, 'lyrixflow/artist_selection.html', context)

@login_required
def chat_view(request, rapper_name):
    genre_slug_for_back_button = ''
    # Find which genre this rapper belongs to
    for genre, artists in GENRE_ARTIST_MAP.items():
        for artist in artists:
            if artist['name'] == rapper_name:
                genre_slug_for_back_button = slugify(genre)
                break
        if genre_slug_for_back_button:
            break

    context = {
        'rapper_name': rapper_name,
        'genre_slug_for_back_button': genre_slug_for_back_button,
    }
    return render(request, 'lyrixflow/chat.html', context)

@login_required
# @transaction.atomic
def generate_lyrics_api(request):
    if request.method == 'POST':
        try:
            # ... (Your usage limit check remains the same) ...

            data = json.loads(request.body)
            topic = data.get('topic')
            session_id = data.get('session_id') # Get session ID from request

            if not topic or not session_id:
                return JsonResponse({'error': 'Missing topic or session ID'}, status=400)

            # Get the session, ensuring it belongs to the user
            session = ChatSession.objects.get(id=session_id, user=request.user)
            
            # Save the user's message to the database
            ChatMessage.objects.create(session=session, role='user', content=topic)

            # --- CONTEXT BUILDING FOR AI ---
            # Get the last few messages from DB to build history
            db_history = session.messages.order_by('-timestamp')[:10] # Get last 10 messages
            history_for_ai = []
            for msg in reversed(db_history): # Reverse to get chronological order
                history_for_ai.append({'role': msg.role, 'content': msg.content})

            # Call the generator with the history from the database
            generated_lyrics_html = get_rapper_lyrics(session.artist_name, topic, history=history_for_ai)
            
            # Save the AI's response to the database
            ChatMessage.objects.create(session=session, role='model', content=generated_lyrics_html)
            
            # Update session title with first user prompt if it's a new chat
            if session.title == "New Chat":
                session.title = topic[:80] # Use first 80 chars of prompt as title
                session.save()

            # ... (Your logic to increment user's generation count) ...

            return JsonResponse({'lyrics': generated_lyrics_html})
        except ChatSession.DoesNotExist:
            return JsonResponse({'error': 'Chat session not found or access denied.'}, status=404)
        except Exception as e:
            return None

@login_required
def new_chat_view(request, artist_name):
    # This view creates a new empty session and redirects to it
    session = ChatSession.objects.create(user=request.user, artist_name=artist_name)
    # The first message can be the AI's greeting
    ChatMessage.objects.create(
        session=session,
        role='model',
        content=f"Yo! I'm {artist_name}. What do you want me to rap about?"
    )
    return redirect('chat_session', session_id=session.id)


@login_required
def chat_session_view(request, session_id):
    # Get the specific session, ensuring it belongs to the current user
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    
    # Get all messages for this session
    chat_history = session.messages.all()
    
    # Get all past sessions for the sidebar
    past_sessions = ChatSession.objects.filter(user=request.user)

    context = {
        'artist_name': session.artist_name,
        'chat_history': chat_history,
        'past_sessions': past_sessions,
        'current_session_id': session.id,
        # For the "Back to Artists" button
        'genre_slug_for_back_button': find_genre_slug_for_artist(session.artist_name)
    }
    return render(request, 'lyrixflow/chat.html', context)

def find_genre_slug_for_artist(artist_name):
    from .data import GENRE_ARTIST_MAP
    from django.utils.text import slugify
    for genre, artists in GENRE_ARTIST_MAP.items():
        for artist in artists:
            if artist['name'] == artist_name:
                return slugify(genre)
    return '' # Return empty string if not found

@require_POST # Ensures this view can only be accessed via a POST request for security
@login_required
def delete_chat_view(request, session_id):
    # Find the session, ensuring it belongs to the logged-in user to prevent unauthorized deletion
    session_to_delete = get_object_or_404(ChatSession, id=session_id, user=request.user)
    
    # Get the artist name before deleting, so we can start a new chat with the same artist
    artist_name = session_to_delete.artist_name
    session_to_delete.delete()
    
    messages.success(request, "Chat session deleted.")
    
    # Redirect the user to start a new chat with the same artist
    return redirect('new_chat', artist_name=artist_name)