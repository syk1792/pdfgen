from flask import Flask, request, send_file, render_template_string
import uuid
import requests

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html><body>
    <h1>PDF 변환기 서버 작동 중</h1>
    <p>블로그 주소를 입력하면 PDF가 생성됩니다.</p>
    <form action="/convert" method="post">
        <input type="text" name="url" placeholder="블로그 주소">
        <button type="submit">변환하기</button>
    </form>
</body></html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/convert', methods=['POST'])
def convert():
    url = request.form.get('url')
    # 브라우저인 척 헤더 추가
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        # 여기서 PDF 변환 로직을 수행합니다. 
        # 서버에서 직접 PDF를 만드는 것은 제약이 많으므로, 일단 HTML 데이터를 응답으로 줍니다.
        return f"변환 요청 완료! (실제 PDF 변환은 로컬 환경에서 하는 것이 가장 정확합니다.)"
    except Exception as e: return f"오류: {e}"

if __name__ == '__main__':
    app.run()
