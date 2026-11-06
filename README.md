# Storage Redirect X 云端规则

面向 [Storage Redirect X](https://github.com/Kindness-Kismet/storage-redirection-x) 的独立规则仓库。**`rules/` 中的每个应用文件都使用 SRX 原生的 `allowed_real_paths` 和 `path_mappings`；客户端不读取或转换 Storage Redirect 旧格式。**

首次迁移来自 [RikkaApps/StorageRedirect-assets](https://github.com/RikkaApps/StorageRedirect-assets/tree/fa1040c6443844dfcd36275820b1c3285ae012bc)，保留全部 2,731 份应用规则对应的原生条目、原始贡献者和可核验来源。历史仓库中的上游文件仅用于来源追溯；当前维护入口是 `rules/`。

## 使用与维护

- 编辑 `rules/<package>.json`，然后运行 `python3 scripts/build_catalog.py`。
- 将原生规则和生成的 `catalog-v1.json` 一并提交。CI 通过 `python3 scripts/build_catalog.py --check` 检查字段、路径、迁移覆盖率和产物是否一致。
- 应用从 `https://raw.githubusercontent.com/Kindness-Net/storage-redirection-x-rules/master/catalog-v1.json` 获取完整目录。进入应用配置页时使用缓存，缓存超过 24 小时按需更新；下载不会自动修改设备配置。
- 应用配置页仅显示简短建议。点击卡片“开启”或打开原有重定向开关，默认合并匹配的云端规则；同路径以已有手动配置为准，保持当前 Android 用户及共享 UID 的配置同步。

## 单应用格式

```json
{
  "package": "com.example.app",
  "recommendation": "recommended",
  "description": {"en": "Isolate app-created files.", "zh-CN": "隔离应用创建的文件。"},
  "authors": ["contributor"],
  "updated_at": 0,
  "upstream_file": "",
  "upstream_verified": false,
  "warnings": [],
  "allowed_real_paths": ["Download/Public"],
  "path_mappings": {"Example/Pictures": "Pictures/Example"}
}
```

路径相对于 `/storage/emulated/<当前用户>/`，不硬编码用户 ID。禁止绝对路径、`.`、`..`、通配符、反斜杠和 `Android/data`。真实路径允许 SRX 的 `!` 排除及 `^` 只读前缀；映射源和目标不可相同。转换后需要路径豁免的同目录导出写入 `allowed_real_paths`。

`recommendation` 可为 `recommended`、`unnecessary`、`not_recommended`、`cause_problems`、`depends_on_situations`、`custom`。它只表达建议；开启重定向时才引入路径，不因下载或查看建议而自动修改配置。只包含基础隔离建议的应用可以有空路径；不推荐隔离的应用显示简短提示，仍由用户决定是否通过原开关开启。

本地化说明接受 `en`、`zh-CN`、`zh-TW`。`upstream_file` 为空表示没有旧规则来源；`upstream_verified` 仅记录原项目状态，不能当作 SRX 实机验证结果。

## 迁移边界

- 普通导出目录的 `source → target` 离线转为 SRX 直接路径映射；相同路径转为真实路径规则。这会直接写入目标，并包含子目录和临时文件，不复现旧应用的文件导出时机、媒体扫描或下载登记。详细行为差异保留在本仓库的迁移记录中。
- 带 `mask` 的过滤导出、空路径、Android 目录导出、冲突目标不生成会扩大访问范围的规则；详细原因和原始字段在 `migration/report.json`。
- `accessible_folders` 跨应用共享规则无法等价转换，保留报告并提示需要人工适配。
- `non_standard_files` 是原应用的行为证据，**不是允许列表**；不反向转换成真实路径权限。
- 6 处身份/嵌套字段错误及 7 处字段类型错误记录在 `migration/corrections.json`；规则原始字节 SHA-256 在 `migration/source-files.json`。修正只发生在转换产物。
- 所有迁移规则均需按当前应用版本评估；此迁移不声称所有规则已经通过 SRX 实机验证，也不搬移用户现有文件。

## 重现初次迁移

使用 Python 3.10+，无需第三方依赖：

```sh
git clone https://github.com/RikkaApps/StorageRedirect-assets.git /tmp/srx-upstream
git -C /tmp/srx-upstream checkout fa1040c6443844dfcd36275820b1c3285ae012bc
python3 scripts/migrate_upstream.py --source /tmp/srx-upstream --output /tmp/srx-migrated
```

输出目录必须为空。脚本先核对全部源文件 SHA-256，再生成原生规则及报告。重现结果用于比较，不覆盖后来人工维护的 `rules/`。辅助推荐文案、分类和认证列表记录在 `migration/reference-data.json`，不参与客户端执行。

## 协议与发布

`catalog-v1.json` 包含 `schema_version: 1`、确定性 `revision`（不含自身字段的规范 JSON 的 SHA-256）、来源提交和 `rules` 数组。UTF-8，最大 8 MiB，最多 10,000 个应用；不支持的版本、字段值或路径使本次更新整体失败并保留旧缓存。

直接维护 `master` 或通过 PR 更新；本仓库不自动拉取上游、不自动推送产物。规则源只使用 HTTPS，不接收用户的已安装应用列表或配置。

## 来源与署名

感谢 RikkaApps 和所有原始规则贡献者。每份原生规则保留原始作者，迁移报告记录原文件名、哈希与未转换内容；Git 历史保留初始来源。本仓库不将原始贡献重新声明为 SRX 作者作品，也不为上游内容附加新的许可证授权。
