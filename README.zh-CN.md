# cp2trans

翻译来自剪贴板的文本内容。您需要将设置`config.ini`文件中`[global]`节的`language`属性为`zh-CN`，将本程序的语言变更为中文。

- [English Document](README.md)

## 安装

这个软件是配合agth文本提取器使用的，所以仅针对Windows平台测试过，但其余平台应该也能支持。安装过程虽然复杂但是值得一试。

1. 在Windows 10上安装Python37。
2. 升级一下pip `pip install -U pip`.
3. 安装 `aws-cli`，可以在此处下载最新版本<https://aws.amazon.com/cli/>。安装后使用`aws configure`命令初始化一下。需要一个具有aws tranlate接口调用的身份。
4. 安装 MeCab，可以从此处获取安装包 <https://github.com/ikegami-yukino/mecab/releases/tag/v0.996>。安装后需要手动将安装目录下的 `/bin` 目录加入 $PATH环境变量。
5. 如果需要更好的日语分词结果，建议下载 [mecab-ipadic-neologd](https://github.com/neologd/mecab-ipadic-neologd)。然后在 WSL 上编译最新的字典，拷贝`/usr/lib/x86_64-linux-gnu/mecab/dic/mecab-ipadic-neologd` 里面的所有内容到 `C:\neologd\`。
6. **注意：** 我们使用pydub库播放TTS合成的音频，它需要下载ffmpeg，官方网站是这个
 <https://ffmpeg.zeranoe.com/builds/>。安装后需要把安装目录下的`bin`目录加入环境变量。如果不需要TTS功能的话，忽略程序的警告即可。我们没有对音频文件做缓存，所以请注意这个接口调用的消费。
7. 安装依赖 `pip install -r requirements.txt`。通常中文系统会因为编码问题在安装`romkan`这个包时失败。网上的`chcp`命令或者是 `locale.setdefaultencoding()`一般解决不了这个问题。我建议下载[romkan 源码](https://github.com/soimort/python-romkan)然后替换第12行的
 `README = open(os.path.join(here, 'README.rst')).read()`为 `README = open(os.path.join(here, 'README.rst'), encoding="utf-8").read()`，然后用 `python .\setup.py install`手动安装。
8. 复制一份 `config.ini.example`文件然后重命名为 `config.ini`。填写有道智云的 `appid`和 `secretkey`，这个有道智云的App需要具有自然语言翻译的接口调用权限。
9. 安装完成，使用`python .\cp2trans.py`运行脚本。

## 用法

你可以使用 `-h` 选项来查看脚本支持的功能。将`config.ini`文件中`[global]`节的`language`属性设置为`zh-CN`，将本程序的语言变更为中文。

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
