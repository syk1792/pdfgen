from flask import Flask, request, send_file, render_template_string
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import io, os, re

app = Flask(__name__)

FONT_PATH = 'NanumGothic-Regular.ttf'

def ensure_font():
    pass

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>웹페이지 PDF 변환기</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; background: #f5f2ec; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
  .card { background: #fff; border-radius: 12px; padding: 40px 36px; max-width: 500px; width: 100%; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
  h1 { font-size: 20px; font-weight: 700; color: #1a1612; margin-bottom: 8px; }
  .sub { font-size: 13px; color: #9a9080; margin-bottom: 28px; line-height: 1.7; }
  label { font-size: 13px; font-weight: 500; color: #3a3530; display: block; margin-bottom: 6px; }
  input[type=text] { width: 100%; padding: 12px 14px; border: 1px solid #e0d8cc; border-radius: 8px; font-size: 14px; color: #1a1612; outline: none; transition: border 0.2s; margin-bottom: 16px; }
  input[type=text]:focus { border-color: #c8a850; }
  button { width: 100%; padding: 14px; background: #1a1612; color: #fff; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; transition: background 0.2s; letter-spacing: 0.03em; }
  button:hover { background: #3a3530; }
  .msg { margin-top: 18px; padding: 14px; border-radius: 8px; font-size: 13px; line-height: 1.6; display: none; }
  .msg.success { background: #edfaed; color: #2a7a2a; border: 1px solid #b8e8b8; }
  .msg.error { background: #faeaea; color: #8a2020; border: 1px solid #e8b8b8; }
  .loading { display: none; text-align: center; margin-top: 16px; font-size: 13px; color: #9a9080; line-height: 1.8; }
  .loading .spinner { display: inline-block; width: 18px; height: 18px; border: 2px solid #e0d8cc; border-top-color: #1a1612; border-radius: 50%; animation: spin 0.8s linear infinite; margin-right: 8px; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .tag { display: inline-block; font-size: 10px; padding: 2px 8px; border-radius: 20px; background: #f0ece4; color: #8a7a60; margin-bottom: 20px; letter-spacing: 0.05em; }
</style>
</head>
<body>
<div class="card">
  <span class="tag">TEXT · PDF · AI READY</span>
  <h1>📄 웹페이지 PDF 변환기</h1>
  <p class="sub">네이버 블로그, 티스토리, 브런치, 뉴스 기사 등<br>어떤 웹페이지든 본문만 깔끔하게 추출해 PDF로 저장합니다.<br>NotebookLM, Gemini AI 학습에 바로 활용하세요.</p>
  <form id="form">
    <label>웹페이지 주소</label>
    <input type="text" id="url" placeholder="https://blog.naver.com/..." />
    <button type="submit">PDF로 변환하기</button>
  </form>
  <div class="loading" id="loading">
    <span class="spinner"></span>본문을 추출하고 있습니다. 잠시만 기다려 주세요.
  </div>
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
      a.download = 'page.pdf';
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

# 광고/불필요 텍스트 필터링 패턴
NOISE_PATTERNS = [
    r'^공감\s*\d*$', r'^댓글\s*\d*$', r'^구독\s*\d*$',
    r'^이웃추가$', r'^카카오스토리$', r'^트위터$', r'^페이스북$',
    r'^URL 복사$', r'^통계$', r'^신고$', r'^목록보기$',
    r'^\d+$', r'^[ㄱ-ㅎ가-힣]{1,2}$',
    r'^\s*$', r'^Copyright', r'^All rights reserved',
    r'로그인', r'회원가입', r'광고', r'본문 바로가기',
]

def is_noise(text):
    text = text.strip()
    if len(text) < 2:
        return True
    for pattern in NOISE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def fetch_page(url):
    if 'blog.naver.com' in url:
        url = url.replace('blog.naver.com', 'm.blog.naver.com')

    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
        'Accept-Language': 'ko-KR,ko;q=0.9'
    }
    res = requests.get(url, headers=headers, timeout=15)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')

    # 불필요한 태그 제거
    for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header',
                               'aside', 'iframe', 'noscript', 'ads']):
        tag.decompose()

    # 제목 추출
    title = ''
    for sel in ['.se-title-text', 'h1', '.tit_h3', '.pcol1', 'title']:
        el = soup.select_one(sel)
        if el:
            t = el.get_text(strip=True)
            if t and len(t) > 2:
                title = t
                break

    # 본문 컨테이너
    container = None
    for sel in [
        '.se-main-container',
        'article',
        '.post-content',
        '.entry-content',
        '.article-body',
        '.tt_article_useless_p_margin',  # 티스토리
        '#postViewArea',
        'main',
        '#content',
        '.content',
    ]:
        container = soup.select_one(sel)
        if container:
            break

    blocks = []
    if container:
        for el in container.descendants:
            if not hasattr(el, 'name') or not el.name:
                continue
            if el.name in ['h2', 'h3', 'h4']:
                text = el.get_text(strip=True)
                if text and not is_noise(text):
                    blocks.append({'type': 'heading', 'text': text})
            elif el.name == 'p':
                text = el.get_text(strip=True)
                if text and len(text) > 5 and not is_noise(text):
                    blocks.append({'type': 'body', 'text': text})
            elif el.name in ['li']:
                text = el.get_text(strip=True)
                if text and len(text) > 2 and not is_noise(text):
                    blocks.append({'type': 'list', 'text': '• ' + text})
    else:
        for line in soup.get_text(separator='\n').split('\n'):
            line = line.strip()
            if line and len(line) > 5 and not is_noise(line):
                blocks.append({'type': 'body', 'text': line})

    # 중복 제거
    seen = set()
    unique = []
    for b in blocks:
        key = b['text']
        if key not in seen:
            seen.add(key)
            unique.append(b)

    return title, unique

def create_pdf(title, blocks, source_url):
    ensure_font()
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Nanum', '', FONT_PATH)

    # 헤더 배경
    pdf.set_fill_color(26, 22, 18)
    pdf.rect(0, 0, 210, 42, 'F')

    # 제목
    pdf.set_font('Nanum', size=17)
    pdf.set_text_color(240, 236, 228)
    pdf.set_xy(12, 8)
    pdf.multi_cell(186, 9, title[:60] if title else '웹페이지')

    # URL
    pdf.set_font('Nanum', size=8)
    pdf.set_text_color(100, 90, 76)
    pdf.set_xy(12, 32)
    pdf.cell(0, 6, source_url[:90], ln=True)

    # 구분선
    pdf.set_draw_color(200, 168, 80)
    pdf.set_line_width(0.5)
    pdf.line(12, 43, 198, 43)

    pdf.set_xy(12, 50)

    for block in blocks:
        if pdf.get_y() > 272:
            pdf.add_page()
            pdf.set_xy(12, 15)

        if block['type'] == 'heading':
            pdf.ln(5)
            pdf.set_x(12)
            pdf.set_font('Nanum', size=14)
            pdf.set_text_color(26, 22, 18)
            pdf.multi_cell(186, 8, block['text'])
            # 소제목 아래 밑줄
            y = pdf.get_y()
            pdf.set_draw_color(220, 210, 190)
            pdf.set_line_width(0.3)
            pdf.line(12, y, 198, y)
            pdf.ln(3)

        elif block['type'] == 'body':
            pdf.set_x(12)
            pdf.set_font('Nanum', size=10)
            pdf.set_text_color(50, 45, 38)
            pdf.multi_cell(186, 6.5, block['text'])
            pdf.ln(1.5)

        elif block['type'] == 'list':
            pdf.set_x(16)
            pdf.set_font('Nanum', size=10)
            pdf.set_text_color(60, 55, 46)
            pdf.multi_cell(182, 6.5, block['text'])
            pdf.ln(1)

    # 푸터
    pdf.set_y(-15)
    pdf.set_font('Nanum', size=8)
    pdf.set_text_color(180, 170, 155)
    pdf.cell(0, 10, 'Generated by pdfgen-prhu.onrender.com', align='C')

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
    if not url.startswith('http'):
        return '올바른 주소를 입력해 주세요. (https://로 시작)', 400
    try:
        title, blocks = fetch_page(url)
        if not blocks:
            return '본문을 가져오지 못했습니다. 공개된 페이지인지 확인해 주세요.', 400
        pdf_buf = create_pdf(title, blocks, url)
        return send_file(pdf_buf, mimetype='application/pdf',
                         as_attachment=True, download_name='page.pdf')
    except Exception as e:
        return f'오류: {str(e)}', 500

if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('PORT', 8080))
    serve(app, host='0.0.0.0', port=port)
