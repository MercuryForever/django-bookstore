# 书店零售管理系统

![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB)
![Django 6.0](https://img.shields.io/badge/Django-6.0-092E20)
![License: MIT](https://img.shields.io/badge/License-MIT-green)

简体中文 | [English](README.en.md)

一个面向中小型书店的零售与进销存管理系统，以「采购入库 → 库存调拨与盘点 → POS 销售 → 财务核算」为主线，把商品、门店、会员、订单与库存流水串成一条可追溯的业务闭环。

## 目录

- [项目简介](#项目简介)
- [项目背景与设计动机](#项目背景与设计动机)
- [功能列表](#功能列表)
- [技术栈](#技术栈)
- [目录结构](#目录结构)
- [本地运行](#本地运行)
- [部署说明](#部署说明)
- [界面截图](#界面截图)
- [演示账户与角色权限](#演示账户与角色权限)
- [提交规范](#提交规范)
- [许可证](#许可证)

## 项目简介

这是一个基于 Django 的单体 Web 应用，采用原生 MVT 架构与服务端模板渲染，无需单独构建前端工程即可运行。系统按业务域拆分为 `users`、`inventory`、`purchase`、`sales`、`finance` 五个应用，各自持有模型、路由、模板与权限约束，通过 URL 命名空间隔离边界。

界面使用 Bootstrap 5 与 Chart.js，覆盖后台仪表盘、POS 收银、库存台账、采购单据、会员档案和财务报表等场景；开发环境下使用 SQLite，配合两个管理命令即可初始化管理员与演示数据，便于直接体验完整流程。

## 项目背景与设计动机

这个项目源于一个很具体的目标：把 Django 从「能跑通的示例」推进到「结构完整、边界清晰的业务系统」。我不想再写一个孤立的 CRUD 页面，而是希望完整走通一个业务域从领域建模、权限控制、事务一致性到统计报表的全过程。

选择书店零售作为题材，是因为它的实体关系足够清晰（商品、分类、仓库、门店、供应商、会员、订单），同时保留了真实的业务复杂度：库存变动需要流水追溯，调拨与采购需要状态流转，折扣与积分需要独立规则，报表则涉及跨表聚合与时间序列。

设计上有三点取舍：

1. **服务端渲染优先**：使用 Django Templates + Bootstrap，把复杂度留在业务层，避免为一个后台系统引入前后端分离与额外的构建链路。
2. **按业务域拆分应用**：每个 app 自带模型、路由、模板与迁移，权限通过 `role_required` 装饰器在视图层统一收口，而不是散落在各处的条件判断。
3. **库存流水作为单一事实来源**：收货、销售扣减、调拨、盘点都写入 `StockMovement`，数量变化始终有据可对账，而不是直接覆盖库存字段。

## 功能列表

| 模块 | 功能 | 说明 |
| :--- | :--- | :--- |
| 认证与权限 `users` | 登录 / 登出、员工增删改查、三级角色控制 | `admin` / `manager` / `cashier`，通过 `role_required` 及快捷装饰器约束视图访问 |
| 仪表盘 | 经营概览与趋势 | 今日 / 本月销售额与订单数、近 7 天销售趋势、库存预警数、会员总数、商品销售排行、最近成交记录 |
| 库存 `inventory` | 商品台账与仓储作业 | 商品与分类、仓库与门店、库存查询与明细、低库存预警、调拨单（创建 / 审批 / 执行 / 取消）、盘点单（创建 / 录入 / 完成）、库存与商品检索 API |
| 采购 `purchase` | 供应商与采购流程 | 供应商维护、采购订单（创建 / 编辑 / 提交 / 审核 / 取消）、采购收货与收货明细 |
| 销售 `sales` | POS 与会员 | 收银与购物车、折扣校验（含周三会员折扣）、会员结账与积分、销售记录与明细、Excel 导出、销售排行与趋势 API、会员注册与档案维护 |
| 财务 `finance` | 报表与核算 | 日报、月报、利润分析，以及日报 / 月报的 Excel 导出 |
| 开发工具 | 数据初始化与校验 | `create_admin`、`generate_test_data` 两个管理命令，以及根目录下的数据一致性检查脚本 |

## 技术栈

| 类别 | 选型 | 用途 |
| :--- | :--- | :--- |
| 语言 | Python ≥ 3.12 | 运行时 |
| Web 框架 | Django ≥ 6.0 | ORM、认证、Admin、模板与迁移 |
| 界面 | Django Templates + Bootstrap 5.3 + Bootstrap Icons 1.10 | 服务端渲染，通过 CDN 引入 |
| 图表 | Chart.js | 销售趋势与排行可视化 |
| 数据库 | SQLite（开发）/ PostgreSQL、MySQL（生产需自行配置） | 统一通过 Django ORM 访问 |
| 依赖库 | Faker、openpyxl | 演示数据生成、报表 Excel 导出 |
| 工具链 | uv | 依赖声明与虚拟环境管理（`pyproject.toml` + `uv.lock`） |

## 目录结构

```text
django-bookstore/
├── config/                         # 项目级配置
│   ├── settings.py                 # 设置、日志、认证跳转
│   ├── urls.py                     # 根路由与仪表盘视图
│   └── asgi.py / wsgi.py
├── users/                          # 员工、认证与角色权限
│   ├── decorators.py               # role_required 及快捷装饰器
│   ├── management/commands/        # create_admin
│   └── templates/users/
├── inventory/                      # 商品、库存、调拨与盘点
│   ├── management/commands/        # generate_test_data
│   ├── templatetags/               # 模板辅助标签
│   └── templates/inventory/
├── purchase/                       # 供应商与采购订单
│   └── templates/purchase/
├── sales/                          # POS、会员与销售记录
│   ├── utils.py                    # 趋势与排行聚合函数
│   └── templates/sales/
├── finance/                        # 日报、月报与利润分析
│   └── templates/finance/
├── templates/                      # base.html 与 dashboard.html
├── static/                         # 本地静态资源（预留）
├── docs/screenshots/               # 界面截图（占位）
├── manage.py
├── pyproject.toml / uv.lock
├── README.md / README.en.md
└── LICENSE
```

根目录下的 `check_sales.py`、`check_sales_data.py`、`sync_check.py`、`create_test_data.py`、`test_dashboard.py` 是开发期使用的数据校验脚本，不参与运行时请求处理。

## 本地运行

### 1. 克隆仓库

```bash
git clone https://github.com/MercuryForever/django-bookstore.git
cd django-bookstore
```

### 2. 准备环境

要求 Python 3.12 或更高版本，二选一安装依赖：

**使用 uv（推荐，版本由 `uv.lock` 锁定）**

```bash
uv sync
```

**使用 pip**

```bash
python -m pip install "django>=6.0" "faker>=40.1.0" "openpyxl>=3.1.5"
```

> 在 uv 环境中，后续命令需加上 `uv run` 前缀，例如 `uv run python manage.py migrate`。

### 3. 初始化数据库

```bash
python manage.py migrate
```

### 4. 创建管理员

```bash
python manage.py create_admin
```

默认账号 `admin` / 密码 `admin123`，**仅用于本地开发**。

### 5. 生成演示数据（可选）

```bash
python manage.py generate_test_data
```

该命令会生成仓库、门店、分类、商品、会员、员工和模拟销售记录，同时创建下表中的经理与收银员演示账号。

### 6. 启动服务

```bash
python manage.py runserver
```

浏览器访问 `http://127.0.0.1:8000`。

## 部署说明

仓库中的 `config/settings.py` 使用开发默认值：`DEBUG = True`、`ALLOWED_HOSTS = ['*']`、硬编码的 `SECRET_KEY` 以及 SQLite。**这些配置不能直接用于生产环境**，上线前需完成以下调整。

### 1. 注入生产配置

将敏感项改为从环境变量读取，例如：

```python
import os

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DEBUG = os.environ.get('DJANGO_DEBUG', '0') == '1'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')
```

随后设置 `DJANGO_SECRET_KEY`（随机长字符串）、`DJANGO_ALLOWED_HOSTS`（实际域名）以及部署所需的 `CSRF_TRUSTED_ORIGINS`、`SECURE_*` 相关项，并启用 HTTPS。

### 2. 切换数据库

SQLite 仅适合本地与单机演示。生产环境建议将 `DATABASES` 切换为 PostgreSQL 或 MySQL，安装对应数据库驱动，并在新库上重新执行迁移。

### 3. 配置静态文件

在 settings 中设置 `STATIC_ROOT` 后执行：

```bash
python manage.py collectstatic --noinput
```

界面依赖的 Bootstrap 与 Chart.js 由 CDN 提供，若部署环境无法访问外网，需改为本地托管。项目预留了 `static/` 目录用于存放自有静态资源。

### 4. 安装依赖并初始化

```bash
uv sync --frozen                 # 或按 pyproject.toml 使用 pip 安装
python manage.py migrate
python manage.py create_admin    # 或 createsuperuser
python manage.py collectstatic --noinput
```

创建管理员后立即修改默认密码；**不要在生产环境执行 `generate_test_data`**，也不要保留任何演示账号。

### 5. 应用服务器与反向代理

使用 Gunicorn 承载 WSGI 应用，由 Nginx 终止 HTTPS 并转发请求、托管静态文件：

```bash
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 3
```

将 `config/wsgi.py` 暴露的应用挂到 Nginx 的 `proxy_pass`，并把 `/static/` 指向 `STATIC_ROOT`。日志默认写入项目根目录的 `bookstore.log`，需确保运行用户对该路径有写权限。

### 6. 上线检查

```bash
python manage.py check --deploy
```

按输出逐项确认安全设置，并复核：环境变量未进入版本库、`DEBUG` 为关闭状态、数据库与日志目录权限正确、演示数据已清除。

## 界面截图

截图统一存放于 `docs/screenshots/`，目录已建立，当前为**占位状态**，图片待补充。

| 页面 | 截图文件 | 展示内容 |
| :--- | :--- | :--- |
| 仪表盘 | `docs/screenshots/dashboard.png` | 今日 / 本月销售、近 7 天趋势、库存预警与销售排行 |
| POS 收银 | `docs/screenshots/pos.png` | 商品检索、购物车、折扣与会员结账 |
| 库存列表 | `docs/screenshots/inventory.png` | 多门店库存查询与低库存标记 |
| 库存调拨 | `docs/screenshots/stock-transfer.png` | 调拨单创建与状态流转 |
| 采购订单 | `docs/screenshots/purchase-order.png` | 订单明细、审核与收货 |
| 会员管理 | `docs/screenshots/members.png` | 会员档案与积分记录 |
| 财务报表 | `docs/screenshots/finance-report.png` | 日报 / 月报与利润分析 |

<!-- 截图补齐后启用以下引用：
![仪表盘](docs/screenshots/dashboard.png)
-->

## 演示账户与角色权限

以下账号由 `generate_test_data` 生成，仅用于本地体验。

| 角色 | 账号 | 密码 |
| :--- | :--- | :--- |
| 管理员 Admin | `admin`（由 `create_admin` 创建） | `admin123` |
| 经理 Manager | `manager_S0001` ~ `manager_S0050` | `password123` |
| 收银员 Cashier | `cashier_S0001_1` | `password123` |

| 角色 | 可访问范围 |
| :--- | :--- |
| 管理员 Admin | 全部功能，含员工管理与系统配置 |
| 经理 Manager | 库存查询 / 调拨 / 盘点、采购审核、财务报表、销售排行、会员管理 |
| 收银员 Cashier | POS 收银与结账 |

## 提交规范

提交信息遵循 [Conventional Commits](https://www.conventionalcommits.org/)，格式为 `<type>(<scope>): <subject>`：

- **type**：`feat`、`fix`、`docs`、`refactor`、`perf`、`test`、`build`、`chore`
- **scope**：应用名（`users`、`inventory`、`purchase`、`sales`、`finance`、`config`）或领域词（`dashboard`、`scripts`、`deps`）

示例：

```text
feat(sales): add membership points redemption at checkout
fix(inventory): prevent negative stock on transfer execution
docs: clarify production deployment checklist
```

## 许可证

本项目基于 [MIT License](LICENSE) 开源，Copyright (c) 2026 MercuryForever。
