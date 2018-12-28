# cp2translate
Translate Japanese text from clipboard.

## Installation
The script is written for Windows, but dependencies support all platform.

1. Python 37 on Windows 10.
2. Upgrade pip by `pip install -U pip`.
3. Install `aws-cli` from <https://aws.amazon.com/cli/>.
4. Configure aws by `aws configure`.
5. Install MeCab from <https://github.com/ikegami-yukino/mecab/releases/tag/v0.996>. Add the `/bin` directory $PATH.
6. Install dictionary for MeCab from <https://github.com/neologd/mecab-ipadic-neologd> on any other platform
7. Install requirements by `pip install -r requirements.pip`
8. Fill in the AppID and the AppSecret in the script.
9. Open agth.exe and attach to your game. Run the script by `python .\cp2translate.py`.
