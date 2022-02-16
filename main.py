import os
from PIL import Image, ImageOps
from io import BytesIO
import aiohttp
from quart import Quart, send_file
from hashlib import sha256

assets_dir = os.path.dirname(__file__) + "/assets"
base_normal = Image.open(assets_dir + "/background-base.png")
mask_img = Image.open(assets_dir + "/mask.png").convert("L")
side_mask = Image.open(assets_dir + "/side-mask.png")
dot_tile = Image.open(assets_dir + "/dot-tilea.png")


def get_asset_hash():
    sha = sha256()
    with open(assets_dir + "/background-base.png", "rb") as f:
        sha.update(f.read())
    with open(assets_dir + "/mask.png", "rb") as f:
        sha.update(f.read())
    with open(assets_dir + "/side-mask.png", "rb") as f:
        sha.update(f.read())
    with open(assets_dir + "/dot-tilea.png", "rb") as f:
        sha.update(f.read())
    return sha.hexdigest()


def alpha(img, al):
    imga = img.copy()
    imga.putalpha(round(255 * al))
    return imga


class Deformer:
    def __init__(self, dist):
        self.dist = dist

    def getmesh(self, im):
        return [((0, 0, *im.size), self.dist)]


app = Quart(__name__)
SUPPORTED_FORMATS = ["png", "jpg", "jpeg", "webp"]


@app.post("/generate/<string:target>")
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
    if os.path.exists(f"dist/{name}-{get_asset_hash()}.{ext}"):
        print("Already exists, using cached version")
    elif os.path.exists(f"dist/{name}-{get_asset_hash()}.png"):
        print("Already exists, converting from png")
        im = Image.open(f"dist/{name}-{get_asset_hash()}.png").convert("RGB")
        im.save(f"dist/{name}-{get_asset_hash()}.{ext}")
    else:
        print("Generating...")
        base_name = name.removesuffix(".extra")
        url = f"https://servers.purplepalette.net/repository/{base_name}/cover.png"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.read()
                jacket = Image.open(BytesIO(data))
        jacket.convert("RGBA")
        base = base_normal.copy().convert("RGBA")
        base2 = Image.new("RGBA", base.size, (0, 0, 0, 0))
        base3 = Image.new("RGBA", base.size, (0, 0, 0, 0))
        shift = -30
        base3.paste(
            alpha(
                ImageOps.deform(
                    jacket,
                    deformer=Deformer(
                        (0, 0, 0, jacket.height, jacket.width, jacket.height - shift * 2, jacket.width, -shift * 2)
                    ),
                ).resize((650, 650)),
                0.8,
            ),
            (461, 135),
        )
        base3.paste(
            alpha(
                ImageOps.deform(
                    jacket,
                    deformer=Deformer(
                        (0, 0, 0, jacket.height, jacket.width, jacket.height - shift * 2, jacket.width, -shift * 2)
                    ),
                ).resize((700, 700)),
                0.8,
            ),
            (939, 80),
        )
        shift = 10
        base2.paste(
            alpha(
                ImageOps.deform(
                    jacket,
                    deformer=Deformer(
                        (0, 0, -shift, jacket.height, jacket.width + shift, jacket.height, jacket.width, 0)
                    ),
                ).resize((470, 450)),
                0.8,
            ),
            (787, 189),
        )
        base2.paste(
            alpha(
                ImageOps.deform(
                    jacket,
                    deformer=Deformer(
                        (0, jacket.height, -shift, 0, jacket.width + shift, 0, jacket.width, jacket.height)
                    ),
                ).resize((450, 450)),
                0.7,
            ),
            (797, 683),
        )

        # base.save(dir + f"/../dist/bg/{name}.png")
        # base.paste(base2, (0, 0), mask=mask_img)
        buffer = Image.alpha_composite(base, base2)
        buffer.paste(base3, (0, 0), mask=side_mask)
        buffer = Image.alpha_composite(buffer, dot_tile)
        res = Image.new("RGBA", mask_img.size)
        diff = (buffer.height - mask_img.height) // 2
        # print(buffer.crop((0, diff, base.width, base.height - diff)).size, mask_img.size)
        res.paste(base.crop((0, diff, base.width, base.height - diff - 1)), (0, 0))
        res.paste(buffer.crop((0, diff, base.width, base.height - diff - 1)), (0, 0), mask=mask_img)
        res = res.convert("RGB")
        res.save(f"dist/{name}-{get_asset_hash()}.png")
        if ext != "png":
            res.save(f"dist/{name}-{get_asset_hash()}.{ext}")

    return await send_file(
        f"dist/{name}-{get_asset_hash()}.{ext}",
    )


if __name__ == "__main__":
    app.run(port=os.environ.get("PORT", 5000), debug=True)
