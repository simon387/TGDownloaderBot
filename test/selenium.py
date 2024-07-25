from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time

def download_tiktok_video(url, output_path):
	# Setup del webdriver
	service = Service(ChromeDriverManager().install())
	options = webdriver.ChromeOptions()
	options.add_argument('--headless')  # Esegui il browser in modalità headless
	driver = webdriver.Chrome(service=service, options=options)

	# Carica la pagina di TikTok
	driver.get(url)
	time.sleep(5)  # Attendi che la pagina si carichi completamente

	# Trova l'elemento video
	video_elements = driver.find_elements_by_tag_name('video')
	if video_elements:
		video_url = video_elements[0].get_attribute('src')

		# Scarica il video
		if video_url:
			video_response = requests.get(video_url, stream=True)
			with open(output_path, 'wb') as f:
				for chunk in video_response.iter_content(chunk_size=8192):
					if chunk:
						f.write(chunk)
			print(f"Video scaricato e salvato in {output_path}")
		else:
			print("Impossibile trovare il link del video.")
	else:
		print("Impossibile trovare l'elemento video.")

	# Chiudi il driver
	driver.quit()

# Esempio di utilizzo
tiktok_url = "https://www.tiktok.com/@username/video/1234567890123456789"
output_file = "tiktok_video.mp4"
download_tiktok_video(tiktok_url, output_file)
