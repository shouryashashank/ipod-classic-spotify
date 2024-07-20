import gradio as gr
import os
from spt import *
# Assuming all necessary imports and functions from the provided script are already included here

def spotify_downloader(fetch_again, spotify_url, only_new_songs, resume_download):
    if fetch_again == "Yes":
        url = validate_url(spotify_url)
        if "track" in url:
            songs = [get_track_info(url)]
        elif "playlist" in url:
            songs = get_playlist_info(url)
        # pickle the songs list
        with open("songs.pkl", "wb") as f:
            pickle.dump(songs, f)
        # Assuming the rest of the logic for downloading songs is encapsulated in a function `download_songs`
        download_status = download_songs(songs, only_new_songs, resume_download)
        return download_status
    else:
        with open("songs.pkl", "rb") as f:
            songs = pickle.load(f)

# Define Gradio interface components
with gr.Blocks() as demo:
    gr.Markdown("### Spotify Downloader")
    with gr.Row():
        fetch_again = gr.Radio(["Yes", "No"], label="Fetch Spotify data again?")
        spotify_url = gr.Textbox(label="Enter a Spotify URL:")
        only_new_songs = gr.Radio(["Yes", "No"], label="Only download new songs?")
        resume_download = gr.Radio(["Yes", "No"], label="Resume download?")
    submit_button = gr.Button("Download")
    output = gr.Textbox(label="Download Status")

    submit_button.click(
        spotify_downloader,
        inputs=[fetch_again, spotify_url, only_new_songs, resume_download],
        outputs=output
    )

demo.launch()