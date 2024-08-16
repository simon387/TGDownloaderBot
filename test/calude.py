import yt_dlp as youtube_dl

def download_video(url):
	ydl_opts = {
		'verbose': True
	}
	with youtube_dl.YoutubeDL(ydl_opts) as ydl:
		ydl.download([url])

# Esempio di utilizzo
url = "https://www.youtube.com/shorts/ZUMSc0XTr00?feature=share"
download_video(url)