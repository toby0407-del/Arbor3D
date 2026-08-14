"""把 RayStudio 匯出的 3DGS PLY (f_rest=18, SH degree 2) 轉成 SuperSplat 可讀格式 (f_rest=45)。"""
import argparse
from pathlib import Path

import numpy as np

from .ply_io import load_ply_vertices, save_ply_vertices

SUPERSPLAT_F_REST = 45


def _sorted_f_rest_names(prefix, vertices):
    names = [n for n in vertices.dtype.names if n.startswith(prefix)]
    return sorted(names, key=lambda n: int(n.split("_")[-1]))


def convert_ply_for_supersplat(in_path, out_path):
    vertices, header_lines = load_ply_vertices(in_path)
    f_rest_names = _sorted_f_rest_names("f_rest_", vertices)
    if len(f_rest_names) == SUPERSPLAT_F_REST:
        print(f"已是 SuperSplat 格式 (f_rest={SUPERSPLAT_F_REST})，略過轉換。")
        return in_path

    if len(f_rest_names) > SUPERSPLAT_F_REST:
        raise ValueError(
            f"f_rest 數量 {len(f_rest_names)} 超過 SuperSplat 上限 {SUPERSPLAT_F_REST}"
        )

    new_fields = []
    for line in header_lines:
        if not line.startswith("property float f_rest_"):
            continue
        if line in {f"property float {n}" for n in f_rest_names}:
            new_fields.append(line)
    for i in range(len(f_rest_names), SUPERSPLAT_F_REST):
        new_fields.append(f"property float f_rest_{i}")

    new_header = []
    inserted = False
    for line in header_lines:
        if line.startswith("property float f_rest_"):
            if not inserted:
                new_header.extend(new_fields)
                inserted = True
            continue
        new_header.append(line)

    out_dtype_fields = []
    for line in new_header:
        if line.startswith("property float "):
            out_dtype_fields.append((line.split()[-1], "f4"))

    out_vertices = np.zeros(len(vertices), dtype=np.dtype(out_dtype_fields))
    for name in vertices.dtype.names:
        if name.startswith("f_rest_"):
            continue
        out_vertices[name] = vertices[name]

    for name in f_rest_names:
        out_vertices[name] = vertices[name]

    save_ply_vertices(out_path, out_vertices, new_header)
    print(f"完成：{in_path.name} -> {out_path.name}")
    print(f"   f_rest {len(f_rest_names)} -> {SUPERSPLAT_F_REST}，共 {len(out_vertices):,} 顆高斯球")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Convert 3DGS PLY for SuperSplat viewer.")
    parser.add_argument("input_ply", type=Path)
    parser.add_argument("output_ply", type=Path, nargs="?")
    args = parser.parse_args()
    out = args.output_ply or args.input_ply.with_name(
        args.input_ply.stem + "_supersplat.ply"
    )
    convert_ply_for_supersplat(args.input_ply, out)


if __name__ == "__main__":
    main()
