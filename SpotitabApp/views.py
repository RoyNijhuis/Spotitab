from django.http import HttpResponseRedirect

from django.shortcuts import render
from spotipy.oauth2 import SpotifyClientCredentials
import spotipy
import spotipy.util as util
import spotipy.oauth2 as oauth2
from bs4 import BeautifulSoup

import requests

sp_oauth = None
sp = None
# Create your views here.
def index(request):
    return render(request, 'index.html')

def spotify_login(request):
    global sp_oauth, sp
    sp_oauth = oauth2.SpotifyOAuth("a1481cb1af0444d9bfd32d5d23b167d5", "3ec7943b2e4d4e008ed161c129173b6a", "http://localhost:8000/user", scope='playlist-read-private', cache_path=".cache-")
    auth_url = sp_oauth.get_authorize_url()
    return HttpResponseRedirect(auth_url)

def user(request):
    global sp_oauth, sp
    if request.GET.get('code', None) != None:
        token_info = sp_oauth.get_access_token(request.GET['code'])
        sp = spotipy.Spotify(auth=token_info['access_token'])

        return HttpResponseRedirect(redirect_to='/user')
    else:
        data = {}

        #Retrieve all playlists
        playlists = sp.user_playlists(sp.current_user()['id'])
        list = parse_playlists(playlists)
        data['playlists'] = list

        #Check if playlist is selected and retrieve all songs
        playlist = request.GET.get('playlist', None)
        if playlist != None:
            result = sp.user_playlist(sp.current_user()['id'], playlist)
            tracks = []
            for track in result['tracks']['items']:
                artist = track['track']['artists'][0]['name']
                song = track['track']['name']
                id = track['track']['id']
                tracks.append([id, artist, song])
            data['tracks'] = tracks

        #Check if tabs or chords should be displayed
        trackID = request.GET.get('track', None)
        if trackID != None:
            track = sp.track(trackID)
            artist = track['artists'][0]['name']
            song = track['name']
            data['song_data'] = [artist, song]

            #Find tabs/chords
            all_song_data = parse_song(artist, song)
            tabs = parse_tabs(all_song_data)
            chords = parse_chords(all_song_data)
            if tabs is not None:
                data['tabs'] = tabs
            if chords is not None:
                data['chords'] = chords
        return render(request, 'user.html', data)


def parse_playlists(raw):
    list = {}
    for item in raw['items']:
        list[item['id']] = item['name']
    return list

def parse_song(artist, song):
    global sp
    r  = requests.get("https://www.ultimate-guitar.com/search.php?search_type=title&order=&value=" + artist + " " + song)
    data = r.content
    soup = BeautifulSoup(data, "html.parser")
    a_elements = soup.find_all("a", class_="song result-link")
    song_data = []
    for a in a_elements:
        link = a.get("href")
        tr = a.parent.parent
        votes = tr.find("b", class_="ratdig")
        if(votes != None):
            votes = votes.text
        rating = tr.find("span", class_="rating")
        if(rating != None):
            rating = rating.find("span").get("class")
            if rating != None:
                rating = rating[0].split("_")[1]
        type = tr.find("strong")
        if(type != None):
            type = type.text

        if votes != None and rating != None and link != None and type != None:
            song_data.append([link, rating, votes, type])
    return song_data

def parse_tabs(all_song_data):

    #Isolate tabs and find the best candidate
    tabList = []
    for entry in all_song_data:
        if entry[3] == "tab":
            tabList.append(entry)

    bestTabScore = -1
    bestTab = None

    for tab in tabList:
        tabScore = int(tab[1])*int(tab[2])
        if tabScore > bestTabScore:
            bestTabScore = tabScore
            bestTab = tab

    if(bestTab == None):
        return None

    #Fetch the tabpage and get the tabs
    tabPage  = requests.get(bestTab[0]).text
    soup = BeautifulSoup(tabPage, "html.parser")
    tab_content = soup.find("pre", class_="js-tab-content").text
    print(tab_content)
    return tab_content

def parse_chords(all_song_data):
    #Isolate chords and find the best candidate
    chordList = []
    for entry in all_song_data:
        if entry[3] == "chords":
            chordList.append(entry)

    bestChordScore = -1
    bestChord = None

    for chord in chordList:
        chordScore = int(chord[1])*int(chord[2])
        if chordScore > bestChordScore:
            bestChordScore = chordScore
            bestChord = chord

    if(bestChord == None):
        return None

    #Fetch the chordpage and get the tabs
    chordPage  = requests.get(bestChord[0]).text
    soup = BeautifulSoup(chordPage, "html.parser")
    chord_content = soup.find("pre", class_="js-tab-content").text
    print(chord_content)
    return chord_content