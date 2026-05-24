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
  .card { background: #fff; border-radius: 12px; padding: 40px 36px; max-width: 520px; width: 100%; box-shadow: 0 4px 24px rgba(0,0,0,0.08); }
  .tag { display: inline-block; font-size: 10px; padding: 2px 8px; border-radius: 20px; background: #f0ece4; color: #8a7a60; margin-bottom: 16px; letter-spacing: 0.05em; }
  h1 { font-size: 20px; font-weight: 700; color: #1a1612; margin-bottom: 8px; }
  .sub { font-size: 13px; color: #9a9080; margin-bottom: 24px; line-height: 1.7; }
  label { font-size: 13px; font-weight: 500; color: #3a3530; display: block; margin-bottom: 6px; }
  .label-sub { font-size: 11px; color: #b0a898; font-weight: 400; margin-left: 6px; }
  textarea { width: 100%; padding: 12px 14px; border: 1px solid #e0d8cc; border-radius: 8px; font-size: 13px; color: #1a1612; outline: none; transition: border 0.2s; margin-bottom: 6px; resize: vertical; min-height: 120px; line-height: 1.8; font-family: inherit; }
  textarea:focus { border-color: #c8a850; }
  textarea::placeholder { color: #c8c0b4; }
  .count { font-size: 11px; color: #b0a898; margin-bottom: 16px; text-align: right; }
  .count.over { color: #e85a5a; }
  button { width: 100%; padding: 14px; background: #1a1612; color: #fff; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; transition: background 0.2s; }
  button:hover { background: #3a3530; }
  button:disabled { background: #9a9080; cursor: not-allowed; }
  .msg { margin-top: 18px; padding: 14px; border-radius: 8px; font-size: 13px; line-height: 1.6; display: none; }
  .msg.success { background: #edfaed; color: #2a7a2a; border: 1px solid #b8e8b8; }
  .msg.error { background: #faeaea; color: #8a2020; border: 1px solid #e8b8b8; }
  .loading { display: none; text-align: center; margin-top: 16px; font-size: 13px; color: #9a9080; line-height: 1.9; }
  .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid #e0d8cc; border-top-color: #1a1612; border-radius: 50%; animation: spin 0.8s linear infinite; margin-right: 8px; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .tips { background: #f9f7f2; border-radius: 8px; padding: 14px 16px; margin-bottom: 20px; }
  .tips-title { font-size: 11px; font-weight: 700; color: #8a7a60; margin-bottom: 8px; letter-spacing: 0.05em; }
  .tips li { font-size: 12px; color: #9a8a70; line-height: 1.8; list-style: none; padding-left: 12px; position: relative; }
  .tips li::before { content: '·'; position: absolute; left: 0; }
</style>
</head>
<body>
<div class="card">
  <span class="tag">TEXT · PDF · AI READY</span>
  <h1>📄 웹페이지 PDF 변환기</h1>
  <p class="sub">네이버 블로그, 티스토리, 브런치, 뉴스 기사 등<br>여러 페이지를 한 번에 하나의 PDF로 변환합니다.</p>

  <div class="tips">
    <div class="tips-title">💡 이렇게 쓰세요</div>
    <ul>
      <li>주소를 한 줄에 하나씩 입력하면 하나의 PDF로 합쳐집니다</li>
      <li>최대 5개까지 한 번에 변환 가능합니다</li>
      <li>NotebookLM, Gemini에 바로 업로드하세요</li>
    </ul>
  </div>

  <label>웹페이지 주소 <span class="label-sub">한 줄에 하나씩 (최대 5개)</span></label>
  <textarea id="urls" placeholder="https://blog.naver.com/...&#10;https://blog.naver.com/...&#10;https://tistory.com/..."></textarea>
  <div class="count" id="count">0 / 5개 입력됨</div>
  <button id="btn" onclick="doConvert()">PDF로 변환하기</button>

  <div class="loading" id="loading">
    <div><span class="spinner"></span>변환 중입니다...</div>
    <div style="margin-top:6px;font-size:12px;">처음 실행 시 서버 준비에 최대 1분이 걸릴 수 있어요.</div>
  </div>
  <div class="msg" id="msg"></div>
</div>

<script>
var urlTextarea = document.getElementById('urls');
var countEl = document.getElementById('count');
var btn = document.getElementById('btn');

urlTextarea.addEventListener('input', updateCount);
urlTextarea.addEventListener('change', updateCount);
urlTextarea.addEventListener('keyup', updateCount);

function updateCount() {
  var lines = urlTextarea.value.split('\\n').filter(function(l) {
    return l.trim().length > 0;
  });
  var n = lines.length;
  countEl.textContent = n + ' / 5개 입력됨';
  if (n > 5) {
    countEl.className = 'count over';
  } else {
    countEl.className = 'count';
  }
}

function doConvert() {
  var raw = urlTextarea.value.trim();
  var urls = raw.split('\\n').map(function(l) { return l.trim(); }).filter(function(l) { return l.length > 0; });

  if (urls.length === 0) {
    showMsg('error', '❌ 주소를 한 줄에 하나씩 입력해 주세요.');
    return;
  }
  if (urls.length > 5) {
    showMsg('error', '❌ 최대 5개까지 입력 가능합니다.');
    return;
  }

  btn.disabled = true;
  document.getElementById('loading').style.display = 'block';
  document.getElementById('msg').style.display = 'none';

  var xhr = new XMLHttpRequest();
  xhr.open('POST', '/convert', true);
  xhr.responseType = 'blob';
  xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
  xhr.timeout = 120000; // 2분

  xhr.onload = function() {
    btn.disabled = false;
    document.getElementById('loading').style.display = 'none';
    if (xhr.status === 200) {
      var blob = xhr.response;
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'pages.pdf';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      showMsg('success', '✅ PDF 다운로드가 시작됩니다!');
    } else {
      var reader = new FileReader();
      reader.onload = function() {
        showMsg('error', '❌ ' + reader.result);
      };
      reader.readAsText(xhr.response);
    }
  };

  xhr.onerror = function() {
    btn.disabled = false;
    document.getElementById('loading').style.display = 'none';
    showMsg('error', '❌ 네트워크 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.');
  };

  xhr.ontimeout = function() {
    btn.disabled = false;
    document.getElementById('loading').style.display = 'none';
    showMsg('error', '❌ 시간이 초과됐습니다. 잠시 후 다시 시도해 주세요.');
  };

  xhr.send('urls=' + encodeURIComponent(urls.join('\\n')));
}

function showMsg(type, text) {
  var el = document.getElementById('msg');
  el.className = 'msg ' + type;
  el.textContent = text;
  el.style.display = 'block';
}
</script>
</body>
</html>
"""

NOISE_PATTERNS = [
    r'^공감\s*\d*$', r'^댓글\s*\d*$', r'^구독\s*\d*$',
    r'^이웃추가$', r'^카카오스토리$', r'^트위터$', r'^페이스북$',
    r'^URL 복사$', r'^통계$', r'^신고$', r'^목록보기$',
    r'^\d+$', r'^[ㄱ-ㅎ가-힣]{1,2}$',
    r'로그인', r'회원가입', r'본문 바로가기',
    r'^Copyright', r'^All rights reserved',
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
    res = requests.get(url, headers=headers, timeout=20)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')

    for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
        tag.decompose()

    title = ''
    for sel in ['.se-title-text', 'h1', '.tit_h3', '.pcol1', 'title']:
        el = soup.select_one(sel)
        if el:
            t = el.get_text(strip=True)
            if t and len(t) > 2:
                title = t
                break

    container = None
    for sel in ['.se-main-container', 'article', '.post-content', '.entry-content',
                '.article-body', '.tt_article_useless_p_margin', '#postViewArea', 'main', '#content', '.content']:
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
            elif el.name == 'li':
                text = el.get_text(strip=True)
                if text and len(text) > 2 and not is_noise(text):
                    blocks.append({'type': 'list', 'text': '• ' + text})
    else:
        for line in soup.get_text(separator='\n').split('\n'):
            line = line.strip()
            if line and len(line) > 5 and not is_noise(line):
                blocks.append({'type': 'body', 'text': line})

    seen = set()
    unique = []
    for b in blocks:
        key = b['text']
        if key not in seen:
            seen.add(key)
            unique.append(b)

    return title, unique

def add_article_to_pdf(pdf, title, blocks, source_url):
    pdf.add_page()

    # 헤더 배경
    pdf.set_fill_color(26, 22, 18)
    pdf.rect(0, 0, 210, 42, 'F')

    # 글 제목
    pdf.set_font('Nanum', size=16)
    pdf.set_text_color(240, 236, 228)
    pdf.set_xy(12, 8)
    pdf.multi_cell(186, 9, title[:55] if title else '웹페이지')

    # 출처 URL
    pdf.set_font('Nanum', size=8)
    pdf.set_text_color(100, 90, 76)
    pdf.set_xy(12, 30)
    pdf.cell(0, 6, source_url[:90], ln=True)

    # 황금 구분선
    pdf.set_draw_color(200, 168, 80)
    pdf.set_line_width(0.5)
    pdf.line(12, 42, 198, 42)
    pdf.set_xy(12, 50)

    for block in blocks:
        if pdf.get_y() > 272:
            pdf.add_page()
            pdf.set_xy(12, 15)

        if block['type'] == 'heading':
            pdf.ln(6)
            pdf.set_x(12)
            pdf.set_font('Nanum', size=13)
            pdf.set_text_color(26, 22, 18)
            pdf.multi_cell(186, 8, block['text'])
            pdf.set_draw_color(220, 210, 190)
            pdf.set_line_width(0.3)
            pdf.line(12, pdf.get_y(), 198, pdf.get_y())
            pdf.ln(4)

        elif block['type'] == 'body':
            pdf.set_x(12)
            pdf.set_font('Nanum', size=10)
            pdf.set_text_color(50, 45, 38)
            pdf.multi_cell(186, 7, block['text'])
            pdf.ln(4)

        elif block['type'] == 'list':
            pdf.set_x(16)
            pdf.set_font('Nanum', size=10)
            pdf.set_text_color(60, 55, 46)
            pdf.multi_cell(182, 7, block['text'])
            pdf.ln(2)

def create_pdf(articles):
    ensure_font()
    pdf = FPDF()
    pdf.set_margins(0, 0, 0)
    pdf.add_font('Nanum', '', FONT_PATH)

    total = len(articles)
    for i, (title, blocks, url) in enumerate(articles):
        add_article_to_pdf(pdf, title, blocks, url)
        # 페이지 번호
        pdf.set_y(-12)
        pdf.set_font('Nanum', size=8)
        pdf.set_text_color(180, 170, 155)
        pdf.cell(0, 10, f'{i+1} / {total}  ·  pdfgen-prhu.onrender.com', align='C')

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/convert', methods=['POST'])
def convert():
    raw = request.form.get('urls', '').strip()
    urls = [u.strip() for u in raw.split('\n') if u.strip()]

    if not urls:
        return '주소를 입력해 주세요.', 400
    if len(urls) > 5:
        return '최대 5개까지 입력 가능합니다.', 400

    articles = []
    for url in urls:
        try:
            title, blocks = fetch_page(url)
            if blocks:
                articles.append((title, blocks, url))
        except Exception:
            pass

    if not articles:
        return '페이지 내용을 가져오지 못했습니다. 공개된 페이지인지 확인해 주세요.', 400

    try:
        pdf_buf = create_pdf(articles)
        return send_file(pdf_buf, mimetype='application/pdf',
                         as_attachment=True, download_name='pages.pdf')
    except Exception as e:
        return f'오류: {str(e)}', 500

if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('PORT', 8080))
    serve(app, host='0.0.0.0', port=port)
