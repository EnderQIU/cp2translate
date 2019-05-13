import os
import io
import re
import sys
import time
import json
import urllib
import random
import getpass
import logging
import hashlib
import argparse
import subprocess
import configparser
from datetime import datetime
from multiprocessing import Process

import boto3
import MeCab
import i18n
import pydub
import romkan
import requests
import pyperclip
from Crypto.Cipher import AES
from pydub.playback import play


# region consts
YOUDAO_API_HTTPS = 'https://openapi.youdao.com/api'
YOUDAO_TTSAPI_HTTPS = 'https://openapi.youdao.com/ttsapi'
DEFAULT_SECTION = 'default'  # This section name is preserved.
# All available source language codes, should be the intersection of youdao and aws translate.
SOURCE_ALL = ('ja', )
# Youdao supported target languages.
TARGET_YOUDAO = ('zh-CHS', )
# AWS translate supported languages.
TARGET_AWS = ('en', )
DIVIDING_TITLE = '- '*10+'{} '+'- '*10
DIVIDING_LINE = '= '*25
TEST_STRING = '8月3日に放送された「中居正広の金曜日のスマイルたちへ」(TBS系)で、1日たった5分で' \
              'ぽっこりおなかを解消するというダイエット方法を紹介。キンタロー。のダイエットにも密着。'
CONFIG_INI = 'config.ini'
API_TOLERATED_DELAY = 1.0  # If API request period is greater than it, log an info.
config = configparser.ConfigParser()
config.read(os.path.join(os.path.dirname(__file__), CONFIG_INI))
# endregion

# region i18n
i18n.load_path.append(os.path.join(os.path.dirname(__file__), 'lang'))
i18n.set('filename_format', '{locale}.{format}')
i18n.set('locale', config.get('global', 'language'))
# Only logger.info and print content supports l18n.
PROGRAM_DESCRIPTION = i18n.t('PROGRAM_DESCRIPTION')
YOUDAO_API_ERROR = i18n.t('YOUDAO_API_ERROR')
YOUDAO_TTS_ERROR = i18n.t('YOUDAO_TTS_ERROR')
CREATE_A_NOT_EXISTS_FILE  = i18n.t('CREATE_A_NOT_EXISTS_FILE')
ACCESS_READONLY_PROPERTY = i18n.t('ACCESS_READONLY_PROPERTY')
WRONG_PASSWORD = i18n.t('WRONG_PASSWORD')
PASSWORD_NOT_SPECIFIED = i18n.t('PASSWORD_NOT_SPECIFIED')
FILE_NOT_FOUND = i18n.t('FILE_NOT_FOUND')
FOLDER_NOT_FOUND = i18n.t('FOLDER_NOT_FOUND')
SECTION_NOT_FOUND = i18n.t('SECTION_NOT_FOUND')
SAVING_TO_PLEASE_WAIT = i18n.t('SAVING_TO_PLEASE_WAIT')
SECTION_IS_PRESERVED = i18n.t('SECTION_IS_PRESERVED')
CHOOSE_A_TARGET = i18n.t('CHOOSE_A_TARGET')
INPUT_OLD_PASSWORD = i18n.t('INPUT_OLD_PASSWORD')
INPUT_NEW_PASSWORD = i18n.t('INPUT_NEW_PASSWORD')
INPUT_PASSWORD_TO_ENCRYPT = i18n.t('INPUT_PASSWORD_TO_ENCRYPT')
INPUT_PASSWORD_TO_DECRYPT = i18n.t('INPUT_PASSWORD_TO_DECRYPT')
DONE = i18n.t('DONE')
START_AGTH_FROM = i18n.t('START_AGTH_FROM')
INVALID_TARGET = i18n.t('INVALID_TARGET')
LOG_WONT_BE_SAVED = i18n.t('LOG_WONT_BE_SAVED')
TTS_PLAYING_WITH_VOICE = i18n.t('TTS_PLAYING_WITH_VOICE')
REQUEST_FINISHED_IN = i18n.t('REQUEST_FINISHED_IN')
HELP_PASSED = i18n.t('HELP_PASSED')
HELP_PROFILE = i18n.t('HELP_PROFILE')
HELP_LOG = i18n.t('HELP_LOG')
HELP_ENCRYPT = i18n.t('HELP_ENCRYPT')
HELP_TTS = i18n.t('HELP_TTS')
HELP_MATCH = i18n.t('HELP_MATCH')
HELP_SOURCE = i18n.t('HELP_SOURCE')
HELP_TARGET = i18n.t('HELP_TARGET')
HELP_DISABLE = i18n.t('HELP_DISABLE')
HELP_INTERVAL = i18n.t('HELP_INTERVAL')
HELP_AGTH = i18n.t('HELP_AGTH')
HELP_OPT = i18n.t('HELP_OPT')
# endregion

# region global vars
aws_client = boto3.client('translate')
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
if not os.path.exists(os.path.join(os.path.dirname(__file__), CONFIG_INI)):
    logger.error(FILE_NOT_FOUND.format(CONFIG_INI))
    exit(1)
try:
    appid = config.get("global", "appid")
    secretkey = config.get("global", "secretkey")
    neologd_path = config.get('global', 'neologd')
    program_language = config.get('global', 'language')
except configparser.NoSectionError as e:
    logger.error(e.message)
    exit(1)
if config.has_section(DEFAULT_SECTION):
    logger.error(SECTION_IS_PRESERVED.format(DEFAULT_SECTION))
    exit(1)
if not os.path.exists(neologd_path):
    logger.error(FOLDER_NOT_FOUND.format(neologd_path))
    exit(1)
mecab_wakati = MeCab.Tagger('-Owakati -d '+neologd_path)
mecab_chasen = MeCab.Tagger('-Ochasen -d '+neologd_path)
# endregion

# region argparse
parser = argparse.ArgumentParser(prog='cp2trans', description=PROGRAM_DESCRIPTION)
# region passwd
parser.add_argument('--passwd', dest='passwd', metavar='log_file', help=HELP_PASSED)
# endregion
# region profile
parser.add_argument('-p', '--profile', dest='profile', metavar='section', help=HELP_PROFILE)
# endregion
# region logger
parser.add_argument('-l', '--log', dest='log', metavar='log_file', help=HELP_LOG)
parser.add_argument('-e', '--encrypt', dest='encrypt', metavar='password', help=HELP_ENCRYPT)
# endregion
# region tts
parser.add_argument('-v', '--voice', dest='voice', choices=('0', '1',), default='0', help=HELP_TTS)
parser.add_argument('-m', '--match', dest='match', metavar='pattern', default=None, help=HELP_MATCH)
# endregion
# region translation
parser.add_argument('-s', '--source', dest='source', metavar='lang_code', default='ja', help=HELP_SOURCE)
parser.add_argument('-t', '--target', dest='target', metavar='lang_code', default='zh-CHS,en', help=HELP_TARGET)
parser.add_argument('-d', '--disable', dest='disable', action='store_true', default=False, help=HELP_DISABLE)
# endregion
# region text hook
parser.add_argument('-i', '--interval', dest='interval', metavar='seconds', type=float, default=1.0, help=HELP_INTERVAL)
parser.add_argument('-a', '--agth', dest='agth', metavar='agth_path', help=HELP_AGTH)
parser.add_argument('-o', '--opt', dest='opt', metavar='agth_opts', help=HELP_OPT)
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
    start_time = datetime.now()
    r = requests.get(YOUDAO_API_HTTPS, params=params)
    period = (datetime.now() - start_time).seconds
    logger.debug('Youdao API finished API request in {} seconds'.format(period))
    if period > API_TOLERATED_DELAY:
        logger.info(REQUEST_FINISHED_IN.format('Youdao API', period))
    if r.ok and 'application/json' in r.headers['Content-type']:
        return json.loads(r.text)['translation'][0]
    else:
        logger.error(YOUDAO_API_ERROR.format(r.status_code))
        return None


def youdao_tts(text, voice='1', lang_type='ja'):
    if text == '':
        return
    salt, sign = gen_salt_and_sign(text)
    params = {
        'appKey': appid,
        'q': urllib.parse.quote(text.encode('utf-8')),
        'langType': lang_type,
        'salt': salt,
        'sign': sign,
        'format': 'mp3',
        'voice': voice
    }
    start_time = datetime.now()
    r = requests.get(YOUDAO_TTSAPI_HTTPS, params=params)
    period = (datetime.now() - start_time).seconds
    logger.debug('Youdao TTS finished API request in {} seconds'.format(period))
    if period > API_TOLERATED_DELAY:
        logger.info(REQUEST_FINISHED_IN.format('Youdao TTS', period))
    if r.ok and 'audio/mp3' in r.headers['Content-Type']:
        data = io.BytesIO(r.content)
        tts = pydub.AudioSegment.from_file(data, format="mp3")
        logger.info(TTS_PLAYING_WITH_VOICE.format(voice))
        play(tts)
        logger.debug('TTS playing finished normally.')
    elif 'application/json' in r.headers['Content-Type']:
        logger.error(YOUDAO_TTS_ERROR.format(json.loads(r.text)['errorCode']))
    else:
        logger.error(YOUDAO_TTS_ERROR.format(r.status_code))


def aws_translate(text, target='en', source='ja'):
    start_time = datetime.now()
    result_dict = aws_client.translate_text(Text=text,
                                            SourceLanguageCode=source,
                                            TargetLanguageCode=target)
    period = (datetime.now() - start_time).seconds
    logger.debug('AWS finished API request in {} seconds'.format(period))
    if period > API_TOLERATED_DELAY:
        logger.info(REQUEST_FINISHED_IN.format('AWS', period))
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
    # str => bytes
    assert isinstance(ascii_safe_text, str)
    aes = AES.new(align(key), AES.MODE_ECB)
    return aes.encrypt(align(ascii_safe_text))


def decrypt(cipher, key):
    # bytes => str
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
    target = input(CHOOSE_A_TARGET)
    if target == 'C':
        old_password = getpass.getpass(INPUT_OLD_PASSWORD)
        with open(filepath, 'rb') as f:
            try:
                log = json.loads(decrypt(f.read(), old_password))
            except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                logger.error(WRONG_PASSWORD.format(filepath))
                exit(1)
        new_password = getpass.getpass(INPUT_NEW_PASSWORD)
        new_filepath = rename(filepath, '(encrypted)')
        logger.info(SAVING_TO_PLEASE_WAIT.format(new_filepath))
        with open(new_filepath, 'wb') as f:
            f.write(encrypt(json.dumps(log), new_password))
        logger.info(DONE)
    elif target == 'E':
        with open(filepath, 'r') as f:
            try:
                log = json.loads(f.read())
            except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                logger.error(PASSWORD_NOT_SPECIFIED.format(filepath))
                exit(1)
        new_filepath = rename(filepath, '(encrypted)')
        logger.info(SAVING_TO_PLEASE_WAIT.format(new_filepath))
        with open(new_filepath, 'wb') as f:
            password = getpass.getpass(INPUT_PASSWORD_TO_ENCRYPT.format(filepath))
            f.write(encrypt(json.dumps(log).encode(ascii), password))
        logger.info(DONE)
    elif target == 'D':
        password = getpass.getpass(INPUT_PASSWORD_TO_DECRYPT.format(filepath))
        with open(filepath, 'rb') as f:
            try:
                log = json.loads(decrypt(f.read(), password))  # Still need to be json.loads to validate password.
            except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                logger.error(WRONG_PASSWORD.format(filepath))
                exit(1)
        new_filepath = rename(filepath, '(decrypted)')
        logger.info(SAVING_TO_PLEASE_WAIT.format(new_filepath))
        with open(new_filepath, 'w') as f:
            f.write(json.dumps(log))
        logger.info(DONE)
    else:
        logger.error(INVALID_TARGET.format(target))
        exit(1)
# endregion


# region main loop
def main_loop(profile):
    paste = pyperclip.paste()
    tts_thread = None
    while True:
        if paste == pyperclip.paste():
            logger.debug('Same paste, continue...')
            continue
        paste = pyperclip.paste()
        # region from log
        if paste in profile.log:
            logger.debug('Found paste from log. Use record.')
            print(DIVIDING_TITLE.format('SOURCE (from log)'))
            print(profile.log[paste]['source'])
            if 'romkan' in profile.log[paste]:
                print(DIVIDING_TITLE.format('ROMKAN (from log)'))
                print(profile.log[paste]['romkan'])
            print(DIVIDING_TITLE.format('YOUDAO (from log)'))
            print(profile.log[paste]['youdao'])
            print(DIVIDING_TITLE.format('AWS (from log)'))
            print(profile.log[paste]['aws'])
            if profile.voice:
                if profile.match and re.search(profile.match, paste) or profile.match is None:
                    logger.debug('"{}" matches in paste. Continue...'.format(profile.match))
                    if tts_thread:
                        tts_thread.kill()
                        logger.debug('Previous TTS process killed.')
                    tts_thread = Process(target=youdao_tts, args=(paste, profile.voice, profile.source))
                    tts_thread.start()
                    logger.debug('TTS process starts.')
                else:
                    logger.debug('"{}" does not match in paste. Pass...'.format(profile.match))
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
            if profile.match and re.search(profile.match, paste) or profile.match is None:
                logger.debug('"{}" matches in paste. Continue...'.format(profile.match))
                if tts_thread:
                    tts_thread.kill()
                    logger.debug('Previous TTS process killed.')
                tts_thread = Process(target=youdao_tts, args=(paste, profile.voice, profile.source))
                tts_thread.start()
                logger.debug('TTS process starts.')
            else:
                logger.debug('"{}" does not match in paste. Pass...'.format(profile.match))
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
                logger.error(SECTION_NOT_FOUND.format(args.profile))
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
        self._agth = agth
        self._opt = opt if opt else ''
        if self._agth:
            cmd = agth + opt
            logger.info(START_AGTH_FROM.format(cmd))
            subprocess.Popen([agth]+opt.split(' '))
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
            logger.info(LOG_WONT_BE_SAVED)
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
        logger.info(SAVING_TO_PLEASE_WAIT.format(profile.log_filename))
        profile.save_log()  # save log in disk.
        logger.info(DONE)
# endregion
