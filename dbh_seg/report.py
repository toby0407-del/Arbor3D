"""Report candidate dimensions separately from accepted measurements."""

def report_dbh(result):
    quality = result.quality or {}
    accepted = quality.get("decision") == "accepted"
    print(f"   方法：{result.method}；候選尺寸 {result.dbh_m * 100:.1f} cm")
    print("   正式量測可採用" if accepted else "   尚未通過品質門檻：此尺寸僅供查驗，不是正式 DBH")
    if quality.get("probability") is not None:
        print(f"   校準達標機率：{quality['probability']:.3f}")
    if quality.get("reasons"):
        print("   複核原因：" + ", ".join(quality["reasons"]))
    return result.dbh_m
