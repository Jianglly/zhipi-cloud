# 智批云 Android 打包指南

> **三天极限交付方案 | 2026-07-01**

---

## 一、项目现状

| 项目 | 状态 |
|------|------|
| Capacitor 环境 | ✅ 已安装 |
| Android 工程 | ✅ 已生成 (`android/`) |
| Web 资源同步 | ✅ 已完成 |
| 路由模式 | ✅ Hash 模式 |
| Vite base 路径 | ✅ 相对路径 (`./`) |
| 移动端 CSS | ✅ 已添加触控适配 |
| API 地址配置 | ✅ 动态可配 |

---

## 二、打包前必须做的事

### 第 1 步：确认后端 IP 地址

```bash
# 在你运行后端的电脑上执行，获取局域网 IP
ipconfig
# 找到 "IPv4 地址"，例如 192.168.1.105
```

### 第 2 步：配置 API 地址

编辑 `zhipi-frontend/.env.production`：

```
VITE_API_BASE_URL=http://192.168.1.105:8000/api
```

> **注意**：手机和电脑必须在**同一个 WiFi** 下！否则访问不通。

### 第 3 步：确认后端防火墙

Windows 防火墙必须允许 8000 端口入站，否则手机连不上。

```powershell
# 管理员 PowerShell 执行
New-NetFirewallRule -DisplayName "智批云后端" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

---

## 三、三天操作流程

### Day 1：出包 + 打通 API（约 6 小时）

```
上午 (3h) ── 环境准备
  ├── [ ] 修改 .env.production 中的服务器 IP
  ├── [ ] 开放防火墙 8000 端口
  ├── [ ] 安装 Android Studio（如果还没有）
  │       下载地址: https://developer.android.com/studio
  │       安装时勾选 Android SDK 和 Android Virtual Device
  └── [ ] 打开 Android Studio，确认 SDK 安装完毕

下午 (3h) ── 构建 + 调试
  ├── [ ] npm run build          # 构建前端
  ├── [ ] npx cap sync           # 同步到 Android
  ├── [ ] npx cap open android   # 在 Android Studio 中打开
  ├── [ ] Build → Build Bundle(s) / APK(s) → Build APK(s)
  └── [ ] 安装 APK 到手机测试
```

#### 安装 APK 到手机

```
方式 1（USB）：手机开 USB 调试 → 数据线连电脑 → Android Studio Run
方式 2（无线）：构建 APK 后，用 QQ/微信传文件安装
方式 3（ADB）：adb install android/app/build/outputs/apk/debug/app-debug.apk
```

#### 如果 API 调不通

手机上访问不了后端，在手机浏览器打开 Chrome → 开发者工具 → Console，输入：

```js
// 检查当前 API 地址
console.log(localStorage.getItem('apiServer'))

// 手动设置（把 IP 换成你电脑的）
localStorage.setItem('apiServer', 'http://192.168.x.x:8000/api')

// 刷新页面重新加载
location.reload()
```

> 这个设置会持久化，无需重新打包！

---

### Day 2：移动端适配打磨（约 6 小时）

```
上午 (3h) ── 真机测试
  ├── [ ] 登录流程：教师登录 / 学生登录
  ├── [ ] 教师端：Dashboard / 试卷管理 / 批阅 / 统计分析
  ├── [ ] 学生端：Dashboard / 成绩查看 / 趋势图
  ├── [ ] 测试表格横滚（小屏手机）
  └── [ ] 记录所有 UI 问题到清单

下午 (3h) ── 修复
  ├── [ ] 修复触控问题（按钮太小、误触等）
  ├── [ ] 修复布局问题（溢出、重叠、错位）
  ├── [ ] 修复 API 相关问题
  └── [ ] 重新 build + sync + 安装测试
```

#### 常见 UI 问题速查

| 问题 | 原因 | 修复位置 |
|------|------|----------|
| 按钮点不到 | 尺寸 < 44px | 检查 CSS，加 min-height/min-width |
| 表格被截断 | 固定宽度 | 给 table 外面包 `<div class="table-responsive">` |
| 输入框点开页面缩放 | font-size < 16px | 移动端 .form-input font-size 已是 16px |
| 底部内容被遮挡 | 系统导航栏 | CSS 已有 safe-area-inset-bottom |
| 图表太小看不清 | Chart.js 容器不够 | 调整 canvas 尺寸或图表组件 |

---

### Day 3：release 打包 + 交付（约 6 小时）

```
上午 (3h) ── 最终测试
  ├── [ ] 找 2-3 台不同品牌手机测试
  ├── [ ] 测试网络切换（WiFi / 4G / 飞行模式恢复）
  ├── [ ] 测试异常场景（token 过期、后端挂了）
  └── [ ] 修复最后的问题

下午 (3h) ── 签名打包
  ├── [ ] 生成签名密钥（只需一次）
  ├── [ ] 配置 signingConfigs
  ├── [ ] Build → Generate Signed Bundle / APK
  └── [ ] 交付 APK
```

#### 生成签名密钥

```bash
keytool -genkey -v -keystore zhipi-release.keystore -alias zhipi -keyalg RSA -keysize 2048 -validity 10000
```

#### 签名配置

编辑 `android/app/build.gradle`，在 `android {}` 块内添加：

```gradle
signingConfigs {
    release {
        storeFile file("zhipi-release.keystore")
        storePassword "你的密码"
        keyAlias "zhipi"
        keyPassword "你的密码"
    }
}
buildTypes {
    release {
        signingConfig signingConfigs.release
    }
}
```

---

## 四、日常开发工作流

以后每次改完前端代码，打包只需要两步：

```bash
npm run build        # 1. 构建前端
npx cap sync         # 2. 同步到 Android
# 然后 Android Studio → Build APK
```

### 一键构建脚本

创建 `zhipi-frontend/build-apk.bat`：

```batch
@echo off
echo ===== 智批云 Android 打包 =====
echo [1/3] 构建前端...
call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo 构建失败！
    pause
    exit /b
)
echo [2/3] 同步到 Android...
call npx cap sync
echo [3/3] 用 Android Studio 打开工程...
call npx cap open android
echo ===== 完成！=====
pause
```

---

## 五、关键文件对照表

| 文件 | 作用 | 变更 |
|------|------|------|
| `vite.config.js` | Vite 构建配置 | ✅ 添加 `base: './'` |
| `src/router/index.js` | 路由配置 | ✅ `createWebHashHistory()` |
| `src/api/index.js` | API 请求层 | ✅ 动态 baseURL + 运行时覆盖 |
| `.env.production` | 生产环境变量 | ✅ 新增，配置 API 地址 |
| `src/assets/main.css` | 全局样式 | ✅ 移动端触控适配 |
| `capacitor.config.json` | Capacitor 配置 | ✅ 新增 |
| `android/` | Android 原生工程 | ✅ 自动生成 |

---

## 六、常见问题

### Q: 手机装好 APK 打开白屏？

1. 确认 `vite.config.js` 有 `base: './'`
2. 确认 `router/index.js` 用的是 `createWebHashHistory`
3. 重新 `npm run build && npx cap sync`，卸载重装 APP

### Q: 登录后报"网络请求失败"？

1. 确认手机和电脑在同一 WiFi
2. 确认防火墙开放了 8000 端口
3. 在手机浏览器 Console 设置 `localStorage.setItem('apiServer', 'http://电脑IP:8000/api')`

### Q: Android Studio 报 SDK 相关错误？

- File → Settings → Appearance → System Settings → Android SDK
- 勾选 Android API 34，Apply 安装

### Q: 图表不显示？

- Chart.js 在 Android WebView 中兼容性良好，一般直接可用
- 如果 canvas 尺寸不对，检查父容器宽度

### Q: 怎么让 APP 图标/名称不显示默认的？

- 图标：替换 `android/app/src/main/res/` 下各密度的 `ic_launcher.png`
- 名称：修改 `android/app/src/main/res/values/strings.xml` 中的 `app_name`

---

## 七、三天后还有时间的话

| 优先级 | 增强项 | 工作量 |
|--------|--------|--------|
| 高 | 替换 APP 图标和启动页 | 1h |
| 高 | 添加下拉刷新 | 2h |
| 中 | 相机拍照上传（Capacitor Camera 插件） | 3h |
| 中 | Token 用 Capacitor Preferences 存储 | 1h |
| 低 | Splash Screen 启动页 | 2h |
| 低 | 网络状态检测提示 | 2h |

---

## 八、团队分工建议（3人团队）

| 成员 | Day 1 | Day 2 | Day 3 |
|------|-------|-------|-------|
| **A（后端）** | 开防火墙、确保 API 正常 | 手机调 API，排查后端问题 | 签名打包、文档 |
| **B（前端）** | 修改 .env.production、build | 真机 UI 测试、修样式 | 集成测试、bug 修 |
| **C（全栈）** | 安装 Android Studio、搭环境 | 协助 B 修 UI、调适配 | 最终验收、APK 分发 |

---

> **一句话总结**：改 4 个文件 → build → sync → Android Studio 打包，核心流程 30 分钟搞定。
> 剩下的时间全部用来真机测试和修 bug。
