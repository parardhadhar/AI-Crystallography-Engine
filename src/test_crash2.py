import cv2
from api_server import analyze_image
import asyncio

image_bgr = cv2.imread(r'C:\Users\Parardha\.gemini\antigravity-ide\brain\1f3c9d96-275c-46f6-8146-0e85a9a14221\final_cryst_23.tif')
_, buf = cv2.imencode('.tif', image_bgr)

class FakeUploadFile:
    def __init__(self, buf):
        self.buf = buf.tobytes()
    async def read(self):
        return self.buf

async def main():
    try:
        res = await analyze_image(
            file=FakeUploadFile(buf),
            material="Iron",
            zoneAxis="011",
            gVector="[2,0,0]",
            scale=120.0,
            sensitivity=0.1,
            enable_fft="false",
            rotationDeg=0.0
        )
        print("Analyze image returned successfully!")
    except Exception as e:
        print(f"Caught python exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
