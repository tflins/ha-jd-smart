# 京东小家 for Home Assistant

这是一个非官方 Home Assistant 自定义集成，用于接入京东小家 App 中的设备。当前版本
支持空调，以及经过实际验证的部分洗衣机功能。

本项目与京东、京东小家及 Home Assistant 没有隶属或官方合作关系。

[English README](README.md)

## 功能

### 空调

- 电源、运行模式与目标温度。
- 当前温度和湿度。
- 风速、上下扫风、左右风向与睡眠模式。
- 设备提供相应数据时，显示背光、屏显与强力模式开关。

### 洗衣机

- 电源、启动、暂停与童锁。
- 洗涤程序与预约启动。
- 工作状态、剩余时间、预约剩余、洗衣完成与故障状态。
- 已在小吉洗衣机上确认标准、单脱水、筒自洁、快洗、婴童、煮洗 95℃、Bra 呵护洗、
  毛巾除菌洗、运动即时洗、衬衣衣领净、新衣物首洗等程序。

实体根据设备实际返回的数据流动态创建。设备不支持的控制项不会生成，避免出现大量
无意义的“不可用”实体。

### 鉴权

- 支持 Home Assistant UI 配置与多设备选择。
- 京东账号会话仍有效时，自动刷新 WJLogin `tgt` 和 Cookie。
- 初次配置和重新认证均可一次粘贴抓包 JSON，无需逐项填写字段。
- 提供可选 Android/ADB 辅助工具，只采集集成所需的最少字段，并自动恢复手机原代理。

## 安装

### HACS

在 HACS 中添加以下自定义仓库，类型选择 `Integration`：

```text
https://github.com/tflins/ha-jd-smart
```

安装 **JD Smart**，重启 Home Assistant，然后进入：

```text
设置 -> 设备与服务 -> 添加集成 -> JD Smart
```

### 手动安装

把 `custom_components/jd_smart` 复制到 Home Assistant 配置目录：

```text
config/custom_components/jd_smart
```

重启 Home Assistant，再从“设置 -> 设备与服务”添加集成。

## 推荐的 Android 配置方式

辅助工具支持 macOS 和 Linux，需要 Python 3、ADB、一台已开启 USB 调试的 Android
手机，以及已经登录京东小家的 App。

克隆本仓库并连接手机后，运行：

```bash
tools/reauth.sh setup
```

按照手机界面把复制过去的 mitmproxy 证书安装为 Android 用户 CA。这个步骤通常只需
执行一次。随后运行：

```bash
tools/reauth.sh capture
```

工具会临时设置 Android 代理、启动京东小家、等待一条已认证请求、恢复原代理，并把
最少鉴权字段保存为私有 JSON；系统支持时还会自动复制到剪贴板。

在 Home Assistant 中选择“JD Smart -> 添加设备 -> 导入抓包 JSON”，粘贴生成的
JSON。Home Assistant 要求重新认证时，也使用同一个 JSON 输入框。

默认本地状态目录为：

```text
~/.local/state/ha-jd-smart
```

可以用 `JD_SMART_STATE_DIR` 修改目录。如果自动识别的电脑 IP 不适用，可以把
`JD_SMART_PROXY_HOST` 设置为手机能够访问的电脑 IP。

不再需要辅助工具时运行：

```bash
tools/reauth.sh cleanup
```

该命令会清除 Android 代理并删除手机“下载”目录中的证书文件。已经安装到系统中的
用户 CA 仍需在 Android 设置中单独删除。

## 鉴权生命周期

集成会自动刷新 `tgt` 及配套 Cookie。当前刷新实现与京东小家 2.3.0 使用的 WJLogin
SDK 12.0.10 一致，包括应用 ID `1421` 和应用名称 `京东小家`。

正常重启 Home Assistant 不需要重新抓包。只有京东使底层账号会话失效、用户退出账号，
或 App 修改私有鉴权协议时，才需要重新运行一次采集工具。因此日常使用不需要每次登录
都填写 Cookie。

仍可使用 Proxyman、Charles、HTTP Toolkit、mitmproxy 等工具手动抓包。应尽量从同一
条成功认证请求中提取所有字段。

## 安全说明

抓取的 Cookie 和 `tgt` 可以访问京东小家账号会话，应当按密码管理。

- 不要提交抓包 JSON、mitmproxy 数据、HAR、Cookie 或 token。
- 辅助工具以仅当前用户可读的权限写入 JSON，不保存完整 HTTP 流量。
- 工具状态目录包含 mitmproxy CA 私钥，必须作为敏感数据保护。
- 不再需要抓包时，应移除 Android 用户 CA。
- 只能用于本人拥有或有权管理的账号与设备。

凭据处理和漏洞报告方式见 [SECURITY.md](SECURITY.md)。

## 已验证设备与兼容范围

京东的私有设备接口会随产品和固件变化。当前映射已验证：

- 使用既有京东小家数据流模型的空调。
- 一台提供 `Power`、`Work`、`State`、`Error`、`Mode`、`BabyLock`、
  `RemainingTimeMin`、`ReserveTimeRemainingMinute`、`ReserveTimeSetHour`
  数据流的小吉洗衣机。

其他设备可能可以被发现，但只会为已识别的数据流创建实体。如需增加设备映射，请在
Issue 中提供脱敏后的数据流名称与数值，不要发布任何鉴权信息。

## 开发与检查

本地基础检查：

```bash
python3 -m pip install --no-deps homeassistant==2025.3.4
python3 -m pip install -r requirements-test.txt
python3 -m unittest discover -s tests
python3 -m compileall -q custom_components/jd_smart tools tests
bash -n tools/reauth.sh
```

GitHub Actions 还会执行 HACS 和 Hassfest 校验。

## 致谢

本仓库基于 [orangeboyChen](https://github.com/orangeboyChen/ha-jd-smart) 的原始
`ha-jd-smart` 项目继续开发，并保留原 MIT 协议与作者署名。

## 免责声明

本集成使用未公开的私有接口，接口可能随时变化，使用行为也可能受到京东小家条款约束。
请自行评估风险。完整内容见 [DISCLAIMER.md](DISCLAIMER.md)。
