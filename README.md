# 表情包工坊（meme）

把一张图做成表情包：字幕、气泡、描边、顶部字幕四种样式。成品通过图库公开的 `offerMedia` 交成临时引用（`mediaRef`，24 小时有效、绑定当前会话）；要收藏进图库由 `gallery_collect` 决定，收藏拿到 asset id 后 QQ 才能发。

思路来自鱼仔 `tools/make_meme_*.py`（PIL 加字幕 + 成套导出），改成插件里可反复调用的小工具。

## 安装

两种方式，选一种：

1. **发行包**：[meme-0.2.1-win32-x64.wlpkg.gz](https://github.com/FelixTaXk/whalelife-community-meme/releases/download/v0.2.1/meme-0.2.1-win32-x64.wlpkg.gz) 是 `.wlpkg.gz` 官方发行包格式（一行 `{"format":1,"files":[...]}` 清单 + 按清单顺序拼接的文件字节，gzip 封装），由宿主商店/校验链路安装；手动安装见下一条。
2. **git clone**：`git clone https://github.com/FelixTaXk/whalelife-community-meme plugins/meme`。

放好后重启本体。需要图库插件 0.1.2 及以上（`depends: [gallery]`），渲染还需要 Python + Pillow：解释器默认按 PATH 找带 Pillow 的 `python` / `python3`，找不到就到插件设置页填 python.exe 的完整路径。

## 工具

| 工具 | 作用 |
| --- | --- |
| `meme_make` | 单张：图 + 字幕 → 一张表情包（返回 `mediaRef` 临时引用） |
| `meme_set` | 一套：同一张原图 + 一组字幕（≤8 条）→ 多张表情包 |

参数：

- `sourceId`：图库图片 id（画室 `draw` / `selfie` / `snapshot` 返回的 `galleryId` 就是）
- `sourcePath`：本地图片路径；只接受本体目录，或设置页「允许读取的本地目录」里由你明确添加的目录（不再内置任何开发机路径）
- `text`：字幕，最多 120 字，短句最好（"就这？""困成鱼干""气死我了"）
- `style`：`band`（底部白条，默认）/ `bubble`（白气泡带尾巴）/ `plain`（描边大字，不挡画面）/ `top`（顶部白条）
- `width`：成品宽度，默认 512

## 设置页一键出图

控制台 → 插件 → 表情包工坊（`/plugins/meme/settings`）最上面那块「一键出图」，不用经过模型：

1. **参考图**三选一
   - **上传图片**：拖进来或点选，PNG / JPG / WebP / GIF，≤15 MB
   - **图库资产 ID**：填已收藏图片的资产 id，点「载入这张」
   - **AI 画参考图**：写一句画面描述（有 4 个快捷短语），选方形 / 竖版 / 横版，点「让 AI 画一张」。先用画室 `studio.health()` 体检当前默认后端：本机 ComfyUI / SD-WebUI 要连得上，网络后端要有 API Key；没配好时按钮直接禁用，面板上写清原因并给「去画室设置」链接。体检通过才走 `studio.generate()`（本地 ComfyUI 可能要一两分钟）
2. **字幕 / 样式 / 宽度**：样式和宽度的默认值取下面的「默认参数」
3. 点 **一键出图**：直接出成品，右侧显示预览、尺寸、样式、图库引用（`mediaRef` 或图库实际返回的错误），可下载

在 AI 模式下如果还没画参考图，直接点「一键出图」会先画再出，一步搞定。
参考图会存成 `data/out/meme-src-*`，同一个参考图可以改字幕反复出（改完字幕再点一次就行）。
成品会调图库 `offerMedia({sessionId, base64, source:'meme'})`，把图交成临时引用并返回 `mediaRef` + `expiresInSeconds`；调用失败或返回里没有 `mediaRef` 时，结果里给 `galleryNote` 写明真实原因（比如图库没提供该接口、当前操作没有会话 id、图库拒绝接收），不会笼统说“图库没在跑”。设置页手动出图没有会话上下文，所以只落本地文件并如实提示。
画室没接通时「AI 画参考图」会明确报错，上传和图库两条路不受影响。

## 出字规则（做表情包时）

- 图上要出现中文，直接写进提示词，用中文引号“”括住，并说明字号和占位：`招牌上用红色黑体写着“热牛奶”，字很大、占画面宽度一半`
- 一句话不超过七八个字；一张图只放一处文字。字越小越糊，塞好几处会糊成伪字
- 字体准确、排版精确（表情包那种要卡死的）：先画一张干净的底图，再用本插件的字幕层压字（`band` / `bubble` / `plain` / `top`）。`image_text` 是补充手段，不是唯一方案
- 字幕本身同样一条一句话、七八个字以内，别写长句

## 流水线

```
draw/selfie → galleryId（资产 id）
   → meme_make(sourceId, text, style)
   → gallery.offerMedia({sessionId, base64, source:"meme"}) → mediaRef（24h）
   → gallery_collect(mediaRef, purposes:["meme"]) → asset id
   → qq_send_gallery(parts:[{"type":"image","id":<asset id>}])
```

返回值里带 `sendHint`，照着走就行。`mediaRef` 不是资产 id，不能直接塞给发送接口；没拿到 `mediaRef` 时结果会给 `galleryNote` 说明具体原因。

## 依赖

- Python + Pillow：留空就先按 PATH 找带 Pillow 的 `python` / `python3`，找不到会提示你填完整路径
- 字体：`C:\Windows\Fonts\msyhbd.ttc` → `msyh.ttc` → `simhei.ttf`，都没有就退到默认字体
- 图库插件（必需）：`depends: [gallery]`，用它的 `readMedia` 取图、`offerMedia` 交付成品
- 画室 `studio` 服务（可选）：只有「AI 画参考图」用得到，`optionalDepends: [studio]`，没有就禁用这一条入口
- 想换 Python 路径：到插件设置页改，或写 `data/config.json` 的 `{"python":"..."}`

## 设置页

控制台 → 插件 → 表情包工坊，或直接打开 `/plugins/meme/settings`：

- **一键出图**：上传 / 图库 / AI 画参考图 + 字幕 → 成品预览、下载
- **默认样式 / 默认宽度**：`meme_make` / `meme_set` 和设置页一键出图没传 `style` / `width` 时用
- **允许读取的本地目录**：一行一个绝对路径，留空就只允许本体目录；保存时校验目录必须存在
- **python.exe 路径**：留空自动探测 PATH 里带 Pillow 的 python；保存时会检查文件是否存在
- **输出统计**：当前 `data/out` 里的张数和占用（不含 `meme-src-*` 参考图）
- **清空输出目录**：删 `meme-*` 的成品、参考图和临时输入，已经进图库、已经发出去的不受影响
- **图库 / 画室状态**：显示两个可选服务是否接通

设置保存在 `data/config.json`，结构：

```json
{
  "python": "",
  "defaultStyle": "band",
  "defaultWidth": 512,
  "allowedDirs": ["D:\\图片\\表情包素材"]
}
```

## 页面接口

| 路由 | 方法 | 作用 |
| --- | --- | --- |
| `/plugins/meme/source` | POST | `{type:"upload",base64}` / `{type:"gallery",galleryId}` / `{type:"ai",prompt,width,height}` → 落一份 `meme-src-*`，返 `sourceFile` / `sourceUrl` |
| `/plugins/meme/oneclick` | POST | `{sourceFile,text,style,width}` → 渲染并调图库 `offerMedia`，返 `url` / `mediaRef` / `mediaRefExpiresInSeconds` / `galleryNote` / 尺寸 |
| `/plugins/meme/model-check` | POST | 出图模型体检：`{ok,backend,label,online,message,settingsUrl}`，客户端每次进页面和点「重新检查」时调用 |
| `/plugins/meme/out` | GET | `?name=meme-*.png` 预览，`&download=1` 下载；只放 `data/out` 里的 `meme-*` 文件 |

## 实现

- `index.ts`：取图（图库资产 id / 本地白名单 / 上传 / 画室生成）、调 Python、调图库 `offerMedia`、拼 sendHint、设置页
- `tools/render_meme.py`：PIL 排版；按像素宽度自动折行、自动缩字号；四套样式
- 临时输入文件写在 `data/tmp/`，渲染完即删；成品和参考图在 `data/out/`

渲染一次约 0.2–0.5 秒（512 宽），不占 GPU。
