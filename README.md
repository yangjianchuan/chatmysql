# ChatMySQL

ChatMySQL 是一个基于自然语言的 MySQL 数据库查询系统，它能让用户使用自然语言来查询数据库信息。系统集成了 OpenAI 的大语言模型，可以智能地将自然语言转换为 SQL 查询语句，并对查询结果进行智能总结。
这只是一个demo，只能基于签约表回答问题。

## 功能特点

- 🤖 自然语言转 SQL 查询
- 📊 实时执行数据库查询
- 📝 查询结果智能总结
- 💫 流式响应支持
- 🎨 是个好玩的玩具
- ✨ Markdown 格式支持
- 📈 智能数据可视化
  - 自动柱状图/条形图
  - 平滑折线图
  - 堆叠面积图
  - 圆角环形图
  - 散点图
  - 热力图

## 技术栈

- 后端：Python + Flask
- 数据库：MySQL 8
- 前端：HTML + JavaScript
- 图表：ECharts 5.4.3
- AI 模型：兼容 OpenAI 格式的 API，例如 qwen2.5:32b
- 跨域支持：Flask-CORS

## 系统要求

- Python 3.12 或以上
- MySQL 8.0 或以上
- OpenAI API 兼容格式的API访问权限
- chrome等现代浏览器

## 在线MySQL环境

如果您没有本地MySQL环境，可以使用[SQLPub](https://sqlpub.com)提供的免费在线MySQL服务：

## 快速开始

### 方式一：本地部署

1. 克隆项目
```bash
git clone https://github.com/yangjianchuan/chatmysql.git
cd chatmysql
```
2. windows系统创建虚拟环境
```bash
python -m venv venv
```
3.激活虚拟环境
```bash
source venv/Scripts/activate
```
4. 安装依赖
```bash
pip install -r requirements.txt
```

5. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填写必要的配置信息
```

6. 数据准备
   - 在MySQL中创建数据表，SQL语句如下：
   ```sql
   CREATE TABLE `contracts` (
     `id` varchar(50) DEFAULT NULL,
     `COMPANY_NAME` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NOT NULL COMMENT '公司',
     `fdate` date NOT NULL COMMENT '日期',
     `SIGNED_SETS` int NOT NULL COMMENT '签约套数',
     `SIGNED_AREA` decimal(16,2) NOT NULL COMMENT '签约面积',
     `SIGNED_AMOUNT` decimal(16,2) NOT NULL COMMENT '签约金额',
     PRIMARY KEY (`COMPANY_NAME`,`fdate`),
     KEY `id` (`id`)
   ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='签约表'
   ```
   
   - 插入示例数据（完整数据见 `databaseTable/contracts_insert.sql`）：
   ```sql
   INSERT INTO `contracts` (`id`,`COMPANY_NAME`,`fdate`,`SIGNED_SETS`,`SIGNED_AREA`,`SIGNED_AMOUNT`) 
   VALUES ('202403151412041642','DG公司','2023-01-01','94',222.00,809530000.00);
   INSERT INTO `contracts` (`id`,`COMPANY_NAME`,`fdate`,`SIGNED_SETS`,`SIGNED_AREA`,`SIGNED_AMOUNT`)
   VALUES ('202403156770318536','DG公司','2023-02-01','66',270.00,1053520000.00);
   -- 更多数据...
   ```
   
   - 在 `databaseTableSchema.md` 文件中编写系统提示词和数据库表结构、示例数据
     - 该文件包含SQL开发规范、数据库表结构定义和示例数据
     - 系统会使用此文件作为上下文来理解数据库结构和生成正确的SQL查询
   - 在 `training_data.jsonl` 中编写预训练数据，作为简易知识库
     - 文件格式为JSONL，每行包含一个完整的问答对
     - 每个问答对包含用户问题和对应的SQL查询响应
     - 系统会使用这些示例来提高自然语言到SQL的转换准确性

7. 启动服务器
```bash
python app.py
```

8. 访问应用
打开浏览器访问 http://localhost:5000

### 方式二：Docker部署

1. 克隆项目并进入目录
```bash
git clone https://github.com/yangjianchuan/chatmysql.git
cd chatmysql
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，填写必要的配置信息
```

3. 启动服务
```bash
docker-compose up -d
```

4. 访问应用
打开浏览器访问 http://localhost:5000

### Docker部署说明

#### 容器服务

本项目使用Docker Compose管理以下服务：

- **chatmysql**: 主应用服务
  - 基于Python 3.12镜像
  - 暴露5000端口
  - 自动加载环境变量配置

#### 环境变量配置

在使用Docker部署时，需要在 `.env` 文件中正确配置以下变量：

```env
# MySQL配置
MYSQL_HOST=mysql    # 使用容器服务名
MYSQL_PORT=3306
MYSQL_DATABASE=your_database
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password

# 其他配置保持不变
```

#### 常用Docker命令

- 启动服务：`docker-compose up -d`
- 停止服务：`docker-compose down`
- 查看日志：`docker-compose logs -f`
- 重启服务：`docker-compose restart`
- 重建容器：`docker-compose up -d --build`

#### 注意事项

1. 首次启动时会自动创建必要的数据卷和网络
2. MySQL数据库首次启动需要一定时间初始化
3. 确保Docker和Docker Compose已正确安装
4. 防火墙需要允许容器间通信

## 环境变量配置

ChatMySQL 应用使用 `.env` 文件来配置系统的各项参数。以下是所有环境变量的详细说明：

### OpenAI 基础配置
- **OPENAI_API_KEY**: OpenAI API 的访问密钥，用于访问 OpenAI 的服务。
- **OPENAI_BASE_URL**: OpenAI API 的基础 URL，可以是官方 API 地址或自定义的 API 代理地址。
- **OPENAI_MODEL**: 默认使用的 OpenAI 模型名称，如 "gpt-4o"、"deepseek-chat" 或其他支持的模型。

### SQL 生成模型配置
- **SQL_API_KEY**: 用于 SQL 生成的 API 密钥。如果未设置，系统将使用 OPENAI_API_KEY。
- **SQL_BASE_URL**: SQL 生成服务的基础 URL。如果未设置，系统将使用 OPENAI_BASE_URL。
- **SQL_MODEL**: 用于 SQL 生成的模型名称。**必须是支持 function calling 功能的模型**，如果未设置，系统将使用 OPENAI_MODEL。

### 结果总结模型配置
- **SUMMARY_API_KEY**: 用于结果总结的 API 密钥。如果未设置，系统将使用 OPENAI_API_KEY。
- **SUMMARY_BASE_URL**: 结果总结服务的基础 URL。如果未设置，系统将使用 OPENAI_BASE_URL。
- **SUMMARY_MODEL**: 用于结果总结的模型名称。如果未设置，系统将使用 OPENAI_MODEL。

### MySQL 数据库配置
- **MYSQL_USER**: MySQL 数据库用户名。
- **MYSQL_PASSWORD**: MySQL 数据库密码。
- **MYSQL_HOST**: MySQL 数据库主机地址。
- **MYSQL_PORT**: MySQL 数据库端口号，默认为 3306。
- **MYSQL_DATABASE**: 要连接的数据库名称。
- **MYSQL_RAISE_ON_WARNINGS**: 是否在警告时抛出异常，值为 "True" 或 "False"。
- **MYSQL_AUTH_PLUGIN**: MySQL 认证插件，通常为 "mysql_native_password"。
- **MYSQL_CONNECTION_TIMEOUT**: 数据库连接超时时间（秒），默认为 10。

### 显示配置
- **SHOW_SQL_QUERY**: 是否在前端界面显示生成的 SQL 查询语句，值为 "是" 或 "否"。
- **SHOW_QUERY_RESULT**: 是否在前端界面显示查询结果，值为 "是" 或 "否"。

### 训练数据配置
- **LOAD_TRAINING_DATA**: 是否加载训练数据作为上下文，值为 "是" 或 "否"。当设置为 "是" 时，系统会从 training_data.jsonl 文件中加载预定义的问答对，用于提高自然语言到 SQL 的转换准确性。

### 结果总结配置
- **SUMMARY_PROMPT**: 用于指导 AI 模型如何总结查询结果的提示词。

### 配置示例
请参考完整的示例 `.env.example` ：

### 注意事项
1. 所有敏感信息（如 API 密钥和数据库密码）应妥善保管，不要将包含真实凭据的 `.env` 文件提交到版本控制系统。
2. SQL_MODEL 必须使用支持 function calling 功能的模型，否则系统将无法正常生成 SQL 查询。
3. 如果您使用的是自定义的 API 代理或服务，请确保在 BASE_URL 中提供正确的端点地址。
4. 对于中文环境，建议将显示配置和训练数据配置设置为 "是"，以获得更好的用户体验。

## API 接口

### 主要接口

1. `/api/chat` (POST)
   - 功能：处理自然语言查询请求
   - 输入：JSON 格式的查询文本
   - 输出：流式响应，包含 SQL 查询、查询结果和总结


## 数据模型

系统主要管理签约数据，核心数据表：

### contracts（签约表）
- id：唯一标识符
- COMPANY_NAME：公司名称
- fdate：签约日期
- SIGNED_SETS：签约套数
- SIGNED_AREA：签约面积
- SIGNED_AMOUNT：签约金额

## 安全特性

- 数据库连接池管理
- 自动关闭数据库连接
- 跨域安全控制
- 环境变量管理敏感信息

## 使用示例

1. 在查询框输入自然语言问题，如：
   今年签约金额是多少
   上个月签约金额多少
   今年2月同比去年签约金额增长了吗
   DG公司今年2月签约金额是多少
   去年有多少家公司签约金额超过1000万元
   2023年卖了多少套房子
   2023年有多少家公司连续3个月签约金额下滑
   去年套均价多少
   对比DG公司和FS公司去年各月的签约金额

2. 系统会：
   - 将问题转换为 SQL 查询
   - 执行查询并获取结果
   - 使用 AI 对结果进行智能总结
   - 自动生成适合的数据可视化图表
   - 以流式方式展示整个过程

3. 图表功能：
   - 系统会根据查询结果自动选择最适合的图表类型
   - 支持多种图表类型切换：
     - 柱状图：适合展示不同类别的数值比较
     - 条形图：适合展示较多分类的横向比较
     - 平滑折线图：适合展示趋势变化
     - 堆叠面积图：适合展示部分与整体的关系
     - 圆角环形图：适合展示占比分布
     - 散点图：适合展示数据分布和相关性
     - 热力图：适合展示多维度数据的强度分布
   - 图表特性：
     - 自动数据格式化（千分位分隔）
     - 智能标签位置调整
     - 炫酷配色方案
     - 交互式提示框
     - 图表导出功能
     - 自适应布局

4. 数据展示：
   - 表格视图：清晰展示详细数据
   - 图表视图：直观展示数据趋势和分布
   - 智能总结：AI 生成的数据洞察

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 许可证

本项目基于 [LICENSE](LICENSE) 许可证开源。
