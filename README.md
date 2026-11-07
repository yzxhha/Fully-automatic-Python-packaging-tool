# Fully automatic Python packaging tool V6.1

6.1 加入黑色系粒子欢迎首页：启动后先展示「从灵感，到构建」动画页面，可点击进入打包工作台。动画对象固定创建并复用，优先减少额外 UI 开销。

## 启动

```bash
python gui.py
```

需要 Python 3.10+ 和 Tkinter。

## 功能

- 深色首页与轻量粒子网络动画、构建设置和实时日志页。
- PyInstaller 打包当前平台可执行程序（单文件/目录模式）。
- 创建 ZIP、TAR.GZ、TAR.BZ2、TAR.XZ 项目归档。
- 项目扫描和构建在后台执行；日志批量追加并限制缓存行数。

## 动画与性能

- 粒子及连线启动时创建一次；动画只调整已有 Canvas 对象坐标和可见状态。
- 动画使用固定粒子数，窗口不可见或最小化时暂停。
- 构建日志最多保留 2,500 行，避免长时间任务使 UI 内存持续增长。

## 注意

- Windows `.exe` 应在 Windows 上构建；建议各目标系统分别构建。
- 只打包可信项目。分享归档前检查是否包含密钥或敏感文件。

## 测试

```bash
python -m unittest discover -s tests -v
```
