import os
import sys
import time
import json
import urllib
import random
import getpass
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
CREATE_A_NOT_EXISTS_FILE = 'File "{}" not exists. Will create a new one when exit.'
WRONG_PASSWORD = 'Failed to load "{}" with a wrong password.'
PASSWORD_NOT_SPECIFIED = '"{}" maybe encrypted. Use --encrypt option to specify password.'
FILE_NOT_FOUND = 'File "{}" not found.'
# endregion

# region global vars
aws_client = boto3.client('translate')
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
if not os.path.exists(os.path.join('C:\\', 'neologd')):
    logger.error('NEologd dictionary folder not found. Please checkout "README.md".')
    exit(1)
mecab_wakati = MeCab.Tagger('-Owakati -d C:\\neologd')
mecab_chasen = MeCab.Tagger('-Ochasen -d C:\\neologd')
# endregion

# region configparser
config = configparser.ConfigParser()
if not os.path.exists(os.path.join(os.path.dirname(__file__), 'config.ini')):
    logger.error('"config.ini" not found. Copy one from the "config.example.ini" file.')
    exit(1)
config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
try:
    appid = config.get("global", "appid")
    secretkey = config.get("global", "secretkey")
except configparser.NoSectionError as e:
    logger.error(e.message)
    exit(1)
if config.has_section(DEFAULT_SECTION):
    logger.error('Section name "{}" is preserved. Try another name.'.format(DEFAULT_SECTION))
    exit(1)
# endregion

# region argparse
parser = argparse.ArgumentParser(prog='cp2trans', description='Clipboard to Translate.')
# region passwd
parser.add_argument('--passwd',
                    dest='passwd',
                    required=False,
                    metavar='log_file',
                    help='Change password of an encrypted log_file or encrypt/decrypt log_file and exit.'
                    )
# endregion
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
parser.add_argument('-d', '--disable',
                    dest='disable',
                    required=False,
                    action='store_true',
                    default=False,
                    help='Disable AWS translate api in low network connection environment.' \
                         ' Log won\'t be recorded into disk (but will be in memory) if set.'
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
        logger.error(YOUDAO_API_ERROR.format(r.status_code))
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
        logger.error(YOUDAO_TTS_ERROR.format(json.loads(r.text)['errorCode']))
    else:
        logger.error(YOUDAO_TTS_ERROR.format(r.status_code))
    return None


def aws_translate(text, target='en', source='ja'):
    result_dict = aws_client.translate_text(Text=text,
                                            SourceLanguageCode=source,
                                            TargetLanguageCode=target)
    return result_dict.get('TranslatedText', None)
# endregion


# region crypto
def align(value):
    if isinstance(value, str):
        value = value.encode('ascii')
    elif isinstance(value, bytes):
        pass
    else:
        logger.critical('align() only accept str and bytes.')
        exit(1)
    while len(value) % 16 != 0:
        value += b' '
    return value


def encrypt(ascii_safe_text, key):
    assert isinstance(ascii_safe_text, str)
    aes = AES.new(align(key), AES.MODE_ECB)
    return aes.encrypt(align(ascii_safe_text))


def decrypt(cipher, key):
    assert isinstance(cipher, bytes)
    aes = AES.new(align(key), AES.MODE_ECB)
    return aes.decrypt(align(cipher)).decode('ascii').rstrip()


# a.b.txt => a.b(insert_text).txt
# Or abc => abc(insert_text) if dot not found
def rename(filepath, insert_text):
    path, ext = os.path.splitext(filepath)
    return path+insert_text+ext


def passwd(filepath):
    if not os.path.isfile(filepath):
        logger.error(FILE_NOT_FOUND.format(filepath))
        exit(1)
    target = input('Choose a target: [C]hange password, [E]ncrypt or [D]ecrypt? ')
    if target == 'C':
        old_password = getpass.getpass('Input old password (won\'t be displayed):')
        with open(filepath, 'rb') as f:
            try:
                log = json.loads(decrypt(f.read(), old_password))
            except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                logger.error(WRONG_PASSWORD.format(filepath))
                exit(1)
        new_password = getpass.getpass('Input new password (won\'t be displayed):')
        with open(rename(filepath, '(encrypted)'), 'wb') as f:
            f.write(encrypt(json.dumps(log), new_password))
        logger.info('Success!')
    elif target == 'E':
        with open(filepath, 'r') as f:
            try:
                log = json.loads(f.read())
            except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                logger.error(PASSWORD_NOT_SPECIFIED.format(filepath))
                exit(1)
        with open(rename(filepath, '(encrypted)'), 'wb') as f:
            password = getpass.getpass('Input a password to encrypt "{}".'.format(filepath))
            f.write(encrypt(json.dumps(log).encode(ascii), password))
        logger.info('Success!')
    elif target == 'D':
        password = getpass.getpass('Input a password to decrypt "{}".'.format(filepath))
        with open(filepath, 'rb') as f:
            try:
                log = json.loads(decrypt(f.read(), password))  # Still need to be json.loads to validate password.
            except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                logger.error(WRONG_PASSWORD.format(filepath))
                exit(1)
        with open(rename(filepath, '(decrypted)'), 'w') as f:
            f.write(decrypt(json.dumps(log).encode('ascii'), password))
        logger.info('Success!')
    else:
        logger.error('Invalid target "{}". Exit.')
        exit(1)
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
        # region tts
        if profile.voice:
            pass
            #TODO
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
        if profile.disable:
            logger.info('The "--disable" option is set. Pass aws translate.')
            aws = None
        else:
            aws = aws_translate(paste, target=profile.target[1], source=profile.source)
            print(aws)
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

    # region type hints
    _log: dict
    _log_filename: str
    # endregion

    # region constructor and destructor
    def __init__(self, section, log, encrypt, voice, match, disable, source, target, interval, agth, opt):
        # region overwrite options
        if section:
            if not config.has_section(section):
                logger.error('No such section "{}" in "config.ini"'.format(args.profile))
                exit(1)
            log = config.get(section, 'log', fallback=section+'.json')
            encrypt = config.get(section, 'encrypt', fallback=None)
            voice = config.get(section, 'voice', fallback='0')
            match = config.get(section, 'match', fallback=None)
            disable = config.get(section, 'disable', fallback=False)
            source = config.get(section, 'source', fallback='ja')
            target = config.get(section, 'target', fallback='zh-CHS,en')
            interval = config.getfloat(section, 'interval', fallback=1.0)
            agth = config.get(section, 'agth', fallback=None)
            opt = config.get(section, 'opt', fallback=None)
        else:
            self._section = DEFAULT_SECTION
        # endregion
        # region init log, encrypt
        self._encrypt = encrypt
        if log and not os.path.isfile(log):
            logger.info(CREATE_A_NOT_EXISTS_FILE.format(log))
            self._log_filename = log
            self._log = {}
        elif log:
            self._log_filename = log
            if encrypt:
                with open(os.path.join(os.path.dirname(__file__), log), 'rb') as f:
                    try:
                        self._log = json.loads(decrypt(f.read(), encrypt))
                    except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                        logger.error(WRONG_PASSWORD.format(log))
                        exit(1)
            else:
                with open(os.path.join(os.path.dirname(__file__), log), 'r') as f:
                    try:
                        self._log = json.loads(f.read())
                    except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                        logger.error(PASSWORD_NOT_SPECIFIED.format(log))
                        exit(1)
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
            logger.warning('--voice option "{}" might be invalid.'.format(voice))
        self._voice = voice
        self._match = match
        # endregion
        # region init disable, source, target
        self._disable = disable
        if source not in SOURCE_ALL:
            logger.error('--source option "{}" is not supported.'.format(source))
            exit(1)
        targets = target.split(',')
        if len(targets) != 2:
            logger.error('--target option "{}" format error.'.format(target))
            exit(1)
        if targets[0] not in TARGET_YOUDAO:
            logger.error('--target option "{}" not supported by youdao.'.format(targets[0]))
            exit(1)
        if targets[1] not in TARGET_AWS:
            logger.error('--target option "{}" not supported by aws.'.format(targets[1]))
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
            logger.warning('Cannot call default section. Continue...')
            return None
        return self._section

    @section.setter
    def section(self, value):
        logger.warning(ACCESS_READONLY_PROPERTY.format('section'))

    @property
    def log_filename(self):
        return self._log_filename
    
    @log_filename.setter
    def log_filename(self, value):
        logger.warning(ACCESS_READONLY_PROPERTY.format('log_filename'))

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
        logger.warning(ACCESS_READONLY_PROPERTY.format('encrypt'))

    @property
    def voice(self):
        return self._voice

    @voice.setter
    def voice(self, value):
        logger.warning(ACCESS_READONLY_PROPERTY.format('voice'))

    @property
    def match(self):
        return self._match

    @match.setter
    def match(self, value):
        logger.warning(ACCESS_READONLY_PROPERTY.format('match'))

    @property
    def disable(self):
        return self._disable
    
    @disable.setter
    def disable(self, value):
        logger.warning(ACCESS_READONLY_PROPERTY.format('disable'))

    @property
    def source(self):
        return self._source

    @source.setter
    def source(self, value):
        logger.warning(ACCESS_READONLY_PROPERTY.format('source'))

    @property
    def target(self):
        return self._target

    @target.setter
    def target(self, value):
        logger.warning(ACCESS_READONLY_PROPERTY.format('target'))

    @property
    def interval(self):
        return self._interval

    @interval.setter
    def interval(self, value):
        logger.warning(ACCESS_READONLY_PROPERTY.format('interval'))

    @property
    def agth(self):
        return self._agth

    @agth.setter
    def agth(self, value):
        logger.warning(ACCESS_READONLY_PROPERTY.format('agth'))

    @property
    def opt(self):
        return self._opt

    @opt.setter
    def opt(self, value):
        logger.warning(ACCESS_READONLY_PROPERTY.format('opt'))
    # endregion

    # region public functions
    def save_log(self):
        if self._disable:
            logger.info('The "--disable" option triggerd. So logs won\'t be saved.')
            return
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
    if args.passwd:
        passwd(args.passwd)
        exit(0)
    profile = Profile(args.profile, args.log, args.encrypt, args.voice, args.match,
                      args.disable, args.source, args.target, args.interval, args.agth, args.opt)
    try:
        main_loop(profile)
    except KeyboardInterrupt:
        logger.info('Saving to "{}". Please wait...'.format(profile.log_filename))
        profile.save_log()  # save log in disk.
        logger.info('done.')
# endregion
