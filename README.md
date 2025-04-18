# Steam大数据可视化和游戏推荐平台

<!-- ![Project Logo](https://via.placeholder.com/150) 有项目logo后替换为实际项目logo，或截图界面 -->

## 项目概述

本项目为西南大学2022级某小组在华迪公司实训答辩项目。

随着Steam平台成为全球最大的PC游戏分发平台之一，海量游戏数据蕴含巨大的商业价值。本项目通过采集和分析Steam平台多维数据，构建了可视化分析系统与智能推荐引擎，帮助玩家发现优质游戏，辅助开发者洞察市场趋势。

### 主要功能

- **数据可视化分析**：提供多维度的Steam游戏数据可视化展示
- **智能推荐系统**：基于用户行为和游戏特征进行个性化推荐
- **市场趋势可视化**：帮助开发者了解市场动态和用户偏好，玩家了解当前游戏热点

## 技术栈

- **后端**：Python (PySpark)
- **数据库**：MySQL
- **数据处理**：Spark SQL, Pandas
- **可视化**：ECharts, WordCloud
- **其他工具**：Git, PyCharm

## 部署指南

### 前置要求

- MySQL (建议版本: 8.0+)
- PySpark (本项目使用3.1.2版本)
- Python 3.7+
- winutils (Hadoop Windows工具)

### 安装步骤

1. **克隆仓库**

   使用下面命令：
   ```bash
   git clone https://github.com/KurotaniTakeo/SteamBigData.git
   cd SteamBigData
   ```
   或直接使用PyCharm克隆仓库

2. **安装依赖**

   使用PyCharm打开项目，IDE会自动根据`requirements.txt`安装所需依赖包。

   或手动安装：

   ```bash
   pip install -r requirements.txt
   ```

3. **数据库配置**

   - 启动MySQL服务
   - 复制`config/db_config.example.toml`为`config/db_config.toml`
   - 编辑`config/db_config.toml`，填写您的数据库配置信息

4. **初始化数据库**

   运行初始化脚本：

   ```bash
   python utils/InitDatabase.py
   ```

   此脚本将：
   - 创建必要的数据库表
   - 修正现有表中错误的表项和数据类型

5. **PySpark环境配置**

   在PyCharm中：
   - 进入 `设置 > 项目: SteamBigData > 项目结构`
   - 添加内容根：`path/to/your/spark_home/python/lib`
   - 将以下两个文件添加到项目：
     - `py4j-0.10.9-src.zip`
     - `pyspark.zip`

6. **运行项目**

   完成上述步骤后，即可通过`app.py`运行项目。

   ```bash
   python app.py
   ```

## 项目结构

```
（待补充）
```

## 使用说明

1. **数据采集**：运行数据采集脚本
2. **数据清洗**：执行数据清洗
3. **可视化**：运行可视化脚本生成图表
4. **推荐系统**：启动推荐服务获取个性化推荐

## 常见问题

**Q: 遇到PySpark连接问题怎么办？**

A: 确保：
- SPARK_HOME环境变量已正确设置
- winutils已正确安装并配置
- Python版本与PySpark兼容

**Q: 数据库初始化失败**

A: 检查：
- MySQL服务是否运行
- db_config.toml中的配置信息是否正确
- 用户是否有创建表的权限

## 贡献指南

欢迎提交Pull Request。对于重大更改，请先开Issue讨论您想做的更改。

1. Fork项目
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

## 许可证

本项目采用 [MIT License](LICENSE)。

## 联系方式

如有问题，请联系：
- 项目负责人: Kurotani Takeo
- 邮箱: kurotake@foxmail.com

---

*README最后更新: 2025/4/18*