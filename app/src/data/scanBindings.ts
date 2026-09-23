import extraParks from "./extraParkBindings.json";
import parkScenarios from "../../scripts/park-simulation-sites.json";
import { hasReport } from "./inventory";

type LatLng = [number, number];

export type ScanBinding = {
  parkName: string;
  pathId: string;
  pathName: string;
  scanId: string;
  polyline: LatLng[];
};

/**
 * 把掃描綁到 OSM 地點（公園或學校）。
 * parkName 必須與 taiwan_sites.json 的 name 完全相同。
 * sim* scanId 為介面示範用的模擬盤點（僅臺中；使用合成技術影像，非當地實拍）。
 * polyline 一律走陸域步道／校道，避開湖面與水域中心。
 */
export const SCAN_BINDINGS: ScanBinding[] = [
  ...extraParks as ScanBinding[],
  {
    parkName: "逢甲大學",
    pathId: "fengchia-campus-20260818",
    pathName: "校園掃描路徑（8/18 · 7-11）",
    scanId: "20260818092855",
    // 沿 OSM pedestrian 405302435 的校內通道取點；位於學思樓／
    // 土木水利館之間，終點停在學思湖以南，不以兩端直線穿越地物。
    polyline: [
      [24.181228, 120.64674],
      [24.181239, 120.64682],
      [24.18125, 120.6469],
      [24.181261, 120.64698],
      [24.18127, 120.647047],
      [24.181288, 120.647095],
      [24.181306, 120.647144],
    ],
  },
  {
    // OSM footway 82257486；日月湖東岸陸域
    parkName: "臺中公園",
    pathId: "tc-park-demo-20260327",
    pathName: "日月湖東岸轉彎（模擬）",
    scanId: "sim20260327tcp001",
    polyline: [
      [24.1429215, 120.6844633],
      [24.1429428, 120.6846849],
      [24.1434005, 120.6849347],
      [24.1435806, 120.68498],
      [24.1438965, 120.6850446],
      [24.144047, 120.6850353],
    ],
  },
  {
    parkName: "豐樂雕塑公園",
    pathId: "fengle-demo-20260328",
    pathName: "南側園道（模擬）",
    scanId: "sim20260328flp001",
    // OSM footway 396642063
    polyline: [
      [24.1305862, 120.6433833],
      [24.1303513, 120.6432904],
      [24.1301962, 120.6431591],
      [24.1300959, 120.6429857],
      [24.1300791, 120.6427296],
      [24.1301231, 120.6426061],
      [24.1301487, 120.6425588],
      [24.1304843, 120.6423948],
    ],
  },
  {
    // OSM footway 336765605；谷頂北側陸域，全程在水池以北
    parkName: "秋紅谷廣場",
    pathId: "qiuhonggu-demo-20260329",
    pathName: "北側高架步道（模擬）",
    scanId: "sim20260329qhg001",
    polyline: [
      [24.1679681, 120.6391904],
      [24.1680653, 120.639238],
      [24.1684602, 120.6391473],
      [24.1685202, 120.6391654],
      [24.1683113, 120.6392992],
      [24.1681728, 120.6393558],
      [24.1681893, 120.6395235],
      [24.1683361, 120.6395485],
    ],
  },
  {
    parkName: "文心森林公園",
    pathId: "wenxin-forest-demo-20260330",
    pathName: "北緣園道（模擬）",
    scanId: "sim20260330wxf001",
    // OSM footway 341681753
    polyline: [
      [24.1465729, 120.6457711],
      [24.1465412, 120.645595],
      [24.146419, 120.6453603],
      [24.1463361, 120.6452236],
      [24.1461508, 120.6450295],
      [24.1461211, 120.6449238],
      [24.1461137, 120.6446961],
      [24.1461341, 120.6445762],
    ],
  },
  {
    parkName: "惠來公園",
    pathId: "huilai-demo-20260331",
    pathName: "惠來路側綠帶（模擬）",
    scanId: "sim20260331hlp001",
    // OSM footway 272604159
    polyline: [
      [24.1549221, 120.6389911],
      [24.154924, 120.639422],
      [24.1549244, 120.6395033],
      [24.1551117, 120.6403102],
    ],
  },
  {
    parkName: "臺中都會公園",
    pathId: "tc-metro-demo-20260401",
    pathName: "東側主園道（模擬）",
    scanId: "sim20260401tcm001",
    // OSM footway 396402614
    polyline: [
      [24.2083553, 120.5978125],
      [24.2082881, 120.5979861],
      [24.2082187, 120.5980441],
      [24.2080482, 120.5980693],
      [24.2079673, 120.5980334],
      [24.2078606, 120.5978855],
      [24.2078477, 120.59781],
      [24.2078791, 120.5976619],
    ],
  },
  {
    parkName: "臺中中央公園",
    pathId: "tc-central-demo-20260402",
    pathName: "中央公園大道東側（模擬）",
    scanId: "sim20260402tcc001",
    // OSM footway 878658732
    polyline: [
      [24.186933, 120.6544822],
      [24.1868537, 120.6544993],
      [24.1866537, 120.6545424],
      [24.1862421, 120.6546645],
      [24.1859741, 120.6547671],
      [24.1856287, 120.6549317],
    ],
  },
  {
    parkName: "草悟道",
    pathId: "calligraphy-greenway-demo-20260403",
    pathName: "草悟道周邊人行步道（模擬）",
    scanId: "sim20260403cgw001",
    // OSM footway 272607747
    polyline: [
      [24.1532911, 120.6616905],
      [24.1532938, 120.6619348],
      [24.1532448, 120.6623465],
    ],
  },
  {
    parkName: "國立自然科學博物館",
    pathId: "nmns-demo-20260404",
    pathName: "館前廣場步道（模擬）",
    scanId: "sim20260404nmns01",
    // OSM pedestrian 937668846
    polyline: [
      [24.1579502, 120.6665146],
      [24.157774, 120.6665884],
      [24.157812, 120.66676],
      [24.1578102, 120.6667869],
      [24.1578022, 120.6669089],
      [24.1578499, 120.66698],
      [24.1580971, 120.6669116],
      [24.1578941, 120.6670459],
    ],
  },
  {
    parkName: "廍子公園",
    pathId: "buzih-demo-20260405",
    pathName: "環園步道北側（模擬）",
    scanId: "sim20260405bzp001",
    // OSM footway 377680420
    polyline: [
      [24.1681481, 120.7317008],
      [24.1682709, 120.7318354],
      [24.168355, 120.7320227],
      [24.1683982, 120.7321294],
      [24.1684437, 120.732274],
      [24.1684574, 120.7324086],
      [24.1683118, 120.7325731],
      [24.1680799, 120.732593],
    ],
  },
  {
    parkName: "黎新公園",
    pathId: "lixin-demo-20260406",
    pathName: "園區西側步道（模擬）",
    scanId: "sim20260406lxp001",
    // OSM footway 572082892
    polyline: [
      [24.153634, 120.6253431],
      [24.153607, 120.6253733],
      [24.1535875, 120.6254102],
      [24.1535532, 120.6254209],
      [24.1535189, 120.6254048],
      [24.1528067, 120.6248872],
    ],
  },
  {
    parkName: "望高寮夜景公園",
    pathId: "wanggaoliao-demo-20260407",
    pathName: "觀景平台外側步道（模擬）",
    scanId: "sim20260407wgl001",
    // OSM footway 871367733
    polyline: [
      [24.1436247, 120.5822656],
      [24.1436792, 120.5821946],
      [24.1438097, 120.5821159],
      [24.143888, 120.5821028],
      [24.1439619, 120.5821027],
      [24.1440149, 120.5821091],
      [24.1441533, 120.5822011],
      [24.1442092, 120.5822963],
    ],
  },
];

export function bindingsForPark(parkName: string, siteId?: string): ScanBinding[] {
  return SCAN_BINDINGS.filter((item) => {
    const scenario = parkScenarios.find(site => site.scanId === item.scanId);
    return item.parkName === parkName && (!siteId || !scenario || scenario.siteId === siteId);
  });
}

export function bindingHasInventory(item: ScanBinding): boolean {
  return Boolean(item.scanId) && hasReport(item.scanId);
}
