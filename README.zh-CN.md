# cp2trans
翻译来自剪贴板的文本内容。您需要将设置`config.ini`文件中`[global]`节的`language`属性为`zh-CN`，将本程序的语言变更为中文。

- [English Document](README.md)

## 安装
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
9. Run the script by `python .\cp2trans.py`.

## Usage

```powershell
PS C:\cp2translate> python .\cp2trans.py -h
usage: cp2trans [-h] [--passwd log_file] [-p section] [-l log_file]
                [-e password] [-v {0,1}] [-m pattern] [-s lang_code]
                [-t lang_code] [-d] [-i seconds] [-a agth_path] [-o agth_opts]

翻译来自剪贴板的内容。

optional arguments:
  -h, --help            show this help message and exit
  --passwd log_file     更改被加密的 log_file 的密码，或者对其进行加密/解密。
  -p section, --profile section
                        从 "config.ini" 中读取配置。任何来自命令行的其余参数将会被覆盖。您可以在
                        "config.example.ini" 文件中获取详情。
  -l log_file, --log log_file
                        保存记录至 "log_file"，这样做可以节约您的 API 调用次数。
  -e password, --encrypt password
                        加密记录文件。读取一个被加密的记录文件时也需要指定此选项。
  -v {0,1}, --voice {0,1}
                        TTS 所使用的语音。"0" 代表男性发音，"1"代表女性发音。不设置此选项则不会启用 TTS 功能。
  -m pattern, --match pattern
                        仅当源文本匹配 pattern 时进行 TTS。
  -s lang_code, --source lang_code
                        源文字语言代码。仅当此选项为 "ja" 时，会显示罗马音。
  -t lang_code, --target lang_code
                        目标语言代码。前一个目标语言使用有道智云 API，后一个使用 AWS Translate API。
  -d, --disable         激活此选项以在网络状况不佳的情况下禁用 AWS Translate
                        APT。如果这样做也会导致记录不会被保存至磁盘（但会暂存于内存）。
  -i seconds, --interval seconds
                        检查剪贴板内容是否发生变化的时间间隔。
  -a agth_path, --agth agth_path
                        启动 AGTH 文本提取进程。必须指定 AGTH 可执行文件的路径。您很可能需要同时指定 "-o,
                        --opt" 选项。
  -o agth_opts, --opt agth_opts
                        "agth.exe" 的额外启动参数。您可以通过点击 "agth.exe" 程序窗口的 "help"
                        按钮获取详情。
```