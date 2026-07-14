# compress_bc3_region

Re-encode BC3/DXT5 4×4 blocks inside an existing DDS mip0 from a full RGBA8888 buffer.
Preserves DDS byte size so `gust_g1t` repack keeps the same `.g1t` file length.

`stb_dxt.h` is vendored in this directory (original: https://raw.githubusercontent.com/nothings/stb/master/stb_dxt.h).

## Build

```bash
cd tools/compress_bc3_region_src
make
```

Or from the scripts root (also installs gust_tools):

```bash
python3 LydieAndSuelleDxRusScripts/init_tools.py
```

Output: `tools/compress_bc3_region`

## Usage

```text
compress_bc3_region <in.dds> <out.dds> <rgba.raw> <width> <height> <x0> <y0> <x1> <y1>
```

- `in.dds` — vanilla compressed DDS (e.g. g1t `000.dds`)
- `out.dds` — patched DDS (only blocks in bbox recompressed)
- `rgba.raw` — raw RGBA bytes, `width * height * 4`
- `x0,y0,x1,y1` — pixel bbox of the edited region (block-aligned internally)

Used by [`work/experiment/font_pack/pack_font_texture.py`](../../work/experiment/font_pack/pack_font_texture.py).
