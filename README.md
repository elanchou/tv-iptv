# tv-iptv

自动筛选的全球电视直播列表。每天北京时间 04:00 从 [iptv-org/iptv](https://github.com/iptv-org/iptv) 重新生成，只保留当时能取到播放列表的频道。

## 订阅地址

```
https://raw.githubusercontent.com/elanchou/tv-iptv/main/playlist.m3u
```

可用于 TVBox（直播地址）、StreamVault（M3U URL）等 M3U 客户端。

## 分组

新闻、纪录片、体育、电影、动画少儿、音乐，以及日本、韩国、香港、台湾、美国、英国、德国、法国、新加坡、澳洲、加拿大。

## 说明

- 检测只确认播放列表能下载，不保证画面可播，部分频道有地区限制。
- 频道清单和规则在 `build_playlist.py`，可自行修改。
- 本仓库只汇总公开链接，不提供任何内容。
