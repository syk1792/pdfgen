from flask import Flask, request, send_file, render_template_string
import os
import uuid

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html><body>
    <h1>AI 데이터 업로더</h1>
    <form action="/convert" method="post" enctype="multipart/form-data">
        <input type="file" name="file">
        <button type="submit">업로드</button>
    </form>
</body></html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/convert', methods=['POST'])
def convert():
    # 서버에 파일을 올리면 여기서 처리하는 로직을 나중에 추가 가능
    return "서버 연결 성공! 이제 이 서버를 통해 파일을 처리할 수 있습니다."

if __name__ == '__main__':
    app.run()
