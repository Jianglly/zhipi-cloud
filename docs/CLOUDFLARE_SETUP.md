# Cloudflare Tunnel 配置指南

> 把 `zhipicloud.top` 变成永久公网地址，替代不稳定的 natapp

## 你需要做的（一次性操作，以后不用再做了）

### 第一步：注册 Cloudflare（免费）

1. 打开 https://dash.cloudflare.com/sign-up
2. 用邮箱注册账号（免费的）
3. 完成邮箱验证

### 第二步：添加你的域名

1. 登录后点 **Add a Site / 添加站点**
2. 输入 `zhipicloud.top`
3. 选 **Free** 免费计划 → Continue

### 第三步：修改 DNS 服务器（关键！）

Cloudflare 会给你两个 DNS 服务器地址，类似：
```
xxx.ns.cloudflare.com
yyy.ns.cloudflare.com
```

**复制这两个地址**，然后去阿里云修改：

1. 打开 https://dc.console.aliyun.com
2. 左侧菜单 → **域名**
3. 找到 `zhipicloud.top` → 点 **管理**
4. 找到 **DNS修改** 或 **域名服务器** 选项
5. 把原来的 DNS 改成 Cloudflare 给的那两个
6. 保存

> ⏳ 这一步需要等 **10分钟 ~ 24小时** 生效（通常十几分钟）

### 第四步：在 Cloudflare 添加 DNS 记录

回到 Cloudflare 控制台：

1. 等状态从 **Pending** 变为 **Active**（DNS 生效后会自动变）
2. 左侧菜单 → **DNS** → **Records**
3. 点 **Add record**，添加两条记录：

| Type | Name | Content | Proxy status |
|:---|:---|:---|:---|
| A | `@` | `192.0.2.1` | Proxied（橙色云朵） |
| A | `www` | `192.0.2.1` | Proxied（橙色云朵） |

> IP 填 `192.0.2.1` 就行，这只是占位符，后面隧道会接管。

### 第五步：登录并创建隧道

打开电脑的 **命令提示符**（cmd），依次运行以下命令：

```bash
# 进入项目目录
cd E:\Homwork\数据库系统\手工试卷批阅

# 登录授权（会自动打开浏览器）
cloudflared.exe tunnel login

# 创建隧道
cloudflared.exe tunnel create zhipi-cloud

# 绑定域名
cloudflared.exe tunnel route dns zhipi-cloud zhipicloud.top
cloudflared.exe tunnel route dns zhipi-cloud www.zhipicloud.top
```

### 第六步：启动！

双击 **`deploy.bat`**，一切自动完成：
```
[1/6] MySQL ✅
[2/6] Config ✅
[3/6] Database ✅
[4/6] Build + Server ✅
[5/6] Cloudflare Tunnel ✅   ← https://zhipicloud.top
```

---

## 以后怎么用？

每次开机后双击 **`deploy.bat`** 就行。公网地址永远是：

**https://zhipicloud.top**

不会变、不会断、不需要重新复制地址。

---

## 如果遇到问题

| 问题 | 解决方法 |
|:---|:---|
| cloudflared.exe 无法运行 | 需要安装 Microsoft Visual C++ Redistributable |
| tunnel login 打不开浏览器 | 复制命令行里的 URL 手动粘贴到浏览器 |
| DNS 一直 Pending | 回阿里云确认 DNS 服务器已改好，等 10-30 分钟 |
| 域名访问不了 | 确认 deploy.bat 的 [5/6] 步骤显示 OK |

---

## 对比 natapp

| | natapp（旧） | Cloudflare Tunnel（新） |
|:---|:---|:---|
| 地址 | 每次都变 | **永远不变** |
| 稳定性 | 经常断线 | 全球 CDN 加速 |
| 费用 | 免费（不稳定） | 免费（稳定） |
| HTTPS | 无 | **自带 HTTPS** |
| 速度 | 一般 | **全球加速节点** |
