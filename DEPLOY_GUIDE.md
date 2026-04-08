# ViralScope Pro - Cloud Deploy Package

这是一个为您准备的 Vercel 生产环境部署包。

## 如何将代码推送到 GitHub 并上线？

1. **创建仓库**：
   在您的 GitHub (imly-sudo) 账号下创建一个名为 `viral-scope-pro` 的新私有仓库。

2. **推送代码**：
   如果您在本地，请在终端执行以下命令：
   ```bash
   git init
   git add .
   git commit -m "Initialize ViralScope Pro v2.3"
   git branch -M main
   git remote add origin https://github.com/imly-sudo/viral-scope-pro.git
   git push -u origin main
   ```

3. **连接 Vercel**：
   - 登录 [vercel.com](https://vercel.com)。
   - 点击 **Add New Project**。
   - 选择您刚才创建的 `viral-scope-pro` 仓库。
   - 点击 **Deploy**。

4. **绑定域名**：
   - 在 Vercel 项目设置中的 **Domains** 页面，填入您的域名（如 `viral.yourdomain.com`）。
   - 按照 Vercel 的提示，去您的域名 DNS 后台配置 CNAME 记录即可。

---
© 2026 ViralScope AI Labs
