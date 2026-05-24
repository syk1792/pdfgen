from flask import Flask, request, send_file, render_template_string
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import io, os, re

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>네이버 블로그 PDF 변환기</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; background: #f5f2ec; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
  .card { background: #fff; border-radius: 12px; padding: 40px 36px; max-width: 500px; width: 100%; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
  h1 { font-size: 20px; font-weight: 700; color: #1a1612; margin-bottom: 8px; }
  .sub { font-size: 13px; color: #9a9080; margin-bottom: 28px; line-height: 1.6; }
  label { font-size: 13px; font-weight: 500; color: #3a3530; display: block; margin-bottom: 6px; }
  input[type=text] { width: 100%; padding: 12px 14px; border: 1px solid #e0d8cc; border-radius: 8px; font-size: 14px; color: #1a1612; outline: none; transition: border 0.2s; }
  input[type=text]:focus { border-color: #c8a850; }
  button { width: 100%; margin-top: 14px; padding: 13px; background: #1a1612; color: #fff; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; transition: background 0.2s; }
  button:hover { background: #333; }
  .msg { margin-top: 18px; padding: 14px; border-radius: 8px; font-size: 13px; line-height: 1.6; display: none; }
  .msg.success { background: #edfaed; color: #2a7a2a; border: 1px solid #b8e8b8; }
  .msg.error { background: #faeaea; color: #8a2020; border: 1px solid #e8b8b8; }
  .loading { display: none; text-align: center; margin-top: 14px; font-size: 13px; color: #9a9080; }
</style>
</head>
<body>
<div class="card">
  <h1>📄 네이버 블로그 PDF 변환기</h1>
  <p class="sub">네이버 블로그 주소를 입력하면 본문만 추출해 PDF로 다운로드합니다.<br>NotebookLM, Gemini AI 학습에 바로 활용하세요.</p>
  <form id="form">
    <label>블로그 주소</label>
    <input type="text" id="url" placeholder="https://blog.naver.com/..." />
    <button type="submit">PDF로 변환하기</button>
  </form>
  <div class="loading" id="loading">⏳ 변환 중입니다... 잠시만 기다려 주세요.</div>
  <div class="msg" id="msg"></div>
</div>
<script>
document.getElementById('form').addEventListener('submit', async function(e) {
  e.preventDefault();
  const url = document.getElementById('url').value.trim();
  if (!url) return;
  document.getElementById('loading').style.display = 'block';
  document.getElementById('msg').style.display = 'none';
  try {
    const res = await fetch('/convert', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'url=' + encodeURIComponent(url)
    });
    if (res.ok && res.headers.get('content-type').includes('pdf')) {
      const blob = await res.blob();
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'naver_blog.pdf';
      a.click();
      showMsg('success', '✅ PDF 다운로드가 시작됩니다!');
    } else {
      const text = await res.text();
      showMsg('error', '❌ ' + text);
    }
  } catch(err) {
    showMsg('error', '❌ 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.');
  }
  document.getElementById('loading').style.display = 'none';
});
function showMsg(type, text) {
  const el = document.getElementById('msg');
  el.className = 'msg ' + type;
  el.textContent = text;
  el.style.display = 'block';
}
</script>
</body>
</html>
"""

def fetch_naver_blog(url):
    # 모바일 URL로 변환 (크롤링 용이)
    mobile_url = url.replace('blog.naver.com', 'm.blog.naver.com')
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Accept-Language': 'ko-KR,ko;q=0.9'
    }
    res = requests.get(mobile_url, headers=headers, timeout=15)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')

    # 제목 추출
    title = ''
    for sel in ['.se-title-text', '.tit_h3', 'h3.tit_view', '.pcol1', 'title']:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(strip=True)
            break

    # 본문 추출
    content = ''
    for sel in ['.se-main-container', '.post-view', '#postViewArea', '.se_component_wrap']:
        el = soup.select_one(sel)
        if el:
            content = el.get_text(separator='\n', strip=True)
            break

    if not content:
        content = soup.get_text(separator='\n', strip=True)

    # 불필요한 빈 줄 정리
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    content = '\n'.join(lines)

    return title, content

def create_pdf(title, content, source_url):
    pdf = FPDF()
    pdf.add_page()

    # 한글 폰트 (기본 내장 폰트로 ASCII만 처리, 한글은 latin-1 안전처리)
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_fill_color(26, 22, 18)
    pdf.set_text_color(255, 255, 255)
    pdf.rect(0, 0, 210, 32, 'F')
    pdf.set_xy(10, 10)
    safe_title = title.encode('latin-1', 'replace').decode('latin-1')
    pdf.cell(0, 12, safe_title[:60] or 'Naver Blog Post', ln=True)

    pdf.set_text_color(150, 140, 120)
    pdf.set_font('Helvetica', '', 8)
    pdf.set_xy(10, 22)
    pdf.cell(0, 6, source_url[:80], ln=True)

    pdf.set_text_color(40, 35, 30)
    pdf.set_font('Helvetica', '', 11)
    pdf.set_xy(10, 40)

    for line in content.split('\n'):
        safe_line = line.encode('latin-1', 'replace').decode('latin-1')
        if not safe_line.strip():
            pdf.ln(4)
            continue
        pdf.set_x(10)
        pdf.multi_cell(190, 6, safe_line)

        if pdf.get_y() > 270:
            pdf.add_page()
            pdf.set_font('Helvetica', '', 11)
            pdf.set_xy(10, 15)

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/convert', methods=['POST'])
def convert():
    url = request.form.get('url', '').strip()
    if not url:
        return '주소를 입력해 주세요.', 400
    if 'blog.naver.com' not in url:
        return '네이버 블로그 주소만 지원합니다.', 400
    try:
        title, content = fetch_naver_blog(url)
        if not content or len(content) < 50:
            return '블로그 내용을 가져오지 못했습니다. 공개된 글인지 확인해 주세요.', 400
        pdf_buf = create_pdf(title, content, url)
        return send_file(pdf_buf, mimetype='application/pdf',
                         as_attachment=True, download_name='naver_blog.pdf')
    except Exception as e:
        return f'오류가 발생했습니다: {str(e)}', 500

if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('PORT', 8080))
    serve(app, host='0.0.0.0', port=port)
