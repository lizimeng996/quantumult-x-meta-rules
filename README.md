# quantumult-x-meta-rules

给 **Quantumult X（圈叉）** 用的 Meta 全家分流规则，顺带提供 Loon 版。覆盖 **Muse**（Meta 的 AI Agent，muse.ai）、**Meta AI**、**Meta 账号登录**，以及 Facebook、Instagram、WhatsApp、Messenger、Threads、Oculus/Quest 等全部 Meta 服务和 Meta 自有 IP 段。

规则由 GitHub Actions **每天自动从上游重新生成**：合并、去重、校验语法，有变化才提交。

## 规则文件

| 文件 | 用途 | 订阅地址 |
| --- | --- | --- |
| `QuantumultX/Meta.list` | **完整版**：Muse + Meta AI + 全部 Meta 服务/账号 + Meta IP 段（推荐） | https://raw.githubusercontent.com/lizimeng996/quantumult-x-meta-rules/main/QuantumultX/Meta.list |
| `QuantumultX/Muse.list` | **精简版**：只含 Muse、Meta AI 和登录必需域名 | https://raw.githubusercontent.com/lizimeng996/quantumult-x-meta-rules/main/QuantumultX/Muse.list |
| `Loon/Meta.list` | Loon 完整版 | https://raw.githubusercontent.com/lizimeng996/quantumult-x-meta-rules/main/Loon/Meta.list |
| `Loon/Muse.list` | Loon 精简版 | https://raw.githubusercontent.com/lizimeng996/quantumult-x-meta-rules/main/Loon/Muse.list |

每个文件开头的注释里有各类规则的条数和更新日期。

## 覆盖范围

- **Muse**：`muse.ai`、`museai.com`，以及 Muse 云端虚拟机和隐私中继：`metaaivm.com`、`metaaiusercontent.com`、`ecto1usercontent.com`、`hatch.ecto1.ai`、`node.hatch.one`、Cloudflare / Fastly 上的 Meta OHTTP 中继（`meta.privacy-gateway.cloudflare.com`、`meta-ohttp-relay-prod.fastly-edge.com` 等）
- **Meta AI / Llama**：`meta.ai`、`llama.com`、`llamameta.net`、`atmeta.com`
- **Meta 账号登录**：`meta.com`（含 `auth.meta.com`、`accountscenter.meta.com`）、`facebook.com`、`fbsbx.com`、`fbpigeon.com`
- **Facebook**：`facebook.com/.net`、`fb.com`、`fb.me`、`fbcdn.net` 等 500+ 个域名
- **Instagram**：`instagram.com`、`cdninstagram.com`、`ig.me`、`igcdn.com` 等
- **WhatsApp**：`whatsapp.com/.net`、`wa.me` 等
- **Messenger**：`messenger.com`、`m.me`、`fbmessenger.com`
- **Threads**：`threads.net`、`threads.com`
- **Oculus / Quest**：`oculus.com`、`oculuscdn.com` 等
- **IP**：Meta 的 3 个 ASN（`IP-ASN` 32934 FACEBOOK、63293 FACEBOOK-OFFNET、54115 FACEBOOK-CORP），以及这三个 ASN 当前在 BGP 中宣告的全部 IPv4/IPv6 网段（来自 RIPEstat，已合并）

刻意**不包含**：
- `HOST-KEYWORD,meta` 这类过宽的关键字规则，它会误伤 `metacritic`、`metamask` 等无关网站。
- `198.18.0.0/15` 这类 fake-IP 地址和内网地址。
- 上游 WhatsApp 规则里那些不属于 Meta 的段，比如 AWS、SoftLayer 的大段地址，以及 `bintray.com`。

## Quantumult X 用法

在配置文件的 `[filter_remote]` 段加入一行（把 `美国节点` 换成你自己的策略组名）：

```ini
[filter_remote]
https://raw.githubusercontent.com/lizimeng996/quantumult-x-meta-rules/main/QuantumultX/Meta.list, tag=Meta, force-policy=美国节点, update-interval=86400, opt-parser=false, enabled=true
```

只想让 Muse / Meta AI 走美国，其它 Meta 服务另走别的节点，就把 `Muse.list` 放在 `Meta.list` **上面**：

```ini
https://raw.githubusercontent.com/lizimeng996/quantumult-x-meta-rules/main/QuantumultX/Muse.list, tag=Muse, force-policy=美国节点, update-interval=86400, opt-parser=false, enabled=true
https://raw.githubusercontent.com/lizimeng996/quantumult-x-meta-rules/main/QuantumultX/Meta.list, tag=Meta, force-policy=代理, update-interval=86400, opt-parser=false, enabled=true
```

**顺序很重要**：QX 按从上到下匹配，这一条要放在其它 Facebook、Instagram、CDN、`GEOIP` 和 `FINAL` 规则**之前**，否则 Meta 流量会先被别的规则截走。

规则行末尾的 `Meta` / `Muse` 只是占位，实际走哪个节点由 `force-policy` 决定。

## Loon 用法

```ini
[Remote Rule]
https://raw.githubusercontent.com/lizimeng996/quantumult-x-meta-rules/main/Loon/Meta.list, policy=美国节点, tag=Meta, enabled=true
```

## ⚠️ 关于 Muse 的地区限制

Muse 目前**只对美国开放**。规则全部正确，仍提示「尚未在你的国家或地区开放」或要排队时，问题出在出口 IP，与分流规则无关。需要换成**美国原生 IP 或家宽 IP**；机房 IP 和广播 IP 常被拦截。也建议给 Meta 用固定节点，不要用自动测速或负载均衡，否则登录状态容易失效。

## 自己构建

```bash
python3 scripts/build.py   # 只用 Python 标准库，生成 QuantumultX/ 和 Loon/ 下的文件并校验语法
```

工作流在 `.github/workflows/update.yml`：每天北京时间 10:17 运行，也可以在 Actions 页面手动运行。

## 规则来源与致谢

- [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)（MIT）：`meta` 及其 include 的 facebook、instagram、whatsapp、messenger、threads、oculus 等列表
- [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)（GPL-2.0）：Facebook、Instagram、Whatsapp、Threads 规则中的域名
- [juner922/muse-loon-rules](https://github.com/juner922/muse-loon-rules)：Muse 专用域名（VM、OHTTP 中继）
- [Tartarus2014/Loon-Script](https://github.com/Tartarus2014/Loon-Script)：Muse 规则
- [VPSDance/ai-proxy-rules](https://github.com/VPSDance/ai-proxy-rules)（MIT）：Meta AI 规则
- [zhbcn/Rules](https://github.com/zhbcn/Rules)：Muse 规则
- [RIPEstat](https://stat.ripe.net/)：Meta 各 ASN 宣告的 IP 网段

## 许可证

本仓库包含来自 blackmatrix7/ios_rule_script（GPL-2.0）的衍生内容，因此整体以 **GPL-2.0** 发布，见 [LICENSE](LICENSE)。
