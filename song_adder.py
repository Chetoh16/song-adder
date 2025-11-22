import os
# Imports the os module to interact with the operating system. Specifically, os is used to generate a secret key for Flask.


from dotenv import find_dotenv, load_dotenv
dotenv_path = find_dotenv()

load_dotenv(dotenv_path)
# Fetching the Spotify client credentials from environment variables
client_id = os.getenv('client_id')
client_secret = os.getenv('client_secret')



# Rather than hardcoding the client secret and therefore giving away my precious code (which would bite me in the ass later if i were to publish this code)
# I created environmental variables and stored my client secret there
# I also gitignored that .env file so it doesn't show up in the repository

from spotipy.oauth2 import SpotifyClientCredentials
# Imports SpotifyClientCredentials from the spotipy.oauth2 module to authenticate the app using client credentials (for requests that don’t require user data).
import sys
# Imports the sys module to interact with the Python runtime environment. Though it’s not used directly in this code, it’s typically for system-specific parameters or function
# For example: sys.argv to get command line arguments
import pprint
# Imports pprint (pretty-print) to display data structures in a formatted, human-readable way. It is not directly used in this script.
import re
# Imports re, Python’s regular expression library, to work with pattern matching, used later in the script to extract the playlist ID from a URL.


from flask import Flask, request, redirect, session, url_for, render_template_string, render_template, jsonify   
# A session is just a place for our web server in this case flask to be able to access the data inside
# Imports several utilities from the Flask web framework:
# Flask is used to create a web server.
# request is for handling incoming HTTP requests.
# redirect is used for redirecting users to another route.
# session stores data between requests (used for storing authentication information).
# url_for is for generating URLs for routes.
# render_template_string allows rendering HTML directly from a string (instead of using separate template files).

from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from spotipy.cache_handler import FlaskSessionCacheHandler
# Modules we're using to set up our authorisation with Spotipy library and Spotify API
# Spotify is the main object for interacting with the Spotify Web API.
# SpotifyOAuth is used for authenticating with Spotify using OAuth (which allows access to user-specific data).
# FlaskSessionCacheHandler is used to manage the caching of the OAuth tokens using Flask’s session (so the user doesn’t need to log in every time).


app = Flask(__name__)
# Creates a Flask web application instance. __name__ is passed so Flask knows where to look for templates, static files, etc
app.config['SECRET_KEY'] = os.urandom(64)
# Generating a string of 64 random byte so users can't tamper with data
# Sets a secret key for the Flask app, which is used to sign session cookies for security. The key is randomly generated.

# Variables needed by spotipy
client_id = os.getenv('client_id')
client_secret = os.getenv('client_secret')
redirect_uri = 'http://localhost:5000/callback'
scope = 'playlist-read-private playlist-modify-private playlist-modify-public user-read-recently-played user-read-playback-state'

cache_handler = FlaskSessionCacheHandler(session)
# Creates a cache handler to store the OAuth access token in the Flask session, so users don’t have to log in repeatedly

sp_oauth = SpotifyOAuth(
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    scope=scope,
    cache_handler=cache_handler,
    show_dialog=True
)
# Initializes the SpotifyOAuth object, which manages authentication with Spotify’s API.
# Show_dialog=True forces Spotify to show the login dialog every time, which is useful for debugging.

sp = Spotify(oauth_manager=sp_oauth)
# Instance of spotify (spotify client)
# Creates a Spotify object (sp) that will be used to make requests to the Spotify API using the authentication manager (sp_oauth).
# Call methods on to get data

@app.route("/", methods=["GET", "POST"])
# Defines the route for the homepage (/). The home() function handles requests to this route.
def home():
    error_message = request.args.get('error_message')  # Get the error message if available
    # If we don't have this here it will say "error_message" is not defined at the end of this function
    if not sp_oauth.validate_token(cache_handler.get_cached_token()):
        # Checks whether the user is authenticated by validating the cached token stored in the Flask session.
        auth_url = sp_oauth.get_authorize_url()
        # If the token is not valid, the app generates an authorisation URL where the user can log in and grant permissions.
        return redirect(auth_url)
        # Redirects the user to the Spotify login page for authentication.
    if request.method == "POST":
        playlist_link = request.form.get("playlist_link")

        if not is_valid_playlist_link(playlist_link):  # Check if the link is valid
            return redirect(url_for("home", error_message="Invalid playlist link! Please enter a valid one."))

    return render_template('home.html', error_message=error_message)

# if the user is authenticated, the app renders an HTML form where the user can enter a Spotify playlist URL. If an error message exists, it’s displayed in a red box.
def is_valid_playlist_link(link):
    """Function to check if a playlist link is valid"""
    return link.startswith("https://") and "playlist" in link  # Example validation

@app.route('/process_playlist', methods=['POST'])
def process_playlist():
    playlist_url = request.form['playlist_url']
    # Extracts the playlist URL from the form submission
   
    allow_repeated_artists = request.form.get('allow_repeated_artists') == 'true'  # Capture the checkbox value as a boolean

    # Capturing whether the checkbox was checked or not

    playlist_id = extract_playlist_id(playlist_url)
    # Calls a helper function extract_playlist_id() to extract the playlist ID from the URL.

    if not playlist_id:
        return redirect(url_for('home', error_message="Invalid Playlist URL. Please try again."))
    # If the playlist ID is invalid, the user is redirected back to the homepage with an error message.
    
    tracks_info = search_and_add_songs_to_playlist(playlist_id, allow_repeated_artists)
    # Calls the search_and_add_songs_to_playlist() function to search for songs and add them to the specified playlist.
    
    # Return the feedback with all songs added, not found, and skipped
    # return render_template_string("""
    #     <h1>Song Processing Feedback</h1>
    #     <h3>Added to Playlist:</h3>
    #     <ul>
    #         {% for track in added_tracks %}
    #             <li>{{ track | safe }}</li>  <!-- Use 'safe' to render the HTML link correctly -->
    #         {% endfor %}
    #     </ul>
    #     <h3>Could Not Be Found:</h3>
    #     <ul>
    #         {% for track in not_found_tracks %}
    #             <li>{{ track }}</li>
    #         {% endfor %}
    #     </ul>
    #     <h3>Skipped Songs:</h3>
    #     <ul>
    #         {% for track in skipped_tracks %}
    #             <li>{{ track }}</li>
    #         {% endfor %}
    #     </ul>
    # """, added_tracks=tracks_info['added'], not_found_tracks=tracks_info['not_found'], skipped_tracks=tracks_info['skipped'])
    # Renders a feedback page displaying the results of the song processing: tracks added, tracks not found, and tracks skipped
    return render_template(
        'home.html',  # The template file
        added_tracks=tracks_info['added'],  # List of added tracks
        not_found_tracks=tracks_info['not_found'],  # List of not found tracks
        skipped_tracks=tracks_info['skipped']  # List of skipped tracks
    )

@app.route('/songs')
def songs():
    tracks_info = {
        'added': ['Song 1', 'Song 2', 'Song 3'],
        'not_found': ['Song A', 'Song B'],
        'skipped': ['Song X', 'Song Y', 'Song Z']
    }

    # Render the external HTML template
    return render_template(
        'templates/home.html', 
        added_tracks=tracks_info['added'], 
        not_found_tracks=tracks_info['not_found'], 
        skipped_tracks=tracks_info['skipped']
    )


def extract_playlist_id(url):
    # A helper function that uses regular expressions (re.search) to extract the playlist ID from the given Spotify URL.
    # Regular expression to match Spotify playlist URLs
    match = re.search(r"spotify\.com/playlist/([^?&/]+)", url)
    if match:
        return match.group(1)
    else:
        return None

def search_and_add_songs_to_playlist(playlist_id,allow_repeated_artists):
    # A function that processes the playlist by searching for songs from a text file (list_of_songs.txt) and adding them to the playlist.

    added_tracks = []
    # Empty list to store the information of tracks that were successfully added to the playlist.

    not_found_tracks = []
    # Empty list to store the names of songs that were not found on Spotify during the search.

    skipped_tracks = set()   
    # Empty set to track songs that were skipped (To track URIs of already added songs). Sets are used here to prevent duplicates since they do not allow repeated values.

    added_uris = set()
    # Empty set to store the URIs of tracks that have already been added to the playlist. Sets are used here to prevent duplicates since they do not allow repeated values.

    added_artists = set()
    # Empty set to store the artists of tracks that have already been added to the playlist.
    
    # Get existing tracks in the playlist
    playlist_tracks = sp.playlist_tracks(playlist_id)
    # Uses Spotipy sp.playlist_tracks() method to get the tracks in the specified playlist (using the playlist_id). This returns a dictionary that includes information about the tracks in the playlist.

    for item in playlist_tracks['items']:
        track = item['track']
        added_uris.add(item['track']['uri'])
        # Iterates over each track item in the playlist_tracks['items'] list, where each item is a dictionary containing information about a track in the playlist.
        # For each track item, the uri (a unique identifier for the track in Spotify) is added to the added_uris set. This will help later to check if a track is already in the playlist.
        
        #---------NEW----------#
        for artist in track['artists']:
            added_artists.add(artist['name'])  # Store existing artist names
        #---------NEW----------#
        


    with open('list_of_songs.txt', 'r') as file:
    # Opens the file list_of_songs.txt in read mode. This file is expected to contain a list of song names (one per line). The with statement ensures that the file is properly closed after reading.
        for line in file:
            query = line.strip().encode('windows-1252').decode('utf-8')
            # Strips any leading or trailing whitespace characters from the line.
            # Encodes the string into windows-1252 (a character encoding), and then decodes it back into utf-8. This step helps ensure compatibility with special characters or encoding issues that might arise when reading the file.
            # For example if the song has a ' symbol it can cause problems

            search_results = sp.search(q=query, type='track', limit=1)
            # Uses the Spotipy search() method to search Spotify for tracks that match the query. 
            # The q=query parameter specifies the search term (the song name), type='track' restricts the search to tracks only, and limit=1 ensures only one result is returned (the most relevant one).

            if search_results['tracks']['items']:
            # Checks if any tracks were returned from the search (search_results['tracks']['items']). If the list is not empty, it means the track was found on Spotify.
                track = search_results['tracks']['items'][0]
                # Retrieves the first track from the search results (since the search is limited to 1 result, this will be the top match).
                track_name = track['name']
                # Extracts the track's name from the search result.
                artist_name = ', '.join([artist['name'] for artist in track['artists']])
                # Joins the names of all the artists (if there are multiple artists for the track) into a single string, separated by commas. This is necessary because a track can have more than one artist.
                track_url = track['external_urls']['spotify']
                # Extracts the URL of the track on Spotify, which can be used to link to the track directly.
                track_uri = track['uri']
                # Extracts the URI of the track, which is a unique identifier used by the Spotify API to identify the track.
                
                # Check if track is already in the playlist
                if track_uri in added_uris:
                # Checks if the track's URI is already in the added_uris set, which means this track has already been added to the playlist
                    skipped_tracks.add(f"{track_name} by {artist_name}")
                    # If the track is already in the playlist, the song is skipped. The song's name and artist are added to the skipped_tracks set.
                
                #---------NEW----------#
                # Check for repeated artists if checkbox was unchecked
                elif not allow_repeated_artists and any(artist['name'] in added_artists for artist in track['artists']):
                    skipped_tracks.add(f"{track_name} by {artist_name} (Artist already in playlist)")
                #---------NEW----------#
                else:
                    sp.playlist_add_items(playlist_id=playlist_id, items=[track_uri])
                    # If the track is not already in the playlist, the sp.playlist_add_items() method is used to add the track to the playlist. 
                    # The playlist_id identifies the playlist, and items=[track_uri] is a list containing the track's URI to be added.
                    added_tracks.append(f"<a href='{track_url}'>{track_name} by {artist_name}</a>")
                    # Adds the track to the added_tracks list. The track name is wrapped in an HTML anchor (<a>) tag, linking to the track's Spotify page.
                    added_uris.add(track_uri)
                    # Adds the track’s URI to the added_uris set to track that it has been added to the playlist.
                    
                    #---------NEW----------#
                    for artist in track['artists']:
                        added_artists.add(artist['name'])  # Add new artist to set
                    #---------NEW----------#
            else:
                # Track not found
                not_found_tracks.append(query)
                # The song’s name (the query) is added to the not_found_tracks list.

    return {'added': added_tracks, 'not_found': not_found_tracks, 'skipped': skipped_tracks}
    #Returns a dictionary containing three lists:
    # 'added': The list of tracks that were successfully added to the playlist.
    # 'not_found': The list of tracks that could not be found on Spotify.
    # 'skipped': The list of tracks that were skipped because they were already in the playlist.



@app.route('/callback')
# Defines a route that Spotify will redirect to after the user logs in. The function retrieves the access token from the query parameters and stores it in the session.
def callback():
    sp_oauth.get_access_token(request.args['code'])
    # Retrieves the access token using the code from the query string (request.args['code']).

    return redirect(url_for('home'))
    # Redirects the user back to the homepage after the login is complete.




@app.route('/logout')
# Defines a route for logging out. This clears the session, effectively logging the user out of the app.
def logout():
    session.clear()
    # Clears the session data, logging out the user.
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
    #This block runs the Flask app when the script is executed. debug=True enables debug mode, so the server will restart automatically on code changes




