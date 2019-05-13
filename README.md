# cp2trans
Translate Japanese text from clipboard.

## Installation
This script is written for Windows. Believe it's a hard way to setup but an easy one to use :).

1. Python 37 on Windows 10.
2. Upgrade pip by `pip install -U pip`. 
3. Install `aws-cli` from <https://aws.amazon.com/cli/> and initiate aws by `aws configure`.
4. Install MeCab from <https://github.com/ikegami-yukino/mecab/releases/tag/v0.996>. Add the `/bin` directory $PATH.
5. Make additional dictionary by [mecab-ipadic-neologd](https://github.com/neologd/mecab-ipadic-neologd).
 Since it's hard to build on Windows 10, I suggest build it on Ubuntu WSL and copy all the files under
 `/usr/lib/x86_64-linux-gnu/mecab/dic/mecab-ipadic-neologd` into `C:\neologd\` if you want the newest dictionary.
 [Here](neologd/)'s a pre-built dictionary on 2019-05-11.
6. **NOTICE:** We use `pygame` to play TTS mp3 audio. We won't save mp3 file so you should be careful of its costs.
7. Install requirements by `pip install -r requirements.txt`. If your system default encoding is not UTF-8, you might
 fail on installing the `romkan` package. Usually neither `chcp` nor `locale.setdefaultencoding()` won't solve this
 problem. I suggest manually download [romkan source code](https://github.com/soimort/python-romkan) and replace line 12
 `README = open(os.path.join(here, 'README.rst')).read()` to
 `README = open(os.path.join(here, 'README.rst'), encoding="utf-8").read()`. Then run `python .\setup.py install`.
8. Copy a file of `config.ini.example` and rename it to `config.ini`. Fill in the `appid` and the `secretkey`, make sure
 `Natural Language Translation` of this app is enabled.
9. Run the script by `python .\cp2trans.py`.
