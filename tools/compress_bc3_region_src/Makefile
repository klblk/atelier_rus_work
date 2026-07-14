CC ?= cc
CFLAGS ?= -O2
LDFLAGS ?= -lm

OUT = ../compress_bc3_region

all: $(OUT)

$(OUT): compress_bc3_region.c stb_dxt.h
	$(CC) $(CFLAGS) -o $(OUT) compress_bc3_region.c $(LDFLAGS)

clean:
	rm -f $(OUT)

.PHONY: all clean
