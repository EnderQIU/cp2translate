# cp2translate
Translate Japanese text from clipboard.

## Installation
This script is written for Windows, but can support all platform with a little modification.

1. Python 37 on Windows 10.
2. Upgrade pip by `pip install -U pip`.
3. Install `aws-cli` from <https://aws.amazon.com/cli/>.
4. Configure aws by `aws configure`.
5. Install MeCab from <https://github.com/ikegami-yukino/mecab/releases/tag/v0.996>. Add the `/bin` directory $PATH.
6. (Optional) Make additional dictionary if you want better words division performance by following the instructions from <https://github.com/neologd/mecab-ipadic-neologd>. I suggest build it under WSL and copy the `dic/` directory into `C:\neologd\`.
7. Install requirements by `pip install -r requirements.pip`
8. Fill in the AppID and the AppSecret of your Youdao App.
9. Open agth.exe and attach to your game. Run the script by `python .\cp2translate.py`.
