import re


def extract_first_url(text):
	url_pattern = re.compile(r"https?://(?:[a-zA-Z]|[0-9]|[$-_]|[!*\\(),])+")
	matches = re.findall(url_pattern, text)
	if matches:
		return matches[0]
	else:
		return None


def contains_valid_url(msg):
	return is_from_yt(msg) or \
		"facebook.com/" in msg or \
		"https://fb.watch/" in msg or \
		"https://www.instagram.com/" in msg or \
		"https://www.tiktok.com/" in msg or \
		"https://vm.tiktok.com/" in msg or \
		"https://twitter.com/" in msg or \
		"https://x.com/" in msg


def is_from_yt(url):
	return ("https://www.youtube." in url and "/watch?" in url) or \
		"https://www.youtube.com/shorts/" in url or \
		"https://youtube.com/shorts/" in url or \
		"https://youtu.be/" in url
