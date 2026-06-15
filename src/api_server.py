import os
import cv2
import torch
import numpy as np
import base64
from fastapi import FastAPI, UploadFile, Form, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
import uvicorn
from pathlib import Path
from openai import OpenAI
import json
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import logging

load_dotenv()

# Import our custom physics and AI engines
from fft_processor import FFTProcessor
from morphology_detector import MorphologyDetector
from sam_segmenter import SAMSegmenter
from crystallography_engine import CrystallographyEngine
from physics_postprocess import AdvancedPostProcessor

# Global variables for VRAM caching
FFT_CORE = None
MATH_CORE = None
AI_CORE = None
PHYSICS_ENGINE = None
CV_POST_CORE = None

def load_models():
    global FFT_CORE, MATH_CORE, AI_CORE, PHYSICS_ENGINE, CV_POST_CORE
    if AI_CORE is not None:
        return
        
    print("Loading AI Models into VRAM...")
    FFT_CORE = FFTProcessor(low_pass_radius=50)
    AI_CORE = SAMSegmenter()
    PHYSICS_ENGINE = CrystallographyEngine()
    CV_POST_CORE = AdvancedPostProcessor(gradient_threshold=50, merge_distance_px=5)
    print("Models loaded successfully!")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load all heavy AI models into VRAM once
    load_models()
    yield
    # Shutdown: OS frees VRAM automatically

# App is created AFTER lifespan is defined to avoid NameError
app = FastAPI(title="S/TEM Physics Engine API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/g_angle")
async def get_theoretical_g_angle(g: str = "[2,0,0]", zone_axis: str = "011"):
    """
    Returns the theoretical angle (0-360°) of the g-vector on the standard
    morphological reference map. The scientist measures their actual g-vector
    angle in the image; the difference is the instrument rotation phi.
    """
    engine = CrystallographyEngine()
    angle = engine.theoretical_g_angle(g, zone_axis)
    return {"theoretical_angle_deg": round(angle, 2), "g": g, "zone_axis": zone_axis}


@app.post("/analyze")
@limiter.limit("10/minute")
async def analyze_image(
    request: Request,
    file: UploadFile,
    material: str = Form(...),
    zoneAxis: str = Form(...),
    gVector: str = Form(...),
    scale: float = Form(...),
    sensitivity: float = Form(...),
    enable_fft: str = Form("false"),
    rotationDeg: float = Form(0.0),   # NEW: instrument rotational calibration φ
):
    print(f"Received request: {material} | {zoneAxis} | {gVector} | Scale: {scale} | Sens: {sensitivity} | FFT: {enable_fft} | phi={rotationDeg}")
    
    # 1. Read Image
    contents = await file.read()
    
    MAX_UPLOAD_MB = 50
    if len(contents) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
        
    ALLOWED_MAGIC = [b'\x89PNG', b'\xff\xd8\xff', b'II*\x00', b'MM\x00*']
    if not any(contents.startswith(m) for m in ALLOWED_MAGIC):
        raise HTTPException(status_code=400, detail="Unsupported file type")
        
    nparr = np.frombuffer(contents, np.uint8)
    image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    
    scale_nm_per_pixel = 100.0 / scale if scale > 0 else None
    
    # Re-initialize Math Core with current scale and sensitivity
    MATH_CORE = MorphologyDetector(
        kernel_size=(35, 35),
        max_sigma=15,
        threshold=sensitivity,
        scale_nm_per_pixel=scale_nm_per_pixel
    )
    
    # A. FFT
    processed_image = image_bgr
    if enable_fft.lower() == "true":
        print("Applying FFT Lattice Suppression...")
        processed_image = FFT_CORE.suppress_lattice(image_bgr)
    
    # B. Morphology
    boxes, diameters = MATH_CORE.get_bounding_boxes(processed_image, return_diameters=True)
    
    # C. SAM Segments
    sam_masks = AI_CORE.generate_masks(image_rgb, boxes)
    
    # C.5 Physical Size Gate
    h_img, w_img = image_rgb.shape[:2]
    MIN_LOOP_AREA_PX = 16
    
    # Calculate physical max area (assuming max diameter is 300nm to account for UI scale errors)
    if scale_nm_per_pixel:
        # Area = pi * r^2
        max_area_nm2 = np.pi * (300.0 / 2) ** 2
        max_area_px = max_area_nm2 / (scale_nm_per_pixel ** 2)
    else:
        # Fallback to 2% of image area if no scale
        max_area_px = (h_img * w_img) * 0.02
        
    sam_masks = [
        m for m in sam_masks
        if m is not None
        and MIN_LOOP_AREA_PX <= cv2.contourArea(m) <= max_area_px
    ]
    print(f"[API] Valid SAM masks after size gate: {len(sam_masks)}")

    total_defects = 0
    perfect_count = 0
    faulted_count = 0
    total_area_nm2 = 0.0
    total_diam_nm = 0.0
    defect_list = []

    h, w = image_rgb.shape[:2]
    composite_mask = np.zeros((h, w, 4), dtype=np.float32)
    color_pink    = np.array([255/255, 105/255, 180/255, 0.85])
    color_cyan    = np.array([0/255,   255/255, 255/255, 0.85])
    color_yellow  = np.array([255/255, 230/255,   0/255, 0.95])
    color_unknown = np.array([100/255, 100/255, 100/255, 0.45])

    # ── CV Shape Analysis & Classification ─────────────────────
    MIN_LOOP_AREA_PX = 16
    for idx, contour in enumerate(sam_masks):
        if contour is None:
            continue

        area_pixels = float(cv2.contourArea(contour))
        if area_pixels < MIN_LOOP_AREA_PX:
            continue

        total_defects += 1
        area_nm = area_pixels * (scale_nm_per_pixel ** 2) if scale_nm_per_pixel else area_pixels
        total_area_nm2 += area_nm

        if scale_nm_per_pixel:
            true_diameter_nm = np.sqrt((4 * area_nm) / np.pi)
        else:
            true_diameter_nm = diameters[idx] if idx < len(diameters) else np.sqrt((4 * area_pixels) / np.pi)
        total_diam_nm += true_diameter_nm

        rect = cv2.minAreaRect(contour)
        w_rect, h_rect = rect[1]
        rect_angle = float(rect[2])

        if w_rect < h_rect:
            rect_angle += 90.0
        if rect_angle > 90.0:
            rect_angle -= 180.0
        elif rect_angle < -90.0:
            rect_angle += 180.0
        contour_angle = float(rect_angle)

        # ── WORLD CLASS SHAPE ANALYSIS: Curvature-Invariant Edge-On Gate ──
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            continue
            
        circularity = (4 * np.pi * area_pixels) / (perimeter * perimeter)
        raw_ratio = min(w_rect, h_rect) / max(w_rect, h_rect) if max(w_rect, h_rect) > 0 else 1.0
        
        # Use fitEllipse for true mathematical mass distribution (highly robust to jagged/bumpy edges)
        ellipse_ratio = raw_ratio
        if len(contour) >= 5:
            (xc, yc), (d1, d2), _ = cv2.fitEllipse(contour)
            if max(d1, d2) > 0:
                ellipse_ratio = min(d1, d2) / max(d1, d2)

        # TEM strain fields make edge-on lines look "fatter" to SAM than to the human eye.
        is_edge_on = (circularity < 0.55 or ellipse_ratio < 0.45)

        # ── WORLD CLASS PHYSICS: Phase Shift Contrast (alpha = 2pi g.R) ──
        # Measure internal contrast to see if it's a hollow ring or solid fault
        mask_2d = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(mask_2d, [contour], -1, 255, cv2.FILLED)
        
        kernel = np.ones((3, 3), np.uint8)
        core_mask = cv2.erode(mask_2d, kernel, iterations=2)
        boundary_mask = cv2.bitwise_xor(mask_2d, core_mask)
        
        # Convert to grayscale for intensity measurement
        gray_img = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        
        visual_type = "Solid" # default for very thin lines
        if cv2.countNonZero(core_mask) > 0 and cv2.countNonZero(boundary_mask) > 0:
            core_intensity = cv2.mean(gray_img, mask=core_mask)[0]
            boundary_intensity = cv2.mean(gray_img, mask=boundary_mask)[0]
            if core_intensity > boundary_intensity * 1.15:
                visual_type = "Hollow"

        # ── Run Crystallography Engine ──
        base_type = "Unknown"
        base_color = color_unknown
        
        if gVector:
            res = PHYSICS_ENGINE.solve_single_mask(
                g_vector_str=gVector,
                material_type=material,
                zone_axis_str=zoneAxis,
                box_width=w_rect,
                box_height=h_rect,
                image_rotation_deg=rotationDeg,
                loop_angle_deg=contour_angle
            )
            
            if res and "classification" in res and res["classification"] != "Unknown Physical Loop" and res["classification"] != "Invalid Shape":
                base_type = res["classification"]
                color_name = res["ui_color"]
                
                if color_name == "Cyan":
                    base_color = color_cyan
                    faulted_count += 1
                elif color_name == "Pink":
                    base_color = color_pink
                    perfect_count += 1
                elif color_name == "Yellow":
                    base_color = color_yellow
                    # Add a tiny heuristic for counting
                    if "Faulted" in base_type: faulted_count += 1
                    elif "Perfect" in base_type: perfect_count += 1
                else:
                    base_color = color_unknown
                    
                found_match = True
            else:
                found_match = False
                
            if not found_match:
                # Fallback to visual phase contrast if theoretical match fails
                if area_pixels < 50:
                    base_type = "Ambiguous (Need 2nd g-vector)"
                    base_color = color_unknown
                elif visual_type == "Hollow":
                    base_type = "1/2<110> Perfect Loop (Vis)"
                    base_color = color_pink
                    perfect_count += 1
                else:
                    base_type = "1/3<111> Faulted Loop (Vis)"
                    base_color = color_cyan
                    faulted_count += 1
        else:
            # Fallback to visual phase contrast if no g-vector provided
            if area_pixels < 50:
                base_type = "Ambiguous (Need 2nd g-vector)"
                base_color = color_unknown
            elif visual_type == "Hollow":
                base_type = "1/2<110> Perfect Loop (Vis)"
                base_color = color_pink
                perfect_count += 1
            else:
                base_type = "1/3<111> Faulted Loop (Vis)"
                base_color = color_cyan
                faulted_count += 1

        # ── Apply family color — morphology only modifies the label ──
        # METALLURGICAL RULE: The loop's family (Faulted, Perfect, <100>, 1/2<111>)
        # determines the color. Edge-On is NOT a separate color; it's an orientation label.
        # The physics engine already encoded this correctly in base_color and base_type.
        defect_type = base_type   # already contains "(Edge-On)" in the label when applicable
        color = base_color        # Cyan for Faulted/1/2<111>, Pink for Perfect/<100>

        cv2.drawContours(composite_mask, [contour], -1, color.tolist(), cv2.FILLED)

        defect_list.append({
            "type":        defect_type,
            "diameter_nm": round(float(true_diameter_nm), 2),
            "area_nm2":    round(float(area_nm), 2),
            "angle_deg":   round(contour_angle, 1),
        })


    # Overlay
    alpha = 0.5
    overlay = image_rgb.copy()
    mask_drawn = np.any(composite_mask[:, :, :3] > 0, axis=-1)
    rgb_mask = (composite_mask[:, :, :3] * 255).astype(np.uint8)
    for c in range(3):
        overlay[:, :, c] = np.where(mask_drawn, (1 - alpha) * overlay[:, :, c] + alpha * rgb_mask[:, :, c], overlay[:, :, c])
        
    # Draw Legend on the image itself
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(overlay, "Purple/Pink: Perfect Loops (1/2<110>)", (20, 40), font, 0.8, (255, 105, 180), 2, cv2.LINE_AA)
    cv2.putText(overlay, "Cyan: Faulted Loops (1/3<111>)", (20, 80), font, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(overlay, "Yellow: Edge-On", (20, 120), font, 0.8, (255, 255, 0), 2, cv2.LINE_AA)
    cv2.putText(overlay, "Gray: Unknown", (20, 160), font, 0.8, (150, 150, 150), 2, cv2.LINE_AA)

    # Convert overlay to base64
    _, buffer = cv2.imencode('.png', cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR))
    base64_img = base64.b64encode(buffer).decode('utf-8')
    data_url = f"data:image/png;base64,{base64_img}"
    
    # Calculate Aggregates
    avg_size = (total_diam_nm / total_defects) if total_defects > 0 else 0
    dom_type = "Unknown"
    if perfect_count > faulted_count:
        dom_type = "1/2<110> Perfect Loop"
    elif faulted_count > perfect_count:
        dom_type = "1/3<111> Faulted Loop"
    elif total_defects > 0:
        dom_type = "Mixed / Edge-On"

    # Density (assuming image area = scale * scale * aspect ratio)
    img_area_nm2 = (w * scale_nm_per_pixel) * (h * scale_nm_per_pixel) if scale_nm_per_pixel else 1.0
    img_area_m2 = img_area_nm2 * 1e-18
    density_m2 = (total_defects / img_area_m2) if img_area_m2 > 0 else 0
    density_str = f"{density_m2:.2e} m⁻²"
    
    results = {
        "Total Defects Detected": str(total_defects),
        "Average Diameter": f"{avg_size:.2f} nm",
        "Dominant Defect Type": dom_type,
        "Estimated Density": density_str
    }
    
    print(f"Successfully processed {total_defects} defects.")
    return {
        "status": "success",
        "data": results,
        "defects": defect_list,
        "image_data_url": data_url
    }

@app.post("/fft_spectrum")
async def get_fft_spectrum(file: UploadFile):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
    
    # Calculate True FFT Magnitude Spectrum
    f = np.fft.fft2(image)
    fshift = np.fft.fftshift(f)
    magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-8)
    
    # Normalize to 0-255 for PNG
    mag_normalized = cv2.normalize(magnitude_spectrum, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    
    # Apply colormap to make it look scientifically "cool"
    colormap = cv2.applyColorMap(mag_normalized, cv2.COLORMAP_INFERNO)
    
    _, buffer = cv2.imencode('.png', colormap)
    base64_img = base64.b64encode(buffer).decode('utf-8')
    data_url = f"data:image/png;base64,{base64_img}"
    
    return {"status": "success", "fft_data_url": data_url}

class LearnPayload(BaseModel):
    mask_b64: str

@app.post("/learn")
@limiter.limit("10/minute")
async def save_learning_data(request: Request, payload: LearnPayload):
    import time
    save_dir = Path("human_feedback")
    save_dir.mkdir(exist_ok=True)
    
    ts = int(time.time())
    try:
        mask_data = base64.b64decode(payload.mask_b64.split(",")[1] if "," in payload.mask_b64 else payload.mask_b64)
        MAX_SIZE_BYTES = 5 * 1024 * 1024
        if len(mask_data) > MAX_SIZE_BYTES:
            return {"status": "error", "message": "Payload too large"}
        if not mask_data[:8] == b'\x89PNG\r\n\x1a\n':
            return {"status": "error", "message": "Invalid image format"}
        with open(save_dir / f"correction_{ts}.png", "wb") as f:
            f.write(mask_data)
        print(f"Saved human correction to {save_dir}/correction_{ts}.png")
        return {"status": "success", "message": "Correction saved to training corpus."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/health")
async def health_check():
    """Returns backend readiness — polled by the frontend loading screen."""
    return {
        "status": "ready" if AI_CORE is not None else "loading",
        "models_loaded": AI_CORE is not None
    }

class ChatPayload(BaseModel):
    messages: list
    system_prompt: str

@app.post("/chat")
@limiter.limit("10/minute")
async def chat_nemotron(request: Request, payload: ChatPayload):
    client = OpenAI(
      base_url = "https://integrate.api.nvidia.com/v1",
      api_key = os.environ.get("NVIDIA_API_KEY")
    )

    # Insert system prompt as the first message
    api_messages = [{"role": "system", "content": payload.system_prompt}]
    for msg in payload.messages:
        role = msg.get("role", "user")
        if role == "ai":
            role = "assistant"
        api_messages.append({"role": role, "content": msg.get("text", "")})

    async def generate_stream():
        try:
            from openai import AsyncOpenAI
            aclient = AsyncOpenAI(
              base_url = "https://openrouter.ai/api/v1",
              api_key = os.environ.get("OPENROUTER_API_KEY")
            )
            completion = await aclient.chat.completions.create(
              model="nvidia/llama-3.3-nemotron-super-49b-v1.5",
              messages=api_messages,
              temperature=1,
              top_p=0.95,
              max_tokens=2048,
              stream=True
            )
            has_started_reasoning = False
            async for chunk in completion:
                if not chunk.choices:
                    continue
                
                # Stream the reasoning (thinking) process so UI doesn't hang
                reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
                if reasoning:
                    if not has_started_reasoning:
                        yield json.dumps({"response": "\n*🧠 System Core Thinking:*\n> "}) + "\n"
                        has_started_reasoning = True
                    # Formatting the thinking blocks slightly
                    formatted_reasoning = reasoning.replace("\n", "\n> ")
                    yield json.dumps({"response": formatted_reasoning}) + "\n"
                
                content = chunk.choices[0].delta.content
                if content is not None:
                    if has_started_reasoning:
                        yield json.dumps({"response": "\n\n*🟢 Response:*\n"}) + "\n"
                        has_started_reasoning = False # Reset so we don't print it again
                    yield json.dumps({"response": content}) + "\n"
        except Exception as e:
            if "404" in str(e) or "Not found for account" in str(e):
                yield json.dumps({"response": "\n\n[API Error: Your NVIDIA API key does not have access to the Nemotron models yet. Please log into build.nvidia.com and accept the Nemotron Terms of Service to unlock it!]"}) + "\n"
            else:
                logging.exception("Chat error")
                yield json.dumps({"response": "\n\n[Error: AI service temporarily unavailable. Please try again.]"}) + "\n"

    return StreamingResponse(generate_stream(), media_type="application/x-ndjson")

@app.post("/generate_synthetic")
async def generate_synthetic(
    defect_type: str = Form(...),
    noise_level: float = Form(...),
    batch_size: int = Form(10)
):
    """
    Synthesizes realistic TEM patches using mathematical noise models and physical strain fields.
    Replaces the heavy Latent Diffusion Model for real-time demonstration.
    """
    import random
    import math
    images = []
    
    # Generate requested number of images (cap at 20 for real-time demo)
    actual_batch = min(batch_size, 20)
    
    for _ in range(actual_batch):
        # 1. Base TEM background (gray)
        bg_intensity = random.randint(110, 140)
        img = np.full((256, 256), bg_intensity, dtype=np.uint8)
        
        # 2. Add Poisson/Gaussian noise based on variance
        noise = np.random.normal(0, noise_level * 50, (256, 256))
        img = np.clip(img + noise, 0, 255).astype(np.uint8)
        
        # 3. Add physical strain field (blob or line)
        center_x = random.randint(80, 176)
        center_y = random.randint(80, 176)
        
        # Edge-on vs Inclined based on defect type string
        is_edge_on = "Edge-On" in defect_type or random.random() > 0.5
        
        # Draw dark inner loop, bright outer halo (typical strain contrast)
        if is_edge_on:
            angle = random.randint(0, 180)
            length = random.randint(30, 80)
            thickness = random.randint(3, 8)
            # Halo
            cv2.ellipse(img, (center_x, center_y), (length//2 + 5, thickness//2 + 5), angle, 0, 360, bg_intensity + 40, -1)
            # Core
            cv2.ellipse(img, (center_x, center_y), (length//2, thickness//2), angle, 0, 360, bg_intensity - 60, -1)
        else:
            angle = random.randint(0, 180)
            axis1 = random.randint(20, 60)
            axis2 = int(axis1 * random.uniform(0.3, 0.9))
            thickness = random.randint(4, 12)
            # Halo
            cv2.ellipse(img, (center_x, center_y), (axis1 + 5, axis2 + 5), angle, 0, 360, bg_intensity + 30, thickness + 4)
            # Core
            cv2.ellipse(img, (center_x, center_y), (axis1, axis2), angle, 0, 360, bg_intensity - 80, thickness)
            
        # 4. Blur to simulate electron scattering
        blur_kernel = random.choice([3, 5])
        img = cv2.GaussianBlur(img, (blur_kernel, blur_kernel), 0)
        
        # 5. Convert to Base64
        _, buffer = cv2.imencode('.png', img)
        img_b64 = base64.b64encode(buffer).decode('utf-8')
        images.append(f"data:image/png;base64,{img_b64}")
        
    return {"status": "success", "images": images}

@app.get("/api/dataset")
async def get_dataset():
    """Returns the full Morphology Maps as JSON"""
    try:
        import pandas as pd
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        fcc_path = os.path.join(base_dir, "Complete_TEM_Morphology_Map.csv")
        df_fcc = pd.read_csv(fcc_path)
        df_fcc['Material'] = 'FCC'
        
        try:
            bcc_path = os.path.join(base_dir, "Complete_BCC_TEM_Morphology_Map.csv")
            df_bcc = pd.read_csv(bcc_path)
            df_bcc['Material'] = 'BCC'
            df = pd.concat([df_fcc, df_bcc], ignore_index=True)
        except Exception as e:
            print(f"Failed to load BCC dataset: {e}")
            df = df_fcc
            
        return {"status": "success", "data": df.to_dict(orient="records")}
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
