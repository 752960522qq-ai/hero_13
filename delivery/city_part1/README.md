# 城市区块第一部分

此目录包含第一部分的 25 个二进制分卷，涵盖区块 01–06、17、18。克隆仓库后在此目录运行：

```sh
python3 reassemble.py
```

脚本按顺序拼接分卷，验证 SHA-256 和 ZIP CRC，生成 `huizhou_city_districts_part1.zip`。将该压缩包与[区块第二部分](https://chatgpt.com/library?file_id=libfile_57ce1917034c8191a950868eba092fba&account_id=personal)解压到同一目录，即可获得全部 18 个区块。导入模型时保留各区块的世界坐标。

第一部分 SHA-256：`b0b15396ebbeeec2ef5921ae42acdf57e8aad35d070b83889f572371de65eff6`。
