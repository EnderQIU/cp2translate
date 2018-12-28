import pyperclip
import time
import hashlib
import urllib
import random
import json
import romkan
import boto3
import MeCab
import requests


def youdao_translate(text, to='zh-CHS', fr='ja'):
    appkey = None
    secretkey = None

    salt = random.randint(1, 65536)
    sign = appkey + text + str(salt) + secretkey
    m1 = hashlib.md5()
    m1.update(sign.encode('utf-8'))
    sign = m1.hexdigest()

    try:
        url = 'http://openapi.youdao.com/api'
        params = {
        	'appKey': appkey,
        	'q': urllib.parse.quote(text.encode('utf-8')),
        	'from': fr,
        	'to': to,
        	'salt': str(salt),
        	'sign': sign,
        }
        r = requests.get(url, params=params)
        result = json.loads(r.text)['translation'][0]
        return result
    except Exception as e:
        print(e)


if __name__ == "__main__":
	client = boto3.client('translate')
	mecab_wakati = MeCab.Tagger('-Owakati -d C:\\neologd')
	mecab_chasen = MeCab.Tagger('-Ochasen -d C:\\neologd')
	clip_board = pyperclip.paste()
	while True:
		if clip_board != pyperclip.paste():
			clip_board = pyperclip.paste()
			print("- - - - - - - - - - - - -  SOURCE  - - - - - - - - - - - - - ")
			print(mecab_wakati.parse(clip_board).rstrip())
			print("- - - - - - - - - - - - -  ROMKAN  - - - - - - - - - - - - - ")
			chasen_list = mecab_chasen.parse(clip_board)
			roma_text = ''
			for line in chasen_list.split('\n'):
				if line != '' and line != 'EOS':
					items = line.split('\t')
					roma_text += romkan.to_roma(items[1]) + ' '
			print(roma_text)
			print("- - - - - - - - - - - - -  CHINESE  - - - - - - - - - - - - - - ")
			print(youdao_translate(clip_board))
			print("- - - - - - - - - - - - -  ENGLISH  - - - - - - - - - - - - - - ")
			text = clip_board
			print(client.translate_text(Text=text, SourceLanguageCode="ja", TargetLanguageCode='en').get('TranslatedText', 'AWS TRANSLATION ERROR'))
			print('= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ')
		else:
			time.sleep(1)
