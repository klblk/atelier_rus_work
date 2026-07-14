// Compress a rectangular region of an RGBA8888 image into BC3/DXT5 blocks
// inside an existing DDS file (mip0 only, linear block order).
#define STB_DXT_IMPLEMENTATION
#include "stb_dxt.h"

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#pragma pack(push, 1)
typedef struct {
    uint32_t magic;
    uint32_t size;
    uint32_t flags;
    uint32_t height;
    uint32_t width;
    uint32_t pitch;
    uint32_t depth;
    uint32_t mipmaps;
    uint32_t reserved[11];
    struct {
        uint32_t size;
        uint32_t flags;
        uint32_t fourcc;
        uint32_t rgb_bit_count;
        uint32_t r_mask, g_mask, b_mask, a_mask;
    } pf;
    uint32_t caps[4];
} DDSHeader;
#pragma pack(pop)

static void rgba_to_block(
    const uint8_t *rgba,
    int stride,
    int x,
    int y,
    uint8_t block[16][4]
) {
    for (int j = 0; j < 4; j++) {
        for (int i = 0; i < 4; i++) {
            const uint8_t *p = rgba + (y + j) * stride + (x + i) * 4;
            block[j * 4 + i][0] = p[0];
            block[j * 4 + i][1] = p[1];
            block[j * 4 + i][2] = p[2];
            block[j * 4 + i][3] = p[3];
        }
    }
}

int main(int argc, char **argv) {
    if (argc != 10) {
        fprintf(
            stderr,
            "usage: %s in.dds out.dds rgba.raw width height x0 y0 x1 y1\n",
            argv[0]
        );
        return 2;
    }
    const char *in_path = argv[1];
    const char *out_path = argv[2];
    const char *rgba_path = argv[3];
    int width = atoi(argv[4]);
    int height = atoi(argv[5]);
    int x0 = atoi(argv[6]);
    int y0 = atoi(argv[7]);
    int x1 = atoi(argv[8]);
    int y1 = atoi(argv[9]);
    (void)width;
    (void)height;

    FILE *fin = fopen(in_path, "rb");
    FILE *frgba = fopen(rgba_path, "rb");
    if (!fin || !frgba) {
        perror("open");
        return 1;
    }
    fseek(fin, 0, SEEK_END);
    long dds_size = ftell(fin);
    fseek(fin, 0, SEEK_SET);
    uint8_t *dds = malloc(dds_size);
    if (!dds || fread(dds, 1, dds_size, fin) != (size_t)dds_size) {
        fprintf(stderr, "read dds failed\n");
        return 1;
    }
    fclose(fin);

    DDSHeader *hdr = (DDSHeader *)dds;
    if (hdr->magic != 0x20534444) {
        fprintf(stderr, "not DDS\n");
        return 1;
    }
    int W = (int)hdr->width;
    int H = (int)hdr->height;
    size_t rgba_size = (size_t)W * H * 4;
    uint8_t *rgba = malloc(rgba_size);
    if (!rgba || fread(rgba, 1, rgba_size, frgba) != rgba_size) {
        fprintf(stderr, "read rgba failed\n");
        return 1;
    }
    fclose(frgba);

    int bx0 = x0 / 4, by0 = y0 / 4;
    int bx1 = (x1 + 3) / 4, by1 = (y1 + 3) / 4;
    int blocks_w = (W + 3) / 4;
    uint8_t block_rgba[16][4];
    uint8_t compressed[16];

    for (int by = by0; by < by1; by++) {
        for (int bx = bx0; bx < bx1; bx++) {
            int px = bx * 4;
            int py = by * 4;
            rgba_to_block(rgba, W * 4, px, py, block_rgba);
            stb_compress_dxt_block(compressed, &block_rgba[0][0], 1, STB_DXT_NORMAL);
            size_t off = 128 + (size_t)(by * blocks_w + bx) * 16;
            memcpy(dds + off, compressed, 16);
        }
    }

    FILE *fout = fopen(out_path, "wb");
    if (!fout || fwrite(dds, 1, dds_size, fout) != (size_t)dds_size) {
        perror("write");
        return 1;
    }
    fclose(fout);
    free(rgba);
    free(dds);
    return 0;
}
