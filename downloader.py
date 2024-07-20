import os
import re
import shutil
import time
import urllib.request
import pickle
import requests
from tqdm import tqdm
import spotipy
from moviepy.editor import *
from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3
from pytube import YouTube
import pytube.exceptions
from rich.console import Console
from spotipy.oauth2 import SpotifyClientCredentials

SPOTIPY_CLIENT_ID = ""
SPOTIPY_CLIENT_SECRET = ""

client_credentials_manager = SpotifyClientCredentials(
    client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


def main():
    if input("fetch spotify again[y/N]:").strip() == "y":
        url = validate_url(input("Enter a spotify url: ").strip())
        if "track" in url:
            songs = [get_track_info(url)]
        elif "playlist" in url:
            songs = get_playlist_info(url)
        # pickle the songs list
        with open("songs.pkl", "wb") as f:
            pickle.dump(songs, f)
    else:
        with open("songs.pkl", "rb") as f:
            songs = pickle.load(f)
    start = time.time()
    downloaded = 0
    song_name_list = []
    if os.path.exists("song_names.txt"):
        if input("only download the songs that are not already downloaded [y/n]: ").strip() == "y":  
            with open("song_names.txt", "r") as f:
                song_name_list = f.read().splitlines()
    # check if downloaded.txt exists
    if os.path.exists("downloaded.txt"):
        if input("Resume download? [y/n]: ").strip() == "y":  
            with open("downloaded.txt", "r") as f:
                downloaded = int(f.read())
    for i, track_info in (enumerate(tqdm(songs), start=1)):
        if track_info["track_title"] in song_name_list:
            continue
        if downloaded >= i:
            continue
        search_term = f"{track_info['artist_name']} {track_info['track_title']} audio"
        video_link = find_youtube(search_term)
        audio = download_yt(video_link,search_term)
        if audio:
            # track_info["track_number"] = downloaded + 1
            set_metadata(track_info, audio)
            os.replace(audio, f"../music/{os.path.basename(audio)}")
            downloaded += 1
            # save the downloaded count to a file
            with open("downloaded.txt", "w") as f:
                f.write(str(downloaded))
        # else:
            # print("File exists. Skipping...")
    shutil.rmtree("../music/tmp")
    end = time.time()
    print()
    os.chdir("../music")
    print(f"Download location: {os.getcwd()}")
    console.print(
        f"DOWNLOAD COMPLETED: {downloaded}/{len(songs)} song(s) dowloaded".center(
            70, " "
        ),
        style="on green",
    )
    console.print(
        f"Total time taken: {round(end - start)} sec".center(70, " "), style="on white"
    )


def validate_url(sp_url):
    if re.search(r"^(https?://)?open\.spotify\.com/(playlist|track)/.+$", sp_url):
        return sp_url

    raise ValueError("Invalid Spotify URL")


def get_track_info(track_url):
    res = requests.get(track_url)
    if res.status_code != 200:
        # retry 3 times
        for i in range(3):
            res = requests.get(track_url)
            if res.status_code == 200:
                break
    if res.status_code != 200:
        print("Invalid Spotify track URL")

    track = sp.track(track_url)

    track_metadata = {
        "artist_name": track["artists"][0]["name"],
        "track_title": track["name"],
        "track_number": track["track_number"],
        "isrc": track["external_ids"]["isrc"],
        "album_art": track["album"]["images"][1]["url"],
        "album_name": track["album"]["name"],
        "release_date": track["album"]["release_date"],
        "artists": [artist["name"] for artist in track["artists"]],
    }

    return track_metadata


def get_playlist_info(sp_playlist):
    res = requests.get(sp_playlist)
    if res.status_code != 200:
        raise ValueError("Invalid Spotify playlist URL")
    pl = sp.playlist(sp_playlist)
    if not pl["public"]:
        raise ValueError(
            "Can't download private playlists. Change your playlist's state to public."
        )
    playlist = sp.playlist_tracks(sp_playlist)

    tracks_item = playlist['items']

    while playlist['next']:
        playlist = sp.next(playlist)
        tracks_item.extend(playlist['items'])

    tracks = [item["track"] for item in tracks_item]
    tracks_info = []
    track_id = []
    # load tracks_id from synced.txt
    if os.path.exists("synced.txt"):
        with open("synced.txt", "r") as f:
            track_id = f.read().splitlines()
    updated_tracks = []
    for track in tqdm(tracks):
        updated_tracks.append(track["id"])
        if track["id"] in track_id:
            continue
        track_url = f"https://open.spotify.com/track/{track['id']}"
        track_info = get_track_info(track_url)
        # make a progress bar
        
        tracks_info.append(track_info)
    # save the updated tracks_id to synced_updated.txt
    with open("synced_updated.txt", "w") as f:
        f.write("\n".join(updated_tracks))
    return tracks_info


def find_youtube(query):
    query = query.replace("é", "e")
    query = query.replace("’", "")
    query = query.replace("æ", "ae")
    query = query.replace("ñ", "n")
    query = query.replace("–", "+")
    query = query.replace("‘", "")
    query = query.replace("ú", "u")
    

    phrase = query.replace(" ", "+")
    search_link = "https://www.youtube.com/results?search_query=" + phrase
    count = 0
    while count < 5:
        try:
            response = urllib.request.urlopen(search_link)
            break
        except:
            count += 1
    else:
        raise ValueError("Please check your internet connection and try again later.")

    search_results = re.findall(r"watch\?v=(\S{11})", response.read().decode())
    first_vid = "https://www.youtube.com/watch?v=" + search_results[0]

    return first_vid


def prompt_exists_action():
    """ask the user what happens if the file being downloaded already exists"""
    global file_exists_action
    if file_exists_action == "SA":  # SA == 'Skip All'
        return False
    elif file_exists_action == "RA":  # RA == 'Replace All'
        return True

    print("This file already exists.")
    while True:
        resp = (
            input("replace[R] | replace all[RA] | skip[S] | skip all[SA]: ")
            .upper()
            .strip()
        )
        if resp in ("RA", "SA"):
            file_exists_action = resp
        if resp in ("R", "RA"):
            return True
        elif resp in ("S", "SA"):
            return False
        print("---Invalid response---")

def download_yt(yt_link,search_term):
    """download the video in mp3 format from youtube"""
    yt = YouTube(yt_link)
    # remove chars that can't be in a windows file name
    yt.title = "".join([c for c in yt.title if c not in ['/', '\\', '|', '?', '*', ':', '>', '<', '"']])
    # don't download existing files if the user wants to skip them
    exists = os.path.exists(f"../music/{yt.title}.mp3")
    if exists and not prompt_exists_action():
        return False

    # download the music
    max_retries = 3
    attempt = 0
    video = None

    while attempt < max_retries:
        try:
            video = yt.streams.filter(only_audio=True).first()
            if video:
                break
        except Exception as e:
            print(f"Attempt {attempt + 1}  {search_term} failed due to: {e}")
            attempt += 1
    if not video:
        print(f"Failed to download {search_term}")
        # check if a file named failed_downloads.txt exists if not create one and append the failed download
        if not os.path.exists("failed_downloads.txt"):
            with open("failed_downloads.txt", "w") as f:
                f.write(f"{search_term}\n")
        else:
            with open("failed_downloads.txt", "a") as f:
                f.write(f"{search_term}\n")
        return False
    vid_file = video.download(output_path="../music/tmp")
    # convert the downloaded video to mp3
    base = os.path.splitext(vid_file)[0]
    audio_file = base + ".mp3"
    mp4_no_frame = AudioFileClip(vid_file)
    mp4_no_frame.write_audiofile(audio_file, logger=None)
    mp4_no_frame.close()
    os.remove(vid_file)
    os.replace(audio_file, f"../music/tmp/{yt.title}.mp3")
    audio_file = f"../music/tmp/{yt.title}.mp3"
    return audio_file


def set_metadata(metadata, file_path):
    """adds metadata to the downloaded mp3 file"""

    mp3file = EasyID3(file_path)

    # add metadata
    mp3file["albumartist"] = metadata["artist_name"]
    mp3file["artist"] = metadata["artists"]
    mp3file["album"] = metadata["album_name"]
    mp3file["title"] = metadata["track_title"]
    mp3file["date"] = metadata["release_date"]
    mp3file["tracknumber"] = str(metadata["track_number"])
    mp3file["isrc"] = metadata["isrc"]
    mp3file.save()

    # add album cover
    audio = ID3(file_path)
    with urllib.request.urlopen(metadata["album_art"]) as albumart:
        audio["APIC"] = APIC(
            encoding=3, mime="image/jpeg", type=3, desc="Cover", data=albumart.read()
        )
    audio.save(v2_version=3)


if __name__ == "__main__":
    file_exists_action = ""
    console = Console()
    main()