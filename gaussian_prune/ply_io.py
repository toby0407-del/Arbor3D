"""通用的 3D Gaussian Splatting 二進位 PLY 讀寫工具。

跟一般點雲的 PLY 不一樣，3DGS 的 PLY 除了 x/y/z 之外還有球諧函數係數
(f_dc_*, f_rest_*)、透明度 (opacity)、縮放 (scale_*)、旋轉四元數 (rot_*)
等好幾十個欄位。用 Open3D 讀寫會把這些欄位全部弄丟，所以這裡直接用
NumPy 手動解析二進位 PLY 的 header + 結構化陣列，讀寫都完整保留每一個
欄位，才能確保刪減完的檔案還能被 RayStudio 等 3DGS 檢視器正常打開。

只支援單一 vertex 元素的 binary_little_endian PLY (3DGS 模型的標準格式，
沒有 face 元素)，這已經涵蓋 RayStudio / 官方 gaussian-splatting 匯出的檔案。
"""
import numpy as np

_TYPE_MAP = {
    "float": "f4", "float32": "f4",
    "double": "f8", "float64": "f8",
    "uchar": "u1", "uint8": "u1", "char": "i1", "int8": "i1",
    "short": "i2", "int16": "i2", "ushort": "u2", "uint16": "u2",
    "int": "i4", "int32": "i4", "uint": "u4", "uint32": "u4",
}


def load_ply_vertices(ply_path):
    """讀取二進位 PLY，回傳 (structured numpy array, header_lines)。

    header_lines 是原始 header 的每一行文字，寫回檔案時只需要更新其中
    "element vertex" 那一行的點數，其餘 (格式、comment、每個屬性的宣告
    順序) 完全原封不動，確保輸出檔案的欄位結構跟原檔一致。
    """
    with open(str(ply_path), "rb") as f:
        header_lines = []
        while True:
            line = f.readline()
            if not line:
                raise ValueError(f"PLY 檔案沒有找到 end_header: {ply_path}")
            text = line.decode("ascii", errors="strict").rstrip("\r\n")
            header_lines.append(text)
            if text == "end_header":
                break
        binary_payload = f.read()

    if not any(line.startswith("format binary_little_endian") for line in header_lines):
        raise ValueError("目前只支援 binary_little_endian 格式的 3DGS PLY")

    vertex_count = None
    current_element = None
    fields = []
    for line in header_lines:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "element":
            current_element = parts[1]
            if current_element == "vertex":
                vertex_count = int(parts[2])
        elif parts[0] == "property" and current_element == "vertex":
            type_name, prop_name = parts[1], parts[2]
            if type_name not in _TYPE_MAP:
                raise ValueError(f"不支援的 PLY 屬性型別: {type_name}")
            fields.append((prop_name, _TYPE_MAP[type_name]))

    if vertex_count is None:
        raise ValueError(f"PLY header 沒有 'element vertex': {ply_path}")

    dtype = np.dtype(fields)
    vertices = np.frombuffer(binary_payload, dtype=dtype, count=vertex_count)
    return vertices, header_lines


def save_ply_vertices(out_path, vertices, header_lines):
    """把篩選過的 vertices 寫成新的 PLY，header 沿用原檔，只更新點數。"""
    new_header = []
    for line in header_lines:
        if line.startswith("element vertex"):
            new_header.append(f"element vertex {len(vertices)}")
        else:
            new_header.append(line)

    with open(str(out_path), "wb") as f:
        f.write(("\n".join(new_header) + "\n").encode("ascii"))
        f.write(vertices.tobytes())
