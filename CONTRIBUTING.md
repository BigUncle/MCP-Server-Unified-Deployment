# Contributing Guidelines | 贡献指南

[English](#contributing-guidelines-english) | [中文](#贡献指南-中文)

<a id="contributing-guidelines-english"></a>

# Contributing Guidelines (English)

Thank you for considering contributing to the MCP-Server-Unified-Deployment project! Here are some guidelines to help you participate in the project development.

## How to Contribute

### Reporting Issues

If you find a bug or have a suggestion for a new feature, please submit it through GitHub Issues. When submitting an issue, please include the following information:

- Detailed description of the issue
- Steps to reproduce (if applicable)
- Expected behavior vs. actual behavior
- Environment information (operating system, Python version, etc.)
- Possible solution (if any)

### Submitting Code

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
   - Please follow the [Conventional Commits](https://www.conventionalcommits.org/) specification
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Pull Request Process

1. Ensure your PR description clearly explains the changes you've made
2. If your PR resolves an Issue, reference that Issue in the PR description (e.g., `Fixes #123`)
3. Make sure your code passes all tests
4. Project maintainers will review your PR and may request some changes
5. Once the PR is approved, it will be merged into the main branch

## Development Guidelines

### Code Style

This project uses the following tools to maintain code quality and consistency:

- **Black**: Python code formatter
- **isort**: Import statement sorter
- **Ruff**: Python linter

Please ensure your code complies with these tools' standards. You can use pre-commit hooks to automatically check and format your code:

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

### Testing

Before submitting a PR, please make sure your code passes all tests. If you add new functionality, please add corresponding tests as well.

### Documentation

If your changes affect the user experience or API, please update the relevant documentation. Good documentation is crucial for the project's usability.

## Code of Conduct

Please refer to the [Code of Conduct](CODE_OF_CONDUCT.md) document to understand our expectations for community members.

## License

By contributing code, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).

<a id="贡献指南-中文"></a>

# 贡献指南 (中文)

感谢您考虑为MCP-Server-Unified-Deployment项目做出贡献！以下是一些指导原则，帮助您参与项目开发。

## 如何贡献

### 报告问题

如果您发现了bug或有新功能建议，请通过GitHub Issues提交。提交问题时，请包含以下信息：

- 问题的详细描述
- 复现步骤（如适用）
- 预期行为与实际行为
- 环境信息（操作系统、Python版本等）
- 可能的解决方案（如有）

### 提交代码

1. Fork本仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
   - 请遵循[约定式提交](https://www.conventionalcommits.org/)规范
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开Pull Request

### Pull Request流程

1. 确保您的PR描述清楚地说明了您所做的更改
2. 如果您的PR解决了某个Issue，请在PR描述中引用该Issue（例如 `Fixes #123`）
3. 确保您的代码通过了所有测试
4. 项目维护者将审查您的PR，可能会要求进行一些更改
5. 一旦PR被批准，它将被合并到主分支

## 开发指南

### 代码风格

本项目使用以下工具来保持代码质量和一致性：

- **Black**：Python代码格式化工具
- **isort**：导入语句排序工具
- **Ruff**：Python linter

请确保您的代码符合这些工具的规范。您可以使用pre-commit钩子来自动检查和格式化代码：

```bash
# 安装pre-commit钩子
pip install pre-commit
pre-commit install
```

### 测试

在提交PR之前，请确保您的代码通过了所有测试。如果您添加了新功能，请同时添加相应的测试。

### 文档

如果您的更改影响了用户体验或API，请更新相应的文档。良好的文档对于项目的可用性至关重要。

## 行为准则

请参阅[行为准则](CODE_OF_CONDUCT.md)文档，了解我们对社区成员的期望。

## 许可证

通过贡献代码，您同意您的贡献将根据项目的[MIT许可证](LICENSE)进行许可。
