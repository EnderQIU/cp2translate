# cp2trans
Translate text from clipboard.

- [中文文档](README.zh-CN.md)

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
6. **NOTICE:** We use `pydub`'s ffmpeg binding to play TTS mp3 audio. If you want to enable TTS, download ffmpeg from
 <https://ffmpeg.zeranoe.com/builds/> or just ignore the warning. We won't save mp3 so you should mind of its costs.
7. Install requirements by `pip install -r requirements.txt`. If your system default encoding is not UTF-8, you might
 fail on installing the `romkan` package. Usually neither `chcp` nor `locale.setdefaultencoding()` won't solve this
 problem. I suggest manually download [romkan source code](https://github.com/soimort/python-romkan) and replace line 12
 `README = open(os.path.join(here, 'README.rst')).read()` to
 `README = open(os.path.join(here, 'README.rst'), encoding="utf-8").read()`. Then run `python .\setup.py install`.
8. Copy a file of `config.ini.example` and rename it to `config.ini`. Fill in the `appid` and the `secretkey`, make sure
 `Natural Language Translation` of this app is enabled.
9. Run the script by `python .\cp2trans\cp2trans.py` or install `cp2trans` by `python setup.py install` (in this way you can pass step 8).

## Usage

```powershell
PS C:\cp2translate> python .\cp2trans.py -h
usage: cp2trans [-h] [--passwd log_file] [-p section] [-l log_file]
                [-e password] [-v {0,1}] [-m pattern] [-s lang_code]
                [-t lang_code] [-d] [-i seconds] [-a agth_path] [-o agth_opts]

Clipboard to Translate.

optional arguments:
  -h, --help            show this help message and exit
  --passwd log_file     Change password of an encrypted log_file or
                        encrypt/decrypt log_file and exit.
  -p section, --profile section
                        Load profiled options from the specified section of
                        "config.ini" file. Any other options from command line
                        will be ignored. See details in "config.example.ini".
  -l log_file, --log log_file
                        Save and read translation history from "log_file" to
                        save API calls.
  -e password, --encrypt password
                        Encrypt logfile if you don't want it too exposed ;P.
                        Have to be specified while loading an encrypted log
                        file.
  -v {0,1}, --voice {0,1}
                        Voice of TTS. "0" for male and "1" for female. Unset
                        for disable TTS.
  -m pattern, --match pattern
                        Only TTS when match <pattern>.
  -s lang_code, --source lang_code
                        Source language code. Romkan will only be shown with
                        "ja".
  -t lang_code, --target lang_code
                        Primary uses Youdao API and the secondary by AWS
                        translate API.
  -d, --disable         Disable AWS translate api in low network connection
                        environment. Log won't be recorded into disk (but will
                        be in memory) if set.
  -i seconds, --interval seconds
                        Time interval in seconds to check the clipboard.
  -a agth_path, --agth agth_path
                        Start AGTH text hook. "agth_path" must be specified.
                        You might also have to specify -o option.
  -o agth_opts, --opt agth_opts
                        Extra options passed to "agth.exe". See details by the
                        help button of "agth.exe" window.
```
