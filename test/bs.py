import requests
from bs4 import BeautifulSoup


def download_tiktok_video(url, output_path):
	headers = {
		"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
	}

	response = requests.get(url, headers=headers)
	soup = BeautifulSoup(response.text, 'html.parser')

	video_url = None
	for video in soup.find_all("video"):
		video_url = video['src']
		break

	if video_url:
		video_response = requests.get(video_url, headers=headers)
		with open(output_path, 'wb') as f:
			f.write(video_response.content)
		print(f"Video scaricato e salvato in {output_path}")
	else:
		print("Impossibile trovare il video.")


# Esempio di utilizzo
tiktok_url = "https://www.tiktok.com/@the.rookie5138/video/7394333292490657070"
output_file = "tiktok_video.mp4"
download_tiktok_video(tiktok_url, output_file)
