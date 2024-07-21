import gradio as gr
import os
from spt import *
# Assuming all necessary imports and functions from the provided script are already included here
file_exists_action = "SA"
def spotify_downloader(fetch_again, spotify_url, only_new_songs, resume_download, songs_exists):
    global file_exists_action
    file_exists_action = songs_exists
    if fetch_again :
        url = validate_url(spotify_url)
        if "track" in url:
            songs = [get_track_info(url)]
        elif "playlist" in url:
            songs = get_playlist_info(url)
        # pickle the songs list
        with open("songs.pkl", "wb") as f:
            pickle.dump(songs, f)
        # Assuming the rest of the logic for downloading songs is encapsulated in a function `download_songs`
        # download_status = download_songs(songs, only_new_songs, resume_download)
        # return download_status
    else:
        with open("songs.pkl", "rb") as f:
            songs = pickle.load(f)
    start = time.time()
    downloaded = 0
    song_name_list = []
    if os.path.exists("song_names.txt"):
        if only_new_songs:  
            with open("song_names.txt", "r") as f:
                song_name_list = f.read().splitlines()
    # check if downloaded.txt exists
    if os.path.exists("downloaded.txt"):
        if resume_download:  
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

# Define Gradio interface components
with gr.Blocks() as demo:
    gr.Markdown("### Spotify Downloader")
    with gr.Row():
        fetch_again = gr.Radio([("Yes", True), ("No", False)], label="Fetch Spotify data again?", value=False)
        spotify_url = gr.Textbox(label="Enter a Spotify URL:")
        only_new_songs = gr.Radio([("Yes", True), ("No", False)], label="Only download new songs?", value=False)
        resume_download = gr.Radio([("Yes", True), ("No", False)], label="Resume download?", value=False)
        songs_exists = gr.Radio([("Skip All", "SA"), ("Re-download All", "RA")], label="What to do if the song exists?", value="SA")
    submit_button = gr.Button("Download")
    output = gr.Textbox(label="Download Status")

    submit_button.click(
        spotify_downloader,
        inputs=[fetch_again, spotify_url, only_new_songs, resume_download, songs_exists],
        outputs=output
    )

demo.launch()