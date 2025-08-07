# 贡献指南

感谢您考虑为NTP时间同步工具做出贡献！以下是一些指导方针，帮助您参与这个项目。

## 开发环境设置

1. 克隆仓库：
   ```bash
   git clone https://github.com/yourusername/ntp.git
   cd ntp
   ```

2. 创建并激活虚拟环境（可选但推荐）：
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

## 代码风格

本项目遵循以下Python代码规范：
- PEP 8 - 代码风格指南
- PEP 257 - 文档字符串约定
- PEP 484 - 类型提示

提交代码前，请确保您的代码符合这些标准。

## 提交流程

1. 创建一个新分支：
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. 进行更改并提交：
   ```bash
   git add .
   git commit -m "描述您的更改"
   ```

3. 推送到您的分支：
   ```bash
   git push origin feature/your-feature-name
   ```

4. 创建一个Pull Request

## 测试

在提交代码前，请确保：
- 您的代码在Windows和Linux/Unix系统上都能正常工作
- 所有功能都按预期运行
- 添加了适当的错误处理

## 报告问题

如果您发现了问题或有改进建议，请创建一个issue，并包含以下信息：
- 问题的详细描述
- 复现步骤
- 预期行为与实际行为
- 您的操作系统和Python版本

## 许可证

通过贡献您的代码，您同意您的贡献将在MIT许可证下发布。