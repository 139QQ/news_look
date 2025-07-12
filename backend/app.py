from flask import Flask, render_template

app = Flask(__name__, 
    static_folder='static',  # 确保静态文件路径正确
    template_folder='templates'
)

@app.route('/')
def index():
    return render_template('index.html')

# 处理前端路由的catch-all路由
@app.route('/<path:path>')
def catch_all(path):
    return render_template('index.html') 