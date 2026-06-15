import os

base_dir = r"C:\Users\Parardha\Desktop\IIsc Intern\saas_app"

import base64

with open(os.path.join(base_dir, "src", "assets", "startup-bg.jpg"), "rb") as f:
    bg_b64_data = base64.b64encode(f.read()).decode('utf-8')
    bg_b64 = "data:image/jpeg;base64," + bg_b64_data

main_cjs_content = f"""const {{ app, BrowserWindow, ipcMain }} = require('electron');
const path = require('path');
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

let mainWindow;

function createSplashWindow() {{
  const splash = new BrowserWindow({{
    width: 800,
    height: 500,
    frame: false,
    alwaysOnTop: true,
    transparent: true,
    backgroundColor: '#00000000',
    webPreferences: {{ nodeIntegration: false }}
  }});

  const splashHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
      <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
          font-family: 'Inter', sans-serif;
          background: #000;
          border-radius: 16px;
          border: 1px solid rgba(255, 255, 255, 0.2);
          height: 100vh;
          color: white;
          overflow: hidden;
          position: relative;
          display: flex;
        }}

        /* ── Background Image ── */
        .bg-image {{
          position: absolute;
          inset: 0;
          background-image: url('{bg_b64}');
          background-size: cover;
          background-position: center;
          z-index: 0;
          filter: grayscale(100%) contrast(1.2) brightness(0.9);
        }}

        /* ── Glassmorphism Overlay ── */
        .glass-overlay {{
          position: absolute;
          inset: 0;
          background: linear-gradient(135deg, rgba(25, 25, 25, 0.4), rgba(0, 0, 0, 0.8));
          backdrop-filter: blur(10px);
          z-index: 1;
        }}

        /* ── Grid overlay ── */
        .grid-overlay {{
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
          background-size: 40px 40px;
          z-index: 2;
          pointer-events: none;
          mask-image: radial-gradient(ellipse at 50% 50%, black 40%, transparent 90%);
          -webkit-mask-image: radial-gradient(ellipse at 50% 50%, black 40%, transparent 90%);
        }}

        /* ── Content layer ── */
        .content-layer {{
          position: relative;
          z-index: 10;
          display: flex;
          width: 100%;
          height: 100%;
        }}

        .left-col {{
          flex: 1.1;
          padding: 48px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          border-right: 1px solid rgba(255, 255, 255, 0.1);
          position: relative;
        }}
        
        .right-col {{
          flex: 0.9;
          padding: 48px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          position: relative;
        }}

        /* ── Smooth Cut Animation for Heading ── */
        .heading-container {{
          overflow: hidden;
          margin-bottom: 12px;
        }}
        h1 {{
          font-size: 30px;
          font-weight: 700;
          line-height: 1.15;
          color: #fff;
          transform: translateY(100%);
          animation: cutIn 1.2s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }}
        @keyframes cutIn {{
          0% {{ transform: translateY(100%); }}
          100% {{ transform: translateY(0); }}
        }}

        .badge {{
          font-size: 9px;
          letter-spacing: 3px;
          color: #ccc;
          text-transform: uppercase;
          margin-bottom: 24px;
          border: 1px solid rgba(255, 255, 255, 0.2);
          padding: 6px 14px;
          border-radius: 50px;
          display: inline-block;
          width: fit-content;
          background: rgba(255, 255, 255, 0.05);
          animation: fadeIn 1s ease 0.5s forwards;
          opacity: 0;
        }}
        @keyframes fadeIn {{
          to {{ opacity: 1; }}
        }}

        .sub {{
          font-size: 13px;
          color: #888;
          margin-bottom: 36px;
          line-height: 1.6;
          animation: fadeIn 1s ease 0.8s forwards;
          opacity: 0;
        }}

        /* ── Progress bar ── */
        .bar-container {{
          width: 100%; height: 2px;
          background: rgba(255, 255, 255, 0.1);
          border-radius: 2px;
          overflow: hidden;
          margin-bottom: 12px;
          animation: fadeIn 1s ease 1s forwards;
          opacity: 0;
        }}
        .bar {{
          height: 100%; width: 25%;
          background: #fff;
          border-radius: 2px;
          animation: slide 2.5s cubic-bezier(0.4, 0, 0.2, 1) infinite;
          box-shadow: 0 0 8px rgba(255, 255, 255, 0.5);
        }}
        @keyframes slide {{
          0% {{ transform: translateX(-100%); }}
          100% {{ transform: translateX(500%); }}
        }}

        .status-row {{
          display: flex;
          justify-content: space-between;
          align-items: center;
          animation: fadeIn 1s ease 1s forwards;
          opacity: 0;
        }}
        .status {{
          font-size: 10px;
          color: #ccc;
          letter-spacing: 1.5px;
          text-transform: uppercase;
          animation: statusPulse 2s ease-in-out infinite;
        }}
        @keyframes statusPulse {{
          0%, 100% {{ opacity: 1; }}
          50% {{ opacity: 0.5; }}
        }}
        .credit {{
          font-size: 9px;
          color: rgba(255, 255, 255, 0.4);
          letter-spacing: 1.5px;
          text-transform: uppercase;
        }}

        /* ── Right column ── */
        .section-label {{
          font-size: 9px;
          color: rgba(255, 255, 255, 0.5);
          letter-spacing: 3px;
          text-transform: uppercase;
          margin-bottom: 24px;
          display: flex;
          align-items: center;
          gap: 10px;
          animation: fadeIn 1s ease 0.5s forwards;
          opacity: 0;
        }}
        .section-label::after {{
          content: '';
          flex: 1;
          height: 1px;
          background: linear-gradient(90deg, rgba(255, 255, 255, 0.2), transparent);
        }}

        .faq-item {{
          display: none;
          animation: fadeSlide 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }}
        .faq-item.active {{ display: block; }}
        @keyframes fadeSlide {{
          from {{ opacity: 0; transform: translateY(12px); }}
          to {{ opacity: 1; transform: translateY(0); }}
        }}

        .faq-icon {{
          width: 32px; height: 32px;
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.1);
          border: 1px solid rgba(255, 255, 255, 0.15);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
          margin-bottom: 14px;
        }}
        .faq-q {{
          font-size: 15px;
          font-weight: 600;
          color: #e0e0e0;
          margin-bottom: 8px;
        }}
        .faq-a {{
          font-size: 12px;
          color: #888;
          line-height: 1.7;
        }}

        /* ── Dot indicators ── */
        .dots {{
          display: flex;
          gap: 6px;
          margin-top: 24px;
          animation: fadeIn 1s ease 1s forwards;
          opacity: 0;
        }}
        .dot {{
          width: 6px; height: 6px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.15);
          transition: all 0.4s ease;
        }}
        .dot.active {{
          background: #ccc;
          box-shadow: 0 0 8px rgba(255, 255, 255, 0.5);
          width: 18px;
          border-radius: 3px;
        }}

        /* ── Author watermark ── */
        .watermark {{
          position: absolute;
          bottom: 16px;
          left: 50%;
          transform: translateX(-50%);
          font-size: 9px;
          color: rgba(255, 255, 255, 0.3);
          letter-spacing: 3px;
          text-transform: uppercase;
          z-index: 20;
          animation: fadeIn 2s ease 1s forwards;
          opacity: 0;
        }}
      </style>
    </head>
    <body>
      <div class="bg-image"></div>
      <div class="glass-overlay"></div>
      <div class="grid-overlay"></div>

      <div class="content-layer">
        <div class="left-col">
          <div class="badge">TEM AI Studio</div>
          <div class="heading-container">
            <h1>Intelligent<br>Crystallography</h1>
          </div>
          <div class="sub">Neural defect classification &amp; physics-aware Burgers vector extraction powered by SAM segmentation.</div>
          
          <div style="margin-top: auto;">
            <div class="bar-container"><div class="bar"></div></div>
            <div class="status-row">
              <div class="status" id="statusText">Initializing Neural Cores...</div>
            </div>
          </div>
        </div>

        <div class="right-col">
          <div class="section-label">System Intelligence</div>
          <div id="faqs">
            <div class="faq-item active">
              <div class="faq-icon">⚛</div>
              <div class="faq-q">Invisibility Criterion</div>
              <div class="faq-a">When g·b = 0, the dislocation loop strain field produces zero diffraction contrast — the defect becomes invisible to the electron beam.</div>
            </div>
            <div class="faq-item">
              <div class="faq-icon">🧠</div>
              <div class="faq-q">Neural Extraction Pipeline</div>
              <div class="faq-a">SAM identifies loop boundaries at sub-pixel precision while the physics engine solves the Weiss Zone Law to determine Burgers vectors.</div>
            </div>
            <div class="faq-item">
              <div class="faq-icon">💎</div>
              <div class="faq-q">Crystal System Support</div>
              <div class="faq-a">BCC materials use ½⟨111⟩ and ⟨100⟩ loop families. FCC systems use ⅓⟨111⟩ faulted and ½⟨110⟩ perfect loop geometries.</div>
            </div>
            <div class="faq-item">
              <div class="faq-icon">📊</div>
              <div class="faq-q">Morphology Classification</div>
              <div class="faq-a">Edge-on loops appear as sharp lines (B·n ≈ 0) while inclined loops show elliptical projections based on their habit plane orientation.</div>
            </div>
          </div>
          <div class="dots" id="dotIndicators">
            <div class="dot active"></div>
            <div class="dot"></div>
            <div class="dot"></div>
            <div class="dot"></div>
          </div>
        </div>
      </div>

      <div class="watermark">Completely Made by Parardha Dhar</div>

      <script>
        /* ── FAQ Carousel ── */
        const items = document.querySelectorAll('.faq-item');
        const dots = document.querySelectorAll('.dot');
        let idx = 0;
        setInterval(() => {{
          items[idx].classList.remove('active');
          dots[idx].classList.remove('active');
          idx = (idx + 1) % items.length;
          items[idx].classList.add('active');
          dots[idx].classList.add('active');
        }}, 4500);

        /* ── Cycling Status Messages ── */
        const statusEl = document.getElementById('statusText');
        const msgs = [
          'Initializing Neural Cores...',
          'Loading SAM ViT-H into VRAM...',
          'Calibrating Crystallography LUTs...',
          'Warming YOLO Detection Engine...',
          'Establishing Physics Pipeline...',
          'Preparing Workspace...'
        ];
        let mi = 0;
        setInterval(() => {{
          mi = (mi + 1) % msgs.length;
          statusEl.style.opacity = 0;
          setTimeout(() => {{ statusEl.textContent = msgs[mi]; statusEl.style.opacity = 1; }}, 400);
        }}, 3000);
      </script>
    </body>
    </html>
  `;
  splash.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(splashHtml));
  return splash;
}}

function createMainWindow() {{
  mainWindow = new BrowserWindow({{
    width: 1600,
    height: 1000,
    minWidth: 1200,
    minHeight: 800,
    autoHideMenuBar: true,
    backgroundColor: '#000000',
    show: false,
    webPreferences: {{
      nodeIntegration: true,
      contextIsolation: false
    }}
  }});

  if (isDev) {{
    mainWindow.loadURL('http://localhost:5173');
  }} else {{
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }}
}}

app.whenReady().then(() => {{
  const splash = createSplashWindow();
  createMainWindow();

  mainWindow.once('ready-to-show', () => {{
    setTimeout(() => {{
      splash.destroy();
      mainWindow.show();
    }}, 6000);
  }});

  app.on('activate', () => {{
    if (BrowserWindow.getAllWindows().length === 0) {{
      createMainWindow();
    }}
  }});
}});

app.on('window-all-closed', () => {{
  if (process.platform !== 'darwin') {{
    app.quit();
  }}
}});
"""

main_cjs_path = os.path.join(base_dir, "electron", "main.cjs")
with open(main_cjs_path, "w", encoding="utf-8") as f:
    f.write(main_cjs_content)

print("Recovered main.cjs successfully.")
