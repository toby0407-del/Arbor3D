import fs from "node:fs";

const text = fs.readFileSync("src/data/scanBindings.ts", "utf8");
const parks = {
  秋紅谷廣場: [24.1660249, 24.1687229, 120.6380189, 120.6400909],
  臺中公園: [24.1425215, 24.1461027, 120.6820503, 120.6860558],
  文心森林公園: [24.1440, 24.1470, 120.6430, 120.6470],
  豐樂雕塑公園: [24.1290, 24.1330, 120.6405, 120.6450],
  臺中中央公園: [24.1820, 24.1920, 120.6480, 120.6580],
  臺中都會公園: [24.2040, 24.2120, 120.5940, 120.6020],
};

const re = /parkName: "([^"]+)"[\s\S]*?polyline: \[([\s\S]*?)\]\s*,?\s*\}/g;
let m;
while ((m = re.exec(text))) {
  const name = m[1];
  const bbox = parks[name];
  if (!bbox) continue;
  const pts = [...m[2].matchAll(/\[([\d.]+),\s*([\d.]+)\]/g)].map((x) => [
    Number(x[1]),
    Number(x[2]),
  ]);
  const [s, n, w, e] = bbox;
  const outside = pts.filter(
    ([lat, lng]) => lat < s || lat > n || lng < w || lng > e,
  );
  let bends = 0;
  for (let i = 1; i < pts.length - 1; i++) {
    const a = [pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]];
    const b = [pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]];
    if (Math.abs(a[0] * b[1] - a[1] * b[0]) > 1e-12) bends += 1;
  }
  console.log(
    `${name}: pts=${pts.length} outside=${outside.length} bends=${bends}`,
  );
}
