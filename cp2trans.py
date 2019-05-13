import os
import sys
import time
import json
import urllib
import random
import logging
import hashlib
import argparse
import configparser

import boto3
import MeCab
import romkan
import requests
import pyperclip
#import simpleaudio
from Crypto.Cipher import AES

# region consts
YOUDAO_API_HTTPS = 'https://openapi.youdao.com/api'
YOUDAO_API_ERROR = 'Youdao API error: {}'
YOUDAO_TTSAPI_HTTPS = 'https://openapi.youdao.com/ttsapi'
YOUDAO_TTS_ERROR = 'Youdao TTS API error: {}'
DEFAULT_SECTION = 'default'  # This section name is preserved.
# All available source language codes, should be the intersection of youdao and aws translate.
SOURCE_ALL = ('ja', )
# Youdao supported target languages.
TARGET_YOUDAO = ('zh-CHS', )
# AWS translate supported languages.
TARGET_AWS = ('en', )
ACCESS_READONLY_PROPERTY = 'Attempt to set a readonly property "{}".'
DIVIDING_TITLE = '- '*10+'{} '+'- '*10
DIVIDING_LINE = '= '*25
TEST_STRING = '8月3日に放送された「中居正広の金曜日のスマイルたちへ」(TBS系)で、1日たった5分で' \
              'ぽっこりおなかを解消するというダイエット方法を紹介。キンタロー。のダイエットにも密着。'
# endregion

# region global vars
aws_client = boto3.client('translate')
if not os.path.exists(os.path.join('c:', 'neologd')):
    logging.error('NEologd dictionary folder not found. Please checkout "README.md".')
    exit(1)
mecab_wakati = MeCab.Tagger('-Owakati -d C:\\neologd')
mecab_chasen = MeCab.Tagger('-Ochasen -d C:\\neologd')
# endregion

# region configparser
config = configparser.ConfigParser()
if not os.path.exists(os.path.join(os.path.dirname(__file__), 'config.ini')):
    logging.error('"config.ini" not found. Copy one from the "config.example.ini" file.')
    exit(1)
config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
try:
    appid = config.get("global", "appid")
    secretkey = config.get("global", "secretkey")
except configparser.NoSectionError as e:
    logging.error(e.message)
    exit(1)
if config.has_section(DEFAULT_SECTION):
    logging.error('Section name "{}" is preserved. Try another name.'.format(DEFAULT_SECTION))
    exit(1)
# endregion

# region argparse
parser = argparse.ArgumentParser(prog='cp2trans', description='Clipboard to Translate.')
# region profile
parser.add_argument('-p', '--profile',
                    dest='profile',
                    required=False,
                    metavar='section',
                    help='Load profiled options from the specified section of "config.ini" file.'
                         ' Any other options from command line will be ignored. See details in "config.example.ini".')
# endregion
# region logger
parser.add_argument('-l', '--log',
                    dest='log',
                    required=False,
                    metavar='log_file',
                    help='Save and read translation history from "log_file" to save API calls.'
                         ' File name will be "profile.encrypted.log" if encrypted.'
                    )
parser.add_argument('-e', '--encrypt',
                    dest='encrypt',
                    required=False,
                    metavar='password',
                    help='Encrypt logfile if you don\'t want it too exposed ;P.'
                         ' Have to be specified while loading an encrypted log file.'
                    )
# endregion
# region tts
parser.add_argument('-v', '--voice',
                    dest='voice',
                    required=False,
                    choices=('0', '1',),
                    default='0',
                    help='Voice of TTS. "0" for male and "1" for female. Unset for disable TTS.'
                    )
parser.add_argument('-m', '--match',
                    dest='match',
                    required=False,
                    metavar='pattern',
                    default=None,
                    help='Only TTS when match <pattern>.'
                    )
# endregion
# region translation
parser.add_argument('-s', '--source',
                    dest='source',
                    required=False,
                    metavar='lang_code',
                    default='ja',
                    help='Source language code. Romkan will only be shown with "ja".'
                    )
parser.add_argument('-t', '--target',
                    dest='target',
                    required=False,
                    metavar='lang_code',
                    default='zh-CHS,en',
                    help='Primary uses Youdao API and the secondary by AWS translate API.'
                    )
# endregion
# region text hook
parser.add_argument('-i', '--interval',
                    dest='interval',
                    required=False,
                    metavar='seconds',
                    type=float,
                    default=1.0,
                    help='Time interval in seconds to check the clipboard.'
                    )
parser.add_argument('-a', '--agth',
                    dest='agth',
                    required=False,
                    metavar='agth_path',
                    help='Start AGTH text hook.'
                         ' We will search current directory to find "agth.exe" if path is not specified.'
                         ' You might also have to specify -o option.')
parser.add_argument('-o', '--opt',
                    dest='opt',
                    required=False,
                    metavar='agth_opts',
                    help='Extra options passed to agth.exe.'
                         ' See details by the help button of agth.exe window.')
# endregion
# endregion


# region functions
def gen_salt_and_sign(text):
    salt = random.randint(1, 65536)
    sign = appid + text + str(salt) + secretkey
    m1 = hashlib.md5()
    m1.update(sign.encode('utf-8'))
    sign = m1.hexdigest()
    return str(salt), sign


def youdao_translate(text, target='zh-CHS', source='ja'):
    salt, sign = gen_salt_and_sign(text)
    params = {
        'appKey': appid,
        'q': urllib.parse.quote(text.encode('utf-8')),
        'from': source,
        'to': target,
        'salt': salt,
        'sign': sign,
    }
    r = requests.get(YOUDAO_API_HTTPS, params=params)
    if r.ok and 'application/json' in r.headers['Content-type']:
        return json.loads(r.text)['translation'][0]
    else:
        logging.error(YOUDAO_API_ERROR.format(r.status_code))
        return None


def youdao_tts(text, voice='1', lang_type='ja'):
    salt, sign = gen_salt_and_sign(text)
    params = {
        'appKey': appid,
        'q': urllib.parse.quote(text.encode('utf-8')),
        'lang_type': lang_type,
        'salt': salt,
        'sign': sign,
        'format': 'mp3',
        'voice': voice
    }
    r = requests.get(YOUDAO_API_HTTPS, params=params)
    if r.ok and 'audio/mp3' in r.headers['Content-Type']:
        return r.content
    elif 'application/json' in r.headers['Content-Type']:
        logging.error(YOUDAO_TTS_ERROR.format(json.loads(r.text)['errorCode']))
    else:
        logging.error(YOUDAO_TTS_ERROR.format(r.status_code))
    return None


def aws_translate(text, target='en', source='ja'):
    result_dict = aws_client.translate_text(Text=text,
                                            SourceLanguageCode=source,
                                            TargetLanguageCode=target)
    return result_dict.get('TranslatedText', None)
# endregion


# region crypto
def align(value):
    assert isinstance(value, str)

    while len(value) % 16 != 0:
        value += ' '
    return value


def encrypt(json_obj, key):
    assert isinstance(json_obj, dict)

    aes = AES.new(align(key), AES.MODE_CBC)
    return aes.encrypt(json.dumps(json_obj))


def decrypt(cipher, key):
    assert isinstance(cipher, bytes)

    aes = AES.new(align(key), AES.MODE_CBC)
    return json.loads(aes.decrypt(cipher))
# endregion


# region main loop
def main_loop(profile):
    paste = pyperclip.paste()
    while True:
        if paste == pyperclip.paste():
            continue
        paste = pyperclip.paste()
        # region from log
        if paste in profile.log:
            print(DIVIDING_TITLE.format('SOURCE (from log)'))
            print(profile.log[paste]['source'])
            if 'romkan' in profile.log[paste]:
                print(DIVIDING_TITLE.format('ROMKAN (from log)'))
                print(profile.log[paste]['romkan'])
            print(DIVIDING_TITLE.format('YOUDAO (from log)'))
            print(profile.log[paste]['youdao'])
            print(DIVIDING_TITLE.format('AWS (from log)'))
            print(profile.log[paste]['aws'])
            print(DIVIDING_LINE)
            continue
        # endregion
        # region source
        print(DIVIDING_TITLE.format('SOURCE'))
        if profile.source == 'ja':
            source = mecab_wakati.parse(paste).rstrip()
            print(source)  # rstrip() to remove ' \n' at the end.
        else:
            source = paste
            print(source)
        # endregion
        # region romkan
        if profile.source == 'ja':
            print(DIVIDING_TITLE.format('ROMKAN'))
            chasen_list, roma_text = mecab_chasen.parse(paste), ''
            for line in chasen_list.split('\n'):
                if line != '' and line != 'EOS':
                    items = line.split('\t')
                    roma_text += romkan.to_roma(items[1]) + ' '
            print(roma_text)
        else:
            roma_text = None
        # endregion
        # region youdao
        print(DIVIDING_TITLE.format('YOUDAO'))
        youdao = youdao_translate(paste, target=profile.target[0], source=profile.source)
        print(youdao)
        # endregion
        # region aws
        print(DIVIDING_TITLE.format('AWS'))
        aws = aws_translate(paste, target=profile.target[1], source=profile.source)
        print(aws)
        # endregion
        # region tts
        if profile.voice:
            pass
            #TODO
        # endregion
        # region save log (in memory)
        profile.log[paste] = {}
        profile.log[paste]['source'] = source
        profile.log[paste]['romkan'] = roma_text
        profile.log[paste]['youdao'] = youdao
        profile.log[paste]['aws'] = aws
        # endregion
        print(DIVIDING_LINE)
        time.sleep(profile.interval)
# endregion


# region profile
class Profile:

    # region constructor and destructor
    def __init__(self, section, log, encrypt, voice, match, source, target, interval, agth, opt):
        # region overwrite options
        if section:
            if not config.has_section(section):
                logging.error('No such section "{}" in "config.ini"'.format(args.profile))
                exit(1)
            log = config.get(section, 'log', fallback=section+'.json')
            encrypt = config.get(section, 'encrypt', fallback=None)
            voice = config.get(section, 'voice', fallback='0')
            match = config.get(section, 'match', fallback=None)
            source = config.get(section, 'source', fallback='ja')
            target = config.get(section, 'target', fallback='zh-CHS,en')
            interval = config.getfloat(section, 'interval', fallback=1.0)
            agth = config.get(section, 'agth', fallback=None)
            opt = config.get(section, 'opt', fallback=None)
        else:
            self._section = DEFAULT_SECTION
        # endregion
        # region init log, encrypt
        self._encrypt = None
        if log:
            self._log_filename = log
            if not os.path.isfile(log):
                logging.error('File "{}" not found.'.format(log))
                exit(1)
            if encrypt:
                self._encrypt = encrypt
                with open(os.path.join(os.path.dirname(__file__), log), 'rb') as f:
                    self._log = json.loads(decrypt(f.read(), encrypt))
            else:
                with open(os.path.join(os.path.dirname(__file__), log), 'r') as f:
                    self._log = json.loads(f.read())
        else:
            self._log_filename = DEFAULT_SECTION + '.json'
            if os.path.exists(os.path.join(os.path.dirname(__file__), self._log_filename)):
                with open(os.path.join(os.path.dirname(__file__), self._log_filename), 'r+') as f:
                    self._log = json.loads(f.read())
            else:
                self._log = {}
        # endregion
        # region init tts, voice
        if voice and voice not in ('0', '1'):
            logging.warning('--voice option "{}" might be invalid.'.format(voice))
        self._voice = voice
        self._match = match
        # endregion
        # region init source, target
        if source not in SOURCE_ALL:
            logging.error('--source option "{}" is not supported.'.format(source))
            exit(1)
        targets = target.split(',')
        if len(targets) != 2:
            logging.error('--target option "{}" format error.'.format(target))
            exit(1)
        if targets[0] not in TARGET_YOUDAO:
            logging.error('--target option "{}" not supported by youdao.'.format(targets[0]))
            exit(1)
        if targets[1] not in TARGET_AWS:
            logging.error('--target option "{}" not supported by aws.'.format(targets[1]))
            exit(1)
        self._source = source
        self._target = (targets[0], targets[1], )
        # endregion
        # region init interval, agth, opt
        self._interval = interval
        self._agth = agth if agth else os.path.join(__file__, 'agth.exe')
        self._opt = opt
        # endregion
    # endregion

    # region getters and setters
    @property
    def section(self):
        if self._section == DEFAULT_SECTION:
            logging.warning('Cannot call default section. Continue...')
            return None
        return self._section

    @section.setter
    def section(self, value):
        logging.warning(ACCESS_READONLY_PROPERTY.format('section'))

    @property
    def log(self):
        return self._log

    @log.setter
    def log(self, value):
        self._log = value

    @property
    def encrypt(self):
        return self._encrypt

    @encrypt.setter
    def encrypt(self, value):
        logging.warning(ACCESS_READONLY_PROPERTY.format('encrypt'))

    @property
    def voice(self):
        return self._voice

    @voice.setter
    def voice(self, value):
        logging.warning(ACCESS_READONLY_PROPERTY.format('voice'))

    @property
    def match(self):
        return self._match

    @match.setter
    def match(self, value):
        logging.warning(ACCESS_READONLY_PROPERTY.format('match'))

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        logging.warning(ACCESS_READONLY_PROPERTY.format('source'))

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, value):
        logging.warning(ACCESS_READONLY_PROPERTY.format('target'))

    @property
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, value):
        logging.warning(ACCESS_READONLY_PROPERTY.format('interval'))

    @property
    def agth(self):
        return self._agth

    @agth.setter
    def agth(self, value):
        logging.warning(ACCESS_READONLY_PROPERTY.format('agth'))

    @property
    def opt(self):
        return self._opt

    @opt.setter
    def opt(self, value):
        logging.warning(ACCESS_READONLY_PROPERTY.format('opt'))
    # endregion

    # region public functions
    def save_log(self):
        if self._encrypt:
            with open(self._log_filename, 'wb') as f:
                f.write(encrypt(json.dumps(self._log), self.encrypt))
        else:
            with open(self._log_filename, 'w') as f:
                f.write(json.dumps(self._log))
    # endregion
# endregion


# region program entry
if __name__ == "__main__":
    args = parser.parse_args(sys.argv[1:])
    profile = Profile(args.profile, args.log, args.encrypt, args.voice, args.match, args.source, args.target,
                      args.interval, args.agth, args.opt)
    try:
        main_loop(profile)
    except KeyboardInterrupt:
        logging.info('Saving to "{}.log". Please wait...')
        profile.save_log()  # save log in disk.
        logging.info('done.')
# endregion
