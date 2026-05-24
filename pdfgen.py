from flask import Flask, request, send_file, render_template_string
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import io, os, tempfile

app = Flask(__name__)

FONT_PATH = 'NanumGothic.ttf'
FONT_BOLD_PATH = 'NanumGothicBold.ttf'
FONT_URL = 'https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf'
FONT_BOLD_URL = 'https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothicBold.ttf'

def ensure_font():
    if not os.path.exists(FONT_PATH):
        r = requests.get(FONT_URL, timeout=30)
        with open(FONT_PATH, 'wb') as f:
            f.write(r.content)
    if not os.path.exists(FONT_BOLD_PATH):
        r = requests.get(FONT_BOLD_URL, timeout=30)
        with open(FONT_BOLD_PATH, 'wb') as f:
            f.write(r.content)

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
  .sub { font-size: 13px; color: #9a9080; margin-bottom: 28px; line-height: 1.6; }
  label { font-size: 13px; font-weight: 500; color: #3a3530; display: block; margin-bottom: 6px; }
  input[type=text] { width: 100%; padding: 12px 14px; border: 1px solid #e0d8cc; border-radius: 8px; font-size: 14px; color: #1a1612; outline: none; transition: border 0.2s; margin-bottom: 20px; }
  input[type=text]:focus { border-color: #c8a850; }

  .mode-group { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
  .mode-card { border: 2px solid #e0d8cc; border-radius: 10px; padding: 16px 14px; cursor: pointer; transition: all 0.2s; position: relative; }
  .mode-card:hover { border-color: #c8a850; background: #fdf9f0; }
  .mode-card.selected { border-color: #1a1612; background: #f7f4ef; }
  .mode-card input[type=radio] { position: absolute; opacity: 0; }
  .mode-icon { font-size: 24px; margin-bottom: 8px; }
  .mode-title { font-size: 13px; font-weight: 700; color: #1a1612; margin-bottom: 4px; }
  .mode-desc { font-size: 11px; color: #9a9080; line-height: 1.5; }
  .mode-badge { display: inline-block; font-size: 10px; padding: 2px 7px; border-radius: 20px; margin-top: 6px; font-weight: 600; }
  .badge-fast { background: #edfaed; color: #2a7a2a; }
  .badge-slow { background: #fff4e0; color: #8a5a00; }

  button { width: 100%; padding: 13px; background: #1a1612; color: #fff; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; transition: background 0.2s; }
  button:hover { background: #333; }
  .msg { margin-top: 18px; padding: 14px; border-radius: 8px; font-size: 13px; line-height: 1.6; display: none; }
  .msg.success { background: #edfaed; color: #2a7a2a; border: 1px solid #b8e8b8; }
  .msg.error { background: #faeaea; color: #8a2020; border: 1px solid #e8b8b8; }
  .loading { display: none; text-align: center; margin-top: 14px; font-size: 13px; color: #9a9080; line-height: 1.7; }
</style>
</head>
<body>
<div class="card">
  <h1>📄 웹페이지 PDF 변환기</h1>
  <p class="sub">네이버 블로그, 티스토리, 브런치, 일반 웹페이지 모두 지원합니다.<br>NotebookLM, Gemini AI 학습에 바로 활용하세요.</p>

  <form id="form">
    <label>웹페이지 주소</label>
    <input type="text" id="url" placeholder="https://..." />

    <label>변환 방식 선택</label>
    <div class="mode-group">
      <div class="mode-card selected" id="card-text" onclick="selectMode('text')">
        <input type="radio" name="mode" value="text" checked />
        <div class="mode-icon">📝</div>
        <div class="mode-title">텍스트만</div>
        <div class="mode-desc">본문 글자만 추출합니다</div>
        <span class="mode-badge badge-fast">⚡ 빠름 5~10초</span>
      </div>
      <div class="mode-card" id="card-full" onclick="selectMode('full')">
        <input type="radio" name="mode" value="full" />
        <div class="mode-icon">🖼️</div>
        <div class="mode-title">텍스트 + 이미지</div>
        <div class="mode-desc">글자와 사진을 함께 저장합니다</div>
        <span class="mode-badge badge-slow">🐢 느림 30초~1분</span>
      </div>
    </div>

    <button type="submit">PDF로 변환하기</button>
  </form>

  <div class="loading" id="loading">
    ⏳ 변환 중입니다...<br>
    <span id="loading-sub">잠시만 기다려 주세요.</span>
  </div>
  <div class="msg" id="msg"></div>
</div>

<script>
function selectMode(mode) {
  document.getElementById('card-text').classList.toggle('selected', mode === 'text');
  document.getElementById('card-full').classList.toggle('selected', mode === 'full');
  document.querySelector('input[value="' + mode + '"]').checked = true;
}

document.getElementById('form').addEventListener('submit', async function(e) {
  e.preventDefault();
  const url = document.getElementById('url').value.trim();
  if (!url) return;
  const mode = document.querySelector('input[name="mode"]:checked').value;

  document.getElementById('loading').style.display = 'block';
  document.getElementById('loading-sub').textContent = mode === 'full'
    ? '이미지를 다운로드 중입니다. 1분 정도 걸릴 수 있어요.'
    : '잠시만 기다려 주세요.';
  document.getElementById('msg').style.display = 'none';

  try {
    const res = await fetch('/convert', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'url=' + encodeURIComponent(url) + '&mode=' + mode
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

def fetch_page(url):
    # 네이버 블로그는 모바일로 변환
    if 'blog.naver.com' in url:
        url = url.replace('blog.naver.com', 'm.blog.naver.com')

    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
        'Accept-Language': 'ko-KR,ko;q=0.9'
    }
    res = requests.get(url, headers=headers, timeout=15)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')

    # 제목 추출
    title = ''
    for sel in ['.se-title-text', 'h1', 'h2', '.tit_h3', '.pcol1', 'title']:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(strip=True)
            break

    # 본문 컨테이너 찾기 (다양한 사이트 대응)
    container = None
    for sel in [
        '.se-main-container',   # 네이버 블로그
        'article',              # 일반 뉴스/블로그
        '.post-content',        # 티스토리
        '.entry-content',       # 워드프레스/블로그스팟
        '.article-body',        # 뉴스
        'main',                 # 일반 사이트
        '#content',
        '.content',
        '#postViewArea',
    ]:
        container = soup.select_one(sel)
        if container:
            break

    blocks = []
    if container:
        for el in container.descendants:
            if not hasattr(el, 'name') or not el.name:
                continue
            if el.name in ['h1', 'h2', 'h3', 'h4']:
                text = el.get_text(strip=True)
                if text:
                    blocks.append({'type': 'heading', 'text': text})
            elif el.name == 'p':
                text = el.get_text(strip=True)
                if text and len(text) > 1:
                    blocks.append({'type': 'body', 'text': text})
            elif el.name == 'img':
                src = el.get('src', '') or el.get('data-src', '')
                if src and src.startswith('http'):
                    blocks.append({'type': 'image', 'src': src})
    else:
        text = soup.get_text(separator='\n', strip=True)
        for line in text.split('\n'):
            if line.strip() and len(line.strip()) > 1:
                blocks.append({'type': 'body', 'text': line.strip()})

    # 중복 제거
    seen = set()
    unique = []
    for b in blocks:
        key = b.get('text', b.get('src', ''))
        if key not in seen:
            seen.add(key)
            unique.append(b)

    return title, unique

def download_image(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        ct = r.headers.get('Content-Type', '')
        if r.status_code == 200 and 'image' in ct:
            suffix = '.png' if 'png' in ct else '.jpg'
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(r.content)
            tmp.close()
            return tmp.name
    except:
        pass
    return None

def create_pdf(title, blocks, source_url, include_images=False):
    ensure_font()

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Nanum', '', FONT_PATH)
    pdf.add_font('NanumB', '', FONT_BOLD_PATH)

    # 헤더
    pdf.set_fill_color(26, 22, 18)
    pdf.rect(0, 0, 210, 38, 'F')
    pdf.set_font('NanumB', size=16)
    pdf.set_text_color(240, 236, 228)
    pdf.set_xy(10, 7)
    pdf.multi_cell(190, 8, title[:50] if title else '웹페이지')
    pdf.set_font('Nanum', size=8)
    pdf.set_text_color(120, 110, 96)
    pdf.set_xy(10, 28)
    pdf.cell(0, 6, source_url[:90], ln=True)
    pdf.set_xy(12, 46)

    tmp_images = []

    for block in blocks:
        if pdf.get_y() > 272:
            pdf.add_page()
            pdf.set_xy(12, 15)

        if block['type'] == 'heading':
            pdf.ln(4)
            pdf.set_x(12)
            pdf.set_font('NanumB', size=14)
            pdf.set_text_color(26, 22, 18)
            pdf.multi_cell(186, 8, block['text'])
            pdf.ln(2)

        elif block['type'] == 'body':
            pdf.set_x(12)
            pdf.set_font('Nanum', size=10)
            pdf.set_text_color(50, 45, 38)
            pdf.multi_cell(186, 6, block['text'])
            pdf.ln(1)

        elif block['type'] == 'image' and include_images:
            img_path = download_image(block['src'])
            if img_path:
                tmp_images.append(img_path)
                try:
                    if pdf.get_y() > 220:
                        pdf.add_page()
                        pdf.set_xy(12, 15)
                    pdf.ln(3)
                    pdf.image(img_path, x=12, w=120)
                    pdf.ln(4)
                except:
                    pass

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)

    for p in tmp_images:
        try:
            os.unlink(p)
        except:
            pass

    return buf

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/convert', methods=['POST'])
def convert():
    url = request.form.get('url', '').strip()
    mode = request.form.get('mode', 'text')
    include_images = (mode == 'full')

    if not url:
        return '주소를 입력해 주세요.', 400
    if not url.startswith('http'):
        return '올바른 주소를 입력해 주세요. (http:// 또는 https://로 시작)', 400
    try:
        title, blocks = fetch_page(url)
        if not blocks:
            return '페이지 내용을 가져오지 못했습니다. 공개된 페이지인지 확인해 주세요.', 400
        pdf_buf = create_pdf(title, blocks, url, include_images=include_images)
        return send_file(pdf_buf, mimetype='application/pdf',
                         as_attachment=True, download_name='page.pdf')
    except Exception as e:
        return f'오류: {str(e)}', 500

if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('PORT', 8080))
    serve(app, host='0.0.0.0', port=port)
