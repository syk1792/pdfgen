from flask import Flask, request, send_file, render_template_string
from weasyprint import HTML
import uuid
import requests

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html><body>
    <h1>PDF 변환기</h1>
    <form action="/convert" method="post">
        <input type="text" name="url" placeholder="블로그 주소">
        <button type="submit">PDF 생성</button>
    </form>
</body></html>
"""

@app.route('/')
def index(): return render_template_string(HTML_TEMPLATE)

@app.route('/convert', methods=['POST'])
def convert():
    url = request.form.get('url')
    # 브라우저인 척 헤더 추가
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)
        output_filename = f"{uuid.uuid4()}.pdf"
        # WeasyPrint로 직접 HTML 처리
        HTML(string=response.text).write_pdf(output_filename)
        return send_file(output_filename, as_attachment=True)
    except Exception as e: return f"오류: {e}"

if __name__ == '__main__':
    app.run()
