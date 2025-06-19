# NewsLook Web应用说明

## 版本说明

本项目包含两个版本的Web应用：

1. **旧版应用**：位于项目根目录下的`web/`文件夹中
   - 入口文件：`web/app.py`
   - 启动方式：`start_web.bat`或`python main.py`

2. **新版应用**：位于`newslook/web/`文件夹中（模块化结构）
   - 入口文件：`newslook/web/__init__.py`
   - 启动方式：`python run.py web`或`python test_flask_app.py`
   - 推荐使用的启动脚本：`start_newslook_web.bat`

## 推荐使用

强烈建议使用**新版应用**，因为：

1. 新版应用使用了更清晰的模块化结构
2. 新版应用支持多数据库自动发现和使用，能够显示所有爬取的数据
3. 新版应用已更新所有导入路径，确保与项目其他部分的兼容性
4. 新版应用支持更多功能，如爬虫状态监控、统计分析等

## 启动方法

### 启动新版Web应用（推荐）

```
python run.py web --debug
```

或者双击运行`start_newslook_web.bat`

### 访问Web应用

启动后，在浏览器中访问：
- http://127.0.0.1:8000（默认）
- http://127.0.0.1:5000（如果使用test_flask_app.py启动）

## 数据库路径

新版应用会自动查找和使用数据库文件，默认查找顺序为：
1. `./data/db/`（项目根目录下的data/db文件夹）
2. `./db/`（项目根目录下的db文件夹）

您也可以通过环境变量指定数据库路径：
```
set DB_DIR=D:\Your\Path\To\DB
python run.py web
```

## 注意事项

1. 如果Web页面未显示爬取的新闻，请检查：
   - 使用的是哪个版本的Web应用
   - 数据库文件路径是否正确
   - 数据库中是否有数据（可以通过`check_db.py`脚本检查）

2. 为避免混淆，建议只使用一个版本的Web应用，推荐使用新版。

3. 如果需要启动爬虫，可以使用：
   ```
   python run.py crawler
   ```

4. 如果需要查看当前数据库中的数据，可以使用：
   ```
   python check_db.py
   ``` 