import os
import json
import pandas as pd
from pathlib import Path
import argparse

def build_dashboard():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale_100nm_pixels", type=float, default=142.0)
    args = parser.parse_args()
    
    print("==================================================")
    print("Building SaaS Interactive Dashboard")
    print("==================================================")

    # 1. Resolve Paths
    script_dir = Path(__file__).parent.resolve()
    base_dir = script_dir.parent
    
    output_dir = base_dir / "data" / "output"
    csv_path = output_dir / "crystallography_report.csv"
    
    if not csv_path.exists():
        print(f"Error: Could not find {csv_path}")
        return
        
    scale_multiplier = args.scale_100nm_pixels / 100.0

    # 2. Parse CSV
    print(" -> Parsing physics quantification data...")
    df = pd.read_csv(csv_path)
    
    image_data = {}
    
    for img_name in df['Image'].unique():
        img_df = df[df['Image'] == img_name]
        defects = []
        for _, row in img_df.iterrows():
            # Store all columns so we can export a lossless CSV later
            defects.append(row.to_dict())
            
        annotated_img_name = f"final_cryst_{img_name}"
        image_data[annotated_img_name] = defects

    # 3. Embed JSON into JS
    import json
    json_data = json.dumps(image_data)
    
    # 4. Generate HTML/JS/CSS (The SaaS Frontend)
    print(" -> Compiling Frontend Assets...")
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HR-STEM Crystallography | DeepMind AI Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0f19;
            --panel-bg: rgba(20, 25, 40, 0.6);
            --border-color: rgba(255, 255, 255, 0.1);
            --text-main: #f0f4f8;
            --text-muted: #8c9baf;
            --accent: #3b82f6;
            --accent-glow: rgba(59, 130, 246, 0.4);
            --danger: #ef4444;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            background-image: 
                radial-gradient(circle at 15% 50%, rgba(59, 130, 246, 0.15), transparent 25%),
                radial-gradient(circle at 85% 30%, rgba(139, 92, 246, 0.15), transparent 25%);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
        }}

        header {{
            padding: 20px 40px;
            background: rgba(11, 15, 25, 0.8);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: sticky;
            top: 0;
            z-index: 100;
        }}

        .brand {{
            font-weight: 800;
            font-size: 1.5rem;
            letter-spacing: 1px;
            background: linear-gradient(90deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .dashboard-container {{ display: flex; flex: 1; padding: 30px; gap: 30px; }}
        .sidebar {{
            width: 300px;
            background: var(--panel-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }}

        .sidebar h2 {{
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}

        .image-btn {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text-main);
            padding: 16px;
            border-radius: 12px;
            font-family: inherit;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            text-align: left;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .image-btn:hover {{ background: rgba(255, 255, 255, 0.1); transform: translateY(-2px); }}
        .image-btn.active {{
            background: var(--accent);
            border-color: var(--accent);
            box-shadow: 0 0 20px var(--accent-glow);
        }}
        
        .export-btn {{
            background: linear-gradient(135deg, #10b981, #059669);
            border: none;
            color: white;
            padding: 16px;
            border-radius: 12px;
            font-family: inherit;
            font-size: 1.1rem;
            font-weight: 800;
            cursor: pointer;
            text-align: center;
            transition: all 0.3s ease;
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.4);
            margin-top: auto;
        }}
        .export-btn:hover {{ transform: translateY(-3px); box-shadow: 0 0 25px rgba(16, 185, 129, 0.6); }}

        .stats-panel {{
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(255,255,255,0.05);
        }}
        .stat-row {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
        .stat-label {{ color: var(--text-muted); font-size: 0.9rem; }}
        .stat-value {{ font-weight: 800; font-size: 1.1rem; color: #fff; }}

        .main-view {{
            flex: 1;
            background: var(--panel-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 0;
            display: flex;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            position: relative;
            overflow: hidden;
        }}

        .viewport {{
            width: 100%;
            height: 100%;
            position: relative;
            cursor: grab;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .viewport:active {{ cursor: grabbing; }}
        .pan-container {{ position: relative; transform-origin: 0 0; }}
        .image-container {{ position: relative; display: block; }}
        .image-container img {{
            display: block;
            box-shadow: 0 0 40px rgba(0,0,0,0.5);
            -webkit-user-drag: none;
        }}

        .hover-zone {{
            position: absolute;
            transform: translate(-50%, -50%);
            border-radius: 50%;
            cursor: crosshair;
            z-index: 10;
            transition: border 0.2s ease, background 0.2s ease, transform 0.2s ease, opacity 0.3s ease;
        }}
        
        .hover-zone:hover {{
            border: 2px solid white;
            background: rgba(255, 255, 255, 0.3);
            box-shadow: 0 0 15px rgba(255, 255, 255, 0.8);
        }}
        
        /* Eraser mode styling */
        .hover-zone.erasing {{
            transform: translate(-50%, -50%) scale(0.1);
            opacity: 0;
        }}

        .glass-tooltip {{
            position: fixed;
            pointer-events: none;
            opacity: 0;
            background: rgba(15, 20, 35, 0.85);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: #fff;
            padding: 12px 20px;
            border-radius: 12px;
            font-size: 0.95rem;
            transform: translateY(10px);
            transition: opacity 0.2s ease, transform 0.2s ease;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            z-index: 1000;
            white-space: nowrap;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .glass-tooltip.visible {{ opacity: 1; transform: translateY(0); }}
        .glass-tooltip.delete-mode {{ border-color: var(--danger); background: rgba(50, 10, 10, 0.9); }}
        .tooltip-id {{ font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }}
        .tooltip-val {{ font-size: 1.2rem; font-weight: 800; color: #fbbf24; }}
        
        .zoom-controls {{
            position: absolute;
            bottom: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
            z-index: 50;
        }}
        .zoom-btn {{
            background: rgba(15, 20, 35, 0.8);
            border: 1px solid var(--border-color);
            color: white;
            width: 40px;
            height: 40px;
            border-radius: 8px;
            font-size: 1.2rem;
            cursor: pointer;
            backdrop-filter: blur(10px);
        }}
        .zoom-btn:hover {{ background: var(--accent); }}
        
        /* Disable context menu globally except for zones */
        body {{ -webkit-user-select: none; user-select: none; }}

    </style>
</head>
<body oncontextmenu="return false;">

    <header>
        <div class="brand">HR-STEM AI Analytics</div>
        <div style="color: var(--text-muted); font-size: 0.9rem;">Interactive Defect Metrology SaaS (V4 - Curated)</div>
    </header>

    <div class="dashboard-container">
        <!-- Sidebar -->
        <div class="sidebar">
            <h2>Datasets</h2>
            <div id="file-list"></div>
            
            <div class="stats-panel">
                <div class="stat-row">
                    <span class="stat-label">Active Image:</span>
                </div>
                <div class="stat-row" style="margin-bottom: 20px;">
                    <span class="stat-value" id="stat-image-name">-</span>
                </div>
                
                <div class="stat-row">
                    <span class="stat-label">Defects Remaining:</span>
                </div>
                <div class="stat-row">
                    <span class="stat-value" id="stat-defect-count">0</span>
                </div>
            </div>
            
            <div style="color: var(--text-muted); font-size: 0.85rem; margin-top: 10px; line-height: 1.5;">
                🖱️ <b>Scroll</b> to zoom.<br>
                ✋ <b>Click & Drag</b> to pan.<br>
                ❌ <b>Right-Click</b> a loop to Erase it.
            </div>
            
            <button class="export-btn" onclick="exportCleanedCSV()">📥 Export Cleaned CSV</button>
        </div>

        <!-- Main View -->
        <div class="main-view">
            <div class="viewport" id="viewport">
                <div class="pan-container" id="pan-container">
                    <div class="image-container" id="img-container">
                        <img id="main-image" src="" alt="Select an image to begin">
                        <div id="hover-layer"></div>
                    </div>
                </div>
            </div>
            
            <div class="zoom-controls">
                <button class="zoom-btn" onclick="zoomIn()">+</button>
                <button class="zoom-btn" onclick="zoomOut()">-</button>
                <button class="zoom-btn" onclick="resetZoom()">⟲</button>
            </div>
        </div>
    </div>

    <!-- Floating Tooltip -->
    <div class="glass-tooltip" id="tooltip">
        <span class="tooltip-id" id="tt-id">Loop_0000</span>
        <span class="tooltip-val" id="tt-val">0.0 nm</span>
        <span style="font-size: 0.7rem; color: #ef4444; margin-top: 4px; display: none;" id="tt-del-msg">Right-Click to Erase</span>
    </div>

    <script src="https://unpkg.com/@panzoom/panzoom@4.5.1/dist/panzoom.min.js"></script>
    <script>
        // Deep copy JSON so we can mutate it freely
        const defectData = JSON.parse('{json_data}');
        
        const fileList = document.getElementById('file-list');
        const mainImage = document.getElementById('main-image');
        const hoverLayer = document.getElementById('hover-layer');
        const statImageName = document.getElementById('stat-image-name');
        const statDefectCount = document.getElementById('stat-defect-count');
        const tooltip = document.getElementById('tooltip');
        const ttId = document.getElementById('tt-id');
        const ttVal = document.getElementById('tt-val');
        const ttDelMsg = document.getElementById('tt-del-msg');
        
        const viewport = document.getElementById('viewport');
        const panContainer = document.getElementById('pan-container');
        
        let currentImageKey = null;
        
        // Pan/Zoom State
        let scale = 1;
        let panning = false;
        let pointX = 0; let pointY = 0;
        let startX = 0; let startY = 0;

        function init() {{
            const keys = Object.keys(defectData);
            if (keys.length === 0) return;
            
            keys.forEach(key => {{
                const btn = document.createElement('button');
                btn.className = 'image-btn';
                btn.innerText = key;
                btn.onclick = () => loadImage(key);
                fileList.appendChild(btn);
            }});
            
            setupPanZoom();
            loadImage(keys[0]);
        }}

        function loadImage(key) {{
            currentImageKey = key;
            Array.from(fileList.children).forEach(btn => {{
                if (btn.innerText === key) btn.classList.add('active');
                else btn.classList.remove('active');
            }});
            
            statImageName.innerText = key;
            updateCounter();
            
            mainImage.src = key; 
            hoverLayer.innerHTML = '';
            
            mainImage.onload = () => {{
                resetZoom();
                drawHoverZones(key);
            }};
        }}
        
        function updateCounter() {{
            if (currentImageKey) {{
                statDefectCount.innerText = defectData[currentImageKey].length;
            }}
        }}

        function drawHoverZones(key) {{
            const defects = defectData[key];
            const naturalW = mainImage.naturalWidth;
            const naturalH = mainImage.naturalHeight;
            if (!naturalW || !naturalH) return;

            defects.forEach((defect, index) => {{
                const xPercent = (defect.X_Coord / naturalW) * 100;
                const yPercent = (defect.Y_Coord / naturalH) * 100;
                
                // Dynamic scaling based on user calibration parameter
                const pxDiameter = defect.Diameter_nm * {scale_multiplier};
                const widthPercent = (pxDiameter / naturalW) * 100;
                
                const zone = document.createElement('div');
                zone.className = 'hover-zone';
                zone.style.left = `${{xPercent}}%`;
                zone.style.top = `${{yPercent}}%`;
                zone.style.width = `${{widthPercent}}%`;
                zone.style.paddingBottom = `${{widthPercent}}%`;
                
                zone.addEventListener('mouseenter', (e) => showTooltip(e, defect));
                zone.addEventListener('mouseleave', hideTooltip);
                zone.addEventListener('mousemove', moveTooltip);
                
                // ERASER TOOL (Right-Click)
                zone.addEventListener('contextmenu', (e) => {{
                    e.preventDefault(); // Prevent standard menu
                    eraseDefect(key, defect.Defect_ID, zone);
                }});
                
                hoverLayer.appendChild(zone);
            }});
        }}
        
        function eraseDefect(imageKey, defectId, domElement) {{
            // 1. Visually erase
            domElement.classList.add('erasing');
            setTimeout(() => domElement.remove(), 300);
            hideTooltip();
            
            // 2. Remove from data structure
            const defects = defectData[imageKey];
            const idx = defects.findIndex(d => d.Defect_ID === defectId);
            if (idx > -1) {{
                defects.splice(idx, 1);
            }}
            
            // 3. Update UI
            updateCounter();
        }}

        // --- PAN AND ZOOM LOGIC (Powered by Panzoom.js) ---
        let panzoomInstance = null;

        function setupPanZoom() {{
            if (panzoomInstance) {{
                panzoomInstance.destroy();
            }}
            
            panzoomInstance = Panzoom(panContainer, {{
                maxScale: 20,
                minScale: 0.1,
                cursor: 'grab'
            }});
            
            // Allow wheel zoom
            viewport.parentElement.addEventListener('wheel', panzoomInstance.zoomWithWheel);
            
            // Make grab cursor active during pan
            panContainer.addEventListener('panzoomstart', () => {{
                panContainer.style.cursor = 'grabbing';
            }});
            panContainer.addEventListener('panzoomend', () => {{
                panContainer.style.cursor = 'grab';
            }});
        }}

        function zoomIn() {{ if (panzoomInstance) panzoomInstance.zoomIn(); }}
        function zoomOut() {{ if (panzoomInstance) panzoomInstance.zoomOut(); }}
        function resetZoom() {{
            if (!panzoomInstance) return;
            const vW = viewport.clientWidth; const vH = viewport.clientHeight;
            const iW = mainImage.naturalWidth; const iH = mainImage.naturalHeight;
            let initialScale = 1;
            if (iW && iH) {{ initialScale = Math.min(vW / iW, vH / iH) * 0.9; }}
            
            panzoomInstance.zoom(initialScale);
            // Center the image
            setTimeout(() => panzoomInstance.pan(0, 0), 10);
        }}

        // --- TOOLTIP LOGIC ---
        function showTooltip(e, defect) {{
            ttId.innerText = defect.Defect_ID;
            ttVal.innerText = defect.Diameter_nm.toFixed(1) + ' nm';
            ttDelMsg.style.display = 'block';
            tooltip.classList.add('delete-mode');
            tooltip.classList.add('visible');
            moveTooltip(e);
        }}
        function hideTooltip() {{ tooltip.classList.remove('visible'); }}
        function moveTooltip(e) {{
            const offset = 15;
            tooltip.style.left = (e.clientX + offset) + 'px';
            tooltip.style.top = (e.clientY + offset) + 'px';
        }}
        
        // --- CSV EXPORT LOGIC ---
        function exportCleanedCSV() {{
            // Flatten all current data back into a single array
            let allDefects = [];
            Object.keys(defectData).forEach(key => {{
                allDefects = allDefects.concat(defectData[key]);
            }});
            
            if (allDefects.length === 0) {{
                alert("No defects left to export!");
                return;
            }}
            
            // Get all unique columns
            const headers = Object.keys(allDefects[0]);
            
            // Build CSV string
            let csvContent = headers.join(",") + "\\n";
            allDefects.forEach(row => {{
                const rowString = headers.map(header => {{
                    let val = row[header];
                    // Handle strings with commas
                    if (typeof val === 'string' && val.includes(',')) {{
                        val = `"${{val}}"`;
                    }}
                    return val;
                }}).join(",");
                csvContent += rowString + "\\n";
            }});
            
            // Trigger download
            const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.setAttribute("href", url);
            link.setAttribute("download", "cleaned_crystallography_report.csv");
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }}

        init();
    </script>
</body>
</html>
"""
    
    out_html_path = output_dir / "index.html"
    with open(out_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f" -> SaaS Dashboard Successfully Generated at: {out_html_path}")

if __name__ == "__main__":
    build_dashboard()
