import asyncio
from hashlib import sha256
import io
import os
from PIL import Image
from io import BytesIO
import aiohttp
from quart import Quart, request, send_file
import pjsekai_background_gen_pillow as pjbg

app = Quart(__name__)
SUPPORTED_FORMATS = ["png", "jpg", "jpeg", "webp"]
generator: pjbg.Generator = pjbg.Generator()
extra_generator: pjbg.Generator = pjbg.Generator(Image.open("./background-base-extra.png"))


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
async def generate_swpt(target: str):
    if "." not in target:
        target += ".png"
    name = target.split(".")[0]
    ext = target.split(".")[-1]
    uniq = name
    if not name.startswith("l_"):
        async with aiohttp.ClientSession() as session:
            if target.startswith("official-"):
                official_name = name.split("-")[2].split(".")[0]
                uniq = "official-" + official_name
            else:
                async with session.get(f"https://servers.purplepalette.net/levels/{name}") as resp:
                    if resp.status == 404:
                        return {
                            "error": f"Level {name} not found. Please check the level ID and try again."
                        }, 404
                    uniq = (await resp.json())["item"]["cover"]["hash"]
    extra = request.args.get("extra") == "true"
    if extra:
        uniq += "-extra"
    if ext not in SUPPORTED_FORMATS:
        return {
            "message": "Unsupported format",
            "supported": SUPPORTED_FORMATS,
        }, 400
    if os.path.exists(f"dist/{uniq}.{ext}"):
        print("Already exists, using cached version")
    elif os.path.exists(f"dist/{uniq}.png"):
        print("Already exists with png, converting from png")
        im = Image.open(f"dist/{uniq}.png").convert("RGB")
        im.save(f"dist/{uniq}.{ext}")
    else:
        print("Generating...")
        base_name = name.removesuffix(".extra")
        if name.startswith("l_"):
            url = f"https://PurplePalette.github.io/sonolus/repository/levels/{name[2:].replace(' ', '%20')}/jacket.jpg"
        elif name.startswith("official-"):
            url = f"https://sekai-res.dnaroma.eu/file/sekai-assets/music/jacket/jacket_s_{official_name:0>3}_rip/jacket_s_{official_name:0>3}.png"
        else:
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
        if extra:
            gen = extra_generator
        else:
            gen = generator
        res = await loop.run_in_executor(None, gen.generate, jacket)
        res.save(f"dist/{uniq}.png")
        if ext != "png":
            res.save(f"dist/{uniq}.{ext}")

    return await send_file(
        f"dist/{uniq}.{ext}",
    )


@app.route("/generate", methods=["POST"])
async def generate():
    if (post_file := (await request.files).get("file")):
        file = post_file.file
    elif await request.data:
        file = io.BytesIO(await request.data)
    else:
        return {
            "message": "No file were uploaded"
        }, 400
    ext = request.args.get("ext", "png")
    if ext not in SUPPORTED_FORMATS:
        return {
            "message": "Unsupported format",
            "supported": SUPPORTED_FORMATS,
        }, 400
    extra = request.args.get("extra") == "true"
    uniq = sha256(file.read()).hexdigest()
    if extra:
        uniq += "-extra"

    if os.path.exists(f"dist/{uniq}.{ext}"):
        print("Already exists, using cached version")
    elif os.path.exists(f"dist/{uniq}.png"):
        print("Already exists with png, converting from png")
        im = Image.open(f"dist/{uniq}.png").convert("RGB")
        im.save(f"dist/{uniq}.{ext}")
    else:
        print("Generating...")
        jacket = Image.open(file)
        loop = asyncio.get_event_loop()
        if extra:
            gen = extra_generator
        else:
            gen = generator
        res = await loop.run_in_executor(None, gen.generate, jacket)
        res.save(f"dist/{uniq}.png")
        if ext != "png":
            res.save(f"dist/{uniq}.{ext}")

    return await send_file(
        f"dist/{uniq}.{ext}",
    )


if __name__ == "__main__":
    app.run(port=os.environ.get("PORT", 5000), debug=True)
