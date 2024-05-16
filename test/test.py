import sys
import youtube_dl
import os

try:
	# getting URL from the user
	url = input("Enter the url of the facebook video to be downloaded: ")
	print("Choose a video resolution to start downloading:-")
	print("1. 1080p(HD)")
	print("2. 720p")
	print("3. 480p(SD)")
	print("4. 360p")
	print("5. 180p")
	print("6.Any available resolution")
	# getting value of resolution from user
	option = int(input("Enter your option (1 - 6): "))
	if(option == 1):
		y = {"format": "(mp4,webm)[height<=1080]"}
	elif(option == 2):
		y = {"format": "(mp4,webm)[height<=720]"}
	elif (option == 3):
		y = {"format": "(mp4,webm)[height<=480]"}
	elif (option == 4):
		y = {"format": "(mp4,webm)[height<=360]"}
	elif (option == 5):
		y = {"format": "(mp4,webm)[height<=180]"}
	elif (option == 6):
		y = {}

	else:
		print("Option not available")
		y = {}

	# setting path to download the video
	path = "C:\dev"
	os.chdir(path)
	# start downloading the video using provided options
	with youtube_dl.YoutubeDL(y) as u:
		print("Downloading........."+url)
		# download the video
		u.show_download_buttons([url])
except Exception as asd:
	print("Invalid link or selected resolution unavailable!")
	sys.exit(1)

print("Download completed !!!")