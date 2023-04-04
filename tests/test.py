# coding=utf8
# the above tag defines encoding for this document and is for Python 2.x compatibility

import re

regex = r"\S+\.mp3"

test_str = ("[youtube] K9mTSekTktw: Downloading android player API JSON\n"
			"[info] K9mTSekTktw: Downloading 1 format(s): 251\n"
			"[download] Rauw_Alejandro_Chencho_Corleone_-_Desesperados_Video_Oficial-[K9mTSekTktw].mp3 has already been downloaded\n"
			"[ExtractAudio] Not converting audio Rauw_Alejandro_Chencho_Corleone_-_Desesperados_Video_Oficial-[K9mTSekTktw].mp3; file is already in target format mp3")

matches = re.finditer(regex, test_str, re.MULTILINE)

for matchNum, match in enumerate(matches, start=1):

	print ("Match {matchNum} was found at {start}-{end}: {match}".format(matchNum = matchNum, start = match.start(), end = match.end(), match = match.group()))

	# for groupNum in range(0, len(match.groups())):
	# 	groupNum = groupNum + 1
	#
	# 	print ("Group {groupNum} found at {start}-{end}: {group}".format(groupNum = groupNum, start = match.start(groupNum), end = match.end(groupNum), group = match.group(groupNum)))

# Note: for Python 2.7 compatibility, use ur"" to prefix the regex and u"" to prefix the test string and substitution.