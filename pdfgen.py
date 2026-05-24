from flask import Flask, request, send_file, render_template_string
import pdfkit
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import uuid

# Flask 앱 설정
app = Flask(__name__)

# HTML UI (포토샵 테마)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #1e1e1e; color: #e0e0e0; font-family: sans-serif; }
        .ps-panel { background-color: #2d2d2d; border: 1px solid #3d3d3d; }
    </style>
</head>
<body class="p-8">
    <div class="max-w-xl mx-auto ps-panel p-8 rounded-lg shadow-xl">
        <h1 class="text-2xl font-bold mb-4 text-blue-400">AI 학습 데이터 변환기</h1>
        <p class="text-gray-400 mb-6">학습하고 싶은 블로그 주소를 입력하세요.</p>
        <form action="/convert" method="post" class="space-y-4">
            <input type="text" name="url" placeholder="https://m.blog.naver.com/..." class="w-full p-3 bg-gray-700 rounded border border-gray-600 focus:outline-none focus:border-blue-500">
            <button type="submit" class="w-full p-3 bg-blue-600 hover:bg-blue-700 rounded font-bold transition">PDF로 변환하기</button>
        </form>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/convert', methods=['POST'])
def convert():
    url = request.form.get('url')
    output_filename = f"{uuid.uuid4()}.pdf"
    
    # 네이버 블로그 모바일화
    if "blog.naver.com" in url and "m.blog.naver.com" not in url:
        url = url.replace("blog.naver.com", "m.blog.naver.com")

    try:
        # PDF 옵션
        options = {
            'page-size': 'A4',
            'margin-top': '0.5in',
            'margin-right': '0.5in',
            'margin-bottom': '0.5in',
            'margin-left': '0.5in',
        }
        # 서버 환경에 맞춰 wkhtmltopdf 경로 설정 필요 (예: /usr/bin/wkhtmltopdf)
        pdfkit.from_url(url, output_filename, options=options)
        return send_file(output_filename, as_attachment=True)
    except Exception as e:
        return f"변환 실패: {e}"

if __name__ == '__main__':
    app.run(debug=True)