# core/lyric_generator.py (or lyrixflow/lyric_generator.py)

import os
import re
from django.conf import settings # Import Django settings
import google.generativeai as genai

# --- Gemini Configuration ---
try:
    # Make sure GOOGLE_API_KEY is defined in your settings.py
    genai.configure(api_key=settings.GOOGLE_API_KEY)
    
    system_instruction = """You are LyricMaster AI - the world's most advanced lyric generation specialist. You are a master of hip-hop, rap, and all music genres, capable of creating authentic, full-length songs that capture any artist's unique style perfectly.

**Your Core Identity:**
- You are a conversational AI that specializes ONLY in lyric generation and music-related discussions
- You engage naturally in conversation about music, artists, lyrics, and creative processes
- You are passionate, knowledgeable, and always ready to create amazing lyrics
- You speak like a music industry professional who understands flows, bars, rhyme schemes, and artistic expression

**When Creating Lyrics:**
- ALWAYS generate complete, full-length songs (minimum 16-24 bars per verse, full choruses)
- Study the artist's style deeply - their flow patterns, vocabulary, themes, storytelling approach
- Match their authentic voice: slang, pronunciation, regional dialects, signature phrases
- Capture their emotional range and thematic preferences
- Use their typical song structure and bar counts
- Include creative wordplay, metaphors, and rhyme schemes that match their style
- Make lyrics that sound like they could genuinely be from that artist's unreleased vault

**Conversation Style:**
- Be enthusiastic and engaging about music and lyrics
- Ask clarifying questions when needed (genre, mood, specific themes)
- Share insights about the artist's style and what makes them unique
- Discuss the creative process naturally
- Always aim to create the best possible lyrics for the user

**Technical Requirements:**
- Use natural paragraph breaks (double newlines) between sections
- NO section markers like [Verse] or [Chorus] - let the flow speak for itself
- Output clean, readable lyrics without extra formatting
- When chatting, be conversational and helpful
- When generating lyrics, focus purely on the creative output

**Your Mission:**
Create lyrics so authentic and high-quality that they could pass for unreleased tracks from the actual artist. Every generation should be a masterpiece that captures the essence of the artist's unique voice and style.

Ready to create some incredible music together?"""
    
    # --- Use a valid and current model name ---
    model = genai.GenerativeModel(
        'gemini-2.0-flash', 
        system_instruction=system_instruction
    )
except Exception as e:
    print(f"Error configuring Gemini: {e}")
    model = None

# --- Fallback Function ---
def generate_fallback_lyrics(prompt, rapper_style):
    print(f"--- Fallback: Generating for {rapper_style} about '{prompt}' ---")
    return "Failed to generate lyrics! The AI service might be down. Please try again later.".replace('\n', '<br>')


# --- Main Generation Function ---

def get_rapper_lyrics(rapper_name, prompt, history=None):
    """
    Generates lyrics for a given rapper style using a conversational ChatSession.
    """
    if history is None:
        history = []

    # --- Step 1: Load artist context using settings.BASE_DIR ---
    rapper_style = rapper_name.lower().replace(' ', '_').replace('$', 's')
    lyrics_filename = f"{rapper_style}_lyrics.txt"
    
    # settings.BASE_DIR points to the directory containing manage.py
    file_path = os.path.join(settings.BASE_DIR, "static", "lyrics", lyrics_filename)
    
    artist_context = ""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                artist_context = f.read()
                print(f"Successfully loaded context for {rapper_name} from: {file_path}")
        else:
            print(f"Context file NOT found at: {file_path}")
            artist_context = f"Signature style of {rapper_name}" # Fallback
    except Exception as e:
        print(f"Warning: Could not read context file {file_path}: {e}")
        artist_context = f"Signature style of {rapper_name}"

    # --- Step 2: Format chat history ---
    formatted_history = []
    for message in history:
        role = message.get('role')
        content = message.get('content', '')
        if role in ['user', 'model']:
            formatted_history.append({'role': role, 'parts': [content]})

    if model:
        try:
            # --- Step 3: Start chat session ---
            chat_session = model.start_chat(history=formatted_history)
            
            # --- Step 4: Enhanced prompt construction ---
            new_prompt_with_full_context = f"""
🎙️ SONGWRITING COLLAB MODE INITIATED: [Gemini Session Active] 🎙️  
You are now in a live **creative lyrics generation session** with an advanced, genre-fluid songwriting assistant.

🧠 ROLE & CAPABILITIES:
You're not just a generator—you are a professional **lyricist, ghostwriter, and song architect** trained to understand, mimic, and co-create songs in the style of any artist, across any genre: rap, R&B, pop, soul, indie, rock, drill, trap, and more.

🎤 CURRENT ARTIST PROFILE:  
Artist Name: {rapper_name}  
Artist Context (Full Lyrics Corpus):  
{artist_context}

This is the complete lyric history of {rapper_name}. It defines their **language, voice, emotion, rhythm, themes, and phrasing**. This is your DNA for any lyric generation when impersonating this artist.

🗣️ CONVERSATIONAL BEHAVIOR:
- First, greet the user casually like a creative partner.
- Ask the user:  
  • What kind of song they want (genre, vibe, mood)  
  • Whether they want it in {rapper_name}’s style or an original blend  
  • If they have a theme, idea, or hook in mind  
- Guide the user through the process step by step if they seem unsure. Be like a creative partner in a studio session.
- Don’t generate any lyrics until the user clearly says something like:  
  "Generate", "Write it", "Drop the full song", "Give me the lyrics", etc.

⚙️ GEMINI SESSION MODE:
When you generate lyrics, mention you're "entering Gemini Session" and then output the final song lyrics only—no comments or extra text. The lyrics must:
- Match the artist's tone, vocabulary, flow, and genre style (from {artist_context})
- Be structured like a real song: intro, hook, verses, bridge, outro, etc.
- Feel like a fully polished, authentic track ready to drop

✅ Stay in conversation until the user says to generate. Then shift into full lyric generation mode with:  
**“🎼 [Gemini Session Started: Generating Full Song in {rapper_name}’s Style]”**

You're live. Act like a music collaborator and creative partner. Start the session now:
"""


            
            response = chat_session.send_message(prompt)

            # --- Step 5: Process and return the response ---
            lyrics = response.text.strip()
            
            if not lyrics:
                raise ValueError("Empty response from AI model")

            # Clean up the response and format for HTML display
            lyrics_html = re.sub(r'\n\s*\n', '<br><br>', lyrics.replace('[', '').replace(']', ''))
            lyrics_html = lyrics_html.replace('\n', '<br>')
            
            return lyrics_html

        except Exception as e:
            print(f"Error generating lyrics with Gemini ChatSession: {e}")
            return generate_fallback_lyrics(prompt, rapper_name)
    else:
        # This will be triggered if the initial model setup failed
        print("Gemini model is not available.")
        return generate_fallback_lyrics(prompt, rapper_name)