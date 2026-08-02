from dataclasses import dataclass

@dataclass
class TPLHeader:
    magic: int
    image_count: int
    image_table_offset: int

    def __repr__(self) -> str:
        return (
            f"TPLHeader(magic=0x{self.magic:08X}, "
            f"image_count={self.image_count}, "
            f"image_table_offset=0x{self.image_table_offset:08X})"
        )
    
@dataclass
class TPLPalHeader:
    count: int
    format: int
    #data_addr -> moved to serialization logic to re-use for encoding
    data: bytes
    data_addr: int = 0

@dataclass
class TPLImage:
    index: int

    width: int
    height: int
    format: int

    #data_addr -> moved to serialization logic to re-use for encoding
    raw_data: bytes

    wrap_s: int
    wrap_t: int
    min_filter: int
    mag_filter: int
    lod_bias: float
    edge_lod_enable: int
    min_lod: int
    max_lod: int
    
    data_addr: int = 0
    palette_addr: int | None = None
    palette: TPLPalHeader | None = None

    def __repr__(self) -> str:
        # intentionally omit raw_data / palette_data (huge)
        raw_len = len(self.raw_data) if self.raw_data is not None else 0
        pal_len = len(self.palette.data) if self.palette else 0

        return (
            "TPLImage("
            f"index={self.index}, "
            f"{self.width}x{self.height}, "
            f"format=0x{self.format:02X}, "
            f"data_addr=0x{self.data_addr:08X}, "
            f"raw_bytes={raw_len}, "
            f"wrap_s={self.wrap_s}, wrap_t={self.wrap_t}, "
            f"min_filter={self.min_filter}, mag_filter={self.mag_filter}, "
            f"lod_bias={self.lod_bias}, edge_lod_enable={self.edge_lod_enable}, "
            f"min_lod={self.min_lod}, max_lod={self.max_lod}, "
            f"palette_addr={None if self.palette_addr is None else f'0x{self.palette_addr:08X}'}, "
            f"palette_bytes={pal_len}"
            ")"
        )