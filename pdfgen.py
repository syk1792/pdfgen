from flask import Flask, request, send_file, render_template_string
import requests
from bs4 import BeautifulSoup
from fpdf import FPDF
import io, os, tempfile, re

app = Flask(__name__)

FONT_PATH = 'NanumGothic.ttf'
FONT_BOLD_PATH = 'NanumGothicBold.ttf'
FONT_URL = 'https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf'
FONT_BOLD_URL = 'https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothicBold.ttf'

def ensure_font():
    if not os.path.exists(FONT_PATH):
        print("폰트 다운로드 중...")
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
  button { width: 100%; margin-top: 14px; padding: 13px; background: #1a1612; color: #fff; border: none; border-radius: 8px; font-size: 15px; font-weight: 700; cursor: pointer; }
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
  <p class="sub">네이버 블로그 주소를 입력하면 본문 텍스트와 이미지를 포함한 PDF로 다운로드합니다.</p>
  <form id="form">
    <label>블로그 주소</label>
    <input type="text" id="url" placeholder="https://blog.naver.com/..." />
    <button type="submit">PDF로 변환하기</button>
  </form>
  <div class="loading" id="loading">⏳ 변환 중입니다... 이미지가 많으면 시간이 걸릴 수 있어요.</div>
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
    mobile_url = url.replace('blog.naver.com', 'm.blog.naver.com')
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
        'Accept-Language': 'ko-KR,ko;q=0.9'
    }
    res = requests.get(mobile_url, headers=headers, timeout=15)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')

    # 제목 추출
    title = ''
    for sel in ['.se-title-text', '.tit_h3', 'h3.tit_view', '.pcol1']:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(strip=True)
            break
    if not title:
        t = soup.find('title')
        if t:
            title = t.get_text(strip=True)

    # 본문 컨테이너 찾기
    container = None
    for sel in ['.se-main-container', '.post-view', '#postViewArea', '.se_component_wrap']:
        container = soup.select_one(sel)
        if container:
            break

    # 구조화된 블록 추출 (텍스트 + 이미지)
    blocks = []
    if container:
        for el in container.descendants:
            if el.name in ['h2', 'h3', 'h4']:
                text = el.get_text(strip=True)
                if text:
                    blocks.append({'type': 'heading', 'text': text})
            elif el.name == 'p' or (el.name and 'paragraph' in el.get('class', [''])[0] if el.get('class') else False):
                text = el.get_text(strip=True)
                if text and len(text) > 1:
                    blocks.append({'type': 'body', 'text': text})
            elif el.name == 'img':
                src = el.get('src', '') or el.get('data-src', '')
                if src and ('postfiles' in src or 'blogfiles' in src or 'mblogthumb' in src):
                    blocks.append({'type': 'image', 'src': src})
    else:
        # 폴백: 전체 텍스트
        text = soup.get_text(separator='\n', strip=True)
        for line in text.split('\n'):
            if line.strip():
                blocks.append({'type': 'body', 'text': line.strip()})

    # 중복 제거
    seen = set()
    unique_blocks = []
    for b in blocks:
        key = b.get('text', b.get('src', ''))
        if key not in seen:
            seen.add(key)
            unique_blocks.append(b)

    return title, unique_blocks

def download_image(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200 and 'image' in r.headers.get('Content-Type', ''):
            suffix = '.jpg'
            if 'png' in r.headers.get('Content-Type', ''):
                suffix = '.png'
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp.write(r.content)
            tmp.close()
            return tmp.name
    except:
        pass
    return None

def create_pdf(title, blocks, source_url):
    ensure_font()

    pdf = FPDF()
    pdf.add_page()
    pdf.add_font('Nanum', '', FONT_PATH)
    pdf.add_font('NanumB', '', FONT_BOLD_PATH)

    # 헤더 배경
    pdf.set_fill_color(26, 22, 18)
    pdf.rect(0, 0, 210, 38, 'F')

    # 제목
    pdf.set_font('NanumB', size=17)
    pdf.set_text_color(240, 236, 228)
    pdf.set_xy(10, 7)
    pdf.multi_cell(190, 8, title[:50] if title else '네이버 블로그')

    # URL
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

        elif block['type'] == 'image':
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

    # 임시 이미지 파일 정리
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
    if not url:
        return '주소를 입력해 주세요.', 400
    if 'blog.naver.com' not in url:
        return '네이버 블로그 주소만 지원합니다.', 400
    try:
        title, blocks = fetch_naver_blog(url)
        if not blocks:
            return '블로그 내용을 가져오지 못했습니다. 공개된 글인지 확인해 주세요.', 400
        pdf_buf = create_pdf(title, blocks, url)
        return send_file(pdf_buf, mimetype='application/pdf',
                         as_attachment=True, download_name='naver_blog.pdf')
    except Exception as e:
        return f'오류: {str(e)}', 500

if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('PORT', 8080))
    serve(app, host='0.0.0.0', port=port)
