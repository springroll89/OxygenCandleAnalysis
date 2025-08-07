# 🔥 AWK产品分析系统

## 🔄 更新日志

### v1.0 (2025-08-06)

- 初始版本发布
- 实现基础数据提取和分析
- 添加Web可视化界面
- 支持配方对比功能

---

这是一个用于分析AWK产品性能数据的综合分析系统，包含数据提取、评分排名、对比分析和Web可视化界面。

## 📋 功能特点

### 核心功能

- **数据自动提取**：从Excel报告中自动提取关键性能指标
- **多维度评分**：基于达标率、产氧时间、启动时长、温度等多个维度进行综合评分
- **配方对比分析**：对比不同产品的配方差异和成分变化
- **可视化展示**：Web界面展示流量曲线、燃烧深度、排名等数据

### 分析维度

- 达标率分析（50分权重）
- 产氧总时长（15分权重）
- 启动时长（15分权重）
- 温度稳定性（20分权重）
- 波谷分析（加分项）

## 🚀 快速开始

### 环境要求

- Python 3.8+
- 推荐使用虚拟环境

### 安装步骤

1. **克隆仓库**

```bash
git clone https://github.com/[your-username]/OxygenCandleAnalysis.git
cd OxygenCandleAnalysis
```

1. **创建虚拟环境**

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
# 或
venv\Scripts\activate  # Windows
```

1. **安装依赖**

```bash
pip install -r requirements.txt
```

1. **准备数据**

- 将产品测试报告放入 `reports_input/` 目录
- 每个产品一个文件夹，如 `reports_input/2A143/`
- 确保配方表.xlsx在 `data/` 目录中

## 📊 使用方法

### 方式一：一键运行全部分析

```bash
python 一键运行全部.py
```

这将依次执行：

1. 简单分析程序（提取数据）
2. 评分排名程序（计算得分）
3. 对比分析程序（生成对比报告）

### 方式二：分步运行

1. **数据提取**

```bash
python 简单分析程序.py
```

1. **评分排名**

```bash
python 评分排名程序.py
```

1. **对比分析**

```bash
python 对比分析程序.py
```

### 方式三：Web界面

```bash
streamlit run 网页系统.py
```

访问 http://localhost:8501 查看Web界面

## 📁 项目结构

```
OxygenCandleAnalysis/
├── data/                      # 配置和基础数据
│   ├── 配方表.xlsx           # 产品配方数据
│   ├── 基准曲线.csv          # 基准流量曲线
│   └── 刻度表.xlsx           # 燃烧深度刻度表
├── modules/                   # 功能模块
│   ├── oxygen_candle_evaluation.py  # 评分算法
│   ├── valley_analyzer.py           # 波谷分析
│   ├── extract_report_data.py       # 数据提取
│   └── formula_parser.py            # 配方解析
├── reports_input/             # 输入数据目录
│   └── [产品编号]/          # 各产品测试报告
├── reports_output/            # 输出结果目录
│   └── [时间戳]/            # 分析结果
├── 一键运行全部.py           # 主程序
├── 简单分析程序.py           # 数据提取
├── 评分排名程序.py           # 评分计算
├── 对比分析程序.py           # 对比分析
└── 网页系统.py               # Web界面
```

## 📈 Web界面功能

### 主要页面

1. **主页**：显示关键指标和快速统计

2. **数据总览**：查看和筛选所有产品数据

3. **排名分析**：TOP N 产品排名展示

4. 对比分析：

   - 流量曲线对比
   - 燃烧深度分析
   - 配方差异对比
   - 详细数据表格
   
5. **最佳配方**：推荐最优配方

### 特色功能

- 🔍 智能搜索和筛选
- 📊 交互式图表（支持缩放、拖动）
- 📥 数据导出（CSV格式）
- 🎨 响应式设计

## 🔧 配置说明

### 评分规则配置

在 `modules/oxygen_candle_evaluation.py` 中可调整：

- 各项评分权重
- 达标阈值
- 温度等级定义

### 配方表格式

配方表.xlsx需包含以下sheet：

- 总表：产品序号和配方对应关系
- a层/b层/c层：各层配方成分详情

## 📝 数据格式要求

### 输入报告格式

每个产品的Excel报告需包含：

- 原始数据sheet：时间、流量等数据
- 产氧-深度曲线sheet：燃烧深度数据

### 配方格式

- 格式：A4(7g)/B16(38g)/C62(32g)/C61(305g)
- 含义：层级代码(重量)

## 🛠️ 主要依赖

- pandas: 数据处理
- numpy: 数值计算
- openpyxl: Excel文件操作
- streamlit: Web界面
- plotly: 交互式图表
- scipy: 科学计算

## 🎯 评分体系说明

### 评分构成

| 指标       | 权重   | 说明                  |
| ---------- | ------ | --------------------- |
| 达标率     | 50分   | 流量≥2L/min的时间占比 |
| 产氧时长   | 15分   | 总产氧时间            |
| 启动时长   | 15分   | 达到2L/min所需时间    |
| 温度稳定性 | 20分   | 最高温度评估          |
| 波谷分析   | 加分项 | 流量稳定性评估        |

### 评级标准

- A级：≥90分
- B级：75-89分
- C级：60-74分
- D级：<60分

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 开发建议

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交Pull Request

## 📄 许可证

MIT License

## 👤 作者

shiding

## 📮 联系方式

如有问题，请提交Issue或联系作者。

## 🙏 致谢

感谢所有为本项目提供帮助和建议的人。

------

*最后更新：2025年8月6日*