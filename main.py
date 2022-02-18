import asyncio
import os
from PIL import Image
from io import BytesIO
import aiohttp
from quart import Quart, send_file
import pjsekai_background_gen_pillow as pjbg

app = Quart(__name__)
SUPPORTED_FORMATS = ["png", "jpg", "jpeg", "webp"]
generator: pjbg.Generator = pjbg.Generator()


@app.get("/")
async def index():
    return {
        "message": "Hi there! This is a web service for generating a custom background image"
        + " like PJSekai from SweetPotato level.\n",
        "api": [
            {
                "method": "POST",
                "path": "/generate/:target_level_id",
                "params": {
                    ":target_level_id": "The level ID of the image you want to generate. "
                    + "You can add extensions to this ID to get a different image format. Supported extensions are: "
                    + ", ".join(SUPPORTED_FORMATS)
                },
            }
        ],
        "repo": "https://github.com/sevenc-nanashi/SP-imgserver",
    }


@app.route("/generate/<string:target>", methods=["GET", "POST"])
async def generate(target: str):
    if "." not in target:
        target += ".png"
    name = target.split(".")[0]
    ext = target.split(".")[1]
    if ext not in SUPPORTED_FORMATS:
        return {
            "message": "Unsupported format",
            "supported": SUPPORTED_FORMATS,
        }, 400
    if os.path.exists(f"dist/{name}.{ext}"):
        print("Already exists, using cached version")
    elif os.path.exists(f"dist/{name}.png"):
        print("Already exists with png, converting from png")
        im = Image.open(f"dist/{name}.png").convert("RGB")
        im.save(f"dist/{name}.{ext}")
    else:
        print("Generating...")
        base_name = name.removesuffix(".extra")
        url = f"https://servers.purplepalette.net/repository/{base_name}/cover.png"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return {
                        "message": "Failed to download cover image",
                    }, 404
                data = await resp.read()
                jacket = Image.open(BytesIO(data))
        loop = asyncio.get_event_loop()
        res = (await loop.run_in_executor(None, generator.generate, jacket))
        res.save(f"dist/{name}.png")
        if ext != "png":
            res.save(f"dist/{name}.{ext}")

    return await send_file(
        f"dist/{name}.{ext}",
    )


if __name__ == "__main__":
    app.run(port=os.environ.get("PORT", 5000), debug=True)
